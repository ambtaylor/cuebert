"""MCP tool: <TOOL_NAME> — <one-line description>.

<Longer description of what this tool does, what service it connects to,
and what structured data it returns.>

Usage:
    Copy this template to cuebert/.cursor/skills/<toolkit>/tools/<tool_name>.py,
    fill in the implementation.  The MCP server auto-discovers tools from
    skill folders — no manual registration needed.

See: docs/_ai_system/standards/tool-skill-promotion.md §4 (when ported)
"""

from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from _vault import get_resolver, redact

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    """Register <TOOL_NAME> tools on the given MCP server."""

    @mcp.tool()
    def tool_name(
        required_param: str,
        optional_param: str | None = None,
        project: str | None = None,
    ) -> dict[str, Any]:
        """<One-line description of what this tool does.>

        Args:
            required_param: Description of the required parameter.
            optional_param: Description of the optional parameter.
            project: Optional project directory path for vault resolution.

        Returns:
            A dict with ``status`` and either ``data`` or ``error``.
        """
        resolver = get_resolver(project_dir=project)

        try:
            # --- Credential resolution ---
            # token = resolver.get_credential("service.api_token")
            # if token is None:
            #     return {
            #         "status": "error",
            #         "error": "Credential 'service.api_token' not found in vault chain.",
            #     }
            # logger.info("Credential loaded: %s", redact(token))

            # --- Tool logic ---
            result = _execute(required_param, optional_param)

            return {
                "status": "ok",
                "data": result,
            }

        except Exception as exc:
            logger.error("Tool <TOOL_NAME> failed: %s", exc, exc_info=True)
            return {
                "status": "error",
                "error": str(exc),
            }


def _execute(
    required_param: str,
    optional_param: str | None,
) -> dict[str, Any]:
    """Core tool logic — separated for testability.

    Args:
        required_param: Description.
        optional_param: Description.

    Returns:
        Structured result dict.
    """
    # TODO: Implement tool logic here
    return {
        "param": required_param,
        "message": "Template tool — replace with real implementation.",
    }
