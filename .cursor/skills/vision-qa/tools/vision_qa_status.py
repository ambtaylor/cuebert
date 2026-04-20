"""MCP tool: probe vision-qa backend (Pillow optional, caps, modes)."""

from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from _image_io import pillow_available
from _vision_common import max_image_bytes, vision_qa_mode_env

logger = logging.getLogger(__name__)

_MAX_DECOMP_PX = 128_000_000


def _vision_qa_status_impl() -> dict[str, Any]:
    warnings: list[str] = []
    pil = pillow_available()
    if not pil:
        warnings.append("Pillow not available or disabled; only PNG via stdlib parser")
    mode = "dry_run" if vision_qa_mode_env() == "dry_run" else "live"
    status = "dry_run" if mode == "dry_run" else "ok"
    if pil:
        supported = ["png", "jpg", "jpeg", "webp", "tga", "bmp"]
    else:
        supported = ["png"]
    mb = max(1, max_image_bytes() // (1024 * 1024))
    return {
        "status": status,
        "mode": mode,
        "pillow": pil,
        "supported_formats": supported,
        "max_image_mb": mb,
        "max_decompressed_px": _MAX_DECOMP_PX,
        "warnings": warnings,
    }


def register(mcp: FastMCP) -> None:
    """Register ``vision_qa_status`` on the MCP server."""

    @mcp.tool()
    def vision_qa_status() -> dict[str, Any]:
        """Probe vision-qa backend availability."""
        return _vision_qa_status_impl()
