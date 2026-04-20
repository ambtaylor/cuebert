# Optional dependencies: PyYAML and jsonschema.
# This tool degrades gracefully when either is missing:
#   - PyYAML missing -> fail status with runtime.pyyaml_missing (required for YAML)
#   - jsonschema missing -> warn + fall back to minimal validator
"""MCP tool: validate a game project's asset manifest against the cuebert JSON Schema."""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from _comfyui_client import _list_local_workflows, find_cuebert_root

logger = logging.getLogger(__name__)

_MANIFEST_SIZE_CAP_BYTES = 1_000_000
_ID_RE = re.compile(r"^[a-z0-9_-]{1,64}$")
_TRAVERSAL_RE = re.compile(r"(^|/)\.\.(/|$)")


def _finding(
    severity: str,
    code: str,
    path: str,
    message: str,
) -> dict[str, Any]:
    return {
        "severity": severity,
        "code": code,
        "path": path,
        "message": message,
    }


def _is_under(child: Path, parent: Path) -> bool:
    c = child.resolve()
    p = parent.resolve()
    try:
        c.relative_to(p)
        return True
    except ValueError:
        return False


def _resolve_manifest_candidate(
    hub_root: Path,
    project_root: Path,
    manifest_path_arg: str | None,
    workspace_asset_manifest_path: str | None,
) -> tuple[Path | None, list[dict[str, Any]]]:
    """Return (resolved_path, preliminary_findings) for security violations."""
    findings: list[dict[str, Any]] = []
    roots = [project_root.resolve(), hub_root.resolve()]

    def _normalize_and_guard(raw: str) -> Path | None:
        p = Path(raw)
        if not p.is_absolute():
            cand = (project_root / p).resolve()
        else:
            cand = p.resolve()
        if not any(_is_under(cand, r) for r in roots):
            findings.append(
                _finding(
                    "fail",
                    "security.path_outside_project",
                    "",
                    "Resolved manifest path must lie under the project root or cuebert hub.",
                ),
            )
            return None
        if _TRAVERSAL_RE.search(str(raw)) or ".." in Path(raw).parts:
            findings.append(
                _finding(
                    "fail",
                    "security.path_traversal_manifest",
                    "",
                    "Manifest path must not contain parent directory segments.",
                ),
            )
            return None
        return cand

    if manifest_path_arg is not None and str(manifest_path_arg).strip():
        cand = _normalize_and_guard(str(manifest_path_arg).strip())
        return (cand, findings)

    if workspace_asset_manifest_path and str(workspace_asset_manifest_path).strip():
        cand = _normalize_and_guard(str(workspace_asset_manifest_path).strip())
        return (cand, findings)

    conv = (project_root / ".cuebert-assets.yaml").resolve()
    if any(_is_under(conv, r) for r in roots):
        return (conv, findings)
    findings.append(
        _finding(
            "fail",
            "security.path_outside_project",
            "/",
            "Convention path .cuebert-assets.yaml resolved outside allowed roots.",
        ),
    )
    return (None, findings)


def _load_workspace_projects(hub_root: Path) -> tuple[dict[str, Any] | None, str | None]:
    wm = hub_root / ".cuebert" / "workspace-manifest.json"
    if not wm.is_file():
        return None, str(wm)
    try:
        with wm.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("workspace-manifest unreadable: %s", exc)
        return None, str(wm)
    projects = data.get("projects")
    if not isinstance(projects, dict):
        return None, str(wm)
    return projects, str(wm)


def _minimal_schema_check(doc: Any, findings: list[dict[str, Any]]) -> bool:
    """Return True if minimal checks pass (no new fail findings)."""
    if not isinstance(doc, dict):
        findings.append(
            _finding(
                "fail",
                "schema.invalid_root",
                "",
                "Manifest document must be a YAML mapping (JSON object).",
            ),
        )
        return False
    ver = doc.get("version")
    if ver != 1:
        findings.append(
            _finding(
                "fail",
                "schema.version_unknown",
                "/version",
                f"Unsupported manifest version {ver!r}; only 1 is accepted for this schema.",
            ),
        )
        return False
    for key in ("project", "engine", "assets"):
        if key not in doc:
            findings.append(
                _finding(
                    "fail",
                    "schema.missing_required_field",
                    f"/{key}",
                    f"Missing required top-level field {key!r}.",
                ),
            )
    if doc.get("engine") not in ("unreal", "unity", "godot"):
        findings.append(
            _finding(
                "fail",
                "schema.invalid_engine",
                "/engine",
                "engine must be one of: unreal, unity, godot.",
            ),
        )
    assets = doc.get("assets")
    if not isinstance(assets, list) or len(assets) < 1:
        findings.append(
            _finding(
                "fail",
                "schema.assets_required",
                "/assets",
                "assets must be a non-empty array.",
            ),
        )
        return False
    for i, a in enumerate(assets):
        pfx = f"/assets/{i}"
        if not isinstance(a, dict):
            findings.append(
                _finding("fail", "schema.asset_not_object", pfx, "Each asset must be a mapping."),
            )
            continue
        for req in ("id", "prompt", "destination"):
            if req not in a or a.get(req) in (None, ""):
                findings.append(
                    _finding(
                        "fail",
                        "schema.missing_required_field",
                        f"{pfx}/{req}",
                        f"Missing or empty required field {req!r}.",
                    ),
                )
        aid = a.get("id")
        if isinstance(aid, str) and not _ID_RE.match(aid):
            findings.append(
                _finding(
                    "fail",
                    "schema.invalid_asset_id",
                    f"{pfx}/id",
                    "id must match ^[a-z0-9_-]{1,64}$.",
                ),
            )
        pr = a.get("prompt")
        if isinstance(pr, str) and (len(pr) < 1 or len(pr) > 4096):
            findings.append(
                _finding(
                    "fail",
                    "schema.prompt_length",
                    f"{pfx}/prompt",
                    "prompt must be non-empty and at most 4096 characters.",
                ),
            )
    return not any(f["severity"] == "fail" for f in findings)


def _semantic_checks(
    doc: dict[str, Any],
    findings: list[dict[str, Any]],
    local_workflows: list[str],
) -> None:
    assets = doc.get("assets")
    if not isinstance(assets, list):
        return
    ids: list[str] = []
    defaults = doc.get("defaults") if isinstance(doc.get("defaults"), dict) else {}
    dest_root = defaults.get("destination_root") if isinstance(defaults, dict) else None
    default_wf = defaults.get("workflow") if isinstance(defaults, dict) else None

    x_locations: list[str] = []
    for k in doc:
        if isinstance(k, str) and k.startswith("x_"):
            x_locations.append(f"/{k}")
    for i, a in enumerate(assets):
        if not isinstance(a, dict):
            continue
        pfx = f"/assets/{i}"
        for k in a:
            if isinstance(k, str) and k.startswith("x_"):
                x_locations.append(f"{pfx}/{k}")
    if x_locations:
        findings.append(
            _finding(
                "info",
                "extension.x_keys_present",
                "/",
                "Opaque x_* keys present at: " + ", ".join(x_locations[:12])
                + ("; ..." if len(x_locations) > 12 else ""),
            ),
        )

    for i, a in enumerate(assets):
        if not isinstance(a, dict):
            continue
        pfx = f"/assets/{i}"
        aid = a.get("id")
        if isinstance(aid, str):
            ids.append(aid)
        wf_override = a.get("workflow")
        eff_wf = (
            wf_override
            if isinstance(wf_override, str) and wf_override.strip()
            else default_wf
        )
        if not eff_wf or not str(eff_wf).strip():
            findings.append(
                _finding(
                    "fail",
                    "manifest.workflow_missing",
                    pfx,
                    "Each asset needs a workflow via asset.workflow or defaults.workflow.",
                ),
            )
        elif str(eff_wf) not in local_workflows:
            findings.append(
                _finding(
                    "warn",
                    "workflow.not_found_local",
                    f"{pfx}/workflow",
                    f"Workflow {eff_wf!r} not found under comfyui-toolkit/workflows/*.json.",
                ),
            )
        if "seed" not in a:
            findings.append(
                _finding(
                    "warn",
                    "reproducibility.seed_omitted",
                    f"{pfx}/seed",
                    "seed omitted; regeneration is non-deterministic for this asset.",
                ),
            )
        dest = a.get("destination")
        if isinstance(dest, str):
            if dest.startswith(("/", "\\")) or Path(dest).is_absolute():
                findings.append(
                    _finding(
                        "fail",
                        "security.absolute_destination",
                        f"{pfx}/destination",
                        "destination must be project-relative (no absolute paths).",
                    ),
                )
            if _TRAVERSAL_RE.search(dest) or ".." in Path(dest).parts:
                findings.append(
                    _finding(
                        "fail",
                        "security.path_traversal_destination",
                        f"{pfx}/destination",
                        "destination must not traverse outside the project (no .. segments).",
                    ),
                )
            if isinstance(dest_root, str) and dest_root.strip():
                norm_d = dest.replace("\\", "/").lstrip("./")
                norm_r = dest_root.replace("\\", "/").lstrip("./")
                if not norm_d.startswith(norm_r.rstrip("/") + "/") and norm_d != norm_r.rstrip(
                    "/"
                ):
                    findings.append(
                        _finding(
                            "warn",
                            "path.outside_destination_root",
                            f"{pfx}/destination",
                            "destination is outside defaults.destination_root (advisory).",
                        ),
                    )

    seen_set = set()
    dup = False
    for i in ids:
        if i in seen_set:
            dup = True
            break
        seen_set.add(i)
    if dup:
        findings.append(
            _finding(
                "fail",
                "asset.duplicate_id",
                "/assets",
                "Duplicate assets[].id values detected.",
            ),
        )


def _envelope(
    status: str,
    manifest_path: str | None,
    project_root: str | None,
    schema_version: int | None,
    asset_count: int,
    findings: list[dict[str, Any]],
    summary: str,
) -> dict[str, Any]:
    return {
        "status": status,
        "manifest_path": manifest_path,
        "project_root": project_root,
        "schema_version": schema_version,
        "asset_count": asset_count,
        "findings": findings,
        "summary": summary,
    }


def _validate_impl(
    project_key: str,
    manifest_path: str | None = None,
) -> dict[str, Any]:
    """Core implementation for asset manifest validation (invoked by MCP tool wrapper)."""
    findings: list[dict[str, Any]] = []
    try:
        hub_root = find_cuebert_root(Path(__file__))
    except FileNotFoundError as exc:
        return _envelope(
            "fail",
            None,
            None,
            None,
            0,
            [_finding("fail", "hub.root_not_found", "", str(exc))],
            "Cuebert hub root could not be resolved.",
        )

    projects, _wm_path = _load_workspace_projects(hub_root)
    if projects is None or project_key not in projects:
        findings.append(
            _finding(
                "info",
                "project.not_in_workspace_manifest",
                "",
                f"No projects.{project_key!r} entry in workspace-manifest.json.",
            ),
        )
        return _envelope(
            "not_configured",
            None,
            None,
            None,
            0,
            findings,
            "Project key is not registered in .cuebert/workspace-manifest.json.",
        )

    entry = projects[project_key]
    if not isinstance(entry, dict):
        findings.append(
            _finding(
                "fail",
                "project.invalid_entry",
                f"/projects/{project_key}",
                "Project entry must be an object.",
            ),
        )
        return _envelope("fail", None, None, None, 0, findings, "Invalid workspace project entry.")

    raw_path = entry.get("path")
    if not raw_path or not isinstance(raw_path, str):
        findings.append(
            _finding(
                "fail",
                "project.path_missing",
                f"/projects/{project_key}/path",
                "Project entry missing string path to application repository.",
            ),
        )
        return _envelope("fail", None, None, None, 0, findings, "Project path not configured.")

    project_root = (hub_root / raw_path).resolve()
    if not project_root.is_dir():
        findings.append(
            _finding(
                "warn",
                "project.root_not_directory",
                f"/projects/{project_key}/path",
                f"Resolved project root is not a directory: {project_root}",
            ),
        )

    ws_manifest_path: str | None = None
    if isinstance(entry.get("assetManifestPath"), str):
        ws_manifest_path = entry["assetManifestPath"]

    candidate, pre_findings = _resolve_manifest_candidate(
        hub_root,
        project_root,
        manifest_path,
        ws_manifest_path,
    )
    findings.extend(pre_findings)
    if any(f["severity"] == "fail" for f in findings):
        return _envelope(
            "fail",
            str(candidate) if candidate else None,
            str(project_root),
            None,
            0,
            findings,
            "Manifest path resolution failed security checks.",
        )
    if candidate is None or not candidate.is_file():
        findings.append(
            _finding(
                "info",
                "manifest.not_found",
                "",
                "No asset manifest file resolved (explicit path, assetManifestPath, or .cuebert-assets.yaml).",
            ),
        )
        return _envelope(
            "not_configured",
            str(candidate) if candidate else None,
            str(project_root),
            None,
            0,
            findings,
            "Asset manifest is absent; M4 asset operations skip this project.",
        )

    try:
        size = candidate.stat().st_size
    except OSError as exc:
        findings.append(
            _finding("fail", "manifest.stat_failed", "", str(exc)),
        )
        return _envelope(
            "fail",
            str(candidate),
            str(project_root),
            None,
            0,
            findings,
            "Could not read manifest file metadata.",
        )
    if size > _MANIFEST_SIZE_CAP_BYTES:
        findings.append(
            _finding(
                "fail",
                "security.manifest_too_large",
                "",
                f"Manifest exceeds {_MANIFEST_SIZE_CAP_BYTES} byte cap.",
            ),
        )
        return _envelope(
            "fail",
            str(candidate),
            str(project_root),
            None,
            0,
            findings,
            "Manifest file is too large to validate safely.",
        )

    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        findings.append(
            _finding(
                "fail",
                "runtime.pyyaml_missing",
                "",
                "PyYAML is required to parse asset manifests; install pyyaml in the MCP environment.",
            ),
        )
        return _envelope(
            "fail",
            str(candidate),
            str(project_root),
            None,
            0,
            findings,
            "YAML parser not available.",
        )

    try:
        raw_text = candidate.read_text(encoding="utf-8")
        doc = yaml.safe_load(raw_text)
    except (yaml.YAMLError, OSError, UnicodeDecodeError) as exc:
        findings.append(
            _finding(
                "fail",
                "manifest.parse_error",
                "",
                f"Could not parse YAML: {exc}",
            ),
        )
        return _envelope(
            "fail",
            str(candidate),
            str(project_root),
            None,
            0,
            findings,
            "Manifest YAML parse failed.",
        )

    schema_path = hub_root / ".cuebert" / "schemas" / "asset-manifest.schema.json"
    if not schema_path.is_file():
        findings.append(
            _finding(
                "fail",
                "schema.file_missing",
                str(schema_path),
                "JSON Schema file missing from hub checkout.",
            ),
        )
        return _envelope(
            "fail",
            str(candidate),
            str(project_root),
            None,
            0,
            findings,
            "asset-manifest.schema.json not found.",
        )
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        findings.append(
            _finding("fail", "schema.invalid_json", str(schema_path), str(exc)),
        )
        return _envelope(
            "fail",
            str(candidate),
            str(project_root),
            None,
            0,
            findings,
            "Could not load JSON Schema.",
        )

    try:
        import jsonschema
    except ImportError:
        findings.append(
            _finding(
                "warn",
                "runtime.jsonschema_missing",
                "",
                "jsonschema package not installed; using minimal structural validation only.",
            ),
        )
        _minimal_schema_check(doc, findings)
    else:
        validator = jsonschema.Draft7Validator(schema)
        for err in validator.iter_errors(doc):
            findings.append(
                _finding(
                    "fail",
                    "schema.validation_error",
                    "/" + "/".join(str(p) for p in err.absolute_path),
                    err.message,
                ),
            )

    schema_version: int | None = None
    if isinstance(doc, dict) and isinstance(doc.get("version"), int):
        schema_version = doc["version"]

    asset_count = 0
    if isinstance(doc, dict) and isinstance(doc.get("assets"), list):
        asset_count = len(doc["assets"])

    schema_phase_failed = any(f["severity"] == "fail" for f in findings)
    local_wf = _list_local_workflows()
    if isinstance(doc, dict) and not schema_phase_failed:
        _semantic_checks(doc, findings, local_wf)

    has_fail = any(f["severity"] == "fail" for f in findings)
    has_warn = any(f["severity"] == "warn" for f in findings)
    if has_fail:
        st = "fail"
        summary = "Validation failed; see findings with severity fail."
    elif has_warn:
        st = "warn"
        summary = "Validation passed with warnings."
    else:
        st = "pass"
        summary = "Validation passed."

    return _envelope(
        st,
        str(candidate),
        str(project_root),
        schema_version,
        asset_count,
        findings,
        summary,
    )


def register(mcp: FastMCP) -> None:
    """Register ``asset_manifest_validate`` on the MCP server."""

    @mcp.tool()
    def asset_manifest_validate(
        project_key: str,
        manifest_path: str | None = None,
    ) -> dict[str, Any]:
        """Validate a project's asset manifest against the cuebert schema.

        Args:
            project_key: Key in .cuebert/workspace-manifest.json projects.
            manifest_path: Optional explicit path (project-relative or absolute),
                overriding workspace assetManifestPath and .cuebert-assets.yaml.

        Returns:
            Envelope with status pass|warn|fail|not_configured, manifest_path,
            project_root, schema_version, asset_count, findings[], summary.
        """
        return _validate_impl(project_key, manifest_path)
