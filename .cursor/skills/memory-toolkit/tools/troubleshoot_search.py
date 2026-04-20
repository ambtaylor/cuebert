"""MCP tool: troubleshoot_search — Hybrid FTS5 + vector search over troubleshooting memory."""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from _memory_db import generate_embedding, get_db, hybrid_search

logger = logging.getLogger(__name__)


def _row_to_result(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    blob = out.pop("embedding", None)
    if blob is not None:
        out["embedding_bytes"] = len(blob) if isinstance(blob, (bytes, memoryview)) else None
    for key in ("what_tried", "errors", "files_touched"):
        val = out.get(key)
        if isinstance(val, str) and val.strip().startswith(("[", "{")):
            try:
                out[key] = json.loads(val)
            except json.JSONDecodeError:
                pass
    return out


def register(mcp: FastMCP) -> None:
    """Register troubleshoot_search on the MCP server."""

    @mcp.tool()
    def troubleshoot_search(
        query: str,
        project: str | None = None,
        tags: str | list[str] | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Search prior debugging sessions (FTS5/BM25; optional vector in hybrid mode).

        With ``CUEBERT_MEMORY_MODE=text`` (default), ranking uses FTS5/BM25 only; query
        embeddings are not computed and vector contribution in the hybrid score is zero.

        With ``CUEBERT_MEMORY_MODE=hybrid``, a query embedding is computed and merged
        with FTS scores (0.6 vector + 0.4 FTS) for rows that have stored embeddings.

        Args:
            query: Natural-language or keyword query.
            project: Optional exact project filter.
            tags: Optional tag filter (string or list of substrings matched against ``tags``).
            limit: Max rows to return (default 10).

        Returns:
            Ranked results with hybrid, vector, and FTS scores plus full text fields.
        """
        try:
            if not query or not str(query).strip():
                return {
                    "status": "error",
                    "error": "query is required and must be non-empty.",
                }

            q_emb = generate_embedding(query.strip())
            filters: dict[str, Any] = {}
            if project:
                filters["project"] = project
            if tags is not None:
                filters["tags"] = tags

            conn = get_db()
            rows = hybrid_search(conn, query.strip(), q_emb, filters, limit)
            conn.close()

            results = [_row_to_result(r) for r in rows]
            return {
                "status": "ok",
                "data": {
                    "query": query.strip(),
                    "count": len(results),
                    "results": results,
                },
            }
        except Exception as exc:
            logger.error("troubleshoot_search failed: %s", exc, exc_info=True)
            return {"status": "error", "error": str(exc)}
