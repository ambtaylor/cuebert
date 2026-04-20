"""MCP tool: qa-resilience-game status probe."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from _resilience_common import (
    _load_config,
    _resolve_mode,
    default_config_path,
    thresholds_from_config,
)


def qa_resilience_status() -> dict[str, Any]:
    """Return mode, config load state, rule count, and effective thresholds."""
    mode = _resolve_mode()
    path = default_config_path()
    try:
        cfg = _load_config(None)
        loaded = path.is_file()
    except Exception:
        cfg = {}
        loaded = False
    thresholds = thresholds_from_config(cfg if isinstance(cfg, dict) else {})
    return {
        "status": "ok",
        "mode": mode,
        "config_loaded": loaded,
        "config_path": str(path),
        "rules_available": 10,
        "thresholds": thresholds,
    }


def register(mcp: FastMCP) -> None:
    """Register ``qa_resilience_status`` MCP tool."""

    @mcp.tool(name="qa_resilience_status")
    def qa_resilience_status_tool() -> dict[str, Any]:
        """Probe qa-resilience-game config and mode."""
        return qa_resilience_status()
