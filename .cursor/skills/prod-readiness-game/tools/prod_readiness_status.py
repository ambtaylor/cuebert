"""MCP tool: prod-readiness-game status probe."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from _readiness_common import _load_config, _resolve_mode, default_config_path


def prod_readiness_status() -> dict[str, Any]:
    """Return mode, config load state, rule count, and default scan parameters."""
    mode = _resolve_mode()
    path = default_config_path()
    try:
        _load_config(None)
        loaded = path.is_file()
    except Exception:
        loaded = False
    return {
        "status": "ok",
        "mode": mode,
        "config_loaded": loaded,
        "config_path": str(path),
        "rules_available": 14,
        "target_defaults": {
            "target_platform": "Win64",
            "target_store": "internal",
            "build_config": "Shipping",
        },
    }


def register(mcp: FastMCP) -> None:
    """Register ``prod_readiness_status`` MCP tool."""

    @mcp.tool(name="prod_readiness_status")
    def prod_readiness_status_tool() -> dict[str, Any]:
        """Probe prod-readiness-game config and mode."""
        return prod_readiness_status()
