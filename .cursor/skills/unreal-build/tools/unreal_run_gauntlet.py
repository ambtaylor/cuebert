"""MCP tool: run Gauntlet automation tests via UAT ``RunUnreal``."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from _build_runner import (
    _cap_gauntlet_timeout,
    _detect_platform,
    _get_mode,
    _resolve_engine_path,
    _run_subprocess,
    _sanitize_config,
    _sanitize_platform,
    _sanitize_project_path,
    _validate_engine_path,
    build_trace_timestamp,
    find_hub_root,
    sanitize_commandlet_extra_args,
    troubleshoot_commit_safe,
)
from _gauntlet_parser import find_junit_fallback_path, parse_gauntlet_report, parse_gauntlet_xml_fallback

logger = logging.getLogger(__name__)

_TEST_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.]{0,127}$")
_ROLE_ALLOW = frozenset({"Editor", "Client", "Server", "CookedClient"})
_REQUIRES_BUILD = frozenset({"Server", "CookedClient"})


def _sanitize_test_name(name: str) -> str | None:
    s = name.strip()
    if not s or not _TEST_NAME_RE.fullmatch(s):
        return None
    return s


def _sanitize_role(role: str) -> str | None:
    s = role.strip()
    return s if s in _ROLE_ALLOW else None


def _sanitize_build_dir(p: str) -> str | None:
    try:
        rp = Path(p).expanduser().resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    return str(rp) if rp.is_dir() else None


def _uat_rununreal_cmd(
    uat_path: str,
    project: str,
    test_name: str,
    platform: str,
    config: str,
    role: str,
    logdir: str,
    build_path: str | None,
    extra_test_flags: list[str],
) -> list[str]:
    parts: list[str] = [
        "RunUnreal",
        f"-project={project}",
        f"-test={test_name}",
        f"-platform={platform}",
        f"-configuration={config}",
        f"-role={role}",
        f"-logdir={logdir}",
    ]
    if build_path:
        parts.append(f"-build={build_path}")
    for a in extra_test_flags:
        parts.append(f"-test={a}")
    if _detect_platform() == "win":
        return [uat_path, *parts]
    return ["/bin/bash", uat_path, *parts]


def _load_gauntlet_registry_names() -> set[str]:
    root = Path(__file__).resolve().parent.parent / "test-plans"
    names: set[str] = set()
    if not root.is_dir():
        return names
    for p in sorted(root.glob("*.json")):
        if not p.is_file():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            n = data.get("name")
            if isinstance(n, str) and n.strip():
                names.add(n.strip())
        except Exception as exc:
            logger.warning("skip malformed gauntlet test-plan json %s: %s", p, exc)
    return names


def _write_gauntlet_trace(
    trace_dir: Path,
    cmd: list[str],
    meta: dict[str, Any],
    stdout_text: str,
    stderr_text: str,
) -> None:
    trace_dir.mkdir(parents=True, exist_ok=True)
    (trace_dir / "cmd.txt").write_text(json.dumps(cmd, ensure_ascii=False, indent=2), encoding="utf-8")
    (trace_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (trace_dir / "stdout.log").write_text(stdout_text, encoding="utf-8")
    (trace_dir / "stderr.log").write_text(stderr_text, encoding="utf-8")


def _synthetic_test_report_json(test_name: str) -> dict[str, Any]:
    def case(suf: str) -> dict[str, Any]:
        return {
            "testDisplayName": f"{test_name}.{suf}",
            "fullTestPath": f"{test_name}.{suf}",
            "state": "Success",
            "duration": 0.14,
            "errors": [],
            "warnings": [],
            "artifacts": [],
        }

    return {
        "devices": [],
        "reportCreatedOn": "2026-04-20T12:00:00Z",
        "totalDuration": 0.42,
        "succeeded": 3,
        "succeededWithWarnings": 0,
        "failed": 0,
        "notRun": 0,
        "tests": [case("A"), case("B"), case("C")],
    }


def _parse_reports(gauntlet_logs: Path, test_name: str) -> dict[str, Any] | None:
    sub = gauntlet_logs / test_name
    json_path = sub / "TestReport.json"
    if json_path.is_file():
        parsed = parse_gauntlet_report(str(json_path.resolve(strict=True)))
        if parsed is not None:
            return parsed
    xml_path = find_junit_fallback_path(sub)
    return parse_gauntlet_xml_fallback(xml_path) if xml_path else None


def _stderr_tail(stderr: str, n: int = 50) -> list[str]:
    lines = stderr.splitlines()
    return lines[-n:] if len(lines) > n else lines


def _envelope(
    status: str,
    mode: str,
    *,
    project_path: str,
    test_name: str,
    role: str,
    platform: str,
    config: str,
    exit_code: int | None = None,
    duration_s: float | None = None,
    report: dict[str, Any] | None = None,
    log_dir: str | None = None,
    trace_dir: str | None = None,
    error: dict[str, str] | None = None,
    memory_id: str | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "mode": mode,
        "project_path": project_path,
        "test_name": test_name,
        "role": role,
        "platform": platform,
        "config": config,
        "exit_code": exit_code,
        "duration_s": duration_s,
        "report": report,
        "log_dir": log_dir,
        "trace_dir": trace_dir,
        "error": error,
        "memory_id": memory_id,
    }


def _mem_commit(problem: str, payload: Any, *, tags: str, agent: str) -> str | None:
    mem = troubleshoot_commit_safe(problem, payload, tags=tags, agent=agent)
    return str(mem["id"]) if mem.get("status") == "ok" and mem.get("id") else None


def _unreal_run_gauntlet_impl(
    project_path: str,
    test_name: str,
    build_path: str | None = None,
    platform: str = "Mac",
    config: str = "Development",
    role: str = "Editor",
    test_args: list[str] | None = None,
    timeout_s: int | None = None,
    caller: str = "agent-play-qa",
) -> dict[str, Any]:
    mode = _get_mode()
    timeout = _cap_gauntlet_timeout(float(timeout_s) if timeout_s is not None else None)
    hub = find_hub_root()
    trace_dir = hub / ".cuebert" / "traces" / "gauntlet" / build_trace_timestamp()
    memory_id: str | None = None

    def err(
        code: str,
        msg: str,
        *,
        st: str = "error",
        m: str | None = None,
        proj: str | None = None,
        tn: str | None = None,
        rl: str | None = None,
        pl: str | None = None,
        cf: str | None = None,
        mem_tags: str | None = None,
        mem_payload: Any | None = None,
    ) -> dict[str, Any]:
        nonlocal memory_id
        if mem_tags and mem_payload is not None:
            memory_id = _mem_commit(f"unreal_run_gauntlet {code} ({caller})", mem_payload, tags=mem_tags, agent=caller)
        return _envelope(
            st,
            m or mode,
            project_path=proj or project_path,
            test_name=tn or test_name,
            role=rl or role,
            platform=pl or platform,
            config=cf or config,
            error={"code": code, "message": msg},
            memory_id=memory_id,
        )

    proj = _sanitize_project_path(project_path)
    if not proj:
        return err(
            "gauntlet.invalid_project",
            "project_path must be absolute, exist, and end with .uproject",
            proj=project_path,
        )

    tname = _sanitize_test_name(test_name)
    if not tname:
        return err("gauntlet.invalid_test_name", "test_name failed allowlist regex", proj=proj, tn=test_name)

    r = _sanitize_role(role)
    if not r:
        return err(
            "gauntlet.invalid_role",
            "role must be Editor, Client, Server, or CookedClient",
            proj=proj,
            tn=tname,
            rl=role,
        )

    plat = _sanitize_platform(platform)
    if not plat:
        return err("gauntlet.invalid_platform", "platform not in allowlist", proj=proj, tn=tname, rl=r, pl=platform)

    cfg = _sanitize_config(config)
    if not cfg:
        return err("gauntlet.invalid_config", "config not in allowlist", proj=proj, tn=tname, rl=r, pl=plat, cf=config)

    extra, arg_err = sanitize_commandlet_extra_args(test_args)
    if arg_err:
        return err("gauntlet.invalid_test_args", arg_err, proj=proj, tn=tname, rl=r, pl=plat, cf=cfg)

    bdir: str | None = None
    if r in _REQUIRES_BUILD:
        if not (build_path and str(build_path).strip()):
            return err(
                "gauntlet.build_path_required",
                "build_path is required for Server and CookedClient roles",
                proj=proj,
                tn=tname,
                rl=r,
                pl=plat,
                cf=cfg,
            )
        bdir = _sanitize_build_dir(str(build_path))
        if not bdir:
            return err(
                "gauntlet.invalid_build_path",
                "build_path must resolve to an existing directory",
                proj=proj,
                tn=tname,
                rl=r,
                pl=plat,
                cf=cfg,
            )
    elif build_path and str(build_path).strip() and r != "Editor":
        bdir = _sanitize_build_dir(str(build_path))
        if not bdir:
            return err(
                "gauntlet.invalid_build_path",
                "build_path must resolve to an existing directory when provided",
                proj=proj,
                tn=tname,
                rl=r,
                pl=plat,
                cf=cfg,
            )

    registered = _load_gauntlet_registry_names()
    if tname not in registered:
        logger.info(
            "gauntlet test_name %r not in registry (.cursor/skills/unreal-build/test-plans/); ad-hoc run allowed",
            tname,
        )

    gauntlet_logs = trace_dir / "gauntlet_logs"
    logdir_str = str(gauntlet_logs.resolve())
    log_subdir = gauntlet_logs / tname

    eng_raw = _resolve_engine_path()
    val = _validate_engine_path(eng_raw) if eng_raw else {"valid": False, "reason": "no engine path"}

    if mode == "dry_run":
        uat_syn = str(val.get("uat_path") or "/dry_run/Engine/Build/BatchFiles/RunUAT.sh")
        cmd = _uat_rununreal_cmd(uat_syn, proj, tname, plat, cfg, r, logdir_str, bdir if r != "Editor" else None, extra)
        trace_dir.mkdir(parents=True, exist_ok=True)
        gauntlet_logs.mkdir(parents=True, exist_ok=True)
        log_subdir.mkdir(parents=True, exist_ok=True)
        (log_subdir / "TestReport.json").write_text(
            json.dumps(_synthetic_test_report_json(tname), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        report = parse_gauntlet_report(str((log_subdir / "TestReport.json").resolve(strict=True)))
        meta = {
            "tool": "unreal_run_gauntlet",
            "mode": "dry_run",
            "caller": caller,
            "project_path": proj,
            "test_name": tname,
            "role": r,
            "platform": plat,
            "config": cfg,
            "timeout_s": timeout,
            "build_path": bdir,
        }
        _write_gauntlet_trace(
            trace_dir,
            cmd,
            meta,
            f"(dry_run synthetic Gauntlet stdout for {tname})\n",
            "(dry_run synthetic stderr)\n",
        )
        memory_id = _mem_commit(
            f"unreal_run_gauntlet dry_run pass ({caller})",
            {"test": tname, "report": report, "trace": str(trace_dir)},
            tags="info,unreal-build,gauntlet,dry_run",
            agent=caller,
        )
        fallback = {"total_tests": 3, "passed": 3, "failed": 0, "skipped": 0, "duration_s": 0.42, "failures": []}
        return _envelope(
            "dry_run",
            "dry_run",
            project_path=proj,
            test_name=tname,
            role=r,
            platform=plat,
            config=cfg,
            exit_code=0,
            duration_s=0.0,
            report=report or fallback,
            log_dir=str(log_subdir.resolve()),
            trace_dir=str(trace_dir.resolve()),
            memory_id=memory_id,
        )

    if not eng_raw or not val.get("valid"):
        memory_id = _mem_commit(
            f"unreal_run_gauntlet engine not found ({caller})",
            {"test": tname, "reason": val.get("reason"), "engine_path": eng_raw},
            tags="error,unreal-build,gauntlet,engine",
            agent=caller,
        )
        return _envelope(
            "error",
            "live",
            project_path=proj,
            test_name=tname,
            role=r,
            platform=plat,
            config=cfg,
            error={
                "code": "gauntlet.engine_not_found",
                "message": val.get("reason") or "engine path missing or invalid",
            },
            memory_id=memory_id,
        )

    uat = val.get("uat_path")
    if not uat:
        memory_id = _mem_commit(
            f"unreal_run_gauntlet RunUAT missing ({caller})",
            {"test": tname, "reason": val.get("reason"), "engine_path": eng_raw},
            tags="error,unreal-build,gauntlet,engine",
            agent=caller,
        )
        return _envelope(
            "error",
            "live",
            project_path=proj,
            test_name=tname,
            role=r,
            platform=plat,
            config=cfg,
            error={"code": "gauntlet.engine_not_found", "message": val.get("reason") or "RunUAT missing"},
            memory_id=memory_id,
        )

    gauntlet_logs.mkdir(parents=True, exist_ok=True)
    cmd = _uat_rununreal_cmd(str(uat), proj, tname, plat, cfg, r, logdir_str, bdir if r != "Editor" else None, extra)
    cwd = str(Path(proj).parent)
    meta = {
        "tool": "unreal_run_gauntlet",
        "mode": "live",
        "caller": caller,
        "project_path": proj,
        "test_name": tname,
        "role": r,
        "platform": plat,
        "config": cfg,
        "timeout_s": timeout,
        "engine_path": eng_raw,
        "build_path": bdir,
    }
    trace_dir.mkdir(parents=True, exist_ok=True)
    (trace_dir / "cmd.txt").write_text(json.dumps(cmd, ensure_ascii=False, indent=2), encoding="utf-8")
    (trace_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    run = _run_subprocess(cmd, cwd=cwd, timeout=timeout)
    stdout_text, stderr_text = run["stdout"], run["stderr"]
    (trace_dir / "stdout.log").write_text(stdout_text, encoding="utf-8")
    (trace_dir / "stderr.log").write_text(stderr_text, encoding="utf-8")
    err_tail = _stderr_tail(stderr_text, 50)

    log_dir_out = str(log_subdir.resolve()) if log_subdir.is_dir() else str(gauntlet_logs.resolve())
    trace_s = str(trace_dir.resolve())

    if run["timed_out"]:
        memory_id = _mem_commit(
            f"unreal_run_gauntlet timeout ({caller})",
            {"cmd": cmd, "trace": trace_s, "stderr_tail": err_tail},
            tags="error,unreal-build,gauntlet,timeout",
            agent=caller,
        )
        return _envelope(
            "timeout",
            "live",
            project_path=proj,
            test_name=tname,
            role=r,
            platform=plat,
            config=cfg,
            duration_s=run["duration_s"],
            report=_parse_reports(gauntlet_logs, tname),
            log_dir=log_dir_out,
            trace_dir=trace_s,
            error={"code": "gauntlet.timeout", "message": run.get("error") or "subprocess timed out"},
            memory_id=memory_id,
        )

    if run.get("error") and run["exit_code"] == -1:
        memory_id = _mem_commit(
            f"unreal_run_gauntlet subprocess error ({caller})",
            {"cmd": cmd, "error": run["error"], "trace": trace_s},
            tags="error,unreal-build,gauntlet,subprocess",
            agent=caller,
        )
        return _envelope(
            "error",
            "live",
            project_path=proj,
            test_name=tname,
            role=r,
            platform=plat,
            config=cfg,
            exit_code=run["exit_code"],
            duration_s=run["duration_s"],
            log_dir=log_dir_out,
            trace_dir=trace_s,
            error={"code": "gauntlet.subprocess_error", "message": str(run["error"])},
            memory_id=memory_id,
        )

    code = int(run["exit_code"])
    report = _parse_reports(gauntlet_logs, tname)
    json_path = log_subdir / "TestReport.json"
    parse_failed = report is None and json_path.is_file()

    if code == 0 and report is not None and int(report.get("failed") or 0) == 0:
        memory_id = _mem_commit(
            f"unreal_run_gauntlet pass ({caller})",
            {"test": tname, "total_tests": report.get("total_tests"), "passed": report.get("passed"), "trace": trace_s},
            tags="info,unreal-build,gauntlet,pass",
            agent=caller,
        )
        return _envelope(
            "pass",
            "live",
            project_path=proj,
            test_name=tname,
            role=r,
            platform=plat,
            config=cfg,
            exit_code=code,
            duration_s=run["duration_s"],
            report=report,
            log_dir=log_dir_out,
            trace_dir=trace_s,
            memory_id=memory_id,
        )

    if code == 0 and report is not None and int(report.get("failed") or 0) > 0:
        memory_id = _mem_commit(
            f"unreal_run_gauntlet test failures ({caller})",
            {"test": tname, "report": report, "stderr_tail": err_tail, "trace": trace_s},
            tags="warn,unreal-build,gauntlet,fail",
            agent=caller,
        )
        return _envelope(
            "fail",
            "live",
            project_path=proj,
            test_name=tname,
            role=r,
            platform=plat,
            config=cfg,
            exit_code=code,
            duration_s=run["duration_s"],
            report=report,
            log_dir=log_dir_out,
            trace_dir=trace_s,
            memory_id=memory_id,
        )

    if code == 0 and report is None:
        if parse_failed:
            memory_id = _mem_commit(
                f"unreal_run_gauntlet TestReport.json parse failure ({caller})",
                {"test": tname, "trace": trace_s, "stderr_tail": err_tail},
                tags="error,unreal-build,gauntlet,parse",
                agent=caller,
            )
        else:
            memory_id = _mem_commit(
                f"unreal_run_gauntlet pass (no report file) ({caller})",
                {"test": tname, "trace": trace_s},
                tags="info,unreal-build,gauntlet,pass",
                agent=caller,
            )
        return _envelope(
            "pass",
            "live",
            project_path=proj,
            test_name=tname,
            role=r,
            platform=plat,
            config=cfg,
            exit_code=code,
            duration_s=run["duration_s"],
            report=None,
            log_dir=log_dir_out,
            trace_dir=trace_s,
            memory_id=memory_id,
        )

    if code != 0 and report is not None:
        memory_id = _mem_commit(
            f"unreal_run_gauntlet non-zero exit with report ({caller})",
            {"test": tname, "exit_code": code, "report": report, "stderr_tail": err_tail, "trace": trace_s},
            tags="warn,unreal-build,gauntlet,fail",
            agent=caller,
        )
        return _envelope(
            "fail",
            "live",
            project_path=proj,
            test_name=tname,
            role=r,
            platform=plat,
            config=cfg,
            exit_code=code,
            duration_s=run["duration_s"],
            report=report,
            log_dir=log_dir_out,
            trace_dir=trace_s,
            memory_id=memory_id,
        )

    memory_id = _mem_commit(
        f"unreal_run_gauntlet error exit without parseable report ({caller})",
        {"test": tname, "exit_code": code, "stderr_tail": err_tail, "trace": trace_s},
        tags="error,unreal-build,gauntlet,error",
        agent=caller,
    )
    return _envelope(
        "error",
        "live",
        project_path=proj,
        test_name=tname,
        role=r,
        platform=plat,
        config=cfg,
        exit_code=code,
        duration_s=run["duration_s"],
        log_dir=log_dir_out,
        trace_dir=trace_s,
        error={"code": "gauntlet.run_failed", "message": "RunUnreal exited non-zero without a parseable Gauntlet report"},
        memory_id=memory_id,
    )


def register(mcp: FastMCP) -> None:
    """Register ``unreal_run_gauntlet`` on the MCP server."""

    @mcp.tool()
    def unreal_run_gauntlet(
        project_path: str,
        test_name: str,
        build_path: str | None = None,
        platform: str = "Mac",
        config: str = "Development",
        role: str = "Editor",
        test_args: list[str] | None = None,
        timeout_s: int | None = None,
        caller: str = "agent-play-qa",
    ) -> dict[str, Any]:
        """Run a Gauntlet automation test via UAT ``RunUnreal`` (live) or synthetic dry-run envelope."""
        try:
            return _unreal_run_gauntlet_impl(
                project_path,
                test_name,
                build_path=build_path,
                platform=platform,
                config=config,
                role=role,
                test_args=test_args,
                timeout_s=timeout_s,
                caller=caller,
            )
        except Exception as exc:
            logger.error("unreal_run_gauntlet failed: %s", exc, exc_info=True)
            return _envelope(
                "error",
                _get_mode(),
                project_path=project_path,
                test_name=test_name,
                role=role,
                platform=platform,
                config=config,
                error={"code": "gauntlet.internal_error", "message": str(exc)},
            )
