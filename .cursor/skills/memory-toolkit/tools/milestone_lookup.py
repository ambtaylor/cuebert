"""MCP tool: milestone_lookup — Read milestone rows for orchestrated harness context."""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from _memory_db import get_db

logger = logging.getLogger(__name__)


def _parse_json_list(raw: str | None) -> list[Any]:
    if not raw:
        return []
    try:
        val = json.loads(raw)
        return val if isinstance(val, list) else []
    except json.JSONDecodeError:
        return []


def _build_bridge(sessions: list[dict[str, Any]]) -> dict[str, Any]:
    deferred_all: list[dict[str, Any]] = []
    decisions_all: list[dict[str, Any]] = []
    files_set: set[str] = set()

    for s in sessions:
        ms_id = s.get("id")
        ms_name = s.get("milestone")
        ms_phase = s.get("phase")
        for item in _parse_json_list(s.get("deferred_items")):
            if isinstance(item, dict):
                row = dict(item)
            else:
                row = {"item": item}
            row["source_milestone_id"] = ms_id
            row["source_milestone"] = ms_name
            row["source_phase"] = ms_phase
            deferred_all.append(row)
        for dec in _parse_json_list(s.get("decisions")):
            if isinstance(dec, dict):
                drow = dict(dec)
            else:
                drow = {"decision": dec}
            drow["source_milestone_id"] = ms_id
            drow["source_milestone"] = ms_name
            drow["source_phase"] = ms_phase
            decisions_all.append(drow)
        for path in _parse_json_list(s.get("files_touched")):
            if isinstance(path, str):
                files_set.add(path)

    return {
        "deferred_items": deferred_all,
        "decisions": decisions_all,
        "files_touched": sorted(files_set),
    }


def register(mcp: FastMCP) -> None:
    """Register milestone_lookup on the MCP server."""

    @mcp.tool()
    def milestone_lookup(
        plan_slug: str,
        milestone: str | None = None,
        include_bridge: bool | None = None,
    ) -> dict[str, Any]:
        """Fetch milestone memory for a plan (single milestone or full plan).

        When *milestone* is omitted, returns all milestones for *plan_slug*
        ordered by ``created_at``. Optionally aggregates a *bridge* summary
        (deferred items, decisions, files touched).

        Args:
            plan_slug: Plan identifier to query.
            milestone: Optional milestone key; when set, returns one row.
            include_bridge: When True, include bridge aggregate. When omitted,
                defaults to True for full-plan mode and False for single row.

        Returns:
            Structured JSON with ``sessions`` and optional ``bridge``.
        """
        try:
            if include_bridge is None:
                include_bridge = milestone is None

            conn = get_db()
            if milestone:
                cur = conn.execute(
                    """
                    SELECT * FROM milestones
                    WHERE plan_slug = ? AND milestone = ?
                    ORDER BY created_at
                    """,
                    (plan_slug, milestone),
                )
            else:
                cur = conn.execute(
                    """
                    SELECT * FROM milestones
                    WHERE plan_slug = ?
                    ORDER BY created_at
                    """,
                    (plan_slug,),
                )
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()

            payload: dict[str, Any] = {"sessions": rows}
            if include_bridge and rows:
                payload["bridge"] = _build_bridge(rows)

            logger.info(
                "milestone_lookup: plan=%s milestone=%s rows=%d bridge=%s",
                plan_slug,
                milestone,
                len(rows),
                include_bridge,
            )
            return {"status": "ok", "data": payload}
        except Exception as exc:
            logger.error("milestone_lookup failed: %s", exc, exc_info=True)
            return {"status": "error", "error": str(exc)}
