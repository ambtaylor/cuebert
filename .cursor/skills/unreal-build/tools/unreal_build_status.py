"""MCP tool: resolve Unreal engine path and UBT/UAT/editor-cmd availability."""

from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from _build_runner import (
    _detect_platform,
    _get_mode,
    _resolve_engine_path,
    _validate_engine_path,
    dry_run_constants,
)

logger = logging.getLogger(__name__)


def _unreal_build_status_impl() -> dict[str, Any]:
    """Resolve engine path, detect UE version, check UBT/UAT/editor availability."""
    try:
        mode = _get_mode()
        plat = _detect_platform()
        warnings: list[str] = []
        dc = dry_run_constants()
        if mode == "dry_run":
            return {
                "status": "dry_run",
                "mode": "dry_run",
                "engine_path": _resolve_engine_path(),
                "platform": plat,
                "version": dc["version"],
                "ubt_available": True,
                "uat_available": True,
                "editor_cmd_available": True,
                "reason": None,
                "warnings": warnings or None,
            }
        eng = _resolve_engine_path()
        if not eng:
            return {
                "status": "not_configured",
                "mode": "live",
                "engine_path": None,
                "platform": plat,
                "version": None,
                "ubt_available": False,
                "uat_available": False,
                "editor_cmd_available": False,
                "reason": (
                    "Unreal engine root not found. Set CUEBERT_UNREAL_ENGINE_PATH or "
                    "vault unreal.engine_path (logical tier: shared/unreal/engine_path)."
                ),
                "warnings": warnings or None,
            }
        val = _validate_engine_path(eng)
        if not val.get("valid"):
            return {
                "status": "invalid",
                "mode": "live",
                "engine_path": eng,
                "platform": plat,
                "version": val.get("version"),
                "ubt_available": bool(val.get("ubt_path")),
                "uat_available": bool(val.get("uat_path")),
                "editor_cmd_available": bool(val.get("editor_cmd_path")),
                "reason": val.get("reason") or "engine layout invalid",
                "warnings": warnings or None,
            }
        return {
            "status": "ok",
            "mode": "live",
            "engine_path": eng,
            "platform": plat,
            "version": val.get("version"),
            "ubt_available": True,
            "uat_available": True,
            "editor_cmd_available": True,
            "reason": None,
            "warnings": warnings or None,
        }
    except Exception as exc:
        logger.error("unreal_build_status failed: %s", exc, exc_info=True)
        return {
            "status": "error",
            "mode": _get_mode(),
            "engine_path": None,
            "platform": _detect_platform(),
            "version": None,
            "ubt_available": False,
            "uat_available": False,
            "editor_cmd_available": False,
            "reason": str(exc),
            "warnings": None,
        }


def register(mcp: FastMCP) -> None:
    """Register ``unreal_build_status`` on the MCP server."""

    @mcp.tool()
    def unreal_build_status() -> dict[str, Any]:
        """Resolve engine path, detect UE version, check UBT/UAT/editor availability."""
        return _unreal_build_status_impl()
