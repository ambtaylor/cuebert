"""MCP tool: list named ComfyUI workflow graphs bundled with this skill."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from _comfyui_client import workflows_dir

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    """Register ``comfyui_list_workflows`` on the MCP server."""

    @mcp.tool()
    def comfyui_list_workflows() -> dict[str, Any]:
        """List workflow JSON files available under this skill's ``workflows/`` directory.

        Each entry may include an optional ``_cuebert_description`` field from the
        workflow JSON root (human-readable summary).

        Returns:
            ``workflows`` (list of dicts), ``count``, ``source_dir``.
        """
        try:
            d = workflows_dir()
            if not d.is_dir():
                return {
                    "status": "ok",
                    "workflows": [],
                    "count": 0,
                    "source_dir": str(d),
                }
            rows: list[dict[str, Any]] = []
            for path in sorted(d.glob("*.json")):
                if not path.is_file():
                    continue
                description: str | None = None
                try:
                    with path.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, dict):
                        raw = data.get("_cuebert_description")
                        if isinstance(raw, str):
                            description = raw
                except (json.JSONDecodeError, OSError) as exc:
                    logger.warning("Skipping unreadable workflow %s: %s", path, exc)
                    continue
                mtime = datetime.fromtimestamp(
                    path.stat().st_mtime, tz=timezone.utc
                ).isoformat()
                rows.append(
                    {
                        "name": path.stem,
                        "path": str(path),
                        "description": description,
                        "last_modified_iso": mtime,
                    }
                )
            return {
                "status": "ok",
                "workflows": rows,
                "count": len(rows),
                "source_dir": str(d.resolve()),
            }
        except Exception as exc:
            logger.error("comfyui_list_workflows failed: %s", exc, exc_info=True)
            return {"status": "error", "error": str(exc)}
