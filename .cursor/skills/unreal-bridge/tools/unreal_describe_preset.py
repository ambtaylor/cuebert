"""MCP tool: describe a Remote Control preset (properties and functions)."""

from __future__ import annotations

import logging
import re
from typing import Any

from mcp.server.fastmcp import FastMCP

from _unreal_client import (
    _get_mode,
    _resolve_base_url,
    _resolve_timeout,
    describe_preset,
)

logger = logging.getLogger(__name__)

_PRESET_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")


def register(mcp: FastMCP) -> None:
    """Register ``unreal_describe_preset`` on the MCP server."""

    @mcp.tool()
    def unreal_describe_preset(preset_name: str) -> dict[str, Any]:
        """Describe a Remote Control preset: exposed properties and callable functions.

        Args:
            preset_name: Preset name (alphanumeric + underscore + dash + dot, max 128 chars).

        Returns:
            {
              "status": "ok" | "error" | "dry_run" | "not_found",
              "base_url": str,
              "mode": "live" | "dry_run",
              "preset_name": str,
              "properties": [{"object_path": str, "property_name": str, "type": str, "exposed_name": str | None}, ...],
              "functions": [{"object_path": str, "function_name": str, "arg_count": int, "exposed_name": str | None}, ...],
              "error": str | None
            }
        """
        try:
            base_url = _resolve_base_url()
            mode = _get_mode()
            if not preset_name or not _PRESET_NAME_RE.match(preset_name):
                return {
                    "status": "error",
                    "base_url": base_url,
                    "mode": mode,
                    "preset_name": preset_name,
                    "properties": [],
                    "functions": [],
                    "error": "invalid preset_name",
                }
            timeout = _resolve_timeout()
            data = describe_preset(base_url, preset_name, timeout)
            if data.get("error") == "invalid preset_name":
                return {
                    "status": "error",
                    "base_url": base_url,
                    "mode": mode,
                    "preset_name": preset_name,
                    "properties": [],
                    "functions": [],
                    "error": "invalid preset_name",
                }
            if data.get("dry_run"):
                return {
                    "status": "dry_run",
                    "base_url": base_url,
                    "mode": "dry_run",
                    "preset_name": str(data.get("name") or preset_name),
                    "properties": data.get("properties") or [],
                    "functions": data.get("functions") or [],
                    "error": None,
                }
            if data.get("missing"):
                return {
                    "status": "not_found",
                    "base_url": base_url,
                    "mode": "live",
                    "preset_name": str(data.get("name") or preset_name),
                    "properties": [],
                    "functions": [],
                    "error": None,
                }
            if data.get("error"):
                return {
                    "status": "error",
                    "base_url": base_url,
                    "mode": mode,
                    "preset_name": str(data.get("name") or preset_name),
                    "properties": [],
                    "functions": [],
                    "error": str(data.get("error")),
                }
            return {
                "status": "ok",
                "base_url": base_url,
                "mode": "live",
                "preset_name": str(data.get("name") or preset_name),
                "properties": data.get("properties") or [],
                "functions": data.get("functions") or [],
                "error": None,
            }
        except Exception as exc:
            logger.error("unreal_describe_preset failed: %s", exc, exc_info=True)
            return {
                "status": "error",
                "base_url": _resolve_base_url(),
                "mode": _get_mode(),
                "preset_name": preset_name,
                "properties": [],
                "functions": [],
                "error": str(exc),
            }
