"""MCP tool: scan Unreal project configs for production-readiness."""

from __future__ import annotations

import configparser
import json
import logging
import re
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from _readiness_common import (
    RULE_CONFIG_ALIASES,
    _load_config,
    _read_ini_file,
    _read_uproject,
    _resolve_mode,
    _rule_on,
    default_config_path,
    ensure_under_project,
    find_uproject,
    read_text_capped,
    rule_applies,
    rule_entry_for,
    troubleshoot_commit_safe,
)

logger = logging.getLogger(__name__)

_RULE_COUNT = 14

_DEFAULT_SEVERITY: dict[str, str] = {
    "readiness.debug_symbols_stripped": "reject",
    "readiness.shipping_config": "reject",
    "readiness.console_output_disabled": "reject",
    "readiness.crash_reporter_enabled": "reject",
    "readiness.pak_file_signing": "reject",
    "readiness.encryption_enabled": "reject",
    "readiness.version_set": "reject",
    "readiness.display_name_set": "reject",
    "readiness.default_map_set": "reject",
    "readiness.splash_screens_set": "info",
    "readiness.icon_set": "reject",
    "readiness.privacy_policy_url": "info",
    "readiness.age_rating_configured": "info",
    "readiness.banned_plugins_absent": "reject",
}

_BANNED_PLUGIN_SUBSTR = (
    "Editor",
    "PythonScript",
    "SequencerScripting",
    "GameplayTagsEditor",
    "DataValidation",
)

def _severity_for(rule_id: str, config: dict[str, Any]) -> str:
    entry = rule_entry_for(rule_id, config)
    s = (entry.get("severity") or "").strip().lower()
    if s in {"info", "reject"}:
        return s
    alias = RULE_CONFIG_ALIASES.get(rule_id, "")
    if alias:
        rules = config.get("rules") or {}
        if isinstance(rules, dict) and alias in rules and isinstance(rules[alias], dict):
            s2 = str(rules[alias].get("severity", "")).strip().lower()
            if s2 == "reject" or s2 == "info":
                return s2
            if s2 == "warn":
                return "info"
    return _DEFAULT_SEVERITY.get(rule_id, "reject")


def _apply_spec_flag(sev: str, config: dict[str, Any]) -> str:
    if config.get("spec_only_as_info") and sev == "reject":
        return "info"
    return sev


def _finding(
    rule_id: str,
    severity: str,
    file_inspected: str,
    key_checked: str,
    current_value: str | None,
    expected: str,
    detail: str,
) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "severity": severity,
        "file_inspected": file_inspected,
        "key_checked": key_checked,
        "current_value": current_value,
        "expected": expected,
        "detail": detail,
    }


def _synthetic_findings() -> list[dict[str, Any]]:
    return [
        _finding(
            "readiness.display_name_set",
            "reject",
            "Config/DefaultGame.ini",
            "ProjectName",
            "",
            "non-empty title",
            "dry_run: missing ProjectName on hypothetical project",
        ),
        _finding(
            "readiness.privacy_policy_url",
            "info",
            "Config/DefaultGame.ini",
            "PrivacyPolicy",
            None,
            "https URL recommended",
            "dry_run: advisory privacy URL",
        ),
        _finding(
            "readiness.splash_screens_set",
            "info",
            "Config/DefaultGame.ini",
            "StartupMovies",
            None,
            "at least one splash or movie entry",
            "dry_run: splash paths not verified",
        ),
    ]


def _rollup(findings: list[dict[str, Any]]) -> str:
    has_reject = any(f.get("severity") == "reject" for f in findings)
    has_info = any(f.get("severity") == "info" for f in findings)
    if has_reject:
        return "fail"
    if has_info:
        return "warn"
    return "pass"


def _summary(findings: list[dict[str, Any]]) -> dict[str, int]:
    rj = sum(1 for f in findings if f.get("severity") == "reject")
    inf = sum(1 for f in findings if f.get("severity") == "info")
    return {"critical": rj, "error": 0, "warn": 0, "info": inf}


def prod_readiness_scan(
    project_path: str,
    target_platform: str = "Win64",
    target_store: str = "internal",
    build_config: str = "Shipping",
    config_path: str | None = None,
    caller: str = "user-direct-debug",
) -> dict[str, Any]:
    """Scan Unreal project configs for production readiness; return structured envelope."""
    memory_id: str | None = None
    cfg_disp = config_path or str(default_config_path())
    try:
        config = _load_config(config_path)
    except Exception as exc:
        return {
            "status": "error",
            "mode": _resolve_mode(),
            "project_path": project_path,
            "target_platform": target_platform,
            "target_store": target_store,
            "build_config": build_config,
            "rules_evaluated": _RULE_COUNT,
            "findings_count": 0,
            "findings": [],
            "summary": {"critical": 0, "error": 0, "warn": 0, "info": 0},
            "thresholds_applied": {
                "target_platform": target_platform,
                "target_store": target_store,
                "build_config": build_config,
            },
            "config_path": cfg_disp,
            "memory_id": None,
            "error": f"config_load_failed: {exc}",
        }

    mode = _resolve_mode()
    thresholds_applied = {
        "target_platform": target_platform,
        "target_store": target_store,
        "build_config": build_config,
    }

    if mode == "dry_run":
        findings = [
            {**f, "severity": _apply_spec_flag(str(f["severity"]), config)}
            for f in _synthetic_findings()
        ]
        status = _rollup(findings)
        return {
            "status": status,
            "mode": "dry_run",
            "project_path": project_path,
            "target_platform": target_platform,
            "target_store": target_store,
            "build_config": build_config,
            "rules_evaluated": _RULE_COUNT,
            "findings_count": len(findings),
            "findings": findings,
            "summary": _summary(findings),
            "thresholds_applied": thresholds_applied,
            "config_path": cfg_disp,
            "memory_id": memory_id,
        }

    try:
        pp = Path(project_path).expanduser()
        if pp.suffix.lower() == ".uproject":
            uproj_path = pp.resolve()
            root = uproj_path.parent.resolve()
        else:
            root = pp.resolve()
            uproj_path = find_uproject(root)
            if uproj_path is None:
                raise FileNotFoundError("no_uproject")
    except (OSError, RuntimeError, FileNotFoundError) as exc:
        return {
            "status": "error",
            "mode": "live",
            "project_path": project_path,
            "target_platform": target_platform,
            "target_store": target_store,
            "build_config": build_config,
            "rules_evaluated": _RULE_COUNT,
            "findings_count": 0,
            "findings": [],
            "summary": {"critical": 0, "error": 0, "warn": 0, "info": 0},
            "thresholds_applied": thresholds_applied,
            "config_path": cfg_disp,
            "memory_id": None,
            "error": f"project_path_resolve_failed: {exc}",
        }

    uproj = uproj_path
    if uproj is None or not ensure_under_project(uproj, root):
        return {
            "status": "error",
            "mode": "live",
            "project_path": project_path,
            "target_platform": target_platform,
            "target_store": target_store,
            "build_config": build_config,
            "rules_evaluated": _RULE_COUNT,
            "findings_count": 0,
            "findings": [],
            "summary": {"critical": 0, "error": 0, "warn": 0, "info": 0},
            "thresholds_applied": thresholds_applied,
            "config_path": cfg_disp,
            "memory_id": None,
            "error": "uproject_not_found",
        }

    cfg_dir = root / "Config"
    path_engine = cfg_dir / "DefaultEngine.ini"
    path_game = cfg_dir / "DefaultGame.ini"
    findings: list[dict[str, Any]] = []

    # --- readiness.shipping_config ---
    if _rule_on("readiness.shipping_config", config) and rule_applies(
        "readiness.shipping_config",
        config,
        target_platform=target_platform,
        target_store=target_store,
        build_config=build_config,
    ):
        if build_config != "Shipping":
            findings.append(
                _finding(
                    "readiness.shipping_config",
                    _severity_for("readiness.shipping_config", config),
                    str(root),
                    "build_config",
                    build_config,
                    "Shipping",
                    "Production readiness expects Shipping build configuration",
                ),
            )
        if (
            build_config == "Shipping"
            and target_store in {"steam", "epic", "gog"}
            and path_game.is_file()
        ):
            raw_pkg, _ = read_text_capped(path_game)
            if raw_pkg and not re.search(
                r"(?im)^\s*Build\s*=\s*BUILD_Shipping\s*$",
                raw_pkg,
            ):
                findings.append(
                    _finding(
                        "readiness.shipping_config",
                        _severity_for("readiness.shipping_config", config),
                        str(path_game),
                        "Build",
                        None,
                        "BUILD_Shipping",
                        "Packaging settings must select BUILD_Shipping for store targets",
                    ),
                )

    # Parse INIs when present
    cp_engine: configparser.ConfigParser | None = None
    cp_game: configparser.ConfigParser | None = None
    try:
        if path_engine.is_file() and ensure_under_project(path_engine, root):
            cp_engine = _read_ini_file(path_engine)
    except OSError:
        cp_engine = None
    try:
        if path_game.is_file() and ensure_under_project(path_game, root):
            cp_game = _read_ini_file(path_game)
    except OSError:
        cp_game = None

    sec_proj = "/Script/EngineSettings.GeneralProjectSettings"
    sec_maps = "/Script/EngineSettings.GameMapsSettings"
    sec_pkg = "/Script/UnrealEd.ProjectPackagingSettings"

    def _get(cp: configparser.ConfigParser | None, sec: str, key: str) -> str | None:
        if cp is None or not cp.has_section(sec):
            return None
        if cp.has_option(sec, key):
            return cp.get(sec, key).strip()
        return None

    # readiness.display_name_set
    if _rule_on("readiness.display_name_set", config):
        pn = _get(cp_game, sec_proj, "ProjectName")
        if not pn:
            raw_g, _e = read_text_capped(path_game) if path_game.is_file() else (None, "missing")
            if raw_g and 'ProjectName=' in raw_g:
                for line in raw_g.splitlines():
                    if "ProjectName=" in line:
                        pn = line.split("=", 1)[-1].strip()
                        break
        if not pn or not pn.strip():
            findings.append(
                _finding(
                    "readiness.display_name_set",
                    _severity_for("readiness.display_name_set", config),
                    str(path_game),
                    "ProjectName",
                    pn or "",
                    "non-empty",
                    "ProjectName must be set for ship metadata",
                ),
            )

    # readiness.version_set (ProjectVersion INI + EngineAssociation uproject)
    if _rule_on("readiness.version_set", config):
        pv = _get(cp_game, sec_proj, "ProjectVersion")
        ver_ok = False
        if pv and re.match(r"^[0-9]+(?:\.[0-9]+){0,3}$", pv.strip()):
            ver_ok = True
        try:
            udata = _read_uproject(uproj)
            eng = udata.get("EngineAssociation")
            if isinstance(eng, str) and eng.strip():
                ver_ok = True
        except (OSError, json.JSONDecodeError, TypeError):
            pass
        if not ver_ok:
            findings.append(
                _finding(
                    "readiness.version_set",
                    _severity_for("readiness.version_set", config),
                    str(path_game),
                    "ProjectVersion",
                    pv,
                    "Major[.Minor[.Patch]] or EngineAssociation in .uproject",
                    "Project version not parseable",
                ),
            )

    # readiness.default_map_set
    if _rule_on("readiness.default_map_set", config):
        gm = _get(cp_engine, sec_maps, "GameDefaultMap") or _get(
            cp_engine,
            sec_maps,
            "EditorStartupMap",
        )
        if not gm or gm.strip() in {"", "/Engine/Maps/Templates/Template_Default", "/Game/Maps/Entry"}:
            findings.append(
                _finding(
                    "readiness.default_map_set",
                    _severity_for("readiness.default_map_set", config),
                    str(path_engine),
                    "GameDefaultMap",
                    gm,
                    "non-empty production map path",
                    "Default game map should be set for ship",
                ),
            )

    # readiness.crash_reporter_enabled
    if _rule_on("readiness.crash_reporter_enabled", config) and rule_applies(
        "readiness.crash_reporter_enabled",
        config,
        target_platform=target_platform,
        target_store=target_store,
        build_config=build_config,
    ):
        cr = _get(cp_game, sec_pkg, "bIncludeCrashReporter")
        ok = cr and re.match(r"(?i)^true$", cr)
        if target_store == "internal" and cr and re.match(r"(?i)^false$", cr):
            ok = True
        if not ok:
            findings.append(
                _finding(
                    "readiness.crash_reporter_enabled",
                    _severity_for("readiness.crash_reporter_enabled", config),
                    str(path_game),
                    "bIncludeCrashReporter",
                    cr,
                    "True",
                    "Crash reporter should be enabled for distribution builds",
                ),
            )

    # readiness.console_output_disabled (bUseLoggingInShipping should be false)
    if (
        _rule_on("readiness.console_output_disabled", config)
        and rule_applies(
            "readiness.console_output_disabled",
            config,
            target_platform=target_platform,
            target_store=target_store,
            build_config=build_config,
        )
    ):
        raw_e, _ = read_text_capped(path_engine) if path_engine.is_file() else (None, None)
        bad = bool(
            raw_e
            and re.search(r"(?im)^\s*bUseLoggingInShipping\s*=\s*True\s*$", raw_e),
        )
        if bad:
            findings.append(
                _finding(
                    "readiness.console_output_disabled",
                    _severity_for("readiness.console_output_disabled", config),
                    str(path_engine),
                    "bUseLoggingInShipping",
                    "True",
                    "False",
                    "Console logging in shipping should be disabled",
                ),
            )

    # readiness.pak_file_signing
    if _rule_on("readiness.pak_file_signing", config):
        raw_e, _ = read_text_capped(path_engine) if path_engine.is_file() else (None, None)
        signed = False
        if raw_e and (
            re.search(r"(?im)^\s*bUsePakSigningKey\s*=\s*True\s*$", raw_e)
            or "PakSigningKey" in raw_e
            or re.search(r"(?im)^\s*bPakSigned\s*=\s*True\s*$", raw_e)
        ):
            signed = True
        if target_store in {"steam", "epic", "gog"} and not signed:
            findings.append(
                _finding(
                    "readiness.pak_file_signing",
                    _severity_for("readiness.pak_file_signing", config),
                    str(path_engine),
                    "bUsePakSigningKey|PakSigningKey",
                    None,
                    "enabled for store distribution",
                    "Pak signing not detected in DefaultEngine.ini",
                ),
            )

    # readiness.encryption_enabled
    if _rule_on("readiness.encryption_enabled", config) and target_store in {"steam", "epic", "gog"}:
        raw_e, _ = read_text_capped(path_engine) if path_engine.is_file() else (None, None)
        enc = bool(
            raw_e
            and (
                re.search(r"(?im)^\s*bDataCryptoEnabled\s*=\s*True\s*$", raw_e)
                or "EncryptionKey" in raw_e
                or "PakEncryptionKey" in raw_e
            ),
        )
        if not enc:
            findings.append(
                _finding(
                    "readiness.encryption_enabled",
                    _severity_for("readiness.encryption_enabled", config),
                    str(path_engine),
                    "EncryptionKey|bDataCryptoEnabled",
                    None,
                    "encryption configured for store builds",
                    "Pak encryption not detected",
                ),
            )

    # readiness.splash_screens_set
    if _rule_on("readiness.splash_screens_set", config):
        raw_g, _ = read_text_capped(path_game) if path_game.is_file() else (None, None)
        has_splash = bool(
            raw_g
            and (
                re.search(r"(?im)^\s*StartupMovies\s*=", raw_g)
                or re.search(r"(?im)^\s*MobileSplashScreen\s*=", raw_g)
                or re.search(r"(?im)^\s*SplashScreen\s*=", raw_g)
            ),
        )
        if not has_splash:
            findings.append(
                _finding(
                    "readiness.splash_screens_set",
                    "info",
                    str(path_game),
                    "StartupMovies|MobileSplashScreen",
                    None,
                    "at least one splash entry",
                    "No splash / startup movie keys found (advisory)",
                ),
            )

    # readiness.icon_set
    if _rule_on("readiness.icon_set", config):
        icon = _get(cp_game, sec_proj, "GameIcon")
        raw_g, _ = read_text_capped(path_game) if path_game.is_file() else (None, None)
        if not icon and raw_g:
            m = re.search(r"(?im)^\s*GameIcon\s*=\s*(.+)\s*$", raw_g)
            if m:
                icon = m.group(1).strip()
        if not icon or icon in {"", "None"}:
            findings.append(
                _finding(
                    "readiness.icon_set",
                    _severity_for("readiness.icon_set", config),
                    str(path_game),
                    "GameIcon",
                    icon,
                    "non-empty icon path",
                    "Game icon not configured",
                ),
            )

    # readiness.privacy_policy_url
    if _rule_on("readiness.privacy_policy_url", config):
        priv = _get(cp_game, sec_proj, "PrivacyPolicy")
        if not priv and path_game.is_file():
            raw_g, _ = read_text_capped(path_game)
            if raw_g:
                m = re.search(r"(?im)^\s*PrivacyPolicy\s*=\s*(.+)\s*$", raw_g)
                if m:
                    priv = m.group(1).strip()
        ok = bool(priv and (priv.startswith("http://") or priv.startswith("https://")))
        if not ok:
            findings.append(
                _finding(
                    "readiness.privacy_policy_url",
                    "info",
                    str(path_game),
                    "PrivacyPolicy",
                    priv,
                    "https:// URL",
                    "Privacy policy URL missing or not http(s)",
                ),
            )

    # readiness.age_rating_configured
    if _rule_on("readiness.age_rating_configured", config):
        raw_g, _ = read_text_capped(path_game) if path_game.is_file() else (None, None)
        has_age = bool(
            raw_g
            and (
                re.search(r"(?im)^\s*AgeRating\s*=", raw_g)
                or re.search(r"(?im)^\s*AgeRatingQueue\s*=", raw_g)
                or re.search(r"(?im)^\s*IARC\s*=", raw_g)
            ),
        )
        if not has_age:
            findings.append(
                _finding(
                    "readiness.age_rating_configured",
                    "info",
                    str(path_game),
                    "AgeRating|IARC",
                    None,
                    "age rating fields present",
                    "No age rating configuration detected (advisory)",
                ),
            )

    # readiness.debug_symbols_stripped
    if _rule_on("readiness.debug_symbols_stripped", config) and build_config == "Shipping":
        bad_sym = False
        for bpath in root.rglob("*.Build.cs"):
            if not bpath.is_file() or not ensure_under_project(bpath, root):
                continue
            txt, err = read_text_capped(bpath)
            if err or not txt:
                continue
            if re.search(r"\bbUsePDBFiles\s*=\s*true\b", txt, re.IGNORECASE):
                bad_sym = True
                break
            if re.search(r"\bbRetainPublicSymbols\s*=\s*true\b", txt, re.IGNORECASE):
                bad_sym = True
                break
        if bad_sym:
            findings.append(
                _finding(
                    "readiness.debug_symbols_stripped",
                    _severity_for("readiness.debug_symbols_stripped", config),
                    str(root),
                    "bUsePDBFiles|bRetainPublicSymbols",
                    "true",
                    "false for Shipping",
                    "Debug symbols retention enabled in Build.cs",
                ),
            )

    # readiness.banned_plugins_absent
    if _rule_on("readiness.banned_plugins_absent", config) and build_config == "Shipping":
        try:
            udata = _read_uproject(uproj)
            plugins = udata.get("Plugins") or []
            bad_p: list[str] = []
            if isinstance(plugins, list):
                for pl in plugins:
                    if not isinstance(pl, dict):
                        continue
                    name = str(pl.get("Name", ""))
                    en = pl.get("Enabled", True)
                    if not en:
                        continue
                    for sub in _BANNED_PLUGIN_SUBSTR:
                        if sub.lower() in name.lower():
                            bad_p.append(name)
                            break
            if bad_p:
                findings.append(
                    _finding(
                        "readiness.banned_plugins_absent",
                        _severity_for("readiness.banned_plugins_absent", config),
                        str(uproj),
                        "Plugins",
                        json.dumps(bad_p),
                        "no editor-only plugins enabled for Shipping",
                        "Editor or dev plugins still enabled",
                    ),
                )
        except (OSError, json.JSONDecodeError, TypeError):
            pass

    # Normalize severities with spec flag (reject -> info)
    norm_findings: list[dict[str, Any]] = []
    for f in findings:
        sev = str(f.get("severity", ""))
        norm_findings.append({**f, "severity": _apply_spec_flag(sev, config)})

    status = _rollup(norm_findings)
    summary = _summary(norm_findings)

    if status == "fail":
        mem = troubleshoot_commit_safe(
            "prod_readiness_scan fail",
            [f for f in norm_findings if f.get("severity") == "reject"],
            tags=f"prod_readiness|error|caller={caller}",
            agent="agent-prod-readiness-game",
            project=str(root),
        )
    elif status == "warn":
        mem = troubleshoot_commit_safe(
            "prod_readiness_scan warn",
            [f.get("rule_id") for f in norm_findings],
            tags=f"prod_readiness|info|caller={caller}",
            agent="agent-prod-readiness-game",
            project=str(root),
        )
    else:
        mem = {}
    if mem.get("status") == "ok" and mem.get("id"):
        memory_id = str(mem["id"])

    return {
        "status": status,
        "mode": "live",
        "project_path": str(root),
        "target_platform": target_platform,
        "target_store": target_store,
        "build_config": build_config,
        "rules_evaluated": _RULE_COUNT,
        "findings_count": len(norm_findings),
        "findings": norm_findings,
        "summary": summary,
        "thresholds_applied": thresholds_applied,
        "config_path": cfg_disp,
        "memory_id": memory_id,
    }


def register(mcp: FastMCP) -> None:
    """Register ``prod_readiness_scan`` MCP tool."""

    @mcp.tool(name="prod_readiness_scan")
    def prod_readiness_scan_tool(
        project_path: str,
        target_platform: str = "Win64",
        target_store: str = "internal",
        build_config: str = "Shipping",
        config_path: str | None = None,
        caller: str = "user-direct-debug",
    ) -> dict[str, Any]:
        """Scan Unreal project configs for production readiness."""
        return prod_readiness_scan(
            project_path,
            target_platform=target_platform,
            target_store=target_store,
            build_config=build_config,
            config_path=config_path,
            caller=caller,
        )


