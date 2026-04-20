"""MCP tool: milestone_commit — Persist structured milestone handoff to SQLite."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from mcp.server.fastmcp import FastMCP

from _memory_db import get_db

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    """Register milestone_commit on the MCP server."""

    @mcp.tool()
    def milestone_commit(
        plan_slug: str,
        milestone: str,
        phase: str,
        status: str | None = None,
        files_touched: str | None = None,
        deferred_items: str | None = None,
        decisions: str | None = None,
        summary: str | None = None,
        errors_encountered: str | None = None,
        project: str | None = None,
        language: str | None = None,
        agent: str | None = None,
    ) -> dict[str, Any]:
        """Upsert a milestone row (``UNIQUE(plan_slug, milestone, phase)``).

        Args:
            plan_slug: Active plan identifier.
            milestone: Milestone name or key within the plan.
            phase: Lifecycle phase (e.g. spec, code, review, qa-l1, qa-l2).
            status: Optional outcome (success | partial | failed).
            files_touched: JSON array string of paths touched.
            deferred_items: JSON array of deferred work objects.
            decisions: JSON array of decision objects.
            summary: Short narrative summary.
            errors_encountered: JSON array of errors encountered.
            project: Optional project label.
            language: Optional language label.
            agent: Optional agent label.

        Returns:
            ``{"status": "ok", "id": "<uuid>"}`` or ``{"status": "error", ...}``.
        """
        try:
            mid = str(uuid.uuid4())
            conn = get_db()
            conn.execute(
                """
                INSERT OR REPLACE INTO milestones (
                  id, plan_slug, milestone, project, language, agent, phase,
                  status, files_touched, deferred_items, decisions, summary,
                  errors_encountered
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mid,
                    plan_slug,
                    milestone,
                    project,
                    language,
                    agent,
                    phase,
                    status,
                    files_touched,
                    deferred_items,
                    decisions,
                    summary,
                    errors_encountered,
                ),
            )
            conn.commit()
            conn.close()
            logger.info(
                "milestone_commit: plan=%s milestone=%s phase=%s id=%s",
                plan_slug,
                milestone,
                phase,
                mid,
            )
            return {"status": "ok", "id": mid}
        except Exception as exc:
            logger.error("milestone_commit failed: %s", exc, exc_info=True)
            return {"status": "error", "error": str(exc)}
