"""Cuebert MCP Tool Server — auto-discovers tools from skill folders and core.

Registers all Cuebert tools (core utilities and toolkit tools) and
runs the MCP server over stdio transport.  Cursor connects via
``.cursor/mcp.json``.

Discovery order:
  1. ``.cursor/mcp-server/lib/`` added to sys.path (shared utilities like _vault)
  2. ``.cursor/mcp-server/core/*.py`` — core Cuebert tools (vault, health, build_verify, npm).
     ``build_verify`` (M6-P4) is gaming-aware: Unreal runs a bounded skill chain
     (``unreal_build_status``, forced-dry-run ``unreal_build_target``, advisory
     ``vision_qa_status``); Unity/Godot return ``skip_with_reason`` until M7; web
     stacks keep the legacy four-check gate when no engine markers match.
  3. ``.cursor/skills/*/tools/*.py`` — toolkit tools

Optional ``--group`` limits discovery to a domain group (see ``GROUPS``). Omit
``--group`` for full discovery (backward compatible).

Usage (standalone):
    python .cursor/mcp-server/server.py
    python .cursor/mcp-server/server.py --group core

Cursor config (in .cursor/mcp.json) — split processes (one per ``--group``):
    {"mcpServers": {
      "cuebert-core": {"command": "/ABS/python3", "args": ["/ABS/cuebert/.cursor/mcp-server/server.py", "--group", "core"]},
      "cuebert-asset": {"command": "/ABS/python3", "args": ["/ABS/cuebert/.cursor/mcp-server/server.py", "--group", "asset"]},
      "cuebert-engine": {"command": "/ABS/python3", "args": ["/ABS/cuebert/.cursor/mcp-server/server.py", "--group", "engine"]},
      "cuebert-qa": {"command": "/ABS/python3", "args": ["/ABS/cuebert/.cursor/mcp-server/server.py", "--group", "qa"]}
    }}
    Omit ``--group`` for a single process that loads all tool modules (legacy monolith; process name ``cuebert-tools``).
"""

from __future__ import annotations

import argparse
import sys
from typing import TypedDict


class GroupSpec(TypedDict):
    """Single domain group: whether to load core tools and which skill dirs to scan."""

    include_core: bool
    skills: list[str]


# Authoritative mapping — cuebert ships gaming-first skills.
# Expected skills (populated across M1-P6 and M4-M6):
#   core:   memory-toolkit (M1-P6)
#   asset:  comfyui-toolkit, asset-manifest-toolkit (M4)
#   engine: unreal-bridge, unreal-build, git-lfs-toolkit (M5-M6)
#   qa:     gauntlet-toolkit, vision-qa, screenshot-baseline-toolkit, engine-log-toolkit (M6)
#
# Each skill directory appears in at most one group. The lists are the
# authoritative source; skills/ dirs that don't exist yet are silently
# skipped at auto-discovery time (see server.py:discover_tools).
GROUPS: dict[str, GroupSpec] = {
    "core": {
        "include_core": True,
        "skills": ["memory-toolkit"],
    },
    # Asset group tools are loaded from each skill's tools/*.py (register(mcp)).
    # comfyui-toolkit: comfyui_health_check, comfyui_generate_asset,
    # comfyui_list_workflows, comfyui_asset_status.
    "asset": {
        "include_core": False,
        "skills": ["comfyui-toolkit", "asset-manifest-toolkit", "asset-guards"],
    },
    # Engine group tools are loaded from each skill's tools/*.py (register(mcp)).
    # Unreal bridge (M5-P1): unreal_health_check, unreal_list_presets,
    # unreal_describe_preset, unreal_ping_actor.
    # Unreal bridge (M5-P4): unreal_set_property, unreal_call_function.
    # Unreal build  (M6-P1): unreal_build_status, unreal_build_target,
    # unreal_run_commandlet, unreal_tail_log.
    # All loaded via dynamic discovery from .cursor/skills/unreal-*/tools/*.py
    "engine": {
        "include_core": False,
        "skills": ["unreal-bridge", "unreal-build", "git-lfs-toolkit"],
    },
    "qa": {
        "include_core": False,
        "skills": [
            "gauntlet-toolkit",
            # Vision QA (M6-P3): vision_qa_status, vision_qa_compare_images,
            # vision_qa_check_image, vision_qa_compare_screenshots
            # All loaded via dynamic discovery from .cursor/skills/vision-qa/tools/*.py
            "vision-qa",
            "screenshot-baseline-toolkit",
            "engine-log-toolkit",
            # M10-P2: qa-resilience-game, prod-readiness-game rule engines
            "qa-resilience-game",
            "prod-readiness-game",
            # M10-P4: harness guard evaluators (/play, /ship)
            "play-guards",
            "ship-guards",
        ],
    },
}


def _parse_active_group() -> str | None:
    """Parse ``--group`` from argv; exit with non-zero on invalid choice."""
    parser = argparse.ArgumentParser(
        prog="cuebert-mcp-server",
        description="Cuebert MCP tool server (stdio).",
        add_help=True,
    )
    parser.add_argument(
        "--group",
        metavar="NAME",
        choices=sorted(GROUPS.keys()),
        default=None,
        help="Load only toolkits for this domain group (omit for full discovery).",
    )
    args, _unknown = parser.parse_known_args()
    return args.group


_ACTIVE_GROUP = _parse_active_group()
_MCP_NAME = f"cuebert-{_ACTIVE_GROUP}" if _ACTIVE_GROUP else "cuebert-tools"

# Third-party imports after argv parse so `--group invalid` exits before requiring `mcp`.
import importlib.util
import logging
from pathlib import Path
from types import ModuleType

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP(_MCP_NAME)

_SERVER_DIR = Path(__file__).resolve().parent
_SKILLS_DIR = _SERVER_DIR.parent / "skills"
_LIB_DIR = _SERVER_DIR / "lib"
_CORE_DIR = _SERVER_DIR / "core"

sys.path.insert(0, str(_LIB_DIR))


def _load_module(path: Path) -> ModuleType | None:
    """Load a Python module from an absolute file path."""
    name = path.stem
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        logger.warning("Cannot load module spec for %s", path)
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        logger.exception("Failed to load module %s", path)
        del sys.modules[name]
        return None
    return mod


def _register_dir(directory: Path) -> int:
    """Load all non-underscore .py modules in *directory* and call register(mcp)."""
    count = 0
    if not directory.is_dir():
        return count
    sys.path.insert(0, str(directory))
    for py in sorted(directory.glob("*.py")):
        if py.name.startswith("_"):
            continue
        mod = _load_module(py)
        if mod and hasattr(mod, "register"):
            mod.register(mcp)
            count += 1
            logger.debug("Registered tools from %s", py.name)
    return count


def _discover_and_register(active_group: str | None) -> None:
    """Auto-discover and register core + toolkit tools, optionally filtered by group."""
    total = 0
    toolkit_count = 0
    core_count = 0

    logger.info(
        "MCP discovery: group=%s, server_name=%s",
        active_group if active_group is not None else "all (full discovery)",
        _MCP_NAME,
    )

    if active_group is None:
        core_count = _register_dir(_CORE_DIR)
        total += core_count
        logger.info("Core tools: %d modules loaded from %s", core_count, _CORE_DIR)

        if _SKILLS_DIR.is_dir():
            for skill_dir in sorted(_SKILLS_DIR.iterdir()):
                if skill_dir.name.startswith("_"):
                    continue
                tools_dir = skill_dir / "tools"
                if not tools_dir.is_dir():
                    continue
                n = _register_dir(tools_dir)
                if n:
                    logger.info(
                        "Toolkit %s: %d tool module(s) loaded", skill_dir.name, n,
                    )
                    toolkit_count += n
        total += toolkit_count
    else:
        spec = GROUPS[active_group]
        if spec["include_core"]:
            core_count = _register_dir(_CORE_DIR)
            total += core_count
            logger.info("Core tools: %d modules loaded from %s", core_count, _CORE_DIR)
        else:
            logger.info(
                "Core tools: skipped (group %r does not include core)", active_group,
            )

        for skill_name in spec["skills"]:
            tools_dir = _SKILLS_DIR / skill_name / "tools"
            if not tools_dir.is_dir():
                logger.debug(
                    "Toolkit %s: skip (no tools/ at %s)", skill_name, tools_dir,
                )
                continue
            n = _register_dir(tools_dir)
            logger.info("Toolkit %s: %d tool module(s) loaded", skill_name, n)
            toolkit_count += n

        total += toolkit_count

    logger.info(
        "MCP server ready: %d tool modules registered (%d core, %d toolkit)",
        total, core_count, toolkit_count,
    )


_discover_and_register(_ACTIVE_GROUP)

if __name__ == "__main__":
    mcp.run()
