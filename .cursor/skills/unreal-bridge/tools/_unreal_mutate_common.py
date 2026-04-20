"""Helpers for ``unreal_set_property`` / ``unreal_call_function`` (not MCP-registered)."""

from __future__ import annotations

import json
import logging
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_MAX_VALUE_JSON_BYTES = 256 * 1024
_MAX_LIST_LEN = 1024
_MAX_DICT_DEPTH = 4
_MAX_STR_LEN = 4096


def find_hub_root() -> Path:
    """Locate repo root (directory containing ``.cuebert``)."""
    p = Path(__file__).resolve()
    for parent in [p, *p.parents]:
        if (parent / ".cuebert").is_dir():
            return parent
    raise FileNotFoundError("Could not locate Cuebert hub root (.cuebert).")


def mutation_trace_timestamp() -> str:
    """Filesystem-safe UTC stamp for ``.cuebert/traces/unreal/<stamp>/``."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


def _normalize_what_tried(what_tried: Any) -> str:
    if isinstance(what_tried, str):
        return what_tried
    if isinstance(what_tried, list):
        return json.dumps(what_tried, ensure_ascii=False)
    return json.dumps(what_tried, ensure_ascii=False)


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
    """Best-effort ``troubleshoot_commit`` equivalent; never raises."""
    skills = Path(__file__).resolve().parents[2]
    mem_tools = skills / "memory-toolkit" / "tools"
    if not mem_tools.is_dir():
        sys.stderr.write(
            "unreal-bridge mutate: memory-toolkit not found; skip troubleshoot_commit\n",
        )
        return {"status": "skipped", "error": "memory-toolkit not found"}

    inserted = False
    if str(mem_tools) not in sys.path:
        sys.path.insert(0, str(mem_tools))
        inserted = True
    try:
        from _memory_db import generate_embedding, get_db, _get_memory_mode

        wt_json = _normalize_what_tried(what_tried)
        rid = str(uuid.uuid4())
        day = date.today().isoformat()
        embed_text = "\n\n".join(
            part for part in (problem, wt_json, why_tried or "", what_worked or "") if part
        )
        embedding_blob = generate_embedding(embed_text)
        if embedding_blob is None and _get_memory_mode() == "text":
            logger.debug("memory_mode=text; skipping embedding for unreal mutate")

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
        logger.info("unreal mutate troubleshoot_commit: id=%s", rid)
        return {"status": "ok", "id": rid}
    except Exception as exc:
        sys.stderr.write(f"unreal-bridge mutate: troubleshoot_commit failed: {exc}\n")
        logger.warning("troubleshoot_commit_safe failed: %s", exc, exc_info=True)
        return {"status": "error", "error": str(exc)}
    finally:
        if inserted:
            try:
                sys.path.remove(str(mem_tools))
            except ValueError:
                pass


def append_mutation_line(hub: Path, trace_ts: str, row: dict[str, Any]) -> Path:
    """Append one JSON object as a line to ``mutations.jsonl``."""
    trace_dir = hub / ".cuebert" / "traces" / "unreal" / trace_ts
    trace_dir.mkdir(parents=True, exist_ok=True)
    path = trace_dir / "mutations.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    return path


def validate_mutation_value(value: Any) -> str | None:
    """Return an error string or ``None`` if *value* is allowed for JSON mutation payloads."""

    def walk(val: Any, dict_stack: int) -> str | None:
        if isinstance(val, (int, float, bool)):
            return None
        if val is None:
            return "null is not an allowed mutation value"
        if isinstance(val, str):
            if len(val) > _MAX_STR_LEN:
                return f"string exceeds {_MAX_STR_LEN} characters"
            return None
        if isinstance(val, list):
            if len(val) > _MAX_LIST_LEN:
                return f"list exceeds {_MAX_LIST_LEN} elements"
            for item in val:
                err = walk(item, dict_stack)
                if err:
                    return err
            return None
        if isinstance(val, dict):
            if dict_stack >= _MAX_DICT_DEPTH:
                return f"dict nesting exceeds max depth {_MAX_DICT_DEPTH}"
            for k, v in val.items():
                if not isinstance(k, str):
                    return "dict keys must be strings"
                err = walk(v, dict_stack + 1)
                if err:
                    return err
            return None
        if callable(val):
            return "callables are not allowed in mutation values"
        return "unsupported value type"

    err = walk(value, 0)
    if err:
        return err
    try:
        raw = json.dumps(value, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError) as exc:
        return f"value is not JSON-serializable: {exc}"
    if len(raw) > _MAX_VALUE_JSON_BYTES:
        return "serialized value exceeds 256KB"
    return None


def validate_parameters_dict(args: dict[str, Any] | None) -> str | None:
    """Validate ``args`` for ``call_exposed_function`` (empty dict allowed)."""
    if args is None:
        return None
    if not isinstance(args, dict):
        return "args must be a dict or null"
    return validate_mutation_value(args)
