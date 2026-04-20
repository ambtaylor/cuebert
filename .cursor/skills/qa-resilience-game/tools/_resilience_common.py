"""Shared helpers for qa-resilience-game: config, mode, paths, memory commit."""

from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from datetime import date
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_VAULT_MODE_KEY = "qa_resilience.mode"

# Defaults aligned with .cuebert/config/qa-resilience-game.yaml
DEFAULT_FRAME_HITCH_MS = 50.0
DEFAULT_MAX_HITCHES_PER_MINUTE = 6
DEFAULT_MEMORY_GROWTH_MB_PER_MINUTE = 20.0
DEFAULT_CRASH_COUNT_TOLERANCE = 0
DEFAULT_STREAMING_STALL_MS = 500.0
DEFAULT_MAX_ENSURE_COUNT = 3
DEFAULT_LATENCY_SPIKE_MS = 200.0
DEFAULT_HEARTBEAT_ABSENCE_S = 30.0
DEFAULT_DEADLOCK_FRAME_MS = 10000.0

_MAX_LOG_BYTES = 10 * 1024 * 1024

# Map resilience.* rule ids to legacy config keys for severity/status overrides.
RULE_CONFIG_ALIASES: dict[str, str] = {
    "resilience.frame_hitch": "hitch.frame_time_exceeded",
    "resilience.memory_growth": "memory.growth_rate",
    "resilience.crash_callstack": "crash.fatal_signal",
    "resilience.gpu_hang": "resilience.deadlock_suspect",
    "resilience.streaming_stall": "streaming.stall",
    "resilience.gc_spike": "memory.leak_signature",
    "resilience.thread_contention": "resilience.deadlock_suspect",
    "resilience.shader_compile_hitch": "hitch.frame_time_exceeded",
    "resilience.disk_io_stall": "streaming.stall",
    "resilience.network_timeout": "network.latency_spike",
}


def find_hub_root(start: Path | None = None) -> Path:
    """Locate repo root (directory containing ``.cuebert``)."""
    p = (start or Path(__file__).resolve()).resolve()
    for parent in [p, *p.parents]:
        if (parent / ".cuebert").is_dir():
            return parent
    raise FileNotFoundError("Could not locate Cuebert hub root (.cuebert).")


def default_config_path() -> Path:
    """Hub default YAML for qa-resilience-game."""
    return find_hub_root() / ".cuebert" / "config" / "qa-resilience-game.yaml"


def _vault_mode_raw() -> str | None:
    """Optional vault override for mode (placeholder integration)."""
    try:
        from _vault import CUEBERT_VAULT_AVAILABLE, get_resolver

        if not CUEBERT_VAULT_AVAILABLE:
            return None
        v = get_resolver().get_credential(_VAULT_MODE_KEY)
        if v and str(v).strip():
            return str(v).strip().lower()
    except Exception as exc:
        logger.debug("vault qa_resilience.mode unavailable: %s", exc)
    return None


def _resolve_mode() -> str:
    """Return ``dry_run`` or ``live`` from env or vault."""
    env = os.environ.get("CUEBERT_QA_RESILIENCE_MODE", "").strip().lower()
    if env in {"dry_run", "dry-run"}:
        return "dry_run"
    if env in {"live", "on", "1", "true"}:
        return "live"
    vault = _vault_mode_raw()
    if vault in {"dry_run", "dry-run"}:
        return "dry_run"
    if vault in {"live", "on", "1", "true"}:
        return "live"
    return "live"


def _load_config(config_path: str | None = None) -> dict[str, Any]:
    """Load YAML config; missing file returns minimal defaults."""
    path = Path(config_path).expanduser() if config_path else default_config_path()
    if not path.is_file():
        return {
            "version": 1,
            "thresholds": {},
            "rules": {},
            "spec_only_as_info": False,
        }
    with open(path, encoding="utf-8", errors="replace") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def rule_entry_for(rule_id: str, config: dict[str, Any]) -> dict[str, Any]:
    """Merge YAML rule overrides for *rule_id* or its legacy alias."""
    rules = config.get("rules") or {}
    if not isinstance(rules, dict):
        return {}
    if rule_id in rules and isinstance(rules[rule_id], dict):
        return dict(rules[rule_id])
    alias = RULE_CONFIG_ALIASES.get(rule_id)
    if alias and alias in rules and isinstance(rules[alias], dict):
        return dict(rules[alias])
    return {}


def thresholds_from_config(config: dict[str, Any]) -> dict[str, float | int]:
    """Normalized threshold map with hub defaults for missing keys."""
    t = config.get("thresholds") or {}
    if not isinstance(t, dict):
        t = {}
    return {
        "frame_hitch_ms": float(t.get("frame_hitch_ms", DEFAULT_FRAME_HITCH_MS)),
        "max_hitches_per_minute": int(t.get("max_hitches_per_minute", DEFAULT_MAX_HITCHES_PER_MINUTE)),
        "memory_growth_mb_per_minute": float(
            t.get("memory_growth_mb_per_minute", DEFAULT_MEMORY_GROWTH_MB_PER_MINUTE),
        ),
        "crash_count_tolerance": int(t.get("crash_count_tolerance", DEFAULT_CRASH_COUNT_TOLERANCE)),
        "streaming_stall_ms": float(t.get("streaming_stall_ms", DEFAULT_STREAMING_STALL_MS)),
        "max_ensure_count": int(t.get("max_ensure_count", DEFAULT_MAX_ENSURE_COUNT)),
        "latency_spike_ms": float(t.get("latency_spike_ms", DEFAULT_LATENCY_SPIKE_MS)),
        "heartbeat_absence_s": float(t.get("heartbeat_absence_s", DEFAULT_HEARTBEAT_ABSENCE_S)),
        "deadlock_frame_ms": float(DEFAULT_DEADLOCK_FRAME_MS),
    }


def sanitize_log_line(line: str, max_len: int = 2048) -> str:
    """Reduce log-injection / control-character risk for stored excerpts."""
    if not line:
        return ""
    cleaned = "".join(ch if ch >= " " or ch in "\t" else " " for ch in line)
    if len(cleaned) > max_len:
        return cleaned[: max_len - 3] + "..."
    return cleaned


def iter_log_files(log_path: Path) -> list[Path]:
    """Resolve *log_path* to a list of readable log files (max size enforced later)."""
    if log_path.is_file():
        return [log_path]
    if log_path.is_dir():
        out: list[Path] = []
        for pat in ("*.log", "*.txt"):
            out.extend(sorted(log_path.glob(pat)))
            for p in log_path.rglob(pat):
                if p not in out:
                    out.append(p)
        return sorted(set(out), key=lambda x: str(x))
    return []


def read_text_file_capped(path: Path, max_bytes: int = _MAX_LOG_BYTES) -> tuple[str | None, str | None]:
    """Read file as text or return (None, error_code)."""
    try:
        st = path.stat()
    except OSError:
        return None, "stat_failed"
    if st.st_size > max_bytes:
        return None, "file_too_large"
    try:
        return path.read_text(encoding="utf-8", errors="replace"), None
    except OSError:
        return None, "read_failed"


def troubleshoot_commit_safe(
    problem: str,
    what_tried: Any,
    *,
    why_tried: str | None = None,
    what_worked: str | None = None,
    tags: str | None = None,
    project: str | None = None,
    agent: str | None = None,
    plan_slug: str | None = None,
) -> dict[str, Any]:
    """Best-effort memory insert; never raises."""
    skills_dir = Path(__file__).resolve().parents[2]
    mem_tools = skills_dir / "memory-toolkit" / "tools"
    if not mem_tools.is_dir():
        sys.stderr.write("qa-resilience-game: memory-toolkit not found; skip troubleshoot_commit\n")
        return {"status": "skipped", "error": "memory-toolkit not found"}

    inserted = False
    if str(mem_tools) not in sys.path:
        sys.path.insert(0, str(mem_tools))
        inserted = True
    try:
        from _memory_db import generate_embedding, get_db, _get_memory_mode

        wt_json = what_tried if isinstance(what_tried, str) else json.dumps(
            what_tried,
            ensure_ascii=False,
        )
        rid = str(uuid.uuid4())
        day = date.today().isoformat()
        embed_text = "\n\n".join(
            part for part in (problem, wt_json, why_tried or "", what_worked or "") if part
        )
        embedding_blob = generate_embedding(embed_text)
        if embedding_blob is None and _get_memory_mode() == "text":
            logger.debug("memory_mode=text; skipping embedding for qa-resilience-game")

        conn = get_db()
        conn.execute(
            """
                INSERT INTO troubleshooting (
                  id, date, project, agent, language, problem, what_tried,
                  why_tried, what_worked, tags, errors, files_touched,
                  plan_slug, milestone, transcript_id, source, embedding
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
            (
                rid,
                day,
                project,
                agent,
                None,
                problem,
                wt_json,
                why_tried,
                what_worked,
                tags,
                None,
                None,
                plan_slug,
                None,
                None,
                "agent",
                embedding_blob,
            ),
        )
        conn.commit()
        conn.close()
        logger.info("qa-resilience-game troubleshoot_commit: id=%s", rid)
        return {"status": "ok", "id": rid}
    except Exception as exc:
        sys.stderr.write(f"qa-resilience-game: troubleshoot_commit failed: {exc}\n")
        logger.warning("troubleshoot_commit_safe failed: %s", exc, exc_info=True)
        return {"status": "error", "error": str(exc)}
    finally:
        if inserted:
            try:
                sys.path.remove(str(mem_tools))
            except ValueError:
                pass
