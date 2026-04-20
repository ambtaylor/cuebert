"""Orchestrate .env sync during the install flow.

Inlines vault ↔ .env sync (originally ``cue_vault.sync`` on the Cue hub)
so the installer stays self-contained under ``scripts/vault_installer/``.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .renderer import dim, green

logger = logging.getLogger(__name__)

_VAULT_START_RE = re.compile(r"^#\s*\[vault:(\w+)\]")
_VAULT_END_RE = re.compile(r"^#\s*\[vault:end\]")


class EnvSyncError(Exception):
    """Raised when .env sync encounters an unrecoverable error."""

    def __init__(self, env_path: Path, reason: str) -> None:
        super().__init__(f"Env sync failed for {env_path}: {reason}")
        self.env_path = env_path
        self.reason = reason


@dataclass
class SyncResult:
    added: int = 0
    updated: int = 0
    removed: int = 0
    preserved: int = 0
    services_synced: list[str] = field(default_factory=list)


def _resolve_dotted(data: dict[str, Any], path: str) -> str | None:
    """Resolve a dotted path from a nested dict."""
    parts = path.split(".")
    current: Any = data
    for part in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return str(current) if current is not None else None


def parse_env_file(env_path: Path) -> tuple[list[str], dict[str, list[str]]]:
    """Parse a .env file into user lines and vault-managed blocks.

    Args:
        env_path: Path to the .env file.

    Returns:
        A tuple of ``(user_lines, vault_blocks)`` where
        ``vault_blocks`` maps service keys to their managed lines
        (excluding the marker comments themselves).
    """
    if not env_path.is_file():
        return [], {}

    user_lines: list[str] = []
    vault_blocks: dict[str, list[str]] = {}
    current_block: str | None = None

    for line in env_path.read_text(encoding="utf-8").splitlines():
        if _VAULT_END_RE.match(line):
            current_block = None
            continue

        start_match = _VAULT_START_RE.match(line)
        if start_match:
            current_block = start_match.group(1)
            vault_blocks.setdefault(current_block, [])
            continue

        if current_block is not None:
            vault_blocks[current_block].append(line)
        else:
            user_lines.append(line)

    return user_lines, vault_blocks


def build_vault_block(
    service_key: str,
    env_mapping: dict[str, str],
    credentials: dict[str, Any],
) -> list[str]:
    """Build the ``.env`` lines for a single service's vault block.

    Args:
        service_key: The service identifier (used in the marker comment).
        env_mapping: ``{ENV_VAR: vault.dotted.path}`` from services.yaml.
        credentials: The full credentials dict for resolution.

    Returns:
        A list of strings including markers and ``KEY=value`` lines.
    """
    lines = [f"# [vault:{service_key}] Managed by Cuebert vault. Do not edit manually."]

    for env_var, vault_path in env_mapping.items():
        if "." not in vault_path:
            lines.append(f"{env_var}={vault_path}")
            continue
        value = _resolve_dotted(credentials, vault_path)
        if value is not None:
            lines.append(f"{env_var}={value}")

    lines.append("# [vault:end]")
    return lines


def sync_env(
    env_path: Path,
    services: dict[str, dict[str, Any]],
    credentials: dict[str, Any],
    selected_services: list[str],
) -> SyncResult:
    """Sync vault credentials into a project's ``.env`` file.

    Vault-managed blocks are rewritten. User-managed lines are preserved.

    Args:
        env_path: Path to the project's ``.env`` file.
        services: The full services dict from services.yaml.
        credentials: The project's resolved credentials.
        selected_services: Which services to sync.

    Returns:
        A :class:`SyncResult` with counts.

    Raises:
        EnvSyncError: If the env file cannot be written.
    """
    result = SyncResult()

    user_lines, old_blocks = parse_env_file(env_path)
    result.preserved = len(user_lines)

    new_lines: list[str] = []

    for svc_key in selected_services:
        svc_def = services.get(svc_key)
        if svc_def is None:
            logger.warning("Service '%s' not in registry — skipping sync.", svc_key)
            continue

        env_mapping: dict[str, str] = svc_def.get("env_mapping", {})
        block_lines = build_vault_block(svc_key, env_mapping, credentials)
        new_lines.extend(block_lines)
        new_lines.append("")
        result.services_synced.append(svc_key)

        old_block = old_blocks.get(svc_key, [])
        content_lines = [ln for ln in block_lines if not ln.startswith("#")]
        if old_block:
            result.updated += len(content_lines)
        else:
            result.added += len(content_lines)

    for old_key in old_blocks:
        if old_key not in selected_services:
            result.removed += len(old_blocks[old_key])

    output_lines = new_lines
    if user_lines:
        if output_lines and output_lines[-1] != "":
            output_lines.append("")
        output_lines.extend(user_lines)

    try:
        env_path.parent.mkdir(parents=True, exist_ok=True)
        env_path.write_text("\n".join(output_lines) + "\n", encoding="utf-8")
    except OSError as exc:
        raise EnvSyncError(env_path, str(exc)) from exc

    return result


def read_user_vars(env_path: Path) -> list[str]:
    """Return non-vault-managed variable names from .env."""
    user_lines, _ = parse_env_file(env_path)
    var_names: list[str] = []
    for line in user_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" in stripped:
            var_names.append(stripped.split("=", 1)[0].strip())
    return var_names


def update_manifest_sync_timestamp(manifest_path: Path) -> None:
    """Update the ``last_synced`` field in a manifest YAML file."""
    try:
        import yaml
    except ImportError:
        logger.warning("PyYAML not installed — cannot update manifest timestamp.")
        return

    if not manifest_path.is_file():
        return

    try:
        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return

    if not isinstance(data, dict):
        return

    data["last_synced"] = datetime.now(timezone.utc).isoformat()

    manifest_path.write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


def run_env_sync(
    env_path: Path,
    services: dict[str, dict[str, Any]],
    credentials: dict[str, Any],
    selected_services: list[str],
) -> SyncResult:
    """Sync vault credentials into the project .env file.

    Args:
        env_path: Path to the project's ``.env`` file.
        services: Full services dict from services.yaml.
        credentials: The project's resolved credentials.
        selected_services: Services to sync.

    Returns:
        :class:`SyncResult` with counts.
    """
    result = sync_env(env_path, services, credentials, selected_services)

    total_vars = result.added + result.updated
    if total_vars > 0:
        print(f"  {green('Synced')} {total_vars} vars to {env_path}")
    if result.removed > 0:
        print(f"  Removed {result.removed} vars from deselected services.")
    if result.preserved > 0:
        print(f"  {dim(f'Preserved {result.preserved} user-managed lines.')}")

    return result


def collect_env_mapping(
    services: dict[str, dict[str, Any]],
    selected_services: list[str],
    credentials: dict[str, Any],
) -> dict[str, str]:
    """Build the vault_vars mapping for the manifest.

    Returns:
        ``{ENV_VAR: vault.dotted.path}`` for all selected services.
    """
    vault_vars: dict[str, str] = {}
    for svc_key in selected_services:
        svc_def = services.get(svc_key, {})
        mapping: dict[str, str] = svc_def.get("env_mapping", {})
        vault_vars.update(mapping)
    return vault_vars
