"""MCP tool: compile a UBT target (Editor/Game/Server, etc.)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from _build_runner import (
    _cap_timeout,
    _detect_platform,
    _get_mode,
    _resolve_engine_path,
    _run_subprocess,
    _sanitize_config,
    _sanitize_platform,
    _sanitize_project_path,
    _sanitize_target_name,
    _validate_engine_path,
    build_trace_timestamp,
    dry_run_build_log_excerpt,
    find_hub_root,
    troubleshoot_commit_safe,
)

logger = logging.getLogger(__name__)


def _write_trace(
    trace_dir: Path,
    cmd: list[str],
    meta: dict[str, Any],
    stdout_text: str,
    stderr_text: str,
) -> None:
    trace_dir.mkdir(parents=True, exist_ok=True)
    (trace_dir / "cmd.txt").write_text(
        json.dumps(cmd, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (trace_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (trace_dir / "stdout.log").write_text(stdout_text, encoding="utf-8")
    (trace_dir / "stderr.log").write_text(stderr_text, encoding="utf-8")


def _ubt_cmd_vec(ubt_path: str, target: str, platform: str, config: str, project: str) -> list[str]:
    host = _detect_platform()
    if host == "win":
        return [ubt_path, target, platform, config, f"-project={project}"]
    return ["/bin/bash", ubt_path, target, platform, config, f"-project={project}"]


def _unreal_build_target_impl(
    project_path: str,
    target_name: str,
    platform: str = "Mac",
    config: str = "Development",
    timeout_s: int | None = None,
    caller: str = "user-direct-debug",
) -> dict[str, Any]:
    """Compile a UBT target (implementation)."""
    mode = _get_mode()
    timeout = _cap_timeout(float(timeout_s) if timeout_s is not None else None)
    hub = find_hub_root()
    ts = build_trace_timestamp()
    trace_dir = hub / ".cuebert" / "traces" / "build" / ts
    memory_id: str | None = None

    proj = _sanitize_project_path(project_path)
    if not proj:
        return {
            "status": "error",
            "mode": mode,
            "engine_path": _resolve_engine_path(),
            "project_path": project_path,
            "target_name": target_name,
            "platform": platform,
            "config": config,
            "exit_code": None,
            "duration_s": None,
            "stdout_bytes": 0,
            "stderr_bytes": 0,
            "log_excerpt": [],
            "trace_dir": None,
            "error": {"code": "build.invalid_project", "message": "project_path must be absolute, exist, and end with .uproject"},
            "memory_id": None,
        }
    tgt = _sanitize_target_name(target_name)
    if not tgt:
        return {
            "status": "error",
            "mode": mode,
            "engine_path": _resolve_engine_path(),
            "project_path": proj,
            "target_name": target_name,
            "platform": platform,
            "config": config,
            "exit_code": None,
            "duration_s": None,
            "stdout_bytes": 0,
            "stderr_bytes": 0,
            "log_excerpt": [],
            "trace_dir": None,
            "error": {"code": "build.invalid_target", "message": "target_name failed allowlist regex"},
            "memory_id": None,
        }
    plat = _sanitize_platform(platform)
    if not plat:
        return {
            "status": "error",
            "mode": mode,
            "engine_path": _resolve_engine_path(),
            "project_path": proj,
            "target_name": tgt,
            "platform": platform,
            "config": config,
            "exit_code": None,
            "duration_s": None,
            "stdout_bytes": 0,
            "stderr_bytes": 0,
            "log_excerpt": [],
            "trace_dir": None,
            "error": {"code": "build.invalid_platform", "message": "platform not in allowlist"},
            "memory_id": None,
        }
    cfg = _sanitize_config(config)
    if not cfg:
        return {
            "status": "error",
            "mode": mode,
            "engine_path": _resolve_engine_path(),
            "project_path": proj,
            "target_name": tgt,
            "platform": plat,
            "config": config,
            "exit_code": None,
            "duration_s": None,
            "stdout_bytes": 0,
            "stderr_bytes": 0,
            "log_excerpt": [],
            "trace_dir": None,
            "error": {"code": "build.invalid_config", "message": "config not in allowlist"},
            "memory_id": None,
        }

    eng_raw = _resolve_engine_path()
    val = _validate_engine_path(eng_raw) if eng_raw else {"valid": False, "reason": "no engine path"}
    if mode == "dry_run":
        stdout_syn = "\n".join(dry_run_build_log_excerpt(500)) + "\n"
        stderr_syn = "(dry_run synthetic stderr)\n"
        cmd = _ubt_cmd_vec(
            str(val.get("ubt_path") or "/dry_run/Engine/Build/BatchFiles/RunUBT.sh"),
            tgt,
            plat,
            cfg,
            proj,
        )
        meta = {
            "tool": "unreal_build_target",
            "mode": "dry_run",
            "caller": caller,
            "project_path": proj,
            "target_name": tgt,
            "platform": plat,
            "config": cfg,
            "timeout_s": timeout,
        }
        _write_trace(trace_dir, cmd, meta, stdout_syn, stderr_syn)
        excerpt = dry_run_build_log_excerpt(20)
        mem = troubleshoot_commit_safe(
            f"unreal_build_target dry_run success ({caller})",
            {"target": tgt, "platform": plat, "config": cfg, "trace": str(trace_dir)},
            tags="unreal-build,build,dry_run",
            agent=caller,
        )
        if mem.get("status") == "ok" and mem.get("id"):
            memory_id = str(mem["id"])
        return {
            "status": "dry_run",
            "mode": "dry_run",
            "engine_path": eng_raw,
            "project_path": proj,
            "target_name": tgt,
            "platform": plat,
            "config": cfg,
            "exit_code": 0,
            "duration_s": 0.0,
            "stdout_bytes": len(stdout_syn.encode("utf-8")),
            "stderr_bytes": len(stderr_syn.encode("utf-8")),
            "log_excerpt": excerpt,
            "trace_dir": str(trace_dir),
            "error": None,
            "memory_id": memory_id,
        }

    if not eng_raw or not val.get("valid"):
        return {
            "status": "error",
            "mode": "live",
            "engine_path": eng_raw,
            "project_path": proj,
            "target_name": tgt,
            "platform": plat,
            "config": cfg,
            "exit_code": None,
            "duration_s": None,
            "stdout_bytes": 0,
            "stderr_bytes": 0,
            "log_excerpt": [],
            "trace_dir": None,
            "error": {
                "code": "build.engine_not_found",
                "message": val.get("reason") or "engine path missing or invalid",
            },
            "memory_id": None,
        }

    ubt = val.get("ubt_path")
    if not ubt:
        return {
            "status": "error",
            "mode": "live",
            "engine_path": eng_raw,
            "project_path": proj,
            "target_name": tgt,
            "platform": plat,
            "config": cfg,
            "exit_code": None,
            "duration_s": None,
            "stdout_bytes": 0,
            "stderr_bytes": 0,
            "log_excerpt": [],
            "trace_dir": None,
            "error": {"code": "build.engine_not_found", "message": val.get("reason") or "invalid engine"},
            "memory_id": None,
        }

    cmd = _ubt_cmd_vec(str(ubt), tgt, plat, cfg, proj)
    cwd = str(Path(proj).parent)
    meta = {
        "tool": "unreal_build_target",
        "mode": "live",
        "caller": caller,
        "project_path": proj,
        "target_name": tgt,
        "platform": plat,
        "config": cfg,
        "timeout_s": timeout,
        "engine_path": eng_raw,
    }
    trace_dir.mkdir(parents=True, exist_ok=True)
    (trace_dir / "cmd.txt").write_text(json.dumps(cmd, ensure_ascii=False, indent=2), encoding="utf-8")
    (trace_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    run = _run_subprocess(cmd, cwd=cwd, timeout=timeout)
    stdout_text = run["stdout"]
    stderr_text = run["stderr"]
    (trace_dir / "stdout.log").write_text(stdout_text, encoding="utf-8")
    (trace_dir / "stderr.log").write_text(stderr_text, encoding="utf-8")

    out_lines = stdout_text.splitlines()
    excerpt = out_lines[-20:] if len(out_lines) > 20 else out_lines
    err_lines = stderr_text.splitlines()
    tail_err = err_lines[-100:] if len(err_lines) > 100 else err_lines

    if run["timed_out"]:
        mem = troubleshoot_commit_safe(
            f"unreal_build_target timeout ({caller})",
            {"cmd": cmd, "trace": str(trace_dir), "stderr_tail": tail_err},
            tags="unreal-build,build,timeout",
            agent=caller,
        )
        if mem.get("status") == "ok" and mem.get("id"):
            memory_id = str(mem["id"])
        return {
            "status": "timeout",
            "mode": "live",
            "engine_path": eng_raw,
            "project_path": proj,
            "target_name": tgt,
            "platform": plat,
            "config": cfg,
            "exit_code": None,
            "duration_s": run["duration_s"],
            "stdout_bytes": len(stdout_text.encode("utf-8")),
            "stderr_bytes": len(stderr_text.encode("utf-8")),
            "log_excerpt": excerpt,
            "trace_dir": str(trace_dir),
            "error": {"code": "build.timeout", "message": run.get("error") or "subprocess timed out"},
            "memory_id": memory_id,
        }

    if run.get("error") and run["exit_code"] == -1:
        mem = troubleshoot_commit_safe(
            f"unreal_build_target subprocess error ({caller})",
            {"cmd": cmd, "error": run["error"], "trace": str(trace_dir)},
            tags="unreal-build,build,error",
            agent=caller,
        )
        if mem.get("status") == "ok" and mem.get("id"):
            memory_id = str(mem["id"])
        return {
            "status": "error",
            "mode": "live",
            "engine_path": eng_raw,
            "project_path": proj,
            "target_name": tgt,
            "platform": plat,
            "config": cfg,
            "exit_code": run["exit_code"],
            "duration_s": run["duration_s"],
            "stdout_bytes": len(stdout_text.encode("utf-8")),
            "stderr_bytes": len(stderr_text.encode("utf-8")),
            "log_excerpt": excerpt,
            "trace_dir": str(trace_dir),
            "error": {"code": "build.subprocess_error", "message": str(run["error"])},
            "memory_id": memory_id,
        }

    code = int(run["exit_code"])
    if code == 0:
        mem = troubleshoot_commit_safe(
            f"unreal_build_target success ({caller})",
            {
                "target": tgt,
                "platform": plat,
                "config": cfg,
                "duration_s": run["duration_s"],
                "trace": str(trace_dir),
            },
            tags="unreal-build,build,success",
            agent=caller,
        )
        if mem.get("status") == "ok" and mem.get("id"):
            memory_id = str(mem["id"])
        return {
            "status": "pass",
            "mode": "live",
            "engine_path": eng_raw,
            "project_path": proj,
            "target_name": tgt,
            "platform": plat,
            "config": cfg,
            "exit_code": code,
            "duration_s": run["duration_s"],
            "stdout_bytes": len(stdout_text.encode("utf-8")),
            "stderr_bytes": len(stderr_text.encode("utf-8")),
            "log_excerpt": excerpt,
            "trace_dir": str(trace_dir),
            "error": None,
            "memory_id": memory_id,
        }

    mem = troubleshoot_commit_safe(
        f"unreal_build_target failure ({caller})",
        {
            "target": tgt,
            "platform": plat,
            "config": cfg,
            "exit_code": code,
            "stderr_tail": tail_err,
            "trace": str(trace_dir),
        },
        tags="unreal-build,build,failure",
        agent=caller,
    )
    if mem.get("status") == "ok" and mem.get("id"):
        memory_id = str(mem["id"])
    return {
        "status": "error",
        "mode": "live",
        "engine_path": eng_raw,
        "project_path": proj,
        "target_name": tgt,
        "platform": plat,
        "config": cfg,
        "exit_code": code,
        "duration_s": run["duration_s"],
        "stdout_bytes": len(stdout_text.encode("utf-8")),
        "stderr_bytes": len(stderr_text.encode("utf-8")),
        "log_excerpt": excerpt,
        "trace_dir": str(trace_dir),
        "error": {"code": "build.ubt_failed", "message": "UBT returned non-zero exit code"},
        "memory_id": memory_id,
    }


def register(mcp: FastMCP) -> None:
    """Register ``unreal_build_target`` on the MCP server."""

    @mcp.tool()
    def unreal_build_target(
        project_path: str,
        target_name: str,
        platform: str = "Mac",
        config: str = "Development",
        timeout_s: int | None = None,
        caller: str = "user-direct-debug",
    ) -> dict[str, Any]:
        """Compile a UBT target via RunUBT (live) or synthetic dry-run envelope."""
        try:
            return _unreal_build_target_impl(
                project_path,
                target_name,
                platform=platform,
                config=config,
                timeout_s=timeout_s,
                caller=caller,
            )
        except Exception as exc:
            logger.error("unreal_build_target failed: %s", exc, exc_info=True)
            return {
                "status": "error",
                "mode": _get_mode(),
                "engine_path": _resolve_engine_path(),
                "project_path": project_path,
                "target_name": target_name,
                "platform": platform,
                "config": config,
                "exit_code": None,
                "duration_s": None,
                "stdout_bytes": 0,
                "stderr_bytes": 0,
                "log_excerpt": [],
                "trace_dir": None,
                "error": {"code": "build.internal_error", "message": str(exc)},
                "memory_id": None,
            }
