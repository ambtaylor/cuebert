"""MCP tool: look up execution state for a previously submitted ComfyUI prompt."""

from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from _comfyui_client import lookup_history

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    """Register ``comfyui_asset_status`` on the MCP server."""

    @mcp.tool()
    def comfyui_asset_status(prompt_id: str) -> dict[str, Any]:
        """Return status for a ComfyUI ``prompt_id`` from a prior ``comfyui_generate_asset`` call.

        Args:
            prompt_id: Identifier returned by ComfyUI (or ``dryrun-`` prefix in dry-run).

        Returns:
            Envelope with ``status`` (``pending`` | ``running`` | ``completed`` |
            ``failed`` | ``unknown``), ``assets`` (filenames or placeholders),
            ``error``, ``dry_run``, and optional ``error_code``.
        """
        try:
            if not prompt_id or not str(prompt_id).strip():
                return {
                    "status": "failed",
                    "assets": [],
                    "error": "prompt_id is required and must be non-empty.",
                    "dry_run": False,
                    "error_code": "prompt_empty",
                }
            pid = str(prompt_id).strip()
            result = lookup_history(pid)
            out: dict[str, Any] = {
                "status": result.get("status", "unknown"),
                "assets": result.get("assets", []),
                "error": result.get("error"),
                "dry_run": bool(result.get("dry_run")),
            }
            if result.get("error_code"):
                out["error_code"] = result["error_code"]
            return out
        except Exception as exc:
            logger.error("comfyui_asset_status failed: %s", exc, exc_info=True)
            return {
                "status": "unknown",
                "assets": [],
                "error": str(exc),
                "dry_run": False,
                "error_code": "network_error",
            }
