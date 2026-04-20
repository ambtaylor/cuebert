"""MCP tool: confirm an exposed actor label exists for a Remote Control preset."""

from __future__ import annotations

import logging
import re
from typing import Any

from mcp.server.fastmcp import FastMCP

from _unreal_client import (
    _get_mode,
    _resolve_base_url,
    _resolve_timeout,
    ping_actor,
)

logger = logging.getLogger(__name__)

_PRESET_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
_ACTOR_LABEL_RE = re.compile(r"^[A-Za-z0-9_. -]{1,256}$")


def register(mcp: FastMCP) -> None:
    """Register ``unreal_ping_actor`` on the MCP server."""

    @mcp.tool()
    def unreal_ping_actor(preset_name: str, actor_label: str) -> dict[str, Any]:
        """Confirm that an actor with the given label is exposed in the preset (read-only).

        Args:
            preset_name: Preset name (same validation as describe_preset).
            actor_label: Actor label (alphanumeric + underscore + dash + space, max 256 chars).

        Returns:
            {
              "status": "ok" | "error" | "dry_run" | "not_found",
              "base_url": str,
              "mode": "live" | "dry_run",
              "preset_name": str,
              "actor_label": str,
              "found": bool,
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
                    "actor_label": actor_label,
                    "found": False,
                    "error": "invalid preset_name",
                }
            if not actor_label or not _ACTOR_LABEL_RE.match(actor_label):
                return {
                    "status": "error",
                    "base_url": base_url,
                    "mode": mode,
                    "preset_name": preset_name,
                    "actor_label": actor_label,
                    "found": False,
                    "error": "invalid actor_label",
                }
            timeout = _resolve_timeout()
            data = ping_actor(base_url, preset_name, actor_label, timeout)
            if data.get("error") in ("invalid preset_name", "invalid actor_label"):
                return {
                    "status": "error",
                    "base_url": base_url,
                    "mode": mode,
                    "preset_name": preset_name,
                    "actor_label": actor_label,
                    "found": False,
                    "error": str(data.get("error")),
                }
            if data.get("dry_run"):
                return {
                    "status": "dry_run",
                    "base_url": base_url,
                    "mode": "dry_run",
                    "preset_name": preset_name,
                    "actor_label": str(data.get("label") or actor_label),
                    "found": bool(data.get("found")),
                    "error": None,
                }
            if data.get("error"):
                return {
                    "status": "error",
                    "base_url": base_url,
                    "mode": mode,
                    "preset_name": preset_name,
                    "actor_label": actor_label,
                    "found": False,
                    "error": str(data.get("error")),
                }
            if not data.get("found"):
                return {
                    "status": "not_found",
                    "base_url": base_url,
                    "mode": "live",
                    "preset_name": preset_name,
                    "actor_label": str(data.get("label") or actor_label),
                    "found": False,
                    "error": None,
                }
            return {
                "status": "ok",
                "base_url": base_url,
                "mode": "live",
                "preset_name": preset_name,
                "actor_label": str(data.get("label") or actor_label),
                "found": True,
                "error": None,
            }
        except Exception as exc:
            logger.error("unreal_ping_actor failed: %s", exc, exc_info=True)
            return {
                "status": "error",
                "base_url": _resolve_base_url(),
                "mode": _get_mode(),
                "preset_name": preset_name,
                "actor_label": actor_label,
                "found": False,
                "error": str(exc),
            }
