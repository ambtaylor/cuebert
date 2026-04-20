"""MCP tool: scan Unreal / Gauntlet logs for resilience rule violations."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

from _resilience_common import (
    DEFAULT_DEADLOCK_FRAME_MS,
    RULE_CONFIG_ALIASES,
    _load_config,
    _resolve_mode,
    _troubleshoot_commit_safe,
    default_config_path,
    iter_log_files,
    read_text_file_capped,
    rule_entry_for,
    sanitize_log_line,
    thresholds_from_config,
)

logger = logging.getLogger(__name__)

_RULE_COUNT = 10

# Compiled patterns (normative where noted in qa-resilience-game-rules.md).
_RE_FRAME_HITCH = re.compile(
    r"LogStats: .*Frame [0-9]+.*took ([0-9]+\.[0-9]+) ms",
)
_RE_MEM_SAMPLE = re.compile(r"Mem Used:\s*([0-9]+(?:\.[0-9]+)?)\s*MB")
_RE_FATAL = re.compile(r"(?:Fatal error:|LogWindows: Error: appError)")
_RE_ENSURE = re.compile(r"Ensure condition failed:")
_RE_ASSERT = re.compile(r"(?:Assertion failed:|check\(|ensureMsgf)", re.IGNORECASE)
_RE_GPU_HANG = re.compile(
    r"(?i)(?:GPU\s+hang|TDR|DXGI.*timeout|D3D.*hung|Rendering thread hung|GPU\s+crash)",
)
_RE_STREAM_STALL = re.compile(
    r"LogStreaming: Warning: Flushing.*took ([0-9]+\.[0-9]+)\s*ms",
)
_RE_GC = re.compile(
    r"(?i)(?:Garbage\s+Collection|GC\s+Finished).*?([0-9]+\.[0-9]+)\s*ms",
)
_RE_THREAD = re.compile(
    r"(?i)(?:deadlock|lock\s+contention|priority\s+inversion|"
    r"blocking\s+the\s+game\s+thread|synchronization\s+primitive)",
)
_RE_SHADER = re.compile(
    r"(?i)(?:ShaderCompil|shader\s+compile|Compiling\s+global\s+shader).*?"
    r"(?:took|in)\s+([0-9]+\.[0-9]+)\s*(?:ms|milliseconds)",
)
_RE_DISK = re.compile(
    r"(?i)(?:Disk\s+I/O|ReadFile|CreateFile|Async\s+loading\s+from\s+).*?"
    r"(?:slow|stall|blocked|([0-9]+\.[0-9]+)\s*ms)",
)
_RE_NET = re.compile(
    r"(?:LogNetPing: Warning: Round-trip.*?([0-9]+\.[0-9]+)\s*ms|"
    r"Connection\s+(?:timed\s+out|lost)|UNetConnection.*timeout)",
    re.IGNORECASE,
)

_DEFAULT_SEVERITIES: dict[str, str] = {
    "resilience.frame_hitch": "warn",
    "resilience.memory_growth": "warn",
    "resilience.crash_callstack": "critical",
    "resilience.gpu_hang": "critical",
    "resilience.streaming_stall": "warn",
    "resilience.gc_spike": "warn",
    "resilience.thread_contention": "error",
    "resilience.shader_compile_hitch": "warn",
    "resilience.disk_io_stall": "warn",
    "resilience.network_timeout": "warn",
}


def _rule_on(rule_id: str, config: dict[str, Any]) -> bool:
    entry = rule_entry_for(rule_id, config)
    st = (entry.get("status") or "on").strip().lower()
    if st == "off":
        return False
    alias = RULE_CONFIG_ALIASES.get(rule_id, "")
    if alias:
        alt = rule_entry_for(alias, config)
        st2 = (alt.get("status") or "").strip().lower()
        if st2 == "off":
            return False
    return True


def _rule_severity(rule_id: str, config: dict[str, Any]) -> str:
    entry = rule_entry_for(rule_id, config)
    sev = (entry.get("severity") or "").strip().lower()
    if sev in {"info", "warn", "error", "critical"}:
        return sev
    alias = RULE_CONFIG_ALIASES.get(rule_id, "")
    if alias:
        alt = rule_entry_for(alias, config)
        sev2 = (alt.get("severity") or "").strip().lower()
        if sev2 in {"info", "warn", "error", "critical"}:
            return sev2
    return _DEFAULT_SEVERITIES.get(rule_id, "warn")


def _finding(
    rule_id: str,
    severity: str,
    line_number: int | None,
    matched_text: str,
    detail: str,
    *,
    metric_value: float | None = None,
    threshold: float | None = None,
) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "severity": severity,
        "line_number": line_number,
        "matched_text": sanitize_log_line(matched_text),
        "detail": detail,
        "metric_value": metric_value,
        "threshold": threshold,
    }


def _estimate_mb_per_minute(samples: list[tuple[int, float]], lines_per_sec: float = 10.0) -> float | None:
    if len(samples) < 2:
        return None
    first_ln, first_mb = samples[0]
    last_ln, last_mb = samples[-1]
    delta_mb = last_mb - first_mb
    delta_lines = max(1, last_ln - first_ln)
    seconds = delta_lines / max(lines_per_sec, 0.1)
    minutes = max(seconds / 60.0, 1e-6)
    return delta_mb / minutes


def _eval_frame_hitches(
    lines: list[str],
    thresholds: dict[str, float | int],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    if not _rule_on("resilience.frame_hitch", config):
        return []
    out: list[dict[str, Any]] = []
    budget = float(thresholds["frame_hitch_ms"])
    sev = _rule_severity("resilience.frame_hitch", config)
    for i, line in enumerate(lines, start=1):
        m = _RE_FRAME_HITCH.search(line)
        if not m:
            continue
        ms = float(m.group(1))
        if ms > budget:
            out.append(
                _finding(
                    "resilience.frame_hitch",
                    sev,
                    i,
                    m.group(0),
                    f"Frame time {ms} ms exceeds threshold {budget} ms",
                    metric_value=ms,
                    threshold=budget,
                ),
            )
    return out


def _eval_memory_growth(
    lines: list[str],
    thresholds: dict[str, float | int],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    if not _rule_on("resilience.memory_growth", config):
        return []
    samples: list[tuple[int, float]] = []
    for i, line in enumerate(lines, start=1):
        m = _RE_MEM_SAMPLE.search(line)
        if m:
            samples.append((i, float(m.group(1))))
    rate = _estimate_mb_per_minute(samples)
    if rate is None:
        return []
    budget = float(thresholds["memory_growth_mb_per_minute"])
    if rate <= budget:
        return []
    sev = _rule_severity("resilience.memory_growth", config)
    return [
        _finding(
            "resilience.memory_growth",
            sev,
            samples[0][0],
            f"Mem Used: {samples[0][1]} MB → {samples[-1][1]} MB",
            f"Estimated memory growth {rate:.2f} MB/min exceeds {budget} MB/min",
            metric_value=rate,
            threshold=budget,
        ),
    ]


def _eval_crash_callstack(
    lines: list[str],
    thresholds: dict[str, float | int],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    if not _rule_on("resilience.crash_callstack", config):
        return []
    out: list[dict[str, Any]] = []
    fatal_sev = _rule_severity("resilience.crash_callstack", config)
    tolerance = int(thresholds["crash_count_tolerance"])
    fatal_count = 0
    ensure_count = 0
    for i, line in enumerate(lines, start=1):
        fm = _RE_FATAL.search(line)
        if fm:
            fatal_count += 1
            if fatal_count > tolerance:
                out.append(
                    _finding(
                        "resilience.crash_callstack",
                        fatal_sev,
                        i,
                        fm.group(0),
                        "Fatal or appError signature in log",
                    ),
                )
        if _RE_ASSERT.search(line):
            out.append(
                _finding(
                    "resilience.crash_callstack",
                    "error",
                    i,
                    sanitize_log_line(line[:200]),
                    "Assertion failure signature",
                ),
            )
        if _RE_ENSURE.search(line):
            ensure_count += 1
    max_ensure = int(thresholds["max_ensure_count"])
    if ensure_count > max_ensure:
        entry = rule_entry_for("crash.ensure_fired", config)
        es = str(entry.get("severity", "warn")).strip().lower()
        if es not in {"info", "warn", "error", "critical"}:
            es = "warn"
        out.append(
            _finding(
                "resilience.crash_callstack",
                es,
                None,
                "",
                f"Ensure condition failed count {ensure_count} exceeds {max_ensure}",
                metric_value=float(ensure_count),
                threshold=float(max_ensure),
            ),
        )
    return out


def _eval_regex_threshold(
    rule_id: str,
    pattern: re.Pattern[str],
    lines: list[str],
    config: dict[str, Any],
    threshold: float,
    compare: Callable[[float, float], bool],
    detail_fmt: str,
    *,
    use_group_value: bool = True,
) -> list[dict[str, Any]]:
    if not _rule_on(rule_id, config):
        return []
    sev = _rule_severity(rule_id, config)
    out: list[dict[str, Any]] = []
    for i, line in enumerate(lines, start=1):
        m = pattern.search(line)
        if not m:
            continue
        if use_group_value and m.lastindex and m.group(1) is not None:
            val = float(m.group(1))
            if not compare(val, threshold):
                continue
            out.append(
                _finding(
                    rule_id,
                    sev,
                    i,
                    m.group(0),
                    detail_fmt.format(val=val, threshold=threshold),
                    metric_value=val,
                    threshold=threshold,
                ),
            )
        elif use_group_value:
            continue
        else:
            out.append(
                _finding(
                    rule_id,
                    sev,
                    i,
                    m.group(0),
                    detail_fmt.format(val=0, threshold=threshold),
                ),
            )
    return out


def _eval_gpu_hang(lines: list[str], config: dict[str, Any]) -> list[dict[str, Any]]:
    if not _rule_on("resilience.gpu_hang", config):
        return []
    sev = _rule_severity("resilience.gpu_hang", config)
    out: list[dict[str, Any]] = []
    for i, line in enumerate(lines, start=1):
        m = _RE_GPU_HANG.search(line)
        if m:
            out.append(
                _finding(
                    "resilience.gpu_hang",
                    sev,
                    i,
                    m.group(0),
                    "GPU hang / TDR / driver timeout signature",
                ),
            )
    return out


def _eval_deadlock_long_frame(lines: list[str], config: dict[str, Any]) -> list[dict[str, Any]]:
    """Extreme frame times (deadlock suspect) attach to thread_contention rule family."""
    if not _rule_on("resilience.thread_contention", config):
        return []
    sev = _rule_severity("resilience.thread_contention", config)
    dl_ms = float(DEFAULT_DEADLOCK_FRAME_MS)
    out: list[dict[str, Any]] = []
    combined = re.compile(
        r"(?:LogStats: .*Frame [0-9]+.*took ([0-9]+\.[0-9]+) ms|"
        r"LogWindows: Error: (?:Hang detected|Not responding))",
    )
    for i, line in enumerate(lines, start=1):
        m = combined.search(line)
        if not m:
            continue
        if m.group(1):
            val = float(m.group(1))
            if val < dl_ms:
                continue
            out.append(
                _finding(
                    "resilience.thread_contention",
                    sev,
                    i,
                    m.group(0),
                    f"Extreme frame / stall {val} ms (deadlock suspect threshold {dl_ms} ms)",
                    metric_value=val,
                    threshold=dl_ms,
                ),
            )
        else:
            out.append(
                _finding(
                    "resilience.thread_contention",
                    sev,
                    i,
                    m.group(0),
                    "Hang detected / not responding signature",
                ),
            )
    return out


def _eval_network(lines: list[str], thresholds: dict[str, float | int], config: dict[str, Any]) -> list[dict[str, Any]]:
    if not _rule_on("resilience.network_timeout", config):
        return []
    budget = float(thresholds["latency_spike_ms"])
    sev = _rule_severity("resilience.network_timeout", config)
    out: list[dict[str, Any]] = []
    for i, line in enumerate(lines, start=1):
        m = _RE_NET.search(line)
        if not m:
            continue
        if m.lastindex and m.group(1):
            val = float(m.group(1))
            if val <= budget:
                continue
            out.append(
                _finding(
                    "resilience.network_timeout",
                    sev,
                    i,
                    m.group(0),
                    f"Network RTT or timeout signal: {val} ms (threshold {budget} ms)",
                    metric_value=val,
                    threshold=budget,
                ),
            )
        else:
            out.append(
                _finding(
                    "resilience.network_timeout",
                    sev,
                    i,
                    m.group(0),
                    "Connection timeout / loss signature",
                ),
            )
    return out


def _synthetic_findings() -> list[dict[str, Any]]:
    return [
        _finding(
            "resilience.frame_hitch",
            "warn",
            42,
            "LogStats: Frame 1200 took 63.2 ms",
            "dry_run: frame hitch sample",
            metric_value=63.2,
            threshold=50.0,
        ),
        _finding(
            "resilience.crash_callstack",
            "critical",
            108,
            "Fatal error: [dry_run synthetic]",
            "dry_run: fatal sample",
        ),
        _finding(
            "resilience.streaming_stall",
            "info",
            77,
            "LogStreaming: Warning: Flushing took 12.0 ms",
            "dry_run: sub-threshold streaming line (info severity for mix)",
            metric_value=12.0,
            threshold=500.0,
        ),
    ]


def _rollup_status(findings: list[dict[str, Any]]) -> str:
    has_crit = any(f.get("severity") == "critical" for f in findings)
    has_err = any(f.get("severity") == "error" for f in findings)
    has_warn = any(f.get("severity") == "warn" for f in findings)
    has_info = any(f.get("severity") == "info" for f in findings)
    if has_crit or has_err:
        return "fail"
    if has_warn or has_info:
        return "warn"
    return "pass"


def _summary_counts(findings: list[dict[str, Any]]) -> dict[str, int]:
    s = {"critical": 0, "error": 0, "warn": 0, "info": 0}
    for f in findings:
        sev = f.get("severity")
        if sev in s:
            s[str(sev)] += 1
    return s


def qa_resilience_scan(
    log_path: str,
    config_path: str | None = None,
    caller: str = "user-direct-debug",
) -> dict[str, Any]:
    """Scan log file or directory for resilience defects; return structured envelope."""
    memory_id: str | None = None
    cfg_path_resolved: str | None = config_path
    try:
        config = _load_config(config_path)
    except Exception as exc:
        return {
            "status": "error",
            "mode": _resolve_mode(),
            "log_path": log_path,
            "rules_evaluated": _RULE_COUNT,
            "findings_count": 0,
            "findings": [],
            "summary": {"critical": 0, "error": 0, "warn": 0, "info": 0},
            "thresholds_applied": {},
            "config_path": cfg_path_resolved or "default",
            "memory_id": None,
            "error": f"config_load_failed: {exc}",
        }

    mode = _resolve_mode()
    thresholds = thresholds_from_config(config)
    gc_budget = max(100.0, float(thresholds["frame_hitch_ms"]) * 2)
    thresholds_applied = {**{k: thresholds[k] for k in thresholds}, "gc_spike_ms": gc_budget}

    if mode == "dry_run":
        findings = _synthetic_findings()
        status = _rollup_status(findings)
        summary = _summary_counts(findings)
        return {
            "status": status,
            "mode": "dry_run",
            "log_path": log_path,
            "rules_evaluated": _RULE_COUNT,
            "findings_count": len(findings),
            "findings": findings,
            "summary": summary,
            "thresholds_applied": thresholds_applied,
            "config_path": cfg_path_resolved or str(default_config_path()),
            "memory_id": memory_id,
        }

    try:
        base = Path(log_path).expanduser()
        resolved = base.resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        return {
            "status": "error",
            "mode": "live",
            "log_path": log_path,
            "rules_evaluated": _RULE_COUNT,
            "findings_count": 0,
            "findings": [],
            "summary": {"critical": 0, "error": 0, "warn": 0, "info": 0},
            "thresholds_applied": thresholds_applied,
            "config_path": cfg_path_resolved or str(default_config_path()),
            "memory_id": None,
            "error": f"path_resolve_failed: {exc}",
        }

    files = iter_log_files(resolved)
    if not files:
        return {
            "status": "error",
            "mode": "live",
            "log_path": log_path,
            "rules_evaluated": _RULE_COUNT,
            "findings_count": 0,
            "findings": [],
            "summary": {"critical": 0, "error": 0, "warn": 0, "info": 0},
            "thresholds_applied": thresholds_applied,
            "config_path": cfg_path_resolved or str(default_config_path()),
            "memory_id": None,
            "error": "no_log_files",
        }

    all_lines: list[str] = []
    for fp in files:
        text, err = read_text_file_capped(fp)
        if err:
            return {
                "status": "error",
                "mode": "live",
                "log_path": log_path,
                "rules_evaluated": _RULE_COUNT,
                "findings_count": 0,
                "findings": [],
                "summary": {"critical": 0, "error": 0, "warn": 0, "info": 0},
                "thresholds_applied": thresholds_applied,
                "config_path": cfg_path_resolved or str(default_config_path()),
                "memory_id": None,
                "error": f"{err}:{fp}",
            }
        assert text is not None
        all_lines.extend(text.splitlines())

    findings: list[dict[str, Any]] = []
    findings.extend(_eval_frame_hitches(all_lines, thresholds, config))
    findings.extend(_eval_memory_growth(all_lines, thresholds, config))
    findings.extend(_eval_crash_callstack(all_lines, thresholds, config))
    findings.extend(_eval_gpu_hang(all_lines, config))
    findings.extend(
        _eval_regex_threshold(
            "resilience.streaming_stall",
            _RE_STREAM_STALL,
            all_lines,
            config,
            float(thresholds["streaming_stall_ms"]),
            lambda v, t: v > t,
            "Streaming flush {val} ms exceeds {threshold} ms",
        ),
    )
    findings.extend(
        _eval_regex_threshold(
            "resilience.gc_spike",
            _RE_GC,
            all_lines,
            config,
            gc_budget,
            lambda v, t: v > t,
            "GC phase {val} ms exceeds {threshold} ms",
        ),
    )
    findings.extend(
        _eval_regex_threshold(
            "resilience.thread_contention",
            _RE_THREAD,
            all_lines,
            config,
            0.0,
            lambda _v, _t: True,
            "Thread contention / deadlock suspect signature",
            use_group_value=False,
        ),
    )
    findings.extend(_eval_deadlock_long_frame(all_lines, config))
    findings.extend(
        _eval_regex_threshold(
            "resilience.shader_compile_hitch",
            _RE_SHADER,
            all_lines,
            config,
            float(thresholds["frame_hitch_ms"]),
            lambda v, t: v > t,
            "Shader compile {val} ms exceeds {threshold} ms",
        ),
    )
    findings.extend(
        _eval_regex_threshold(
            "resilience.disk_io_stall",
            _RE_DISK,
            all_lines,
            config,
            float(thresholds["streaming_stall_ms"]),
            lambda v, t: v > t,
            "Disk I/O stall signal (parsed {val} ms, threshold {threshold} ms)",
            use_group_value=False,
        ),
    )
    findings.extend(_eval_network(all_lines, thresholds, config))

    status = _rollup_status(findings)
    summary = _summary_counts(findings)

    if status == "fail":
        mem = _troubleshoot_commit_safe(
            "qa_resilience_scan fail",
            {"findings": [f for f in findings if f.get("severity") in {"error", "critical"}]},
            tags=f"qa_resilience|severity=error|caller={caller}",
            agent="agent-qa-resilience-game",
        )
    elif status == "warn":
        mem = _troubleshoot_commit_safe(
            "qa_resilience_scan warn",
            {"findings": findings[:3]},
            tags=f"qa_resilience|severity=warn|caller={caller}",
            agent="agent-qa-resilience-game",
        )
    else:
        mem = {}
    if mem.get("status") == "ok" and mem.get("id"):
        memory_id = str(mem["id"])

    return {
        "status": status,
        "mode": "live",
        "log_path": log_path,
        "rules_evaluated": _RULE_COUNT,
        "findings_count": len(findings),
        "findings": findings,
        "summary": summary,
        "thresholds_applied": thresholds_applied,
        "config_path": cfg_path_resolved or str(default_config_path()),
        "memory_id": memory_id,
    }


def register(mcp: FastMCP) -> None:
    """Register ``qa_resilience_scan`` MCP tool."""

    @mcp.tool(name="qa_resilience_scan")
    def qa_resilience_scan_tool(
        log_path: str,
        config_path: str | None = None,
        caller: str = "user-direct-debug",
    ) -> dict[str, Any]:
        """Scan Unreal/Gauntlet logs for resilience defects (frame hitches, leaks, crashes)."""
        return qa_resilience_scan(log_path, config_path=config_path, caller=caller)
