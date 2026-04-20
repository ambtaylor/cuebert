"""MCP tool: troubleshoot_commit — Record debugging knowledge with embedding + FTS5."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import date
from typing import Any

from mcp.server.fastmcp import FastMCP

from _memory_db import _get_memory_mode, generate_embedding, get_db

logger = logging.getLogger(__name__)

_text_mode_embed_log_done = False


def _normalize_what_tried(what_tried: Any) -> str:
    if isinstance(what_tried, str):
        return what_tried
    if isinstance(what_tried, list):
        return json.dumps(what_tried, ensure_ascii=False)
    return json.dumps(what_tried, ensure_ascii=False)


def register(mcp: FastMCP) -> None:
    """Register troubleshoot_commit on the MCP server."""

    @mcp.tool()
    def troubleshoot_commit(
        problem: str,
        what_tried: Any,
        why_tried: str | None = None,
        what_worked: str | None = None,
        tags: str | None = None,
        errors: str | None = None,
        files_touched: str | None = None,
        project: str | None = None,
        agent: str | None = None,
        language: str | None = None,
        plan_slug: str | None = None,
        milestone: str | None = None,
        transcript_id: str | None = None,
        record_date: str | None = None,
        source: str = "agent",
    ) -> dict[str, Any]:
        """Insert a troubleshooting record and refresh the FTS5 index via triggers.

        Args:
            problem: Short problem statement (required).
            what_tried: JSON array of ``{approach, outcome}`` objects, or JSON string.
            why_tried: Reasoning / hypothesis text.
            what_worked: Resolution that fixed the issue.
            tags: Freeform tags (comma-separated or plain text).
            errors: JSON array string of raw errors.
            files_touched: JSON array string of file paths.
            project, agent, language: Optional labels.
            plan_slug, milestone, transcript_id: Optional traceability fields.
            record_date: ISO date string; defaults to today when omitted.
            source: ``agent`` (default) or ``scanner`` for future backfill.

        Returns:
            ``{"status": "ok", "id": "<uuid>"}`` or ``{"status": "error", ...}``.
        """
        global _text_mode_embed_log_done
        try:
            wt_json = _normalize_what_tried(what_tried)
            rid = str(uuid.uuid4())
            day = record_date or date.today().isoformat()

            embed_text = "\n\n".join(
                part for part in (
                    problem,
                    wt_json,
                    why_tried or "",
                    what_worked or "",
                ) if part
            )
            embedding_blob = generate_embedding(embed_text)
            if embedding_blob is None and _get_memory_mode() == "text":
                if not _text_mode_embed_log_done:
                    logger.debug("memory_mode=text; skipping embedding")
                    _text_mode_embed_log_done = True

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
                    language,
                    problem,
                    wt_json,
                    why_tried,
                    what_worked,
                    tags,
                    errors,
                    files_touched,
                    plan_slug,
                    milestone,
                    transcript_id,
                    source,
                    embedding_blob,
                ),
            )
            conn.commit()
            conn.close()
            logger.info("troubleshoot_commit: id=%s project=%s", rid, project)
            return {"status": "ok", "id": rid}
        except Exception as exc:
            logger.error("troubleshoot_commit failed: %s", exc, exc_info=True)
            return {"status": "error", "error": str(exc)}
