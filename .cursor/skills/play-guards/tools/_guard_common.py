"""Shared helpers for play-guards, ship-guards, and asset-guards evaluators."""

from __future__ import annotations

import contextlib
import importlib.util
import logging
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_VAULT_GUARD_MODE_KEY = "cuebert.guard_mode"


def find_hub_root(start: Path | None = None) -> Path:
    """Locate Cuebert hub root (directory containing ``.cuebert``)."""
    p = (start or Path(__file__).resolve()).resolve()
    for parent in [p, *p.parents]:
        if (parent / ".cuebert").is_dir():
            return parent
    raise FileNotFoundError("Could not locate Cuebert hub root (.cuebert).")


def _vault_guard_mode_raw() -> str | None:
    try:
        from _vault import CUEBERT_VAULT_AVAILABLE, get_resolver

        if not CUEBERT_VAULT_AVAILABLE:
            return None
        v = get_resolver().get_credential(_VAULT_GUARD_MODE_KEY)
        if v and str(v).strip():
            return str(v).strip().lower()
    except Exception as exc:
        logger.debug("vault cuebert.guard_mode unavailable: %s", exc)
    return None


def _resolve_mode() -> str:
    """Return ``dry_run`` or ``live`` from ``CUEBERT_GUARD_MODE`` or vault."""
    env = os.environ.get("CUEBERT_GUARD_MODE", "").strip().lower()
    if env in {"dry_run", "dry-run"}:
        return "dry_run"
    if env in {"live", "on", "1", "true"}:
        return "live"
    vault = _vault_guard_mode_raw()
    if vault in {"dry_run", "dry-run"}:
        return "dry_run"
    if vault in {"live", "on", "1", "true"}:
        return "live"
    return "live"


def _load_yaml_config(path: str | Path) -> dict[str, Any]:
    """Load YAML from *path*; return empty dict on missing file or bad root type."""
    p = Path(path).expanduser()
    if not p.is_file():
        return {}
    with open(p, encoding="utf-8", errors="replace") as fh:
        data = yaml.safe_load(fh)
    return data if isinstance(data, dict) else {}


def _validate_path(path: str | Path, root: str | Path) -> Path:
    """Resolve *path* and ensure it is under *root* (realpath containment)."""
    root_p = Path(root).expanduser().resolve(strict=False)
    target = Path(path).expanduser().resolve(strict=False)
    try:
        target.relative_to(root_p)
    except ValueError as exc:
        raise ValueError(f"path {target} escapes root {root_p}") from exc
    return target


def GuardResult(
    guard_id: str,
    status: str,
    severity: str,
    detail: str,
    evidence_path: str | None = None,
) -> dict[str, Any]:
    """Build a single-guard result row (dict factory)."""
    return {
        "guard_id": guard_id,
        "status": status,
        "severity": severity,
        "detail": detail,
        "evidence_path": evidence_path,
    }


def import_skill_tool_module(skill_dir_name: str, tool_stem: str) -> ModuleType:
    """Load ``.cursor/skills/<skill>/tools/<tool_stem>.py`` like hub build_verify."""
    hub = find_hub_root()
    tool_path = hub / ".cursor" / "skills" / skill_dir_name / "tools" / f"{tool_stem}.py"
    if not tool_path.is_file():
        raise ImportError(f"Skill tool not found: {tool_path}")
    mod_name = f"cuebert_skills.{skill_dir_name.replace('-', '_')}.{tool_stem}"
    spec = importlib.util.spec_from_file_location(mod_name, tool_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create spec for {tool_path}")
    insert_path = str(tool_path.parent)
    pushed = False
    if insert_path not in sys.path:
        sys.path.insert(0, insert_path)
        pushed = True
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        if pushed:
            with contextlib.suppress(ValueError):
                sys.path.remove(insert_path)
    return module


def default_play_guards_config_path() -> Path:
    return find_hub_root() / ".cuebert" / "config" / "play-guards.yaml"
