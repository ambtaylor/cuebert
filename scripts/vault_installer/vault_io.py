"""YAML read/write utilities for vault files.

Handles permissions, backup, and manifest operations.
"""

from __future__ import annotations

import logging
import os
import shutil
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .constants import CREDS_FILE_PERMS

logger = logging.getLogger(__name__)


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file, returning an empty dict on failure."""
    try:
        import yaml
    except ImportError:
        logger.error("PyYAML is required. Install with: pip install pyyaml")
        return {}

    if not path.is_file():
        return {}

    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
            return data if isinstance(data, dict) else {}
    except yaml.YAMLError as exc:
        logger.error("Failed to parse YAML at %s: %s", path, exc)
        return {}


def save_yaml(
    path: Path,
    data: dict[str, Any],
    *,
    header: str = "",
    secure: bool = False,
) -> None:
    """Write a dict as YAML, optionally with a header and restricted perms."""
    import yaml

    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as fh:
        if header:
            fh.write(header)
            if not header.endswith("\n"):
                fh.write("\n")
        yaml.dump(data, fh, default_flow_style=False, sort_keys=False)

    if secure:
        os.chmod(path, CREDS_FILE_PERMS)


def backup_file(path: Path) -> Path | None:
    """Create a timestamped backup of a file if it exists.

    Returns:
        The backup path, or ``None`` if no backup was needed.
    """
    if not path.is_file():
        return None

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    backup_path = path.with_suffix(f".{timestamp}.bak")
    shutil.copy2(path, backup_path)
    logger.info("Backed up %s → %s", path, backup_path)
    return backup_path


def write_manifest(
    manifest_path: Path,
    *,
    selected_services: list[str],
    env_path: str = ".env",
    vault_vars: dict[str, str] | None = None,
    non_vault_vars: list[str] | None = None,
) -> None:
    """Write or update the project vault manifest."""
    now = datetime.now(timezone.utc).isoformat()
    manifest: dict[str, Any] = {
        "ade_version": "2.1",
        "created": now,
        "last_synced": now,
        "selected_services": selected_services,
    }

    if vault_vars is not None:
        manifest["configured_files"] = [
            {
                "path": env_path,
                "vault_vars": vault_vars,
                "non_vault_vars": non_vault_vars or [],
            },
        ]

    save_yaml(manifest_path, manifest)


def read_manifest(manifest_path: Path) -> dict[str, Any]:
    """Read and return the manifest, or empty dict if absent."""
    return load_yaml(manifest_path)


def check_permissions(path: Path) -> bool:
    """Return True if the file has 0600 permissions (or doesn't exist)."""
    if not path.is_file():
        return True
    mode = os.stat(path).st_mode & 0o777
    return mode == CREDS_FILE_PERMS


def fix_permissions(path: Path) -> None:
    """Set file permissions to 0600."""
    if path.is_file():
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
