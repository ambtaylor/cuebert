"""MCP tool: evaluate /play Preview Guards G-1 through G-5."""

from __future__ import annotations

import fnmatch
import logging
import re
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from _guard_common import (
    GuardResult,
    _load_yaml_config,
    _resolve_mode,
    _validate_path,
    default_play_guards_config_path,
    find_hub_root,
    import_skill_tool_module,
)

logger = logging.getLogger(__name__)

_CRITICAL_LOG_RES = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"Error:",
        r"Fatal:",
        r"Assert:",
        r"Ensure:",
        r"LogCrash",
        r"appError",
    )
)

_UASSET_PATH_RE = re.compile(r"[^\s\"']+\.uasset\b", re.IGNORECASE)


def _detect_engine(project_root: Path) -> str | None:
    if any(project_root.glob("*.uproject")):
        return "unreal"
    if (project_root / "ProjectSettings").is_dir():
        return "unity"
    if (project_root / "project.godot").is_file():
        return "godot"
    return None


def _invoke_unreal_health_envelope() -> dict[str, Any]:
    """Mirror unreal_health_check behavior using bridge client (module has no top-level fn)."""
    try:
        mod = import_skill_tool_module("unreal-bridge", "unreal_health_check")
        fn = getattr(mod, "unreal_health_check", None)
        if callable(fn):
            return fn()
    except ImportError as exc:
        return {"status": "import_error", "error": str(exc)}
    try:
        client = import_skill_tool_module("unreal-bridge", "_unreal_client")
    except ImportError as exc:
        return {"status": "import_error", "error": str(exc)}

    health_probe = getattr(client, "health_probe", None)
    resolve_base = getattr(client, "_resolve_base_url", None)
    resolve_timeout = getattr(client, "_resolve_timeout", None)
    get_mode = getattr(client, "_get_mode", None)
    is_configured = getattr(client, "_is_unreal_configured_explicitly", None)
    get_explicit = getattr(client, "_get_mode_explicit", None)
    non_local_warn = getattr(client, "non_localhost_warning", None)
    if not all(callable(x) for x in (health_probe, resolve_base, resolve_timeout, get_mode)):
        return {"status": "error", "error": "unreal bridge client incomplete"}

    base_url = resolve_base()
    warnings: list[str] = []
    if callable(non_local_warn):
        nw = non_local_warn(base_url)
        if nw:
            warnings.append(nw)

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
                "version": probe.get("version"),
                "plugins": probe.get("plugins"),
                "error": None,
                "warnings": warnings or None,
            }
        return {
            "status": "not_configured",
            "base_url": base_url,
            "mode": effective_mode,
            "version": None,
            "plugins": None,
            "error": (
                "Unreal Remote Control base URL is not configured. "
                "Set CUEBERT_UNREAL_BASE_URL or vault unreal.base_url."
            ),
            "warnings": warnings or None,
        }

    if effective_mode == "dry_run":
        probe = health_probe(base_url, resolve_timeout())
        return {
            "status": "dry_run",
            "base_url": base_url,
            "mode": "dry_run",
            "version": probe.get("version"),
            "plugins": probe.get("plugins"),
            "error": None,
            "warnings": warnings or None,
        }

    timeout = resolve_timeout()
    probe = health_probe(base_url, timeout)
    if probe.get("dry_run"):
        return {
            "status": "dry_run",
            "base_url": base_url,
            "mode": "dry_run",
            "version": probe.get("version"),
            "plugins": probe.get("plugins"),
            "error": None,
            "warnings": warnings or None,
        }
    if probe.get("reachable"):
        return {
            "status": "ok",
            "base_url": base_url,
            "mode": "live",
            "version": probe.get("version"),
            "plugins": probe.get("plugins"),
            "error": None,
            "warnings": warnings or None,
        }
    return {
        "status": "unreachable",
        "base_url": base_url,
        "mode": "live",
        "version": probe.get("version"),
        "plugins": probe.get("plugins"),
        "error": probe.get("error"),
        "warnings": warnings or None,
    }


def _g1_engine(
    project_root: Path,
    engine: str | None,
    evidence_path: str | None,
) -> dict[str, Any]:
    name = "engine_reachability"
    if engine is None:
        return {
            **GuardResult("G-1", "skip", "info", "No Unreal/Unity/Godot project markers found", evidence_path),
            "name": name,
        }
    if engine == "unity" or engine == "godot":
        return {
            **GuardResult(
                "G-1",
                "skip",
                "info",
                f"Tier 2/3 — automation pending ({engine})",
                evidence_path,
            ),
            "name": name,
        }
    # unreal
    try:
        env = _invoke_unreal_health_envelope()
    except Exception as exc:
        logger.exception("G-1 unreal health failed")
        return {
            **GuardResult("G-1", "skip", "info", f"unreal health probe failed: {exc}", evidence_path),
            "name": name,
        }
    st = str(env.get("status", ""))
    if st == "ok":
        return {
            **GuardResult("G-1", "pass", "info", "Unreal Remote Control reachable (ok)", evidence_path),
            "name": name,
        }
    if st == "dry_run":
        return {
            **GuardResult("G-1", "pass", "info", "Unreal health dry_run envelope", evidence_path),
            "name": name,
        }
    if st == "import_error":
        return {
            **GuardResult("G-1", "skip", "info", str(env.get("error", "import_error")), evidence_path),
            "name": name,
        }
    detail = str(env.get("error") or env.get("status") or "unreal not reachable")
    return {
        **GuardResult("G-1", "warn", "warn", detail, evidence_path),
        "name": name,
    }


def _g2_compile(project_root: Path, engine: str | None, evidence_path: str | None) -> dict[str, Any]:
    name = "compile_sanity"
    if engine is None:
        return {
            **GuardResult("G-2", "skip", "info", "No engine detected", evidence_path),
            "name": name,
        }
    if engine != "unreal":
        return {
            **GuardResult("G-2", "skip", "info", f"Tier 2/3 — automation pending ({engine})", evidence_path),
            "name": name,
        }
    try:
        mod = import_skill_tool_module("unreal-build", "unreal_build_status")
    except ImportError as exc:
        return {
            **GuardResult("G-2", "skip", "info", f"unreal_build_status import failed: {exc}", evidence_path),
            "name": name,
        }
    impl = getattr(mod, "_unreal_build_status_impl", None)
    fn = impl if callable(impl) else getattr(mod, "unreal_build_status", None)
    if not callable(fn):
        return {
            **GuardResult(
                "G-2",
                "skip",
                "info",
                "unreal_build_status not exposed as callable on skill module",
                evidence_path,
            ),
            "name": name,
        }
    try:
        raw = fn()
    except Exception as exc:
        return {
            **GuardResult("G-2", "warn", "warn", f"unreal_build_status raised: {exc}", evidence_path),
            "name": name,
        }
    ubt = raw.get("ubt_available")
    rs = str(raw.get("status", ""))
    if rs in {"ok", "dry_run"} and ubt is not False:
        return {
            **GuardResult(
                "G-2",
                "pass",
                "info",
                f"compile sanity: status={rs} ubt_available={ubt}",
                evidence_path,
            ),
            "name": name,
        }
    reason = str(raw.get("reason") or rs or "unknown")
    return {
        **GuardResult("G-2", "warn", "warn", f"UBT/engine not fully available: {reason}", evidence_path),
        "name": name,
    }


def _g3_logs(log_path: str | None, project_root: Path, evidence_path: str | None) -> dict[str, Any]:
    name = "critical_log_patterns"
    if not log_path:
        return {
            **GuardResult("G-3", "skip", "info", "no log file provided", evidence_path),
            "name": name,
        }
    try:
        lp = _validate_path(log_path, project_root)
    except ValueError:
        hub = find_hub_root()
        lp = _validate_path(log_path, hub)
    if not lp.is_file():
        return {
            **GuardResult("G-3", "fail", "reject", f"log path is not a file: {lp}", str(lp)),
            "name": name,
        }
    try:
        text = lp.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {
            **GuardResult("G-3", "fail", "reject", f"cannot read log: {exc}", str(lp)),
            "name": name,
        }
    hits: list[str] = []
    for i, line in enumerate(text.splitlines(), start=1):
        for rx in _CRITICAL_LOG_RES:
            if rx.search(line):
                hits.append(f"L{i}:{line.strip()[:200]}")
                break
    if hits:
        detail = "; ".join(hits[:20])
        if len(hits) > 20:
            detail += f" ... ({len(hits)} total matches)"
        return {
            **GuardResult("G-3", "fail", "reject", detail, str(lp)),
            "name": name,
        }
    return {
        **GuardResult("G-3", "pass", "info", "no critical log patterns matched", str(lp)),
        "name": name,
    }


def _g4_assets(
    changed_files: list[str] | None,
    project_root: Path,
    evidence_path: str | None,
) -> dict[str, Any]:
    name = "asset_reference_integrity"
    if not changed_files:
        return {
            **GuardResult("G-4", "skip", "info", "no changed_files list provided", evidence_path),
            "name": name,
        }
    missing: list[str] = []
    seen: set[str] = set()
    for cf in changed_files:
        for m in _UASSET_PATH_RE.findall(cf or ""):
            if m in seen:
                continue
            seen.add(m)
            p = Path(m)
            if not p.is_absolute():
                cand = (project_root / m).resolve()
            else:
                cand = p.resolve()
            try:
                cand.relative_to(project_root.resolve())
            except ValueError:
                missing.append(f"{m} (outside project root)")
                continue
            if not cand.is_file():
                missing.append(m)
    if not seen:
        return {
            **GuardResult("G-4", "skip", "info", "no .uasset paths in changed_files", evidence_path),
            "name": name,
        }
    if missing:
        return {
            **GuardResult(
                "G-4",
                "fail",
                "reject",
                "missing or out-of-root uasset paths: " + ", ".join(missing[:30]),
                evidence_path,
            ),
            "name": name,
        }
    return {
        **GuardResult("G-4", "pass", "info", f"verified {len(seen)} uasset path(s) exist", evidence_path),
        "name": name,
    }


def _path_matches_any_scope(rel: str, declared_scope: list[str]) -> bool:
    rel_norm = rel.replace("\\", "/").lstrip("./")
    for raw_pat in declared_scope:
        pat = raw_pat.replace("\\", "/").lstrip("./")
        if fnmatch.fnmatch(rel_norm, pat):
            return True
        if pat.endswith("/**"):
            prefix = pat[:-3].rstrip("/")
            if rel_norm == prefix or rel_norm.startswith(prefix + "/"):
                return True
        pref = pat.rstrip("/")
        if rel_norm == pref or rel_norm.startswith(pref + "/"):
            return True
    return False


def _g5_scope(
    declared_scope: list[str] | None,
    changed_files: list[str] | None,
    project_root: Path,
    evidence_path: str | None,
) -> dict[str, Any]:
    name = "scope_containment"
    if not declared_scope:
        return {
            **GuardResult("G-5", "skip", "info", "no scope constraint", evidence_path),
            "name": name,
        }
    if not changed_files:
        return {
            **GuardResult("G-5", "skip", "info", "declared_scope set but no changed_files", evidence_path),
            "name": name,
        }
    root = project_root.resolve()
    bad: list[str] = []
    for cf in changed_files:
        if not cf or not str(cf).strip():
            continue
        raw = Path(cf).expanduser()
        try:
            abs_p = raw.resolve(strict=False)
        except (OSError, RuntimeError):
            bad.append(str(cf))
            continue
        try:
            rel = str(abs_p.relative_to(root))
        except ValueError:
            bad.append(str(cf))
            continue
        if not _path_matches_any_scope(rel, declared_scope):
            bad.append(rel)
    if bad:
        return {
            **GuardResult(
                "G-5",
                "fail",
                "reject",
                "out-of-scope paths: " + ", ".join(bad[:40]),
                evidence_path,
            ),
            "name": name,
        }
    return {
        **GuardResult("G-5", "pass", "info", "all changed files within declared_scope", evidence_path),
        "name": name,
    }


def _dry_run_results(project_path: str) -> list[dict[str, Any]]:
    return [
        {**GuardResult("G-1", "pass", "info", "dry_run: engine marker present (synthetic)", None), "name": "engine_reachability"},
        {**GuardResult("G-2", "skip", "info", "dry_run: compile check skipped (synthetic)", None), "name": "compile_sanity"},
        {**GuardResult("G-3", "skip", "info", "dry_run: no log provided (synthetic)", None), "name": "critical_log_patterns"},
        {**GuardResult("G-4", "pass", "info", "dry_run: asset refs ok (synthetic)", None), "name": "asset_reference_integrity"},
        {**GuardResult("G-5", "warn", "warn", "dry_run: scope advisory (synthetic)", None), "name": "scope_containment"},
    ]


def _rollup_play(results: list[dict[str, Any]]) -> tuple[str, str]:
    statuses = [str(r.get("status", "")) for r in results]
    if "fail" in statuses:
        return "fail", "blocked"
    if "warn" in statuses:
        return "warn", "manual_review"
    if all(s == "skip" for s in statuses):
        return "skip", "manual_review"
    return "pass", "proceed"


def play_guard_evaluate(
    project_path: str,
    declared_scope: list[str] | None = None,
    changed_files: list[str] | None = None,
    log_path: str | None = None,
    config_path: str | None = None,
    caller: str = "user-direct-debug",
) -> dict[str, Any]:
    """Evaluate Preview Guards G-1 through G-5 for a game project under *project_path*."""
    _ = caller
    mode = _resolve_mode()
    cfg_p = config_path or str(default_play_guards_config_path())
    _load_yaml_config(cfg_p)

    project_root = Path(project_path).expanduser().resolve(strict=False)
    evidence_base = str(project_root)

    if mode == "dry_run":
        results = _dry_run_results(str(project_root))
        top, rec = _rollup_play(results)
        np = sum(1 for r in results if r.get("status") == "pass")
        nf = sum(1 for r in results if r.get("status") == "fail")
        ns = sum(1 for r in results if r.get("status") == "skip")
        nw = sum(1 for r in results if r.get("status") == "warn")
        return {
            "status": top,
            "mode": "dry_run",
            "project_path": str(project_root),
            "guards_evaluated": 5,
            "guards_passed": np,
            "guards_failed": nf,
            "guards_skipped": ns,
            "guards_warned": nw,
            "results": results,
            "overall_recommendation": rec,
            "config_path": cfg_p,
        }

    engine = _detect_engine(project_root)
    results: list[dict[str, Any]] = [
        _g1_engine(project_root, engine, evidence_base),
        _g2_compile(project_root, engine, evidence_base),
        _g3_logs(log_path, project_root, evidence_base),
        _g4_assets(changed_files, project_root, evidence_base),
        _g5_scope(declared_scope, changed_files, project_root, evidence_base),
    ]

    top, rec = _rollup_play(results)
    np = sum(1 for r in results if r.get("status") == "pass")
    nf = sum(1 for r in results if r.get("status") == "fail")
    ns = sum(1 for r in results if r.get("status") == "skip")
    nw = sum(1 for r in results if r.get("status") == "warn")

    return {
        "status": top,
        "mode": "live",
        "project_path": str(project_root),
        "guards_evaluated": 5,
        "guards_passed": np,
        "guards_failed": nf,
        "guards_skipped": ns,
        "guards_warned": nw,
        "results": results,
        "overall_recommendation": rec,
        "config_path": cfg_p,
    }


def register(mcp: FastMCP) -> None:
    """Register ``play_guard_evaluate`` MCP tool."""

    @mcp.tool(name="play_guard_evaluate")
    def play_guard_evaluate_tool(
        project_path: str,
        declared_scope: list[str] | None = None,
        changed_files: list[str] | None = None,
        log_path: str | None = None,
        config_path: str | None = None,
        caller: str = "user-direct-debug",
    ) -> dict[str, Any]:
        """Evaluate /play preview guards (G-1..G-5) for *project_path*."""
        return play_guard_evaluate(
            project_path,
            declared_scope=declared_scope,
            changed_files=changed_files,
            log_path=log_path,
            config_path=config_path,
            caller=caller,
        )
