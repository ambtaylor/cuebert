"""MCP tool: orchestrate Unreal UAT BuildCookRun cook / stage / package phases."""

from __future__ import annotations

import importlib.util
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Callable

from _cook_common import (
    _get_platform_config,
    _load_config,
    _platform_runnable_status,
    _resolve_mode,
    _validate_project_path,
    default_config_path,
    find_hub_root,
    troubleshoot_commit_safe,
)

logger = logging.getLogger(__name__)

_DENIED_CALLERS = {"agent-play-qa"}


def _import_skill_tool(skill_name: str, module_name: str, func_name: str) -> Callable[..., Any]:
    """Dynamically import a function from another skill's tools."""
    skills_dir = Path(__file__).resolve().parent.parent.parent
    mod_path = skills_dir / skill_name / "tools" / f"{module_name}.py"
    if not mod_path.exists():
        raise ImportError(f"Skill tool not found: {mod_path}")
    spec = importlib.util.spec_from_file_location(module_name, str(mod_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create spec for {mod_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, func_name)


def _import_build_runner() -> Any:
    """Load unreal-build ``_build_runner`` (adds mcp lib to path for ``_vault``)."""
    hub = find_hub_root()
    lib = hub / ".cursor" / "mcp-server" / "lib"
    inserted_lib: str | None = None
    if lib.is_dir():
        s = str(lib)
        if s not in sys.path:
            sys.path.insert(0, s)
            inserted_lib = s

    skills_dir = Path(__file__).resolve().parent.parent.parent
    mod_path = skills_dir / "unreal-build" / "tools" / "_build_runner.py"
    if not mod_path.is_file():
        if inserted_lib:
            with suppress_path_remove(inserted_lib):
                pass
        raise ImportError(f"_build_runner not found: {mod_path}")
    spec = importlib.util.spec_from_file_location("cuebert_unreal_build_runner", str(mod_path))
    if spec is None or spec.loader is None:
        if inserted_lib:
            with suppress_path_remove(inserted_lib):
                pass
        raise ImportError(f"Could not load spec for {mod_path}")
    tools_dir = str(mod_path.parent)
    inserted_tools = False
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
        inserted_tools = True
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        if inserted_tools:
            with suppress_path_remove(tools_dir):
                pass
        if inserted_lib:
            with suppress_path_remove(inserted_lib):
                pass
    return mod


class suppress_path_remove:
    """Remove *path* from sys.path if present."""

    def __init__(self, path: str) -> None:
        self.path = path

    def __enter__(self) -> None:
        return None

    def __exit__(self, *exc: object) -> None:
        try:
            sys.path.remove(self.path)
        except ValueError:
            pass


def _expand_output_dir(template: str, project_path: str, target_platform: str, build_config: str) -> str:
    project_dir = str(Path(project_path).resolve().parent)
    return (
        template.replace("{project_dir}", project_dir)
        .replace("{target_platform}", target_platform)
        .replace("{build_config}", build_config)
    )


def _extras_from_row(row: dict[str, Any] | None) -> list[str]:
    if not row:
        return []
    raw = row.get("uat_extra_args")
    if isinstance(raw, list):
        return [str(x) for x in raw if str(x).strip()]
    return []


def _uat_cmd_vec(br: Any, uat_path: str, argv_tail: list[str]) -> list[str]:
    host = br._detect_platform()
    if host == "win":
        return [uat_path, *argv_tail]
    return ["/bin/bash", uat_path, *argv_tail]


def _log_excerpt_from_run(run: dict[str, Any], max_lines: int = 50) -> str:
    out = (run.get("stdout") or "") + "\n" + (run.get("stderr") or "")
    lines = [ln for ln in out.splitlines() if ln.strip()]
    tail = lines[-max_lines:] if len(lines) > max_lines else lines
    return "\n".join(tail)


def _synth_artifacts(project_path: str, target_platform: str, build_config: str, archive_dir: str) -> dict[str, Any]:
    base = Path(project_path).resolve().parent
    cooked = base / "Saved" / "Cooked" / target_platform
    return {
        "cooked_content": str(cooked) + ".synthesized",
        "staged_build": str(Path(archive_dir).resolve()) + ".synthesized",
        "package_size_mb": None,
    }


def _maybe_package_size_mb(staged_root: Path, target_platform: str) -> float | None:
    plat_dir = staged_root / target_platform
    root = plat_dir if plat_dir.is_dir() else staged_root
    if not root.is_dir():
        return None
    total = 0
    n = 0
    max_files = 200_000
    try:
        for p in root.rglob("*"):
            if n >= max_files:
                return round(total / (1024 * 1024), 2)
            if p.is_file():
                try:
                    total += p.stat().st_size
                except OSError:
                    continue
                n += 1
    except OSError:
        return None
    return round(total / (1024 * 1024), 2)


def cook_package_run(
    project_path: str,
    target_platform: str = "Win64",
    target_store: str = "internal",
    build_config: str = "Shipping",
    skip_cook: bool = False,
    skip_package: bool = False,
    timeout_s: int | None = None,
    config_path: str | None = None,
    caller: str = "user-direct-debug",
    *,
    build_path: str | None = None,
    status_only: bool = False,
) -> dict[str, Any]:
    """Run cook, stage, and package UAT phases (or synthetic dry-run) and return a phase envelope."""
    cfg_path_resolved = str(Path(config_path).expanduser().resolve()) if config_path else str(default_config_path())
    config = _load_config(config_path)
    mode = _resolve_mode()
    memory_id: str | None = None

    if caller.strip() in _DENIED_CALLERS:
        return {
            "status": "error",
            "mode": mode,
            "project_path": project_path,
            "target_platform": target_platform,
            "build_config": build_config,
            "phases": [],
            "artifacts": {"cooked_content": None, "staged_build": None, "package_size_mb": None},
            "config_path": cfg_path_resolved,
            "memory_id": None,
            "detail": f"caller {caller!r} is not allowed for cook-package-game",
        }

    resolved, err = _validate_project_path(project_path)
    if err:
        return {
            "status": "error",
            "mode": mode,
            "project_path": project_path,
            "target_platform": target_platform,
            "build_config": build_config,
            "phases": [],
            "artifacts": {"cooked_content": None, "staged_build": None, "package_size_mb": None},
            "config_path": cfg_path_resolved,
            "memory_id": None,
            "detail": err,
        }
    assert resolved is not None

    defaults = config.get("defaults") if isinstance(config.get("defaults"), dict) else {}
    compression = str(defaults.get("compression") or "zlib")
    tmpl = str(
        defaults.get("output_dir_template")
        or "{project_dir}/Saved/StagedBuilds/{target_platform}-{build_config}",
    )
    archive_dir = _expand_output_dir(tmpl, resolved, target_platform, build_config)
    cfg_timeout = defaults.get("timeout_s")
    try:
        t_cfg = int(cfg_timeout) if cfg_timeout is not None else 3600
    except (TypeError, ValueError):
        t_cfg = 3600
    phase_timeout = float(timeout_s if timeout_s is not None else t_cfg)

    row = _get_platform_config(config, target_platform)
    ok_plat, plat_reason = _platform_runnable_status(row)
    extras = _extras_from_row(row)

    if not ok_plat:
        return {
            "status": "fail",
            "mode": mode,
            "project_path": resolved,
            "target_platform": target_platform,
            "build_config": build_config,
            "phases": [],
            "artifacts": {"cooked_content": None, "staged_build": None, "package_size_mb": None},
            "config_path": cfg_path_resolved,
            "memory_id": None,
            "detail": f"skip: {plat_reason}",
        }

    if row and isinstance(row.get("supported_stores"), list):
        stores = [str(s).lower() for s in row["supported_stores"]]
        if target_store.lower() not in stores and target_store.lower() != "internal":
            return {
                "status": "fail",
                "mode": mode,
                "project_path": resolved,
                "target_platform": target_platform,
                "build_config": build_config,
                "phases": [],
                "artifacts": {"cooked_content": None, "staged_build": None, "package_size_mb": None},
                "config_path": cfg_path_resolved,
                "memory_id": None,
                "detail": f"skip: target_store {target_store!r} not in supported_stores for {target_platform}",
            }

    if status_only:
        _ = build_path
        return {
            "status": "pass",
            "mode": mode,
            "project_path": resolved,
            "target_platform": target_platform,
            "build_config": build_config,
            "phases": [
                {"name": "cook", "status": "skipped", "detail": "status_only gate"},
                {"name": "stage", "status": "skipped", "detail": "status_only gate"},
                {"name": "package", "status": "skipped", "detail": "status_only gate"},
            ],
            "artifacts": {"cooked_content": None, "staged_build": None, "package_size_mb": None},
            "config_path": cfg_path_resolved,
            "memory_id": None,
            "detail": "status_only: project and platform_matrix eligible; UAT not invoked",
        }

    if mode == "dry_run":
        phases_out: list[dict[str, Any]] = []
        if not skip_cook:
            phases_out.append(
                {"name": "cook", "status": "pass", "duration_s": 120.5, "exit_code": 0, "detail": "dry_run synthetic"},
            )
        else:
            phases_out.append(
                {"name": "cook", "status": "pass", "duration_s": 0.0, "exit_code": None, "detail": "skipped (skip_cook)"},
            )
        if not skip_package:
            phases_out.append(
                {"name": "stage", "status": "pass", "duration_s": 15.2, "exit_code": 0, "detail": "dry_run synthetic"},
            )
            phases_out.append(
                {"name": "package", "status": "pass", "duration_s": 8.7, "exit_code": 0, "detail": "dry_run synthetic"},
            )
        else:
            phases_out.append(
                {
                    "name": "stage",
                    "status": "pass",
                    "duration_s": 0.0,
                    "exit_code": None,
                    "detail": "skipped (skip_package)",
                },
            )
            phases_out.append(
                {
                    "name": "package",
                    "status": "pass",
                    "duration_s": 0.0,
                    "exit_code": None,
                    "detail": "skipped (skip_package)",
                },
            )
        arts = _synth_artifacts(resolved, target_platform, build_config, archive_dir)
        return {
            "status": "pass",
            "mode": "dry_run",
            "project_path": resolved,
            "target_platform": target_platform,
            "build_config": build_config,
            "phases": phases_out,
            "artifacts": arts,
            "config_path": cfg_path_resolved,
            "memory_id": memory_id,
        }

    # live
    phases_live: list[dict[str, Any]] = []
    try:
        br = _import_build_runner()
        unreal_build_target_impl = _import_skill_tool("unreal-build", "unreal_build_target", "_unreal_build_target_impl")
        _import_skill_tool("unreal-build", "unreal_run_commandlet", "_unreal_run_commandlet_impl")
    except Exception as exc:
        logger.warning("cook_package_run import unreal-build tools failed: %s", exc)
        mem = troubleshoot_commit_safe(
            "cook_package_run failed to import unreal-build delegation",
            {"error": str(exc), "project_path": resolved, "caller": caller},
            tags="cook-package-game,import_error",
            agent=caller,
            project=resolved,
        )
        if mem.get("status") == "ok" and mem.get("id"):
            memory_id = str(mem["id"])
        return {
            "status": "error",
            "mode": "live",
            "project_path": resolved,
            "target_platform": target_platform,
            "build_config": build_config,
            "phases": [],
            "artifacts": {"cooked_content": None, "staged_build": None, "package_size_mb": None},
            "config_path": cfg_path_resolved,
            "memory_id": memory_id,
            "detail": f"import error: {exc}",
        }

    eng_raw = br._resolve_engine_path()
    val = br._validate_engine_path(eng_raw) if eng_raw else {"valid": False, "reason": "no engine path"}
    uat = val.get("uat_path") if isinstance(val, dict) else None
    if not val.get("valid") or not uat:
        return {
            "status": "error",
            "mode": "live",
            "project_path": resolved,
            "target_platform": target_platform,
            "build_config": build_config,
            "phases": [],
            "artifacts": {"cooked_content": None, "staged_build": None, "package_size_mb": None},
            "config_path": cfg_path_resolved,
            "memory_id": None,
            "detail": val.get("reason") or "UAT path not available",
        }

    cwd = str(Path(resolved).parent)
    timeout = br._cap_timeout(phase_timeout)

    cooked_guess = Path(resolved).resolve().parent / "Saved" / "Cooked" / target_platform
    staged_guess = Path(archive_dir).resolve()

    if not skip_cook:
        stem = Path(resolved).stem
        pre = unreal_build_target_impl(
            resolved,
            stem,
            platform=target_platform,
            config=build_config,
            timeout_s=int(timeout),
            caller=caller,
        )
        pre_ok = pre.get("status") in ("pass", "dry_run")
        if not pre_ok:
            detail = _log_excerpt_from_run(
                {
                    "stdout": "",
                    "stderr": json.dumps(pre.get("error") or pre, ensure_ascii=False),
                },
            )
            phases_live.append(
                {
                    "name": "cook",
                    "status": "fail",
                    "duration_s": float(pre.get("duration_s") or 0.0),
                    "exit_code": pre.get("exit_code"),
                    "detail": f"unreal_build_target preflight failed: {detail[:2000]}",
                },
            )
            mem = troubleshoot_commit_safe(
                "cook_package_run cook preflight (UBT) failed",
                {"envelope": pre, "caller": caller},
                tags="cook-package-game,cook,fail",
                agent=caller,
                project=resolved,
            )
            if mem.get("status") == "ok" and mem.get("id"):
                memory_id = str(mem["id"])
            return {
                "status": "fail",
                "mode": "live",
                "project_path": resolved,
                "target_platform": target_platform,
                "build_config": build_config,
                "phases": phases_live,
                "artifacts": {
                    "cooked_content": str(cooked_guess),
                    "staged_build": str(staged_guess),
                    "package_size_mb": None,
                },
                "config_path": cfg_path_resolved,
                "memory_id": memory_id,
            }

        cook_argv = [
            "BuildCookRun",
            f"-project={resolved}",
            "-noP4",
            f"-platform={target_platform}",
            f"-clientconfig={build_config}",
            "-cook",
            "-pak",
            f"-compress={compression}",
            *extras,
        ]
        cmd = _uat_cmd_vec(br, str(uat), cook_argv)
        t0 = time.monotonic()
        run = br._run_subprocess(cmd, cwd=cwd, timeout=timeout)
        dur = round(time.monotonic() - t0, 4)
        if run["timed_out"] or run.get("error") or int(run["exit_code"]) != 0:
            detail = _log_excerpt_from_run(run)
            phases_live.append(
                {
                    "name": "cook",
                    "status": "fail",
                    "duration_s": dur,
                    "exit_code": run.get("exit_code"),
                    "detail": detail[:8000],
                },
            )
            mem = troubleshoot_commit_safe(
                "cook_package_run UAT cook phase failed",
                {"cmd": cook_argv, "run": {k: run[k] for k in ("exit_code", "timed_out", "error") if k in run}},
                tags="cook-package-game,uat,fail",
                agent=caller,
                project=resolved,
            )
            if mem.get("status") == "ok" and mem.get("id"):
                memory_id = str(mem["id"])
            return {
                "status": "fail",
                "mode": "live",
                "project_path": resolved,
                "target_platform": target_platform,
                "build_config": build_config,
                "phases": phases_live,
                "artifacts": {
                    "cooked_content": str(cooked_guess),
                    "staged_build": str(staged_guess),
                    "package_size_mb": None,
                },
                "config_path": cfg_path_resolved,
                "memory_id": memory_id,
            }
        phases_live.append(
            {
                "name": "cook",
                "status": "pass",
                "duration_s": dur,
                "exit_code": int(run["exit_code"]),
                "detail": "UAT cook completed",
            },
        )
    else:
        phases_live.append(
            {
                "name": "cook",
                "status": "pass",
                "duration_s": 0.0,
                "exit_code": None,
                "detail": "skipped (skip_cook)",
            },
        )

    if skip_package:
        phases_live.append(
            {
                "name": "stage",
                "status": "pass",
                "duration_s": 0.0,
                "exit_code": None,
                "detail": "skipped (skip_package)",
            },
        )
        phases_live.append(
            {
                "name": "package",
                "status": "pass",
                "duration_s": 0.0,
                "exit_code": None,
                "detail": "skipped (skip_package)",
            },
        )
        sz = _maybe_package_size_mb(staged_guess, target_platform) if staged_guess.is_dir() else None
        return {
            "status": "pass",
            "mode": "live",
            "project_path": resolved,
            "target_platform": target_platform,
            "build_config": build_config,
            "phases": phases_live,
            "artifacts": {
                "cooked_content": str(cooked_guess),
                "staged_build": str(staged_guess),
                "package_size_mb": sz,
            },
            "config_path": cfg_path_resolved,
            "memory_id": memory_id,
        }

    # Stage always uses -skipcook in this chained flow (cook satisfied or intentionally skipped).
    stage_argv = [
        "BuildCookRun",
        f"-project={resolved}",
        "-noP4",
        f"-platform={target_platform}",
        f"-clientconfig={build_config}",
        "-skipcook",
        "-stage",
        "-archive",
        f"-archivedirectory={archive_dir}",
        *extras,
    ]
    cmd_s = _uat_cmd_vec(br, str(uat), stage_argv)
    t1 = time.monotonic()
    run_s = br._run_subprocess(cmd_s, cwd=cwd, timeout=timeout)
    d1 = round(time.monotonic() - t1, 4)
    if run_s["timed_out"] or run_s.get("error") or int(run_s["exit_code"]) != 0:
        detail = _log_excerpt_from_run(run_s)
        phases_live.append(
            {
                "name": "stage",
                "status": "fail",
                "duration_s": d1,
                "exit_code": run_s.get("exit_code"),
                "detail": detail[:8000],
            },
        )
        mem = troubleshoot_commit_safe(
            "cook_package_run UAT stage phase failed",
            {"argv": stage_argv, "exit_code": run_s.get("exit_code")},
            tags="cook-package-game,stage,fail",
            agent=caller,
            project=resolved,
        )
        if mem.get("status") == "ok" and mem.get("id"):
            memory_id = str(mem["id"])
        return {
            "status": "fail",
            "mode": "live",
            "project_path": resolved,
            "target_platform": target_platform,
            "build_config": build_config,
            "phases": phases_live,
            "artifacts": {
                "cooked_content": str(cooked_guess),
                "staged_build": str(staged_guess),
                "package_size_mb": None,
            },
            "config_path": cfg_path_resolved,
            "memory_id": memory_id,
        }
    phases_live.append(
        {
            "name": "stage",
            "status": "pass",
            "duration_s": d1,
            "exit_code": int(run_s["exit_code"]),
            "detail": "UAT stage completed",
        },
    )

    pack_argv = [
        "BuildCookRun",
        f"-project={resolved}",
        "-noP4",
        f"-platform={target_platform}",
        f"-clientconfig={build_config}",
        "-package",
        "-skipcook",
        "-skipstage",
        *extras,
    ]
    cmd_p = _uat_cmd_vec(br, str(uat), pack_argv)
    t2 = time.monotonic()
    run_p = br._run_subprocess(cmd_p, cwd=cwd, timeout=timeout)
    d2 = round(time.monotonic() - t2, 4)
    if run_p["timed_out"] or run_p.get("error") or int(run_p["exit_code"]) != 0:
        detail = _log_excerpt_from_run(run_p)
        phases_live.append(
            {
                "name": "package",
                "status": "fail",
                "duration_s": d2,
                "exit_code": run_p.get("exit_code"),
                "detail": detail[:8000],
            },
        )
        mem = troubleshoot_commit_safe(
            "cook_package_run UAT package phase failed",
            {"argv": pack_argv, "exit_code": run_p.get("exit_code")},
            tags="cook-package-game,package,fail",
            agent=caller,
            project=resolved,
        )
        if mem.get("status") == "ok" and mem.get("id"):
            memory_id = str(mem["id"])
        return {
            "status": "fail",
            "mode": "live",
            "project_path": resolved,
            "target_platform": target_platform,
            "build_config": build_config,
            "phases": phases_live,
            "artifacts": {
                "cooked_content": str(cooked_guess),
                "staged_build": str(staged_guess),
                "package_size_mb": None,
            },
            "config_path": cfg_path_resolved,
            "memory_id": memory_id,
        }
    phases_live.append(
        {
            "name": "package",
            "status": "pass",
            "duration_s": d2,
            "exit_code": int(run_p["exit_code"]),
            "detail": "UAT package completed",
        },
    )

    sz_live = _maybe_package_size_mb(staged_guess, target_platform)
    return {
        "status": "pass",
        "mode": "live",
        "project_path": resolved,
        "target_platform": target_platform,
        "build_config": build_config,
        "phases": phases_live,
        "artifacts": {
            "cooked_content": str(cooked_guess),
            "staged_build": str(staged_guess),
            "package_size_mb": sz_live,
        },
        "config_path": cfg_path_resolved,
        "memory_id": memory_id,
    }
