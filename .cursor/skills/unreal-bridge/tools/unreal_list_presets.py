"""MCP tool: list Remote Control presets from the active Unreal project."""

from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from _unreal_client import (
    _get_mode,
    _resolve_base_url,
    _resolve_timeout,
    list_presets,
)

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    """Register ``unreal_list_presets`` on the MCP server."""

    @mcp.tool()
    def unreal_list_presets() -> dict[str, Any]:
        """List Remote Control presets registered in the active Unreal project.

        Returns:
            {
              "status": "ok" | "error" | "dry_run",
              "base_url": str,
              "mode": "live" | "dry_run",
              "preset_count": int,
              "presets": [{"name": str, "path": str, "exposed_count": int}, ...],
              "error": str | None
            }
        """
        try:
            base_url = _resolve_base_url()
            mode = _get_mode()
            timeout = _resolve_timeout()
            data = list_presets(base_url, timeout)
            if data.get("dry_run"):
                presets = data.get("presets") or []
                return {
                    "status": "dry_run",
                    "base_url": base_url,
                    "mode": "dry_run",
                    "preset_count": len(presets),
                    "presets": presets,
                    "error": None,
                }
            if data.get("error"):
                return {
                    "status": "error",
                    "base_url": base_url,
                    "mode": mode,
                    "preset_count": 0,
                    "presets": [],
                    "error": str(data.get("error")),
                }
            presets = data.get("presets") or []
            return {
                "status": "ok",
                "base_url": base_url,
                "mode": "live",
                "preset_count": len(presets),
                "presets": presets,
                "error": None,
            }
        except Exception as exc:
            logger.error("unreal_list_presets failed: %s", exc, exc_info=True)
            return {
                "status": "error",
                "base_url": _resolve_base_url(),
                "mode": _get_mode(),
                "preset_count": 0,
                "presets": [],
                "error": str(exc),
            }
