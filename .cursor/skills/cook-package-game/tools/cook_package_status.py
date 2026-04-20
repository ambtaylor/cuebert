"""MCP tool: cook-package-game status (mode, config, unreal-build delegation)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from _cook_common import _load_config, _resolve_mode, default_config_path, find_hub_root


class suppress_path_remove:
    """Remove *path* from sys.path on exit."""

    def __init__(self, path: str) -> None:
        self.path = path

    def __enter__(self) -> None:
        return None

    def __exit__(self, *exc: object) -> None:
        import sys

        try:
            sys.path.remove(self.path)
        except ValueError:
            pass


def _import_skill_tool(skill_name: str, module_name: str, func_name: str) -> Any:
    skills_dir = Path(__file__).resolve().parent.parent.parent
    mod_path = skills_dir / skill_name / "tools" / f"{module_name}.py"
    if not mod_path.exists():
        raise ImportError(f"Skill tool not found: {mod_path}")
    spec = importlib.util.spec_from_file_location(module_name, str(mod_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create spec for {mod_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, func_name)


def cook_package_status(config_path: str | None = None) -> dict[str, Any]:
    """Return cook-package mode, config summary, platform matrix keys, and unreal-build import status."""
    cfg_path = str(Path(config_path).expanduser().resolve()) if config_path else str(default_config_path())
    mode = _resolve_mode()
    config = _load_config(config_path)
    matrix = config.get("platform_matrix")
    platform_keys: list[str] = []
    platform_summary: dict[str, Any] = {}
    if isinstance(matrix, dict):
        for k, v in matrix.items():
            platform_keys.append(str(k))
            if isinstance(v, dict):
                platform_summary[str(k)] = {
                    "status": v.get("status"),
                    "supported_stores": v.get("supported_stores"),
                }

    unreal: dict[str, Any] = {"build_runner": False, "unreal_build_target": False, "unreal_run_commandlet": False}
    try:
        import sys

        hub = find_hub_root()
        lib = hub / ".cursor" / "mcp-server" / "lib"
        inserted: str | None = None
        if lib.is_dir():
            s = str(lib)
            if s not in sys.path:
                sys.path.insert(0, s)
                inserted = s
        try:
            br_path = Path(__file__).resolve().parent.parent.parent / "unreal-build" / "tools" / "_build_runner.py"
            unreal["build_runner"] = br_path.is_file()
            _import_skill_tool("unreal-build", "unreal_build_target", "_unreal_build_target_impl")
            unreal["unreal_build_target"] = True
            _import_skill_tool("unreal-build", "unreal_run_commandlet", "_unreal_run_commandlet_impl")
            unreal["unreal_run_commandlet"] = True
        finally:
            if inserted:
                with suppress_path_remove(inserted):
                    pass
    except Exception as exc:
        unreal["import_error"] = str(exc)

    return {
        "mode": mode,
        "config_path": cfg_path,
        "config_loaded": bool(config),
        "platform_matrix_keys": sorted(platform_keys),
        "platform_summary": platform_summary,
        "unreal_build": unreal,
    }
