"""MCP tool: evaluate a single /ship pipeline guard (dispatch to rule engines)."""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from types import ModuleType
from typing import Any

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def _hub_root_from_here() -> Path:
    return Path(__file__).resolve().parents[4]


def _load_guard_common() -> ModuleType:
    """Load play-guards ``_guard_common`` (shared helpers) from disk."""
    path = _hub_root_from_here() / ".cursor/skills/play-guards/tools/_guard_common.py"
    if not path.is_file():
        raise FileNotFoundError(f"missing shared guard common: {path}")
    name = "cuebert_play_guard_common_shared"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"spec failed for {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_gc: ModuleType | None = None


def _gc_mod() -> ModuleType:
    global _gc
    if _gc is None:
        _gc = _load_guard_common()
    return _gc


def default_ship_guards_config_path() -> Path:
    return _gc_mod().find_hub_root() / ".cuebert" / "config" / "ship-guards.yaml"


def _override_fields(caller: str) -> tuple[bool, str]:
    if caller.strip() == "user-direct-debug":
        return True, "--override=accept-risk"
    return False, "n/a"


def _dispatch_prod_readiness(
    project_path: str,
    target_platform: str,
    target_store: str,
    build_config: str,
    config_path: str | None,
    caller: str,
) -> dict[str, Any]:
    gc = _gc_mod()
    mod = gc.import_skill_tool_module("prod-readiness-game", "prod_readiness_scan")
    fn = getattr(mod, "prod_readiness_scan", None)
    if not callable(fn):
        return {"error": "prod_readiness_scan not callable", "status": "error"}
    return fn(
        project_path,
        target_platform=target_platform,
        target_store=target_store,
        build_config=build_config,
        config_path=config_path,
        caller=caller,
    )


def _dispatch_qa_resilience(
    log_path: str | None,
    config_path: str | None,
    caller: str,
) -> dict[str, Any]:
    if not log_path or not str(log_path).strip():
        return {
            "status": "error",
            "error": "log_path required for ship.qa_resilience",
            "findings": [],
        }
    gc = _gc_mod()
    mod = gc.import_skill_tool_module("qa-resilience-game", "qa_resilience_scan")
    fn = getattr(mod, "qa_resilience_scan", None)
    if not callable(fn):
        return {"error": "qa_resilience_scan not callable", "status": "error"}
    return fn(log_path, config_path=config_path, caller=caller)


def _dispatch_cook_package(
    project_path: str,
    target_platform: str,
    build_path: str | None,
    config_path: str | None,
) -> dict[str, Any]:
    gc = _gc_mod()
    try:
        mod_run = gc.import_skill_tool_module("cook-package-game", "cook_package_run")
        fn = getattr(mod_run, "cook_package_run", None)
        if callable(fn):
            return fn(
                project_path=project_path,
                build_path=build_path,
                target_platform=target_platform,
                config_path=config_path,
                status_only=True,
            )
    except ImportError:
        pass
    try:
        mod_c = gc.import_skill_tool_module("cook-package-game", "_cook_common")
    except ImportError as exc:
        return {"status": "error", "error": f"cook-package skill unavailable: {exc}", "phases": []}
    load_cfg = getattr(mod_c, "_load_config", None)
    get_plat = getattr(mod_c, "_get_platform_config", None)
    plat_stat = getattr(mod_c, "_platform_runnable_status", None)
    if not all(callable(x) for x in (load_cfg, get_plat, plat_stat)):
        return {"status": "error", "error": "cook-package _cook_common incomplete", "phases": []}
    cfg = load_cfg(config_path)
    row = get_plat(cfg, target_platform)
    ok, reason = plat_stat(row)
    if ok:
        return {
            "status": "pass",
            "mode": "status_only",
            "detail": "platform_matrix allows cook (synthetic status check)",
            "phases": [{"name": "cook", "status": "skipped"}, {"name": "stage", "status": "skipped"}, {"name": "package", "status": "skipped"}],
        }
    return {
        "status": "fail",
        "mode": "status_only",
        "detail": reason,
        "phases": [{"name": "cook", "status": "fail", "reason": reason}],
    }


def _dispatch_cert(project_path: str, config_path: str | None, caller: str) -> dict[str, Any]:
    gc = _gc_mod()
    try:
        mod = gc.import_skill_tool_module("cert-game", "cert_scan")
    except ImportError:
        return {
            "status": "info",
            "findings": [],
            "detail": "cert-game cert_scan not available (skill missing)",
            "project_path": project_path,
        }
    fn = getattr(mod, "cert_scan", None)
    if not callable(fn):
        return {
            "status": "info",
            "findings": [],
            "detail": "cert_scan not callable on cert-game module",
            "project_path": project_path,
        }
    try:
        return fn(project_path=project_path, config_path=config_path, caller=caller)
    except TypeError:
        return fn(project_path, config_path=config_path, caller=caller)


def _generic_guard_check(
    guard_id: str,
    project_path: str,
    log_path: str | None,
    build_path: str | None,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    guards = cfg.get("guards") or {}
    entry = guards.get(guard_id) if isinstance(guards, dict) else None
    if not isinstance(entry, dict):
        entry = {}
    enabled = entry.get("enabled", True)
    if enabled is False:
        return {"status": "pass", "detail": f"{guard_id} disabled in config", "severity": "info"}
    # Spec-only placeholders: bounded filesystem hints
    root = Path(project_path).expanduser().resolve(strict=False)
    if guard_id == "guard.package.exists" and build_path:
        try:
            bp = Path(build_path).expanduser().resolve(strict=False)
            gc = _gc_mod()
            gc._validate_path(bp, root)
            exists = bp.is_file() or bp.is_dir()
        except ValueError:
            exists = False
        if exists:
            return {"status": "pass", "detail": "build_path exists under project", "severity": "info"}
        return {"status": "fail", "detail": "build_path missing", "severity": "fail"}
    if guard_id == "guard.cook.exit_code" and log_path:
        lp = Path(log_path).expanduser()
        if lp.is_file():
            return {"status": "pass", "detail": "log present for post-cook review (stub)", "severity": "info"}
        return {"status": "warn", "detail": "log_path not a file", "severity": "warn"}
    sev = str(entry.get("default_severity") or "info")
    return {
        "status": "pass",
        "detail": f"generic stub for {guard_id} (spec_only_as_info path)",
        "severity": sev,
    }


def ship_guard_evaluate(
    project_path: str,
    guard_id: str,
    phase_boundary: str,
    log_path: str | None = None,
    build_path: str | None = None,
    target_platform: str = "Win64",
    target_store: str = "internal",
    build_config: str = "Shipping",
    config_path: str | None = None,
    caller: str = "user-direct-debug",
) -> dict[str, Any]:
    """Dispatch *guard_id* to the appropriate ship rule engine or generic config check."""
    cfg_path = config_path or str(default_ship_guards_config_path())
    cfg = _gc_mod()._load_yaml_config(cfg_path)
    override_avail, override_mech = _override_fields(caller)

    engine: dict[str, Any] = {}
    detail = ""
    severity = str(
        (cfg.get("guards") or {}).get(guard_id, {}).get("default_severity", "info")
        if isinstance(cfg.get("guards"), dict)
        else "info",
    )
    status = "pass"

    if guard_id == "ship.prod_readiness":
        engine = _dispatch_prod_readiness(
            project_path, target_platform, target_store, build_config, config_path, caller
        )
        rs = str(engine.get("status", ""))
        if rs == "pass":
            status = "pass"
        elif rs == "warn":
            status = "pass"
            detail = "prod_readiness reported warn-level findings"
        elif rs == "error":
            status = "fail"
            detail = str(engine.get("error") or "prod_readiness_scan error")
        else:
            status = "reject"
            detail = str(engine.get("summary") or engine.get("error") or "prod_readiness failed")
        severity = "reject" if status == "reject" else "fail" if status == "fail" else "info"

    elif guard_id == "ship.qa_resilience":
        engine = _dispatch_qa_resilience(log_path, config_path, caller)
        rs = str(engine.get("status", ""))
        if rs == "pass":
            status = "pass"
        elif rs == "warn":
            status = "pass"
            detail = "qa_resilience warnings only"
        elif rs in {"error", "fail"}:
            status = "reject"
            detail = str(engine.get("error") or "qa_resilience_scan failed")
        else:
            status = "fail"
            detail = rs or "unexpected qa_resilience status"
        severity = "reject" if status == "reject" else "error" if status == "fail" else "info"

    elif guard_id == "ship.cook_package":
        engine = _dispatch_cook_package(project_path, target_platform, build_path, config_path)
        rs = str(engine.get("status", ""))
        if rs in {"pass", "dry_run"}:
            status = "pass"
        elif rs == "fail":
            status = "fail"
            detail = str(engine.get("detail") or engine.get("error") or "cook_package status fail")
        else:
            status = "fail"
            detail = rs or "cook_package uncertain status"
        severity = "fail" if status == "fail" else "info"

    elif guard_id == "ship.cert_advisory":
        engine = _dispatch_cert(project_path, config_path, caller)
        status = "advisory"
        detail = str(engine.get("detail") or "cert advisory scan complete")
        severity = "advisory"

    else:
        engine = _generic_guard_check(guard_id, project_path, log_path, build_path, cfg)
        gs = str(engine.get("status", "pass"))
        status = gs if gs in {"pass", "fail", "reject", "advisory", "warn"} else "pass"
        detail = str(engine.get("detail", ""))
        severity = str(engine.get("severity", severity))

    if guard_id != "ship.cert_advisory" and status == "advisory":
        status = "pass"

    return {
        "guard_id": guard_id,
        "phase_boundary": phase_boundary,
        "status": status,
        "severity": severity,
        "engine_result": engine,
        "override_available": override_avail,
        "override_mechanism": override_mech,
        "detail": detail or f"ship guard {guard_id} evaluated",
    }


def register(mcp: FastMCP) -> None:
    """Register ``ship_guard_evaluate`` MCP tool."""

    @mcp.tool(name="ship_guard_evaluate")
    def ship_guard_evaluate_tool(
        project_path: str,
        guard_id: str,
        phase_boundary: str,
        log_path: str | None = None,
        build_path: str | None = None,
        target_platform: str = "Win64",
        target_store: str = "internal",
        build_config: str = "Shipping",
        config_path: str | None = None,
        caller: str = "user-direct-debug",
    ) -> dict[str, Any]:
        """Evaluate one ship guard (dispatch to prod-readiness, qa-resilience, cook-package, cert, or generic)."""
        return ship_guard_evaluate(
            project_path,
            guard_id,
            phase_boundary,
            log_path=log_path,
            build_path=build_path,
            target_platform=target_platform,
            target_store=target_store,
            build_config=build_config,
            config_path=config_path,
            caller=caller,
        )
