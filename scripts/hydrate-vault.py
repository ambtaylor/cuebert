#!/usr/bin/env python3
"""Hydrate the **hub** vault from application `.env` files (hub-centric).

For each target application repository, reads `.env` and the corresponding
`services.yaml` (see `load_services_yaml`) and writes merged credentials into
the hub under `.cuebert/vault/`.

Tiers:
  - shared (default): `cuebert/.cuebert/vault/shared/credentials.yaml`
  - project: `cuebert/.cuebert/vault/{project}/credentials.yaml`
  - auto (`--all`): uses `.cuebert/workspace-manifest.json` on the hub to find registered
    workspace roots, then auto-tiers shared vs per-project credentials.

`workspace-manifest.json` is an optional hub file listing app repo paths for
multi-root workflows; it is not installed into app repos by Cuebert.

Usage:
    python scripts/hydrate-vault.py /path/to/kaces-backend
    python scripts/hydrate-vault.py /path/to/kaces-backend --tier project --project-name kaces-backend
    python scripts/hydrate-vault.py /path/to/kaces-backend --services techzone,mongodb
    python scripts/hydrate-vault.py --all
    python scripts/hydrate-vault.py --all --dry-run
"""
# SECURITY: Credentials loaded from .env at runtime. Never hardcoded.
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

HUB_ROOT = Path(__file__).resolve().parent.parent
VAULT_ROOT = HUB_ROOT / ".cuebert" / "vault"
SHARED_CREDS = VAULT_ROOT / "shared" / "credentials.yaml"
# Optional hub registry of workspace app roots (multi-root); used by --all batch mode.
MANIFEST_PATH = HUB_ROOT / ".cuebert" / "workspace-manifest.json"


def resolve_output_path(tier: str, project_name: str | None = None) -> Path:
    """Return the credentials.yaml path for the given tier."""
    if tier == "project":
        if not project_name:
            logger.error("--project-name is required when --tier=project")
            sys.exit(1)
        return VAULT_ROOT / project_name / "credentials.yaml"
    return SHARED_CREDS


def load_services_yaml(project_dir: Path) -> dict[str, Any]:
    """Load the project's services.yaml."""
    import yaml

    svc_path = project_dir / ".cuebert" / "vault" / "services.yaml"
    if not svc_path.is_file():
        logger.warning("services.yaml not found at %s — skipping", svc_path)
        return {}

    with open(svc_path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_dotenv_values(project_dir: Path) -> dict[str, str]:
    """Load env vars from the project's .env file."""
    from dotenv import dotenv_values

    env_path = project_dir / ".env"
    if not env_path.is_file():
        logger.warning(".env not found at %s — skipping", env_path)
        return {}

    values = dotenv_values(env_path)
    return {k: v for k, v in values.items() if v}


def build_vault_tree(
    services_config: dict[str, Any],
    env_values: dict[str, str],
    service_filter: set[str] | None = None,
) -> dict[str, Any]:
    """Build the nested vault structure from env_mapping + env values.

    For each service, reverses the env_mapping (ENV_VAR -> dotted.path)
    to produce the nested dict (service -> field -> value).
    """
    tree: dict[str, Any] = {}
    services = services_config.get("services", {})

    for svc_name, svc_def in services.items():
        if service_filter and svc_name not in service_filter:
            continue

        env_mapping: dict[str, str] = svc_def.get("env_mapping", {})
        for env_var, vault_path in env_mapping.items():
            if "." not in vault_path:
                continue

            value = env_values.get(env_var)
            if not value:
                continue

            parts = vault_path.split(".")
            node = tree
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = value

    return tree


def vault_header(tier: str, project_name: str | None = None) -> str:
    """Generate the YAML header comment for a credentials file."""
    if tier == "project" and project_name:
        return (
            f"# Hub Per-Project Vault — Credentials for {project_name}\n"
            "# Managed by Cuebert Credential Intake Protocol (vault-standard.md §8)\n"
            "# Hydrated by: scripts/hydrate-vault.py\n"
            "# Permissions: 0600 (owner read/write only)\n"
            "# NEVER commit this file to version control.\n\n"
        )
    return (
        "# Hub Shared Vault — Credentials shared across hub projects\n"
        "# Managed by Cuebert Credential Intake Protocol (vault-standard.md §8)\n"
        "# Hydrated by: scripts/hydrate-vault.py\n"
        "# Permissions: 0600 (owner read/write only)\n"
        "# NEVER commit this file to version control.\n\n"
    )


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge overlay into base. Overlay values win on conflict."""
    merged = dict(base)
    for key, value in overlay.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_existing_credentials(path: Path) -> dict[str, Any]:
    """Load existing credentials.yaml if present, stripping comment lines."""
    import yaml

    if not path.is_file():
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except Exception:
        logger.warning("Could not parse existing %s — starting fresh", path)
        return {}


def write_credentials(
    tree: dict[str, Any],
    dest: Path,
    *,
    tier: str = "shared",
    project_name: str | None = None,
    dry_run: bool = False,
) -> None:
    """Merge new credentials into existing credentials.yaml (additive)."""
    import yaml

    dest.parent.mkdir(parents=True, exist_ok=True)

    existing = load_existing_credentials(dest)
    merged = deep_merge(existing, tree)

    new_services = [s for s in tree if s not in existing]
    updated_services = [s for s in tree if s in existing]

    if dry_run:
        field_count = sum(
            len(v) if isinstance(v, dict) else 1
            for v in tree.values()
        )
        logger.info("[DRY RUN] Would merge %d new services into %s (total: %d)",
                     len(new_services), dest, len(merged))
        if new_services:
            logger.info("[DRY RUN] New: %s", new_services)
        if updated_services:
            logger.info("[DRY RUN] Updated: %s", updated_services)
        logger.info("[DRY RUN] Preserved: %s",
                     [s for s in existing if s not in tree])
        return

    header = vault_header(tier, project_name)
    content = header + yaml.dump(merged, default_flow_style=False, sort_keys=True)

    with open(dest, "w", encoding="utf-8") as fh:
        fh.write(content)

    os.chmod(dest, 0o600)

    logger.info("Wrote %d services to %s", len(merged), dest)
    if new_services:
        logger.info("Added: %s", new_services)
    if updated_services:
        logger.info("Updated: %s", updated_services)
    logger.info("Preserved: %s", [s for s in existing if s not in tree])


def load_workspace_manifest() -> dict[str, Any]:
    """Load workspace-manifest.json from the hub."""
    if not MANIFEST_PATH.is_file():
        logger.error("workspace-manifest.json not found at %s", MANIFEST_PATH)
        sys.exit(1)

    with open(MANIFEST_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def hydrate_single(
    project_dir: Path,
    tier: str,
    project_name: str | None,
    service_filter: set[str] | None,
    dry_run: bool,
) -> dict[str, Any]:
    """Hydrate a single project. Returns the vault tree built."""
    services_config = load_services_yaml(project_dir)
    if not services_config:
        return {}

    env_values = load_dotenv_values(project_dir)
    if not env_values:
        return {}

    logger.info("Loaded %d env vars from %s/.env", len(env_values), project_dir)

    tree = build_vault_tree(services_config, env_values, service_filter)
    if not tree:
        logger.warning("No credentials resolved for %s", project_dir.name)
        return {}

    dest = resolve_output_path(tier, project_name)
    write_credentials(tree, dest, tier=tier, project_name=project_name, dry_run=dry_run)
    return tree


def hydrate_all(dry_run: bool) -> None:
    """Batch mode: discover app repos from the hub manifest and auto-tier credentials.

    Tiering rules (in priority order):
      1. Services already in the existing shared vault stay shared.
      2. Services whose env keys appear in 2+ project .env files go to shared.
      3. Everything else goes to the owning project's per-project vault.

    All writes are additive (deep-merge) — existing credentials are never lost.
    """
    manifest = load_workspace_manifest()
    projects = manifest.get("projects", {})

    if not projects:
        logger.error("No projects found in workspace-manifest.json")
        sys.exit(1)

    logger.info("Discovered %d projects in workspace manifest", len(projects))

    existing_shared = load_existing_credentials(SHARED_CREDS)
    existing_shared_services = set(existing_shared.keys())
    if existing_shared_services:
        logger.info("Existing shared services (will be preserved): %s",
                     sorted(existing_shared_services))

    env_key_owners: dict[str, list[str]] = defaultdict(list)
    project_envs: dict[str, dict[str, str]] = {}
    project_services: dict[str, dict[str, Any]] = {}

    for proj_name, proj_info in projects.items():
        proj_path = (HUB_ROOT / proj_info["path"]).resolve()
        if not proj_path.is_dir():
            logger.warning("Project directory not found: %s — skipping", proj_path)
            continue

        svc_config = load_services_yaml(proj_path)
        env_vals = load_dotenv_values(proj_path)

        if not svc_config or not env_vals:
            logger.info("Skipping %s (no services.yaml or .env)", proj_name)
            continue

        project_services[proj_name] = svc_config
        project_envs[proj_name] = env_vals

        for env_key in env_vals:
            env_key_owners[env_key].append(proj_name)

    shared_tree: dict[str, Any] = {}
    per_project_trees: dict[str, dict[str, Any]] = defaultdict(dict)

    for proj_name, svc_config in project_services.items():
        env_vals = project_envs[proj_name]
        services = svc_config.get("services", {})

        for svc_name, svc_def in services.items():
            env_mapping: dict[str, str] = svc_def.get("env_mapping", {})

            already_shared = svc_name in existing_shared_services
            overlap = any(
                env_var in env_vals and len(env_key_owners.get(env_var, [])) > 1
                for env_var in env_mapping
            )
            is_shared = already_shared or overlap

            target_tree = shared_tree if is_shared else per_project_trees[proj_name]

            for env_var, vault_path in env_mapping.items():
                if "." not in vault_path:
                    continue
                value = env_vals.get(env_var)
                if not value:
                    continue
                parts = vault_path.split(".")
                node = target_tree
                for part in parts[:-1]:
                    node = node.setdefault(part, {})
                node[parts[-1]] = value

    if shared_tree:
        logger.info("Shared tier (new/updated): %s", list(shared_tree.keys()))
        write_credentials(
            shared_tree, SHARED_CREDS,
            tier="shared", dry_run=dry_run,
        )
    elif existing_shared_services:
        logger.info("Shared tier unchanged (preserving %d existing services)",
                     len(existing_shared_services))

    for proj_name, tree in per_project_trees.items():
        if not tree:
            continue
        logger.info("Project tier [%s]: %s", proj_name, list(tree.keys()))
        dest = VAULT_ROOT / proj_name / "credentials.yaml"
        write_credentials(
            tree, dest,
            tier="project", project_name=proj_name, dry_run=dry_run,
        )

    if not shared_tree and not any(per_project_trees.values()):
        logger.warning("No credentials resolved from any project .env files")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Hydrate hub vault from project .env")
    parser.add_argument("project_dir", type=Path, nargs="?", default=None,
                        help="Path to the application repo root (not needed with --all)")
    parser.add_argument("--tier", choices=["shared", "project"], default="shared",
                        help="Vault tier to write to (default: shared)")
    parser.add_argument("--project-name", type=str, default=None,
                        help="Project name for hub per-project vault (required with --tier=project)")
    parser.add_argument("--all", action="store_true", dest="all_projects",
                        help="Discover all projects from workspace-manifest.json and auto-tier")
    parser.add_argument("--services", type=str, default=None,
                        help="Comma-separated service names to hydrate (default: all)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be written without writing")
    args = parser.parse_args()

    if args.all_projects:
        hydrate_all(dry_run=args.dry_run)
        return

    if not args.project_dir:
        parser.error("project_dir is required unless --all is specified")

    project_dir = args.project_dir.resolve()
    if not project_dir.is_dir():
        logger.error("Project directory not found: %s", project_dir)
        sys.exit(1)

    if args.tier == "project" and not args.project_name:
        args.project_name = project_dir.name
        logger.info("Inferred --project-name=%s from directory name", args.project_name)

    svc_filter = set(args.services.split(",")) if args.services else None

    tree = hydrate_single(
        project_dir,
        tier=args.tier,
        project_name=args.project_name,
        service_filter=svc_filter,
        dry_run=args.dry_run,
    )

    if not tree:
        logger.warning("No credentials resolved — check that .env has values matching services.yaml env_mapping")
        sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    main()
