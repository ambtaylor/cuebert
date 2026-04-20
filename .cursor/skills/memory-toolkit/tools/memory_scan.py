"""MCP tool: memory_scan — Backfill troubleshooting rows from JSONL agent transcripts."""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import time
import urllib.error
import urllib.request
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from _memory_db import generate_embedding, get_db
from troubleshoot_commit import _normalize_what_tried

logger = logging.getLogger(__name__)

_DEFAULT_TRANSCRIPTS_DIR = (
    "/Users/ambtaylo/.cursor/projects/"
    "Users-ambtaylo-Library-CloudStorage-OneDrive-Cisco-AID-V2-AID-UI-V2-aid-design-code-workspace/"
    "agent-transcripts"
)

_OPENAI_BASE = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
_CHAT_URL = f"{_OPENAI_BASE}/chat/completions"
_CHAT_MODEL = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini")
_MIN_TRANSCRIPT_CHARS = 500
_MAX_USER_CHARS = 12000
_LLM_SLEEP_SEC = 0.5

_SCAN_SYSTEM_PROMPT = """You are analyzing an AI agent conversation transcript to extract debugging and troubleshooting knowledge.

Extract ONLY conversations where the agent encountered errors, fixed bugs, resolved issues, or tried multiple approaches. Skip conversations that are purely feature implementation without debugging.

Return a JSON array (can be empty if no debugging knowledge found):
[
  {
    "problem": "Short description of the error/issue",
    "what_tried": [{"approach": "What was attempted", "outcome": "What happened"}],
    "why_tried": "Reasoning/hypothesis behind the approaches",
    "what_worked": "The final resolution (or null if unresolved)",
    "tags": "comma-separated relevant tags"
  }
]

If no debugging/troubleshooting content is found, return []."""


def _since_epoch_cutoff(since: str | None) -> float | None:
    if not since:
        return None
    raw = since.strip()
    if "T" in raw:
        raw = raw.split("T", 1)[0]
    d = date.fromisoformat(raw[:10])
    dt = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return dt.timestamp()


def _discover_jsonl(root: Path, since_ts: float | None, limit: int) -> list[Path]:
    files = [p for p in root.rglob("*.jsonl") if p.is_file()]
    filtered: list[Path] = []
    for p in files:
        try:
            mtime = p.stat().st_mtime
        except OSError:
            continue
        if since_ts is not None and mtime < since_ts:
            continue
        filtered.append(p)
    filtered.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    if limit > 0:
        filtered = filtered[:limit]
    return filtered


def _message_text_from_obj(obj: dict[str, Any]) -> tuple[str, str]:
    role = str(obj.get("role", "") or "")
    msg = obj.get("message")
    if not isinstance(msg, dict):
        return role, ""
    content = msg.get("content")
    texts: list[str] = []
    if isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                t = block.get("text")
                if isinstance(t, str) and t.strip():
                    texts.append(t.strip())
    elif isinstance(content, str) and content.strip():
        texts.append(content.strip())
    return role, "\n".join(texts)


def _parse_transcript(path: Path) -> str:
    parts: list[str] = []
    with path.open(encoding="utf-8", errors="replace") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue
            role, text = _message_text_from_obj(obj)
            if text:
                label = role or "unknown"
                parts.append(f"{label}: {text}")
    return "\n\n".join(parts)


def _truncate_tail(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def _parse_json_array_from_llm(content: str) -> list[dict[str, Any]]:
    t = content.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
        t = re.sub(r"\s*```\s*$", "", t)
    t = t.strip()
    try:
        val = json.loads(t)
    except json.JSONDecodeError:
        start = t.find("[")
        end = t.rfind("]")
        if start == -1 or end <= start:
            return []
        val = json.loads(t[start : end + 1])
    if isinstance(val, list):
        return [x for x in val if isinstance(x, dict)]
    if isinstance(val, dict):
        inner = val.get("items")
        if isinstance(inner, list):
            return [x for x in inner if isinstance(x, dict)]
    return []


def _chat_extract_items(transcript_text: str) -> list[dict[str, Any]]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set in the environment.")
    user_body = (
        "Transcript (may be truncated to the end of the conversation):\n\n"
        + transcript_text
    )
    payload = json.dumps(
        {
            "model": _CHAT_MODEL,
            "messages": [
                {"role": "system", "content": _SCAN_SYSTEM_PROMPT},
                {"role": "user", "content": user_body},
            ],
            "temperature": 0.2,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        _CHAT_URL,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ValueError(f"OpenAI chat HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"OpenAI chat request failed: {exc}") from exc

    data = json.loads(raw)
    err = data.get("error")
    if err:
        raise ValueError(f"OpenAI API error: {err}")
    choices = data.get("choices") or []
    if not choices:
        raise ValueError("OpenAI response missing choices.")
    msg = choices[0].get("message") or {}
    content = msg.get("content")
    if not isinstance(content, str):
        raise ValueError("OpenAI response missing message content.")
    return _parse_json_array_from_llm(content)


def _transcript_id_from_path(path: Path) -> str:
    return path.stem


def _has_transcript(conn: sqlite3.Connection, transcript_id: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM troubleshooting WHERE transcript_id = ? LIMIT 1",
        (transcript_id,),
    )
    return cur.fetchone() is not None


def _insert_troubleshooting_row(
    conn: sqlite3.Connection,
    item: dict[str, Any],
    *,
    transcript_id: str,
    project: str | None,
    record_date: str,
    dry_run: bool,
) -> bool:
    problem = (item.get("problem") or "").strip()
    if not problem:
        logger.warning("memory_scan: skip item with empty problem transcript=%s", transcript_id)
        return False
    wt_json = _normalize_what_tried(item.get("what_tried") or [])
    why_raw = item.get("why_tried")
    if why_raw is None:
        why_tried: str | None = None
    elif isinstance(why_raw, str):
        why_tried = why_raw.strip() or None
    else:
        why_tried = json.dumps(why_raw, ensure_ascii=False)
    ww = item.get("what_worked")
    if ww is None:
        what_worked: str | None = None
    elif isinstance(ww, str):
        what_worked = ww.strip() or None
    else:
        what_worked = json.dumps(ww, ensure_ascii=False)
    tags_raw = item.get("tags")
    if tags_raw is None:
        tags: str | None = None
    elif isinstance(tags_raw, str):
        tags = tags_raw.strip() or None
    else:
        tags = str(tags_raw)

    embed_text = "\n\n".join(
        part
        for part in (problem, wt_json, why_tried or "", what_worked or "")
        if part
    )
    rid = str(uuid.uuid4())

    if dry_run:
        logger.info(
            "memory_scan dry_run: would insert id=%s transcript=%s problem=%.80s…",
            rid,
            transcript_id,
            problem,
        )
        return True

    embedding_blob = generate_embedding(embed_text)
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
            record_date,
            project,
            None,
            None,
            problem,
            wt_json,
            why_tried,
            what_worked,
            tags,
            None,
            None,
            None,
            None,
            transcript_id,
            "scanner",
            embedding_blob,
        ),
    )
    conn.commit()
    return True


def register(mcp: FastMCP) -> None:
    """Register memory_scan on the MCP server."""

    @mcp.tool()
    def memory_scan(
        transcripts_dir: str | None = None,
        project: str | None = None,
        since: str | None = None,
        limit: int = 0,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Scan JSONL transcripts and extract troubleshooting knowledge."""
        root = Path(transcripts_dir or _DEFAULT_TRANSCRIPTS_DIR).expanduser()
        if not root.is_dir():
            return {
                "status": "error",
                "error": f"transcripts_dir is not a directory: {root}",
            }

        since_ts = _since_epoch_cutoff(since)
        paths = _discover_jsonl(root, since_ts, limit)

        conn = get_db()
        try:
            stats: dict[str, Any] = {
                "status": "ok",
                "transcripts_discovered": len(paths),
                "transcripts_skipped_duplicate": 0,
                "transcripts_skipped_short": 0,
                "transcripts_llm_called": 0,
                "items_extracted": 0,
                "items_inserted": 0,
                "errors": [],
                "dry_run": dry_run,
            }

            for idx, path in enumerate(paths, start=1):
                tid = _transcript_id_from_path(path)
                if _has_transcript(conn, tid):
                    stats["transcripts_skipped_duplicate"] += 1
                else:
                    text = _parse_transcript(path)
                    if len(text) < _MIN_TRANSCRIPT_CHARS:
                        stats["transcripts_skipped_short"] += 1
                    else:
                        truncated = _truncate_tail(text, _MAX_USER_CHARS)
                        record_date = datetime.fromtimestamp(
                            path.stat().st_mtime,
                            tz=timezone.utc,
                        ).date().isoformat()

                        try:
                            items = _chat_extract_items(truncated)
                        except Exception as exc:
                            logger.error(
                                "memory_scan LLM failed transcript=%s: %s",
                                tid,
                                exc,
                                exc_info=True,
                            )
                            stats["errors"].append({"transcript_id": tid, "error": str(exc)})
                            time.sleep(_LLM_SLEEP_SEC)
                        else:
                            stats["transcripts_llm_called"] += 1
                            stats["items_extracted"] += len(items)

                            for it in items:
                                try:
                                    if _insert_troubleshooting_row(
                                        conn,
                                        it,
                                        transcript_id=tid,
                                        project=project,
                                        record_date=record_date,
                                        dry_run=dry_run,
                                    ):
                                        stats["items_inserted"] += 1
                                except Exception as exc:
                                    logger.error(
                                        "memory_scan insert failed transcript=%s: %s",
                                        tid,
                                        exc,
                                        exc_info=True,
                                    )
                                    stats["errors"].append(
                                        {"transcript_id": tid, "error": str(exc)},
                                    )

                            time.sleep(_LLM_SLEEP_SEC)

                if idx % 10 == 0:
                    logger.info(
                        "memory_scan progress: %s/%s (last=%s)",
                        idx,
                        len(paths),
                        tid,
                    )

            stats["errors_count"] = len(stats["errors"])
            return stats
        finally:
            conn.close()
