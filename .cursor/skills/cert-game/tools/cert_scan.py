"""MCP tool: advisory cert checklist scan (INFO/WARN only)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from _cert_common import (
    _coerce_severity,
    _load_config,
    _merge_project_config,
    _read_ini_safe,
    _read_json_safe,
    _resolve_mode,
    checklist_applies,
    checklist_entry,
    checklist_on,
    default_config_path,
    validate_optional_dir,
    validate_project_file,
)

_DENIED_CALLERS = {"agent-play-qa"}

CHECKLIST_ORDER: list[tuple[str, str, dict[str, Any] | None]] = [
    ("legal.eula_present", "legal", {"target_store": ["steam", "epic", "gog", "itchio"]}),
    ("legal.privacy_policy_present", "legal", None),
    ("legal.age_rating_configured", "legal", {"target_store": ["steam", "epic"]}),
    ("metadata.game_description_set", "metadata", None),
    ("metadata.version_string_set", "metadata", None),
    ("metadata.store_assets_present", "metadata", {"target_store": ["steam", "epic", "gog"]}),
    ("technical.min_os_version_set", "technical", None),
    ("technical.controller_support_declared", "technical", None),
    ("technical.resolution_settings_valid", "technical", None),
    ("technical.audio_settings_valid", "technical", None),
    ("packaging.redistrib_included", "packaging", None),
    ("packaging.install_size_documented", "packaging", None),
]

_DEFAULT_SEVERITY: dict[str, str] = {
    "legal.eula_present": "warn",
    "legal.privacy_policy_present": "warn",
    "legal.age_rating_configured": "warn",
    "metadata.game_description_set": "info",
    "metadata.version_string_set": "info",
    "metadata.store_assets_present": "warn",
    "technical.min_os_version_set": "info",
    "technical.controller_support_declared": "info",
    "technical.resolution_settings_valid": "info",
    "technical.audio_settings_valid": "info",
    "packaging.redistrib_included": "warn",
    "packaging.install_size_documented": "info",
}

_PLACEHOLDER_RE = re.compile(r"\b(todo|tbd|lorem|placeholder)\b", re.IGNORECASE)


def _finding(
    checklist_id: str,
    category: str,
    severity: str,
    file_inspected: str,
    current_value: str,
    recommendation: str,
    detail: str,
) -> dict[str, Any]:
    sev = _coerce_severity(severity)
    return {
        "checklist_id": checklist_id,
        "category": category,
        "severity": sev,
        "file_inspected": file_inspected,
        "current_value": current_value,
        "recommendation": recommendation,
        "detail": detail,
    }


def _ini_get_any(cp: Any, *needles: str) -> tuple[str | None, str | None]:
    nlow = [n.lower() for n in needles]
    for sec in cp.sections():
        for opt in cp.options(sec):
            ol = opt.lower()
            for nd in nlow:
                if nd in ol:
                    try:
                        v = cp.get(sec, opt, fallback="")
                    except Exception:
                        v = ""
                    if v is not None and str(v).strip():
                        return str(v).strip(), f"{sec}:{opt}"
    return None, None


def _project_ini(project_root: Path, name: str) -> Any | None:
    p = project_root / "Config" / name
    if not p.is_file():
        return None
    try:
        return _read_ini_safe(p)
    except OSError:
        return None


def _check_eula(project_root: Path, build_resolved: str | None, cfg: dict[str, Any], cid: str, cat: str) -> dict[str, Any] | None:
    entry = checklist_entry(cfg, cid)
    sev = _coerce_severity(entry.get("severity") or _DEFAULT_SEVERITY.get(cid, "warn"))
    roots = [project_root / "Legal", project_root / "Content" / "Legal"]
    if build_resolved:
        roots.append(Path(build_resolved) / "Legal")
    for d in roots:
        if not d.is_dir():
            continue
        for pat in ("EULA.txt", "EULA.md", "EULA.pdf", "eula.txt"):
            if (d / pat).is_file():
                return None
    game = _project_ini(project_root, "DefaultGame.ini")
    if game:
        val, _key = _ini_get_any(game, "eula", "licenseurl", "eulalicense")
        if val and not _PLACEHOLDER_RE.search(val):
            return None
    return _finding(
        cid,
        cat,
        sev,
        str(project_root / "Legal"),
        "missing",
        "Add Legal/EULA.txt (or URL in DefaultGame.ini) for storefront distribution.",
        "No EULA file or license URL found under project or staged Legal/.",
    )


def _check_privacy(project_root: Path, cfg: dict[str, Any], cid: str, cat: str) -> dict[str, Any] | None:
    entry = checklist_entry(cfg, cid)
    sev = _coerce_severity(entry.get("severity") or _DEFAULT_SEVERITY.get(cid, "warn"))
    game = _project_ini(project_root, "DefaultGame.ini")
    eng = _project_ini(project_root, "DefaultEngine.ini")
    for cp in (game, eng):
        if not cp:
            continue
        val, _key = _ini_get_any(cp, "privacypolicy", "privacyurl", "privacypolicyurl")
        if val and not _PLACEHOLDER_RE.search(val):
            return None
    legal = project_root / "Legal" / "Privacy.txt"
    if legal.is_file():
        return None
    return _finding(
        cid,
        cat,
        sev,
        str(project_root / "Config" / "DefaultGame.ini"),
        "missing",
        "Set PrivacyPolicy URL in DefaultGame.ini or ship Legal/Privacy.txt.",
        "No privacy policy URL or bundled privacy file detected.",
    )


def _check_age_rating(project_root: Path, cfg: dict[str, Any], cid: str, cat: str) -> dict[str, Any] | None:
    entry = checklist_entry(cfg, cid)
    sev = _coerce_severity(entry.get("severity") or _DEFAULT_SEVERITY.get(cid, "warn"))
    game = _project_ini(project_root, "DefaultGame.ini")
    if game:
        val, _key = _ini_get_any(game, "rating", "agerating", "iarc", "contentrating")
        if val and not _PLACEHOLDER_RE.search(val):
            return None
    side = project_root / "Config" / "ContentRating.ini"
    if side.is_file():
        return None
    return _finding(
        cid,
        cat,
        sev,
        str(project_root / "Config" / "DefaultGame.ini"),
        "missing",
        "Declare age rating / questionnaire metadata for Steam or Epic listings.",
        "No rating or IARC-style fields found in DefaultGame.ini.",
    )


def _check_game_description(project_root: Path, cfg: dict[str, Any], cid: str, cat: str) -> dict[str, Any] | None:
    entry = checklist_entry(cfg, cid)
    sev = _coerce_severity(entry.get("severity") or _DEFAULT_SEVERITY.get(cid, "info"))
    game = _project_ini(project_root, "DefaultGame.ini")
    if not game:
        return _finding(
            cid,
            cat,
            sev,
            str(project_root / "Config" / "DefaultGame.ini"),
            "missing_file",
            "Add Config/DefaultGame.ini with GeneralProjectSettings Description.",
            "DefaultGame.ini not found.",
        )
    sec = "/Script/EngineSettings.GeneralProjectSettings"
    if not game.has_section(sec):
        return _finding(
            cid,
            cat,
            sev,
            str(project_root / "Config" / "DefaultGame.ini"),
            "section_missing",
            "Populate [/Script/EngineSettings.GeneralProjectSettings] Description.",
            "GeneralProjectSettings section missing.",
        )
    desc = game.get(sec, "Description", fallback="").strip()
    if not desc or _PLACEHOLDER_RE.search(desc):
        return _finding(
            cid,
            cat,
            sev,
            str(project_root / "Config" / "DefaultGame.ini"),
            repr(desc)[:200],
            "Set a non-placeholder Description in project settings.",
            "Description empty or placeholder.",
        )
    return None


def _check_version_string(project_root: Path, project_file: str, cfg: dict[str, Any], cid: str, cat: str) -> dict[str, Any] | None:
    entry = checklist_entry(cfg, cid)
    sev = _coerce_severity(entry.get("severity") or _DEFAULT_SEVERITY.get(cid, "info"))
    game = _project_ini(project_root, "DefaultGame.ini")
    if game:
        sec = "/Script/EngineSettings.GeneralProjectSettings"
        if game.has_section(sec):
            pv = game.get(sec, "ProjectVersion", fallback="").strip()
            if pv and not _PLACEHOLDER_RE.search(pv):
                return None
    try:
        data = _read_json_safe(Path(project_file))
        if isinstance(data, dict) and data.get("EngineAssociation"):
            return None
    except (OSError, ValueError):
        pass
    return _finding(
        cid,
        cat,
        sev,
        project_file,
        "missing",
        "Set ProjectVersion in GeneralProjectSettings or EngineAssociation in .uproject.",
        "ProjectVersion / version metadata not found.",
    )


def _check_store_assets(project_root: Path, cfg: dict[str, Any], cid: str, cat: str) -> dict[str, Any] | None:
    entry = checklist_entry(cfg, cid)
    sev = _coerce_severity(entry.get("severity") or _DEFAULT_SEVERITY.get(cid, "warn"))
    patterns = ("capsule", "header", "library_capsule", "main_capsule")
    found = 0
    roots = [
        project_root / "Build" / "Resources" / "Store",
        project_root / "Store",
        project_root / "Build" / "Windows" / "Resources",
    ]
    img_re = re.compile(r"\.(png|jpg|jpeg|webp)$", re.IGNORECASE)
    for root in roots:
        if not root.is_dir():
            continue
        try:
            for p in root.rglob("*"):
                if p.is_file() and img_re.search(p.name):
                    name_l = p.name.lower()
                    if any(pat in name_l for pat in patterns) or found == 0:
                        found += 1
        except OSError:
            continue
    if found >= 1:
        return None
    return _finding(
        cid,
        cat,
        sev,
        str(project_root / "Build" / "Resources" / "Store"),
        "0_matching_files",
        "Stage store capsule/header PNGs under Build/Resources/Store per partner specs.",
        "No store artwork files matched heuristic patterns.",
    )


def _check_min_os(project_root: Path, cfg: dict[str, Any], cid: str, cat: str) -> dict[str, Any] | None:
    entry = checklist_entry(cfg, cid)
    sev = _coerce_severity(entry.get("severity") or _DEFAULT_SEVERITY.get(cid, "info"))
    for fname in ("DefaultGame.ini", "DefaultEngine.ini"):
        cp = _project_ini(project_root, fname)
        if not cp:
            continue
        val, _key = _ini_get_any(cp, "minimumos", "targetos", "min_os")
        if val:
            return None
    return _finding(
        cid,
        cat,
        sev,
        str(project_root / "Config" / "DefaultGame.ini"),
        "missing",
        "Set MinimumOSVersion / platform SDK minimums in project INI.",
        "No minimum OS / target OS keys found.",
    )


def _check_controller(project_root: Path, cfg: dict[str, Any], cid: str, cat: str) -> dict[str, Any] | None:
    entry = checklist_entry(cfg, cid)
    sev = _coerce_severity(entry.get("severity") or _DEFAULT_SEVERITY.get(cid, "info"))
    cp = _project_ini(project_root, "DefaultInput.ini")
    if cp:
        blob = ""
        for sec in cp.sections():
            blob += sec.lower() + " "
            for opt in cp.options(sec):
                blob += opt.lower() + " "
        if "gamepad" in blob or "xinput" in blob or "dualsense" in blob:
            return None
    return _finding(
        cid,
        cat,
        sev,
        str(project_root / "Config" / "DefaultInput.ini"),
        "no_gamepad_signals",
        "Add default gamepad mappings or document keyboard-only intent.",
        "DefaultInput.ini lacks obvious gamepad/XInput/DualSense markers.",
    )


def _check_resolution(project_root: Path, cfg: dict[str, Any], cid: str, cat: str) -> dict[str, Any] | None:
    entry = checklist_entry(cfg, cid)
    sev = _coerce_severity(entry.get("severity") or _DEFAULT_SEVERITY.get(cid, "info"))
    for fname in ("DefaultEngine.ini", "DefaultGame.ini"):
        cp = _project_ini(project_root, fname)
        if not cp:
            continue
        val, _key = _ini_get_any(cp, "resolutionsizex", "resolutionx", "defaultresolution")
        if val:
            try:
                if int(re.sub(r"[^\d]", "", val) or 0) > 0:
                    return None
            except ValueError:
                return None
    return _finding(
        cid,
        cat,
        sev,
        str(project_root / "Config" / "DefaultEngine.ini"),
        "missing",
        "Set default resolution / GameUserSettings resolution keys for desktop builds.",
        "No resolution defaults found in engine/game INI.",
    )


def _check_audio(project_root: Path, cfg: dict[str, Any], cid: str, cat: str) -> dict[str, Any] | None:
    entry = checklist_entry(cfg, cid)
    sev = _coerce_severity(entry.get("severity") or _DEFAULT_SEVERITY.get(cid, "info"))
    cp = _project_ini(project_root, "DefaultEngine.ini")
    if cp:
        for sec in cp.sections():
            if "audio" in sec.lower():
                return None
        val, _key = _ini_get_any(cp, "audiomixer", "soundcue", "volume")
        if val:
            return None
    return _finding(
        cid,
        cat,
        sev,
        str(project_root / "Config" / "DefaultEngine.ini"),
        "no_audio_section",
        "Verify audio output device defaults and mixer quality settings for cert questionnaires.",
        "No audio-related sections or keys found in DefaultEngine.ini.",
    )


def _check_redist(project_root: Path, build_resolved: str | None, cfg: dict[str, Any], cid: str, cat: str) -> dict[str, Any] | None:
    entry = checklist_entry(cfg, cid)
    sev = _coerce_severity(entry.get("severity") or _DEFAULT_SEVERITY.get(cid, "warn"))
    eng = _project_ini(project_root, "DefaultEngine.ini")
    if eng:
        val, _key = _ini_get_any(eng, "includeprerequisites", "prerequisites", "vc_redist")
        if val and val.lower() in ("1", "true", "yes"):
            return None
    if build_resolved:
        root = Path(build_resolved)
        try:
            for p in root.rglob("*"):
                if p.is_file() and "vc_redist" in p.name.lower():
                    return None
        except OSError:
            pass
    return _finding(
        cid,
        cat,
        sev,
        str(project_root / "Config" / "DefaultEngine.ini"),
        "not_detected",
        "Enable IncludePrerequisites / ship VC++ redistributable with staged build.",
        "Prerequisite / VC++ redistributable inclusion not detected.",
    )


def _check_install_size(build_resolved: str | None, cfg: dict[str, Any], cid: str, cat: str) -> dict[str, Any] | None:
    entry = checklist_entry(cfg, cid)
    sev = _coerce_severity(entry.get("severity") or _DEFAULT_SEVERITY.get(cid, "info"))
    if not build_resolved:
        return _finding(
            cid,
            cat,
            sev,
            "(build_path)",
            "absent",
            "Pass build_path to estimate install size or document size in ship plan.",
            "build_path not provided; install size not estimated.",
        )
    root = Path(build_resolved)
    total = 0
    n = 0
    try:
        for p in root.rglob("*"):
            if n > 200_000:
                break
            if p.is_file():
                try:
                    total += p.stat().st_size
                except OSError:
                    continue
                n += 1
    except OSError:
        return _finding(
            cid,
            cat,
            sev,
            build_resolved,
            "unreadable",
            "Ensure staged build directory is readable for size estimation.",
            "Could not walk build_path for size estimation.",
        )
    mb = total / (1024 * 1024)
    if mb <= 0:
        return _finding(
            cid,
            cat,
            sev,
            build_resolved,
            "0",
            "Verify staging output populated before cert scan.",
            "Staged build appears empty for size estimation.",
        )
    return None


def _dispatch(
    cid: str,
    project_root: Path,
    project_file: str,
    build_resolved: str | None,
    cfg: dict[str, Any],
    cat: str,
) -> dict[str, Any] | None:
    if cid == "legal.eula_present":
        return _check_eula(project_root, build_resolved, cfg, cid, cat)
    if cid == "legal.privacy_policy_present":
        return _check_privacy(project_root, cfg, cid, cat)
    if cid == "legal.age_rating_configured":
        return _check_age_rating(project_root, cfg, cid, cat)
    if cid == "metadata.game_description_set":
        return _check_game_description(project_root, cfg, cid, cat)
    if cid == "metadata.version_string_set":
        return _check_version_string(project_root, project_file, cfg, cid, cat)
    if cid == "metadata.store_assets_present":
        return _check_store_assets(project_root, cfg, cid, cat)
    if cid == "technical.min_os_version_set":
        return _check_min_os(project_root, cfg, cid, cat)
    if cid == "technical.controller_support_declared":
        return _check_controller(project_root, cfg, cid, cat)
    if cid == "technical.resolution_settings_valid":
        return _check_resolution(project_root, cfg, cid, cat)
    if cid == "technical.audio_settings_valid":
        return _check_audio(project_root, cfg, cid, cat)
    if cid == "packaging.redistrib_included":
        return _check_redist(project_root, build_resolved, cfg, cid, cat)
    if cid == "packaging.install_size_documented":
        return _check_install_size(build_resolved, cfg, cid, cat)
    return None


def cert_scan(
    project_path: str,
    build_path: str | None = None,
    target_platform: str = "Win64",
    target_store: str = "internal",
    build_config: str = "Shipping",
    config_path: str | None = None,
    caller: str = "user-direct-debug",
) -> dict[str, Any]:
    """Evaluate twelve advisory checklists; severities are info or warn only."""
    _ = build_config
    cfg_path_resolved = str(Path(config_path).expanduser().resolve()) if config_path else str(default_config_path())
    mode = _resolve_mode()
    hub_cfg = _load_config(config_path)
    memory_id: str | None = None

    if mode == "dry_run":
        return {
            "status": "pass",
            "mode": "dry_run",
            "project_path": project_path,
            "build_path": build_path,
            "target_store": target_store,
            "findings": [],
            "summary": {
                "total_checklists_evaluated": 12,
                "warn_count": 0,
                "info_count": 0,
                "skipped_count": 0,
            },
            "config_path": cfg_path_resolved,
            "memory_id": memory_id,
        }

    resolved_proj, err = validate_project_file(project_path)
    if err:
        return {
            "status": "warn",
            "mode": "live",
            "project_path": project_path,
            "build_path": build_path,
            "target_store": target_store,
            "findings": [
                _finding(
                    "advisory.project_path",
                    "metadata",
                    "warn",
                    project_path,
                    err,
                    "Provide a valid absolute .uproject path.",
                    "Project path validation failed.",
                ),
            ],
            "summary": {
                "total_checklists_evaluated": 12,
                "warn_count": 1,
                "info_count": 0,
                "skipped_count": 11,
            },
            "config_path": cfg_path_resolved,
            "memory_id": memory_id,
        }
    assert resolved_proj is not None

    project_root = Path(resolved_proj).parent
    cfg = _merge_project_config(hub_cfg, project_root)

    br, br_err = validate_optional_dir(build_path)
    if build_path and br_err:
        return {
            "status": "warn",
            "mode": "live",
            "project_path": resolved_proj,
            "build_path": build_path,
            "target_store": target_store,
            "findings": [
                _finding(
                    "advisory.build_path",
                    "metadata",
                    "warn",
                    str(build_path),
                    br_err,
                    "Omit build_path or pass a directory produced by cook-package staging.",
                    "build_path validation failed.",
                ),
            ],
            "summary": {
                "total_checklists_evaluated": 12,
                "warn_count": 1,
                "info_count": 0,
                "skipped_count": 11,
            },
            "config_path": cfg_path_resolved,
            "memory_id": memory_id,
        }

    findings: list[dict[str, Any]] = []
    skipped = 0

    if caller.strip() in _DENIED_CALLERS:
        return {
            "status": "warn",
            "mode": "live",
            "project_path": resolved_proj,
            "build_path": br,
            "target_store": target_store,
            "findings": [
                _finding(
                    "advisory.caller_scope",
                    "metadata",
                    "warn",
                    caller,
                    "denied_caller",
                    "Use agent-ship-cert, agent-ship-package, or user-direct-debug for cert scans.",
                    "caller is not in the cert-game allowlist.",
                ),
            ],
            "summary": {
                "total_checklists_evaluated": 12,
                "warn_count": 1,
                "info_count": 0,
                "skipped_count": 12,
            },
            "config_path": cfg_path_resolved,
            "memory_id": memory_id,
        }

    for cid, cat, default_applies in CHECKLIST_ORDER:
        entry = checklist_entry(cfg, cid)
        merged_applies: dict[str, Any] = {}
        if default_applies:
            merged_applies.update(default_applies)
        at = entry.get("applies_to")
        if isinstance(at, dict):
            merged_applies.update(at)
        synthetic = {**entry, "applies_to": merged_applies} if merged_applies else entry
        if not checklist_on(entry):
            skipped += 1
            continue
        if not checklist_applies(synthetic, target_store=target_store, target_platform=target_platform):
            skipped += 1
            continue
        res = _dispatch(cid, project_root, resolved_proj, br, cfg, cat)
        if res:
            findings.append(res)

    findings.sort(key=lambda f: (f["category"], f["checklist_id"]))

    warn_c = sum(1 for f in findings if f["severity"] == "warn")
    info_c = sum(1 for f in findings if f["severity"] == "info")
    if warn_c:
        top = "warn"
    elif info_c:
        top = "info"
    else:
        top = "pass"

    return {
        "status": top,
        "mode": "live",
        "project_path": resolved_proj,
        "build_path": br,
        "target_store": target_store,
        "findings": findings,
        "summary": {
            "total_checklists_evaluated": 12,
            "warn_count": warn_c,
            "info_count": info_c,
            "skipped_count": skipped,
        },
        "config_path": cfg_path_resolved,
        "memory_id": memory_id,
    }
