"""MCP tool: probe ComfyUI server reachability.

Returns an envelope indicating whether the server is reachable,
what version is reported, and whether we are in dry-run mode.
"""

from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from _comfyui_client import (
    _get_mode,
    _get_mode_explicit,
    _is_comfyui_configured,
    _resolve_base_url,
    _resolve_timeout,
    health_probe,
)

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    """Register ``comfyui_health_check`` on the MCP server."""

    @mcp.tool()
    def comfyui_health_check() -> dict[str, Any]:
        """Probe the configured ComfyUI server and report reachability.

        When ComfyUI is not configured (no ``CUEBERT_COMFYUI_BASE_URL`` and no
        vault ``comfyui.base_url`` under hub shared credentials), returns
        ``not_configured`` so callers can degrade to dry-run without treating
        the outcome as a hard failure. See ``docs/_ai_system/standards/vault-standard.md``.

        Returns:
            Envelope with keys: ``status``, ``base_url``, ``mode``, ``version``,
            ``queue_remaining``, ``error``.
        """
        try:
            base_url = _resolve_base_url()
            configured = _is_comfyui_configured()
            explicit_mode = _get_mode_explicit()
            effective_mode = _get_mode()

            if not configured:
                if explicit_mode == "dry_run":
                    return {
                        "status": "dry_run",
                        "base_url": base_url,
                        "mode": "dry_run",
                        "version": "dry_run",
                        "queue_remaining": 0,
                        "error": None,
                    }
                return {
                    "status": "not_configured",
                    "base_url": base_url,
                    "mode": effective_mode,
                    "version": None,
                    "queue_remaining": None,
                    "error": (
                        "ComfyUI base URL is not configured. Set "
                        "CUEBERT_COMFYUI_BASE_URL or add comfyui.base_url to hub "
                        "shared vault (see docs/_ai_system/standards/vault-standard.md)."
                    ),
                }

            if effective_mode == "dry_run":
                probe = health_probe(base_url, _resolve_timeout())
                return {
                    "status": "dry_run",
                    "base_url": base_url,
                    "mode": "dry_run",
                    "version": probe.get("version"),
                    "queue_remaining": probe.get("queue_remaining"),
                    "error": None,
                }

            timeout = _resolve_timeout()
            probe = health_probe(base_url, timeout)
            if probe.get("dry_run"):
                return {
                    "status": "dry_run",
                    "base_url": base_url,
                    "mode": "dry_run",
                    "version": probe.get("version"),
                    "queue_remaining": probe.get("queue_remaining"),
                    "error": None,
                }
            if probe.get("reachable"):
                return {
                    "status": "ok",
                    "base_url": base_url,
                    "mode": "live",
                    "version": probe.get("version"),
                    "queue_remaining": probe.get("queue_remaining"),
                    "error": None,
                }
            return {
                "status": "unreachable",
                "base_url": base_url,
                "mode": "live",
                "version": probe.get("version"),
                "queue_remaining": probe.get("queue_remaining"),
                "error": probe.get("error"),
            }
        except Exception as exc:
            logger.error("comfyui_health_check failed: %s", exc, exc_info=True)
            return {
                "status": "error",
                "base_url": _resolve_base_url(),
                "mode": _get_mode(),
                "version": None,
                "queue_remaining": None,
                "error": str(exc),
            }
