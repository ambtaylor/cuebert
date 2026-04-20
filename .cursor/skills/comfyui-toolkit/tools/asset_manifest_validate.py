# Optional dependencies: PyYAML and jsonschema.
# This tool degrades gracefully when either is missing:
#   - PyYAML missing -> fail status with runtime.pyyaml_missing (required for YAML)
#   - jsonschema missing -> warn + fall back to minimal validator
"""MCP tool: validate a game project's asset manifest against the cuebert JSON Schema."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from _comfyui_client import _list_local_workflows, find_cuebert_root

logger = logging.getLogger(__name__)

_MANIFEST_SIZE_CAP_BYTES = 1_000_000
_ID_RE = re.compile(r"^[a-z0-9_-]{1,64}$")
_TRAVERSAL_RE = re.compile(r"(^|/)\.\.(/|$)")


def _f(sev: str, code: str, path: str, msg: str) -> dict[str, Any]:
    return {"severity": sev, "code": code, "path": path, "message": msg}


def _out(
    st: str,
    cand: Path | None,
    proj: Path | None,
    sv: int | None,
    ac: int,
    fs: list[dict[str, Any]],
    summ: str,
) -> dict[str, Any]:
    return {
        "status": st,
        "manifest_path": str(cand) if cand else None,
        "project_root": str(proj) if proj else None,
        "schema_version": sv,
        "asset_count": ac,
        "findings": fs,
        "summary": summ,
    }


def _under(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _resolve_manifest_path(
    hub: Path,
    proj: Path,
    arg: str | None,
    ws_field: str | None,
) -> tuple[Path | None, list[dict[str, Any]]]:
    roots = (proj.resolve(), hub.resolve())
    out: list[dict[str, Any]] = []

    def norm(raw: str) -> Path | None:
        p = Path(raw.strip())
        cand = (proj / p).resolve() if not p.is_absolute() else p.resolve()
        if _TRAVERSAL_RE.search(raw) or ".." in Path(raw).parts:
            out.append(_f("fail", "security.path_traversal_manifest", "", "Manifest path must not contain .. segments."))
            return None
        if not any(_under(cand, r) for r in roots):
            out.append(_f("fail", "security.path_outside_project", "", "Manifest path must lie under project or hub root."))
            return None
        return cand

    if arg and str(arg).strip():
        return norm(str(arg)), out
    if ws_field and str(ws_field).strip():
        return norm(str(ws_field)), out
    conv = (proj / ".cuebert-assets.yaml").resolve()
    return (conv if any(_under(conv, r) for r in roots) else None, out)


def _load_projects(hub: Path) -> dict[str, Any] | None:
    wm = hub / ".cuebert" / "workspace-manifest.json"
    if not wm.is_file():
        return None
    try:
        data = json.loads(wm.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("workspace-manifest: %s", exc)
        return None
    p = data.get("projects")
    return p if isinstance(p, dict) else None


def _minimal_check(doc: Any, fs: list[dict[str, Any]]) -> None:
    if not isinstance(doc, dict):
        fs.append(_f("fail", "schema.invalid_root", "", "Root must be a mapping."))
        return
    if doc.get("version") != 1:
        fs.append(_f("fail", "schema.version_unknown", "/version", "Only version 1 is supported."))
    for k in ("project", "engine", "assets"):
        if k not in doc:
            fs.append(_f("fail", "schema.missing_required_field", f"/{k}", f"Missing {k!r}."))
    if doc.get("engine") not in ("unreal", "unity", "godot"):
        fs.append(_f("fail", "schema.invalid_engine", "/engine", "Invalid engine enum."))
    assets = doc.get("assets")
    if not isinstance(assets, list) or len(assets) < 1:
        fs.append(_f("fail", "schema.assets_required", "/assets", "assets must be a non-empty array."))
        return
    for i, a in enumerate(assets):
        px = f"/assets/{i}"
        if not isinstance(a, dict):
            fs.append(_f("fail", "schema.asset_not_object", px, "Asset must be a mapping."))
            continue
        for req in ("id", "prompt", "destination"):
            if req not in a or a.get(req) in (None, ""):
                fs.append(_f("fail", "schema.missing_required_field", f"{px}/{req}", f"Missing {req!r}."))
        aid = a.get("id")
        if isinstance(aid, str) and not _ID_RE.match(aid):
            fs.append(_f("fail", "schema.invalid_asset_id", f"{px}/id", "Invalid id pattern or length."))
        pr = a.get("prompt")
        if isinstance(pr, str) and not (1 <= len(pr) <= 4096):
            fs.append(_f("fail", "schema.prompt_length", f"{px}/prompt", "prompt length must be 1..4096."))


def _semantic(doc: dict[str, Any], fs: list[dict[str, Any]], wfs: list[str]) -> None:
    assets = doc.get("assets")
    if not isinstance(assets, list):
        return
    defaults = doc.get("defaults") if isinstance(doc.get("defaults"), dict) else {}
    dest_root = defaults.get("destination_root") if isinstance(defaults, dict) else None
    def_wf = defaults.get("workflow") if isinstance(defaults, dict) else None
    xlocs = [f"/{k}" for k in doc if isinstance(k, str) and k.startswith("x_")]
    for i, a in enumerate(assets):
        if not isinstance(a, dict):
            continue
        px = f"/assets/{i}"
        xlocs += [f"{px}/{k}" for k in a if isinstance(k, str) and k.startswith("x_")]
    if xlocs:
        fs.append(_f("info", "extension.x_keys_present", "/", "x_* keys: " + ", ".join(xlocs[:12]) + ("; ..." if len(xlocs) > 12 else "")))

    ids: list[str] = []
    for i, a in enumerate(assets):
        if not isinstance(a, dict):
            continue
        px = f"/assets/{i}"
        wf_o = a.get("workflow")
        eff = wf_o if isinstance(wf_o, str) and wf_o.strip() else def_wf
        if not eff or not str(eff).strip():
            fs.append(_f("fail", "manifest.workflow_missing", px, "Set defaults.workflow or asset.workflow."))
        elif str(eff) not in wfs:
            fs.append(_f("warn", "workflow.not_found_local", f"{px}/workflow", f"Workflow {eff!r} not in workflows/."))
        if "seed" not in a:
            fs.append(_f("warn", "reproducibility.seed_omitted", f"{px}/seed", "seed omitted; non-deterministic."))
        dest = a.get("destination")
        if isinstance(dest, str):
            if dest.startswith(("/", "\\")):
                fs.append(_f("fail", "security.absolute_destination", f"{px}/destination", "No absolute destinations."))
            if _TRAVERSAL_RE.search(dest) or ".." in Path(dest).parts:
                fs.append(_f("fail", "security.path_traversal_destination", f"{px}/destination", "No .. in destination."))
            if isinstance(dest_root, str) and dest_root.strip():
                nd, nr = dest.replace("\\", "/").lstrip("./"), dest_root.replace("\\", "/").lstrip("./")
                root = nr.rstrip("/")
                if nd != root and not nd.startswith(root + "/"):
                    fs.append(_f("warn", "path.outside_destination_root", f"{px}/destination", "Outside defaults.destination_root."))
        aid = a.get("id")
        if isinstance(aid, str):
            ids.append(aid)
    if len(ids) != len(set(ids)):
        fs.append(_f("fail", "asset.duplicate_id", "/assets", "Duplicate assets[].id."))


def _validate_impl(project_key: str, manifest_path: str | None = None) -> dict[str, Any]:
    fs: list[dict[str, Any]] = []
    try:
        hub = find_cuebert_root(Path(__file__))
    except FileNotFoundError as exc:
        return _out("fail", None, None, None, 0, [_f("fail", "hub.root_not_found", "", str(exc))], str(exc))

    projects = _load_projects(hub)
    if projects is None:
        fs.append(
            _f(
                "info",
                "workspace_manifest.unreadable",
                "",
                "Could not load .cuebert/workspace-manifest.json projects map.",
            ),
        )
        return _out("not_configured", None, None, None, 0, fs, "Workspace manifest missing or invalid JSON.")
    if project_key not in projects:
        fs.append(_f("info", "project.not_in_workspace_manifest", "", f"No projects.{project_key!r}."))
        return _out("not_configured", None, None, None, 0, fs, "Project not registered.")

    entry = projects[project_key]
    if not isinstance(entry, dict):
        fs.append(_f("fail", "project.invalid_entry", f"/projects/{project_key}", "Not an object."))
        return _out("fail", None, None, None, 0, fs, "Bad manifest entry.")
    rp = entry.get("path")
    if not isinstance(rp, str) or not rp.strip():
        fs.append(_f("fail", "project.path_missing", f"/projects/{project_key}/path", "Missing path."))
        return _out("fail", None, None, None, 0, fs, "Missing project path.")

    proj_root = (hub / rp).resolve()
    if not proj_root.is_dir():
        fs.append(_f("warn", "project.root_not_directory", f"/projects/{project_key}/path", str(proj_root)))

    ws_asset = entry.get("assetManifestPath") if isinstance(entry.get("assetManifestPath"), str) else None
    cand, pre = _resolve_manifest_path(hub, proj_root, manifest_path, ws_asset)
    fs.extend(pre)
    if any(x["severity"] == "fail" for x in fs):
        return _out("fail", cand, proj_root, None, 0, fs, "Path resolution failed.")
    if cand is None or not cand.is_file():
        fs.append(_f("info", "manifest.not_found", "", "No manifest at resolved path."))
        return _out("not_configured", cand, proj_root, None, 0, fs, "Asset manifest absent.")

    try:
        sz = cand.stat().st_size
    except OSError as exc:
        fs.append(_f("fail", "manifest.stat_failed", "", str(exc)))
        return _out("fail", cand, proj_root, None, 0, fs, str(exc))
    if sz > _MANIFEST_SIZE_CAP_BYTES:
        fs.append(_f("fail", "security.manifest_too_large", "", "Manifest exceeds 1 MiB."))
        return _out("fail", cand, proj_root, None, 0, fs, "Too large.")

    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        fs.append(_f("fail", "runtime.pyyaml_missing", "", "Install PyYAML for YAML parsing."))
        return _out("fail", cand, proj_root, None, 0, fs, "PyYAML missing.")

    try:
        doc = yaml.safe_load(cand.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError, UnicodeDecodeError) as exc:
        fs.append(_f("fail", "manifest.parse_error", "", str(exc)))
        return _out("fail", cand, proj_root, None, 0, fs, "YAML parse error.")

    sp = hub / ".cuebert" / "schemas" / "asset-manifest.schema.json"
    if not sp.is_file():
        fs.append(_f("fail", "schema.file_missing", str(sp), "Schema missing."))
        return _out("fail", cand, proj_root, None, 0, fs, "Schema file missing.")
    try:
        schema = json.loads(sp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        fs.append(_f("fail", "schema.invalid_json", str(sp), str(exc)))
        return _out("fail", cand, proj_root, None, 0, fs, "Bad schema JSON.")

    try:
        import jsonschema
        for err in jsonschema.Draft7Validator(schema).iter_errors(doc):
            fs.append(_f("fail", "schema.validation_error", "/" + "/".join(str(p) for p in err.absolute_path), err.message))
    except ImportError:
        fs.append(_f("warn", "runtime.jsonschema_missing", "", "jsonschema not installed; minimal checks only."))
        _minimal_check(doc, fs)

    sv = doc.get("version") if isinstance(doc, dict) and isinstance(doc.get("version"), int) else None
    ac = len(doc["assets"]) if isinstance(doc, dict) and isinstance(doc.get("assets"), list) else 0
    schema_failed = any(x["severity"] == "fail" for x in fs)
    if isinstance(doc, dict) and not schema_failed:
        _semantic(doc, fs, _list_local_workflows())

    fail = any(x["severity"] == "fail" for x in fs)
    warn = any(x["severity"] == "warn" for x in fs)
    st = "fail" if fail else ("warn" if warn else "pass")
    summ = "Validation failed." if fail else ("Warnings present." if warn else "Validation passed.")
    return _out(st, cand, proj_root, sv, ac, fs, summ)


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def asset_manifest_validate(project_key: str, manifest_path: str | None = None) -> dict[str, Any]:
        """Validate asset manifest YAML (see M4-P2 standard). Returns structured envelope."""
        return _validate_impl(project_key, manifest_path)
