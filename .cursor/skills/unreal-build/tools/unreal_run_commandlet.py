"""MCP tool: run a headless Unreal editor commandlet."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from _build_runner import (
    _cap_timeout,
    _get_mode,
    _resolve_engine_path,
    _run_subprocess,
    _sanitize_project_path,
    _validate_engine_path,
    allow_unlisted_commandlets,
    build_trace_timestamp,
    dry_run_constants,
    find_hub_root,
    load_allowlisted_commandlets,
    sanitize_commandlet_extra_args,
    sanitize_commandlet_name_for_bypass,
    troubleshoot_commit_safe,
)

logger = logging.getLogger(__name__)


def _commandlet_cmd(editor_cmd: str, project: str, commandlet_name: str, args: list[str]) -> list[str]:
    return [editor_cmd, project, f"-run={commandlet_name}", *args]


def _unreal_run_commandlet_impl(
    project_path: str,
    commandlet_name: str,
    args: list[str] | None = None,
    timeout_s: int | None = None,
    caller: str = "user-direct-debug",
) -> dict[str, Any]:
    timeout = _cap_timeout(float(timeout_s) if timeout_s is not None else None)
    hub = find_hub_root()
    ts = build_trace_timestamp()
    trace_dir = hub / ".cuebert" / "traces" / "build" / ts
    memory_id: str | None = None
    mode = _get_mode()

    proj = _sanitize_project_path(project_path)
    if not proj:
        return {
            "status": "error",
            "mode": mode,
            "project_path": project_path,
            "commandlet_name": commandlet_name,
            "exit_code": None,
            "duration_s": None,
            "trace_dir": None,
            "error": {"code": "build.invalid_project", "message": "project_path must be absolute, exist, and end with .uproject"},
            "memory_id": None,
        }

    extra, arg_err = sanitize_commandlet_extra_args(args)
    if arg_err:
        return {
            "status": "error",
            "mode": mode,
            "project_path": proj,
            "commandlet_name": commandlet_name,
            "exit_code": None,
            "duration_s": None,
            "trace_dir": None,
            "error": {"code": "build.invalid_commandlet_args", "message": arg_err},
            "memory_id": None,
        }

    allowed = load_allowlisted_commandlets()
    bypass = allow_unlisted_commandlets()
    canonical_name = commandlet_name.strip()
    if not bypass and canonical_name not in allowed:
        mem = troubleshoot_commit_safe(
            "unreal_run_commandlet blocked (commandlet not allowlisted)",
            {
                "commandlet": canonical_name,
                "caller": caller,
                "allowed_count": len(allowed),
            },
            tags="warning,unreal-build,commandlet_blocked",
            agent=caller,
        )
        if mem.get("status") == "ok" and mem.get("id"):
            memory_id = str(mem["id"])
        return {
            "status": "blocked",
            "mode": mode,
            "project_path": proj,
            "commandlet_name": canonical_name,
            "exit_code": None,
            "duration_s": None,
            "trace_dir": None,
            "error": {
                "code": "build.commandlet_not_allowlisted",
                "message": (
                    "Commandlet not in .cursor/skills/unreal-build/commandlets/*.json allowlist. "
                    "Set CUEBERT_UNREAL_BUILD_ALLOW_UNLISTED_COMMANDLETS=1 for local dev only."
                ),
            },
            "memory_id": memory_id,
        }

    if bypass:
        cname = sanitize_commandlet_name_for_bypass(canonical_name)
        if not cname:
            return {
                "status": "error",
                "mode": mode,
                "project_path": proj,
                "commandlet_name": canonical_name,
                "exit_code": None,
                "duration_s": None,
                "trace_dir": None,
                "error": {"code": "build.invalid_commandlet_name", "message": "commandlet_name failed bypass regex"},
                "memory_id": None,
            }
        canonical_name = cname
    else:
        canonical_name = canonical_name

    dc = dry_run_constants()["commandlet"]
    if mode == "dry_run":
        eng = _resolve_engine_path()
        val = _validate_engine_path(eng) if eng else {"valid": False}
        editor = str(val.get("editor_cmd_path") or "/dry_run/Engine/Binaries/Mac/UnrealEditor-Cmd")
        cmd = _commandlet_cmd(editor, proj, canonical_name, extra)
        meta = {
            "tool": "unreal_run_commandlet",
            "mode": "dry_run",
            "caller": caller,
            "commandlet": canonical_name,
            "timeout_s": timeout,
        }
        trace_dir.mkdir(parents=True, exist_ok=True)
        (trace_dir / "cmd.txt").write_text(json.dumps(cmd, ensure_ascii=False, indent=2), encoding="utf-8")
        (trace_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        out_txt = json.dumps(dc, indent=2) + "\n"
        (trace_dir / "stdout.log").write_text(out_txt, encoding="utf-8")
        (trace_dir / "stderr.log").write_text("(dry_run)\n", encoding="utf-8")
        mem = troubleshoot_commit_safe(
            f"unreal_run_commandlet dry_run pass ({caller})",
            {"commandlet": canonical_name, "trace": str(trace_dir), "fixture": dc},
            tags="unreal-build,commandlet,dry_run",
            agent=caller,
        )
        if mem.get("status") == "ok" and mem.get("id"):
            memory_id = str(mem["id"])
        return {
            "status": "dry_run",
            "mode": "dry_run",
            "project_path": proj,
            "commandlet_name": canonical_name,
            "exit_code": int(dc["exit_code"]),
            "duration_s": float(dc["duration_s"]),
            "trace_dir": str(trace_dir),
            "error": None,
            "memory_id": memory_id,
        }

    eng_raw = _resolve_engine_path()
    if not eng_raw:
        return {
            "status": "error",
            "mode": "live",
            "project_path": proj,
            "commandlet_name": canonical_name,
            "exit_code": None,
            "duration_s": None,
            "trace_dir": None,
            "error": {"code": "build.engine_not_found", "message": "engine path not resolved"},
            "memory_id": None,
        }
    val = _validate_engine_path(eng_raw)
    if not val.get("valid") or not val.get("editor_cmd_path"):
        return {
            "status": "error",
            "mode": "live",
            "project_path": proj,
            "commandlet_name": canonical_name,
            "exit_code": None,
            "duration_s": None,
            "trace_dir": None,
            "error": {
                "code": "build.engine_not_found",
                "message": val.get("reason") or "editor cmd binary missing",
            },
            "memory_id": None,
        }

    editor_cmd = str(val["editor_cmd_path"])
    cmd = _commandlet_cmd(editor_cmd, proj, canonical_name, extra)
    cwd = str(Path(proj).parent)
    meta = {
        "tool": "unreal_run_commandlet",
        "mode": "live",
        "caller": caller,
        "commandlet": canonical_name,
        "timeout_s": timeout,
        "engine_path": eng_raw,
    }
    trace_dir.mkdir(parents=True, exist_ok=True)
    (trace_dir / "cmd.txt").write_text(json.dumps(cmd, ensure_ascii=False, indent=2), encoding="utf-8")
    (trace_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    run = _run_subprocess(cmd, cwd=cwd, timeout=timeout)
    (trace_dir / "stdout.log").write_text(run["stdout"], encoding="utf-8")
    (trace_dir / "stderr.log").write_text(run["stderr"], encoding="utf-8")

    if run["timed_out"]:
        mem = troubleshoot_commit_safe(
            f"unreal_run_commandlet timeout ({caller})",
            {"commandlet": canonical_name, "trace": str(trace_dir)},
            tags="unreal-build,commandlet,timeout",
            agent=caller,
        )
        if mem.get("status") == "ok" and mem.get("id"):
            memory_id = str(mem["id"])
        return {
            "status": "timeout",
            "mode": "live",
            "project_path": proj,
            "commandlet_name": canonical_name,
            "exit_code": None,
            "duration_s": run["duration_s"],
            "trace_dir": str(trace_dir),
            "error": {"code": "build.timeout", "message": run.get("error") or "subprocess timed out"},
            "memory_id": memory_id,
        }

    if run.get("error") and run["exit_code"] == -1:
        mem = troubleshoot_commit_safe(
            f"unreal_run_commandlet subprocess error ({caller})",
            {"commandlet": canonical_name, "error": run["error"], "trace": str(trace_dir)},
            tags="unreal-build,commandlet,error",
            agent=caller,
        )
        if mem.get("status") == "ok" and mem.get("id"):
            memory_id = str(mem["id"])
        return {
            "status": "error",
            "mode": "live",
            "project_path": proj,
            "commandlet_name": canonical_name,
            "exit_code": run["exit_code"],
            "duration_s": run["duration_s"],
            "trace_dir": str(trace_dir),
            "error": {"code": "build.subprocess_error", "message": str(run["error"])},
            "memory_id": memory_id,
        }

    code = int(run["exit_code"])
    if code == 0:
        mem = troubleshoot_commit_safe(
            f"unreal_run_commandlet success ({caller})",
            {"commandlet": canonical_name, "duration_s": run["duration_s"], "trace": str(trace_dir)},
            tags="unreal-build,commandlet,success",
            agent=caller,
        )
        if mem.get("status") == "ok" and mem.get("id"):
            memory_id = str(mem["id"])
        return {
            "status": "pass",
            "mode": "live",
            "project_path": proj,
            "commandlet_name": canonical_name,
            "exit_code": code,
            "duration_s": run["duration_s"],
            "trace_dir": str(trace_dir),
            "error": None,
            "memory_id": memory_id,
        }

    err_tail = run["stderr"].splitlines()[-100:]
    mem = troubleshoot_commit_safe(
        f"unreal_run_commandlet failure ({caller})",
        {
            "commandlet": canonical_name,
            "exit_code": code,
            "stderr_tail": err_tail,
            "trace": str(trace_dir),
        },
        tags="unreal-build,commandlet,failure",
        agent=caller,
    )
    if mem.get("status") == "ok" and mem.get("id"):
        memory_id = str(mem["id"])
    return {
        "status": "error",
        "mode": "live",
        "project_path": proj,
        "commandlet_name": canonical_name,
        "exit_code": code,
        "duration_s": run["duration_s"],
        "trace_dir": str(trace_dir),
        "error": {"code": "build.commandlet_failed", "message": "editor commandlet exited non-zero"},
        "memory_id": memory_id,
    }


def register(mcp: FastMCP) -> None:
    """Register ``unreal_run_commandlet`` on the MCP server."""

    @mcp.tool()
    def unreal_run_commandlet(
        project_path: str,
        commandlet_name: str,
        args: list[str] | None = None,
        timeout_s: int | None = None,
        caller: str = "user-direct-debug",
    ) -> dict[str, Any]:
        """Run a headless Unreal editor commandlet (allowlist + dry-run safe)."""
        try:
            return _unreal_run_commandlet_impl(
                project_path,
                commandlet_name,
                args=args,
                timeout_s=timeout_s,
                caller=caller,
            )
        except Exception as exc:
            logger.error("unreal_run_commandlet failed: %s", exc, exc_info=True)
            return {
                "status": "error",
                "mode": _get_mode(),
                "project_path": project_path,
                "commandlet_name": commandlet_name,
                "exit_code": None,
                "duration_s": None,
                "trace_dir": None,
                "error": {"code": "build.internal_error", "message": str(exc)},
                "memory_id": None,
            }
