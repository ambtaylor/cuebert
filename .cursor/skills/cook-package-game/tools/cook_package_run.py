"""MCP-oriented cook/package status hook (status-only path for ship guards)."""

from __future__ import annotations

from typing import Any

from _cook_common import _get_platform_config, _load_config, _platform_runnable_status


def cook_package_run(
    project_path: str,
    build_path: str | None = None,
    target_platform: str = "Win64",
    config_path: str | None = None,
    status_only: bool = True,
) -> dict[str, Any]:
    """Return synthetic phase status from platform_matrix (no UAT subprocess).

    When *status_only* is True (default), only configuration eligibility is checked.
    *build_path* and *project_path* are accepted for API parity with /ship harness.
    """
    _ = build_path
    _ = project_path
    _ = status_only
    cfg = _load_config(config_path)
    row = _get_platform_config(cfg, target_platform)
    ok, reason = _platform_runnable_status(row)
    if ok:
        return {
            "status": "pass",
            "mode": "status_only",
            "target_platform": target_platform,
            "detail": "platform_matrix allows cook-package phases (synthetic)",
            "phases": [
                {"name": "cook", "status": "skipped"},
                {"name": "stage", "status": "skipped"},
                {"name": "package", "status": "skipped"},
            ],
        }
    return {
        "status": "fail",
        "mode": "status_only",
        "target_platform": target_platform,
        "detail": reason,
        "phases": [{"name": "cook", "status": "fail", "reason": reason}],
    }


def register(mcp: Any) -> None:
    """Register MCP tool when cook-package-game is loaded as a toolkit."""
    from mcp.server.fastmcp import FastMCP

    if not isinstance(mcp, FastMCP):
        return

    @mcp.tool(name="cook_package_run")
    def cook_package_run_tool(
        project_path: str,
        build_path: str | None = None,
        target_platform: str = "Win64",
        config_path: str | None = None,
        status_only: bool = True,
    ) -> dict[str, Any]:
        """Status-only cook/package gate from platform_matrix (no full UAT run)."""
        return cook_package_run(
            project_path,
            build_path=build_path,
            target_platform=target_platform,
            config_path=config_path,
            status_only=status_only,
        )
