"""MCP tool: probe Unreal Editor Remote Control HTTP reachability."""

from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from _unreal_client import (
    _get_mode,
    _get_mode_explicit,
    _is_unreal_configured_explicitly,
    _resolve_base_url,
    _resolve_timeout,
    health_probe,
    non_localhost_warning,
)

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    """Register ``unreal_health_check`` on the MCP server."""

    @mcp.tool()
    def unreal_health_check() -> dict[str, Any]:
        """Probe the configured Unreal Remote Control HTTP endpoint (``GET /remote/info``).

        When Unreal is not configured (no ``CUEBERT_UNREAL_BASE_URL`` and no
        vault ``unreal.base_url``), returns ``not_configured`` unless the
        operator forces ``CUEBERT_UNREAL_MODE=dry_run``. Non-loopback hosts add
        a ``warnings`` entry without failing the check.

        Returns:
            Envelope with keys: ``status``, ``base_url``, ``mode``, ``version``,
            ``plugins``, ``error``, optional ``warnings``.
        """
        try:
            base_url = _resolve_base_url()
            configured = _is_unreal_configured_explicitly()
            explicit_mode = _get_mode_explicit()
            effective_mode = _get_mode()
            warnings: list[str] = []
            nw = non_localhost_warning(base_url)
            if nw:
                warnings.append(nw)

            if not configured:
                if explicit_mode == "dry_run":
                    probe = health_probe(base_url, _resolve_timeout())
                    return {
                        "status": "dry_run",
                        "base_url": base_url,
                        "mode": "dry_run",
                        "version": probe.get("version"),
                        "plugins": probe.get("plugins"),
                        "error": None,
                        "warnings": warnings or None,
                    }
                return {
                    "status": "not_configured",
                    "base_url": base_url,
                    "mode": effective_mode,
                    "version": None,
                    "plugins": None,
                    "error": (
                        "Unreal Remote Control base URL is not configured. Set "
                        "CUEBERT_UNREAL_BASE_URL or add unreal.base_url to hub "
                        "shared vault (see docs/_ai_system/standards/vault-standard.md)."
                    ),
                    "warnings": warnings or None,
                }

            if effective_mode == "dry_run":
                probe = health_probe(base_url, _resolve_timeout())
                return {
                    "status": "dry_run",
                    "base_url": base_url,
                    "mode": "dry_run",
                    "version": probe.get("version"),
                    "plugins": probe.get("plugins"),
                    "error": None,
                    "warnings": warnings or None,
                }

            timeout = _resolve_timeout()
            probe = health_probe(base_url, timeout)
            if probe.get("dry_run"):
                return {
                    "status": "dry_run",
                    "base_url": base_url,
                    "mode": "dry_run",
                    "version": probe.get("version"),
                    "plugins": probe.get("plugins"),
                    "error": None,
                    "warnings": warnings or None,
                }
            if probe.get("reachable"):
                return {
                    "status": "ok",
                    "base_url": base_url,
                    "mode": "live",
                    "version": probe.get("version"),
                    "plugins": probe.get("plugins"),
                    "error": None,
                    "warnings": warnings or None,
                }
            return {
                "status": "unreachable",
                "base_url": base_url,
                "mode": "live",
                "version": probe.get("version"),
                "plugins": probe.get("plugins"),
                "error": probe.get("error"),
                "warnings": warnings or None,
            }
        except Exception as exc:
            logger.error("unreal_health_check failed: %s", exc, exc_info=True)
            return {
                "status": "error",
                "base_url": _resolve_base_url(),
                "mode": _get_mode(),
                "version": None,
                "plugins": None,
                "error": str(exc),
                "warnings": None,
            }
