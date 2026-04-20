"""MCP tool: tail the latest Unreal log under Saved/Logs."""

from __future__ import annotations

import logging
import re
from typing import Any

from mcp.server.fastmcp import FastMCP

from _build_runner import (
    _find_latest_log,
    _get_mode,
    _sanitize_project_path,
    _tail_file,
    dry_run_build_log_excerpt,
)

logger = logging.getLogger(__name__)


def _unreal_tail_log_impl(
    project_path: str,
    n_lines: int = 100,
    filter_regex: str | None = None,
) -> dict[str, Any]:
    mode = _get_mode()
    n_lines = max(1, min(10_000, int(n_lines)))

    if mode == "dry_run":
        lines = dry_run_build_log_excerpt(20)
        if filter_regex:
            try:
                cre = re.compile(filter_regex, flags=re.MULTILINE)
                lines = [ln for ln in lines if cre.search(ln)]
            except re.error as exc:
                return {
                    "status": "error",
                    "mode": "dry_run",
                    "project_path": project_path,
                    "log_path": None,
                    "line_count": 0,
                    "lines": [],
                    "error": f"invalid filter_regex: {exc}",
                }
        proj = _sanitize_project_path(project_path) or project_path
        return {
            "status": "dry_run",
            "mode": "dry_run",
            "project_path": proj,
            "log_path": None,
            "line_count": len(lines),
            "lines": lines,
            "error": None,
        }

    proj = _sanitize_project_path(project_path)
    if not proj:
        return {
            "status": "error",
            "mode": "live",
            "project_path": project_path,
            "log_path": None,
            "line_count": 0,
            "lines": [],
            "error": "project_path must be absolute, exist, and end with .uproject",
        }

    cre = None
    if filter_regex is not None and str(filter_regex).strip():
        try:
            cre = re.compile(str(filter_regex).strip(), flags=re.MULTILINE)
        except re.error as exc:
            return {
                "status": "error",
                "mode": "live",
                "project_path": proj,
                "log_path": None,
                "line_count": 0,
                "lines": [],
                "error": f"invalid filter_regex: {exc}",
            }

    latest = _find_latest_log(proj)
    if not latest:
        return {
            "status": "not_found",
            "mode": "live",
            "project_path": proj,
            "log_path": None,
            "line_count": 0,
            "lines": [],
            "error": None,
        }

    lines = _tail_file(latest, n_lines)
    if cre is not None:
        lines = [ln for ln in lines if cre.search(ln)]
    return {
        "status": "ok",
        "mode": "live",
        "project_path": proj,
        "log_path": latest,
        "line_count": len(lines),
        "lines": lines,
        "error": None,
    }


def register(mcp: FastMCP) -> None:
    """Register ``unreal_tail_log`` on the MCP server."""

    @mcp.tool()
    def unreal_tail_log(
        project_path: str,
        n_lines: int = 100,
        filter_regex: str | None = None,
    ) -> dict[str, Any]:
        """Tail the most recent Unreal log under ``Saved/Logs`` (read-only)."""
        try:
            return _unreal_tail_log_impl(project_path, n_lines=n_lines, filter_regex=filter_regex)
        except Exception as exc:
            logger.error("unreal_tail_log failed: %s", exc, exc_info=True)
            return {
                "status": "error",
                "mode": _get_mode(),
                "project_path": project_path,
                "log_path": None,
                "line_count": 0,
                "lines": [],
                "error": str(exc),
            }
