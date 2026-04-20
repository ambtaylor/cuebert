"""MCP tool: evaluate /asset pipeline guards (manifest, PNG, ComfyUI, scope)."""

from __future__ import annotations

import importlib.util
import logging
import os
from collections import Counter
from pathlib import Path
from types import ModuleType
from typing import Any

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

_gc_mod_cache: ModuleType | None = None


def _hub_root_from_here() -> Path:
    return Path(__file__).resolve().parents[4]


def _load_guard_common() -> ModuleType:
    path = _hub_root_from_here() / ".cursor/skills/play-guards/tools/_guard_common.py"
    if not path.is_file():
        raise FileNotFoundError(f"missing shared guard common: {path}")
    name = "cuebert_play_guard_common_asset"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"spec failed for {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _gc() -> ModuleType:
    global _gc_mod_cache
    if _gc_mod_cache is None:
        _gc_mod_cache = _load_guard_common()
    return _gc_mod_cache


def default_asset_guards_config_path() -> Path:
    return _gc().find_hub_root() / ".cuebert" / "config" / "asset-guards.yaml"


def _guard_row(
    guard_id: str,
    name: str,
    status: str,
    severity: str,
    detail: str,
    evidence_path: str | None = None,
) -> dict[str, Any]:
    return {
        "guard_id": guard_id,
        "name": name,
        "status": status,
        "severity": severity,
        "detail": detail,
        "evidence_path": evidence_path,
    }


def _max_bytes_from_config(cfg: dict[str, Any]) -> int:
    guards = cfg.get("guards") or {}
    gen = guards.get("guard.generate.file_size_sane") if isinstance(guards, dict) else None
    if isinstance(gen, dict):
        th = gen.get("threshold") or {}
        if isinstance(th, dict) and th.get("warn_bytes_max"):
            try:
                return int(th["warn_bytes_max"])
            except (TypeError, ValueError):
                pass
    return 50 * 1024 * 1024


def _content_prefix(engine: str) -> str | None:
    e = (engine or "unreal").strip().lower()
    if e == "unity":
        return "Assets/"
    if e == "godot":
        return None
    return "Content/"


def _comfyui_health_envelope() -> dict[str, Any]:
    try:
        gc = _gc()
        mod = gc.import_skill_tool_module("comfyui-toolkit", "comfyui_health_check")
        fn = getattr(mod, "comfyui_health_check", None)
        if callable(fn):
            return fn()
    except ImportError as exc:
        return {"status": "import_error", "error": str(exc)}
    try:
        client = gc.import_skill_tool_module("comfyui-toolkit", "_comfyui_client")
    except ImportError as exc:
        return {"status": "import_error", "error": str(exc)}
    health_probe = getattr(client, "health_probe", None)
    resolve_base = getattr(client, "_resolve_base_url", None)
    resolve_timeout = getattr(client, "_resolve_timeout", None)
    get_mode = getattr(client, "_get_mode", None)
    is_configured = getattr(client, "_is_comfyui_configured", None)
    get_explicit = getattr(client, "_get_mode_explicit", None)
    if not all(callable(x) for x in (health_probe, resolve_base, resolve_timeout, get_mode)):
        return {"status": "error", "error": "comfyui client incomplete"}
    base_url = resolve_base()
    configured = bool(is_configured()) if callable(is_configured) else False
    explicit_mode = get_explicit() if callable(get_explicit) else None
    effective_mode = get_mode()
    if not configured:
        if explicit_mode == "dry_run":
            probe = health_probe(base_url, resolve_timeout())
            return {
                "status": "dry_run",
                "base_url": base_url,
                "mode": "dry_run",
                "version": probe.get("version") or "dry_run",
                "queue_remaining": probe.get("queue_remaining", 0),
                "error": None,
            }
        return {
            "status": "not_configured",
            "base_url": base_url,
            "mode": effective_mode,
            "version": None,
            "queue_remaining": None,
            "error": "ComfyUI base URL not configured",
        }
    if effective_mode == "dry_run":
        probe = health_probe(base_url, resolve_timeout())
        return {
            "status": "dry_run",
            "base_url": base_url,
            "mode": "dry_run",
            "version": probe.get("version"),
            "queue_remaining": probe.get("queue_remaining", 0),
            "error": None,
        }
    probe = health_probe(base_url, resolve_timeout())
    if probe.get("reachable"):
        return {
            "status": "ok",
            "base_url": base_url,
            "mode": "live",
            "version": probe.get("version"),
            "queue_remaining": probe.get("queue_remaining", 0),
            "error": None,
        }
    return {
        "status": "unreachable",
        "base_url": base_url,
        "mode": "live",
        "version": probe.get("version"),
        "error": probe.get("error"),
    }


def asset_guard_evaluate(
    project_path: str,
    manifest_path: str | None = None,
    generated_files: list[str] | None = None,
    config_path: str | None = None,
    caller: str = "user-direct-debug",
) -> dict[str, Any]:
    """Evaluate asset pipeline guards for *project_path* and optional manifest / outputs."""
    _ = caller
    gc = _gc()
    cfg_p = config_path or str(default_asset_guards_config_path())
    yaml_cfg = gc._load_yaml_config(cfg_p)
    max_b = _max_bytes_from_config(yaml_cfg)
    mode = gc._resolve_mode()

    root = Path(project_path).expanduser().resolve(strict=False)
    results: list[dict[str, Any]] = []
    manifest_data: dict[str, Any] = {}
    engine = "unreal"

    # asset.manifest_valid
    if not manifest_path:
        results.append(
            _guard_row(
                "asset.manifest_valid",
                "manifest_valid",
                "skip",
                "info",
                "no manifest_path provided",
                None,
            )
        )
    else:
        try:
            mp = gc._validate_path(manifest_path, root)
        except ValueError:
            try:
                mp = Path(manifest_path).expanduser().resolve(strict=False)
            except (OSError, RuntimeError):
                mp = Path(manifest_path)
        if not mp.is_file():
            results.append(
                _guard_row(
                    "asset.manifest_valid",
                    "manifest_valid",
                    "fail",
                    "reject",
                    f"manifest not found: {mp}",
                    str(mp),
                )
            )
        else:
            raw = gc._load_yaml_config(mp)
            ok = (
                isinstance(raw.get("version"), int)
                and isinstance(raw.get("assets"), list)
                and len(raw["assets"]) > 0
            )
            if ok:
                manifest_data = raw
                engine = str(raw.get("engine") or "unreal")
                results.append(
                    _guard_row(
                        "asset.manifest_valid",
                        "manifest_valid",
                        "pass",
                        "info",
                        "manifest has version and non-empty assets",
                        str(mp),
                    )
                )
            else:
                results.append(
                    _guard_row(
                        "asset.manifest_valid",
                        "manifest_valid",
                        "fail",
                        "reject",
                        "manifest missing version or assets[]",
                        str(mp),
                    )
                )

    assets_list = manifest_data.get("assets") if isinstance(manifest_data.get("assets"), list) else []

    # asset.duplicate_check
    dests = [
        str(a.get("destination", ""))
        for a in assets_list
        if isinstance(a, dict) and a.get("destination")
    ]
    if dests:
        c = Counter(dests)
        dups = [d for d, n in c.items() if n > 1]
        if dups:
            results.append(
                _guard_row(
                    "asset.duplicate_check",
                    "duplicate_check",
                    "fail",
                    "reject",
                    "duplicate destinations: " + ", ".join(dups[:20]),
                    manifest_path,
                )
            )
        else:
            results.append(
                _guard_row(
                    "asset.duplicate_check",
                    "duplicate_check",
                    "pass",
                    "info",
                    "no duplicate destination paths",
                    manifest_path,
                )
            )
    else:
        results.append(
            _guard_row(
                "asset.duplicate_check",
                "duplicate_check",
                "skip",
                "info",
                "no destinations to compare",
                None,
            )
        )

    # asset.destination_writable
    if dests:
        bad: list[str] = []
        for d in dests:
            p = (root / d).resolve(strict=False)
            try:
                p.relative_to(root)
            except ValueError:
                bad.append(f"{d} (outside project)")
                continue
            parent = p.parent
            try:
                parent.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                bad.append(f"{d} (mkdir: {exc})")
                continue
            if not os.access(parent, os.W_OK):
                bad.append(f"{d} (parent not writable)")
        if bad:
            results.append(
                _guard_row(
                    "asset.destination_writable",
                    "destination_writable",
                    "fail",
                    "reject",
                    "; ".join(bad[:15]),
                    str(root),
                )
            )
        else:
            results.append(
                _guard_row(
                    "asset.destination_writable",
                    "destination_writable",
                    "pass",
                    "info",
                    "destination parent directories exist and are writable",
                    str(root),
                )
            )
    else:
        results.append(
            _guard_row(
                "asset.destination_writable",
                "destination_writable",
                "skip",
                "info",
                "no manifest destinations",
                None,
            )
        )

    # asset.scope_containment
    prefix = _content_prefix(engine)
    if dests:
        oob: list[str] = []
        for d in dests:
            norm = str(d).replace("\\", "/").lstrip("./")
            if ".." in norm.split("/"):
                oob.append(d)
                continue
            if prefix is None:
                continue
            if not norm.startswith(prefix):
                oob.append(d)
        if oob:
            msg = (
                f"destinations not under {prefix}: "
                if prefix
                else "invalid destination paths: "
            )
            results.append(
                _guard_row(
                    "asset.scope_containment",
                    "scope_containment",
                    "fail",
                    "reject",
                    msg + ", ".join(oob[:20]),
                    str(root),
                )
            )
        else:
            ok_msg = (
                f"all destinations under {prefix}"
                if prefix
                else "all destinations project-relative (godot)"
            )
            results.append(
                _guard_row(
                    "asset.scope_containment",
                    "scope_containment",
                    "pass",
                    "info",
                    ok_msg,
                    str(root),
                )
            )
    else:
        results.append(
            _guard_row(
                "asset.scope_containment",
                "scope_containment",
                "skip",
                "info",
                "no destinations for scope check",
                None,
            )
        )

    # asset.format_check + asset.size_limit (generated_files)
    gen = generated_files or []
    if not gen:
        results.append(
            _guard_row("asset.format_check", "format_check", "skip", "info", "no generated_files", None)
        )
        results.append(
            _guard_row("asset.size_limit", "size_limit", "skip", "info", "no generated_files", None)
        )
        results.append(
            _guard_row(
                "asset.dimensions_match",
                "dimensions_match",
                "skip",
                "info",
                "no generated_files",
                None,
            )
        )
    else:
        fmt_bad: list[str] = []
        size_bad: list[str] = []
        for gf in gen:
            if not gf:
                continue
            try:
                fp = gc._validate_path(gf, root)
            except ValueError:
                fp = Path(gf).expanduser().resolve(strict=False)
            if not fp.is_file():
                fmt_bad.append(f"{gf} (missing)")
                continue
            try:
                sz = fp.stat().st_size
            except OSError:
                size_bad.append(f"{gf} (stat failed)")
                continue
            if sz > max_b:
                size_bad.append(f"{gf} ({sz} bytes > {max_b})")
            try:
                head = fp.read_bytes()[:8]
            except OSError:
                fmt_bad.append(f"{gf} (read failed)")
                continue
            if head != _PNG_MAGIC:
                fmt_bad.append(f"{gf} (not PNG magic)")
        if fmt_bad:
            results.append(
                _guard_row(
                    "asset.format_check",
                    "format_check",
                    "fail",
                    "reject",
                    "; ".join(fmt_bad[:12]),
                    str(root),
                )
            )
        else:
            results.append(
                _guard_row(
                    "asset.format_check",
                    "format_check",
                    "pass",
                    "info",
                    "PNG magic bytes verified for generated files",
                    str(root),
                )
            )
        if size_bad:
            results.append(
                _guard_row(
                    "asset.size_limit",
                    "size_limit",
                    "fail",
                    "reject",
                    "; ".join(size_bad[:12]),
                    str(root),
                )
            )
        else:
            results.append(
                _guard_row(
                    "asset.size_limit",
                    "size_limit",
                    "pass",
                    "info",
                    f"all generated files within {max_b} bytes",
                    str(root),
                )
            )

        # asset.dimensions_match — map generated files to manifest rows by basename
        dim_issues: list[str] = []
        load_image_fn = None
        if assets_list and gen:
            try:
                vmod = gc.import_skill_tool_module("vision-qa", "_image_io")
                load_image_fn = getattr(vmod, "load_image", None)
            except ImportError:
                load_image_fn = None
        if not callable(load_image_fn):
            results.append(
                _guard_row(
                    "asset.dimensions_match",
                    "dimensions_match",
                    "skip",
                    "info",
                    "vision-qa _image_io.load_image not importable",
                    None,
                )
            )
        else:
            by_base: dict[str, tuple[int, int]] = {}
            for a in assets_list:
                if not isinstance(a, dict):
                    continue
                dest = str(a.get("destination", ""))
                base = Path(dest).name.lower()
                params = a.get("params") if isinstance(a.get("params"), dict) else {}
                w = params.get("width") or a.get("width")
                h = params.get("height") or a.get("height")
                if w is not None and h is not None:
                    try:
                        by_base[base] = (int(w), int(h))
                    except (TypeError, ValueError):
                        pass
            checked = 0
            for gf in gen:
                base = Path(gf).name.lower()
                if base not in by_base:
                    continue
                checked += 1
                exp_w, exp_h = by_base[base]
                try:
                    fp = gc._validate_path(gf, root)
                except ValueError:
                    fp = Path(gf).expanduser().resolve(strict=False)
                loaded = load_image_fn(str(fp))
                if loaded.get("error"):
                    dim_issues.append(f"{gf}: {loaded.get('error')}")
                    continue
                aw = loaded.get("width")
                ah = loaded.get("height")
                if aw != exp_w or ah != exp_h:
                    dim_issues.append(f"{gf}: got {aw}x{ah} expected {exp_w}x{exp_h}")
            if dim_issues:
                results.append(
                    _guard_row(
                        "asset.dimensions_match",
                        "dimensions_match",
                        "fail",
                        "reject",
                        "; ".join(dim_issues[:12]),
                        str(root),
                    )
                )
            elif not by_base:
                results.append(
                    _guard_row(
                        "asset.dimensions_match",
                        "dimensions_match",
                        "skip",
                        "info",
                        "manifest has no width/height declarations for assets",
                        manifest_path,
                    )
                )
            elif checked == 0:
                results.append(
                    _guard_row(
                        "asset.dimensions_match",
                        "dimensions_match",
                        "skip",
                        "info",
                        "no generated file basename matches a manifest row with dimensions",
                        manifest_path,
                    )
                )
            else:
                results.append(
                    _guard_row(
                        "asset.dimensions_match",
                        "dimensions_match",
                        "pass",
                        "info",
                        "dimensions match manifest for generated PNGs",
                        str(root),
                    )
                )

    # asset.comfyui_available
    if mode == "dry_run":
        probe = _comfyui_health_envelope()
        results.append(
            _guard_row(
                "asset.comfyui_available",
                "comfyui_available",
                "pass",
                "info",
                f"dry_run: ComfyUI probe status={probe.get('status')}",
                None,
            )
        )
    else:
        probe = _comfyui_health_envelope()
        st = str(probe.get("status", ""))
        if st in {"ok", "dry_run"}:
            results.append(
                _guard_row(
                    "asset.comfyui_available",
                    "comfyui_available",
                    "pass",
                    "info",
                    f"ComfyUI health status={st}",
                    None,
                )
            )
        elif st == "not_configured":
            results.append(
                _guard_row(
                    "asset.comfyui_available",
                    "comfyui_available",
                    "warn",
                    "warn",
                    "ComfyUI not configured (not a hard fail for local asset guards)",
                    None,
                )
            )
        else:
            results.append(
                _guard_row(
                    "asset.comfyui_available",
                    "comfyui_available",
                    "warn",
                    "warn",
                    str(probe.get("error") or st),
                    None,
                )
            )

    np = sum(1 for r in results if r.get("status") == "pass")
    nf = sum(1 for r in results if r.get("status") == "fail")
    ns = sum(1 for r in results if r.get("status") == "skip")
    nw = sum(1 for r in results if r.get("status") == "warn")
    if nf > 0:
        top = "fail"
        rec = "blocked"
    elif nw > 0:
        top = "warn"
        rec = "manual_review"
    elif ns == len(results):
        top = "skip"
        rec = "manual_review"
    else:
        top = "pass"
        rec = "proceed"

    return {
        "status": top,
        "mode": mode,
        "project_path": str(root),
        "guards_evaluated": len(results),
        "guards_passed": np,
        "guards_failed": nf,
        "guards_skipped": ns,
        "guards_warned": nw,
        "results": results,
        "overall_recommendation": rec,
        "config_path": cfg_p,
    }


def register(mcp: FastMCP) -> None:
    """Register ``asset_guard_evaluate`` MCP tool."""

    @mcp.tool(name="asset_guard_evaluate")
    def asset_guard_evaluate_tool(
        project_path: str,
        manifest_path: str | None = None,
        generated_files: list[str] | None = None,
        config_path: str | None = None,
        caller: str = "user-direct-debug",
    ) -> dict[str, Any]:
        """Evaluate /asset pipeline guards (manifest, PNG bytes, ComfyUI, scope)."""
        return asset_guard_evaluate(
            project_path,
            manifest_path=manifest_path,
            generated_files=generated_files,
            config_path=config_path,
            caller=caller,
        )
