"""CLI entry point for the Cuebert vault interactive installer.

Modes:
  --interactive      Full guided setup (default)
  --verify           Re-run health checks on existing vault
  --sync             Re-sync vault credentials to .env
  --check            Local file health (backward compat)
  --add-service KEY  Add a single service to existing project vault
  --list-services    List available services from registry
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any

from .constants import (
    CREDENTIALS_FILENAME,
    DEFAULT_REGISTRY_PATH,
    MANIFEST_FILENAME,
    PROJECT_VAULT_REL,
    SERVICES_FILENAME,
    SERVICES_LOCAL_FILENAME,
)
from .env_sync import collect_env_mapping, run_env_sync, update_manifest_sync_timestamp
from .health_runner import HealthResult, check_service, print_summary
from .prompts import prompt_confirm, prompt_secret, prompt_text
from .renderer import banner, bold, dim, green, red, section, set_color_enabled, yellow
from .service_picker import (
    load_service_registry,
    order_by_dependency,
    run_service_picker,
)
from .vault_io import (
    backup_file,
    check_permissions,
    fix_permissions,
    load_yaml,
    read_manifest,
    save_yaml,
    write_manifest,
)

logger = logging.getLogger(__name__)


def _detect_project_name() -> str:
    return Path.cwd().name


def _prompt_service_credentials(
    service_key: str,
    service_def: dict[str, Any],
    existing_creds: dict[str, Any],
) -> dict[str, str]:
    """Prompt the user for all fields of a single service."""
    print(section(f"{service_def.get('name', service_key)}"))

    section_creds = existing_creds.get(service_key, {})
    if not isinstance(section_creds, dict):
        section_creds = {}

    result: dict[str, str] = {}
    for field_def in service_def.get("fields", []):
        name = field_def["name"]
        current = str(section_creds.get(name, ""))
        default = field_def.get("default", "")
        is_secret = field_def.get("secret", False)

        if is_secret:
            result[name] = prompt_secret(field_def["prompt"], current=current)
        else:
            result[name] = prompt_text(field_def["prompt"], default=default, current=current)

    return result


def _run_interactive(
    vault_dir: Path,
    registry_path: Path,
    env_path: Path,
    *,
    skip_health: bool = False,
    auto_yes: bool = False,
) -> None:
    """Full guided setup: select → prompt → health check → write → sync."""
    project_name = _detect_project_name()
    print(banner(f"Cuebert Vault Setup (Project: {project_name})"))

    local_path = vault_dir / SERVICES_LOCAL_FILENAME
    services = load_service_registry(registry_path, local_path)
    if not services:
        print(red("No services found in registry. Check your services.yaml path."))
        sys.exit(1)

    manifest = read_manifest(vault_dir / MANIFEST_FILENAME)
    preselected = set(manifest.get("selected_services", []))

    ordered = run_service_picker(services, preselected=preselected)
    if not ordered:
        print("No services selected. Exiting.")
        return

    creds_path = vault_dir / CREDENTIALS_FILENAME
    existing_creds = load_yaml(creds_path)
    all_creds: dict[str, Any] = dict(existing_creds)
    health_results: list[HealthResult] = []

    for svc_key in ordered:
        svc_def = services[svc_key]
        svc_creds = _prompt_service_credentials(svc_key, svc_def, all_creds)
        all_creds[svc_key] = svc_creds

        if not skip_health:
            health_cfg = svc_def.get("health_check")
            if health_cfg:
                result = check_service(svc_key, health_cfg, all_creds)
                health_results.append(result)

    if health_results:
        print_summary(health_results, services)

    if not auto_yes and not prompt_confirm("Save vault and sync .env?"):
        print("Aborted.")
        return

    backup_file(creds_path)
    save_yaml(
        creds_path,
        all_creds,
        header=(
            f"# {vault_dir / CREDENTIALS_FILENAME}\n"
            "# Project vault credentials — NEVER commit.\n\n"
        ),
        secure=True,
    )
    print(f"\n  {green('Vault saved')} to {creds_path} (permissions: 600)")

    vault_vars = collect_env_mapping(services, ordered, all_creds)
    write_manifest(
        vault_dir / MANIFEST_FILENAME,
        selected_services=ordered,
        vault_vars=vault_vars,
    )
    print(f"  {green('Manifest saved')} to {vault_dir / MANIFEST_FILENAME}")

    run_env_sync(env_path, services, all_creds, ordered)
    print(f"\n{green('Done!')} Your project vault is ready.")


def _run_verify(
    vault_dir: Path,
    registry_path: Path,
) -> None:
    """Re-run health checks against an existing project vault."""
    print(banner("Cuebert Vault Verify"))

    manifest = read_manifest(vault_dir / MANIFEST_FILENAME)
    selected = manifest.get("selected_services", [])
    if not selected:
        print("No services configured. Run --interactive first.")
        return

    local_path = vault_dir / SERVICES_LOCAL_FILENAME
    services = load_service_registry(registry_path, local_path)
    creds = load_yaml(vault_dir / CREDENTIALS_FILENAME)

    results: list[HealthResult] = []
    for svc_key in selected:
        svc_def = services.get(svc_key, {})
        health_cfg = svc_def.get("health_check")
        if health_cfg:
            results.append(check_service(svc_key, health_cfg, creds))

    print_summary(results, services)


def _run_sync(
    vault_dir: Path,
    registry_path: Path,
    env_path: Path,
) -> None:
    """Re-sync vault credentials into .env."""
    print(banner("Cuebert Vault Sync"))

    manifest = read_manifest(vault_dir / MANIFEST_FILENAME)
    selected = manifest.get("selected_services", [])
    if not selected:
        print("No services configured. Run --interactive first.")
        return

    local_path = vault_dir / SERVICES_LOCAL_FILENAME
    services = load_service_registry(registry_path, local_path)
    creds = load_yaml(vault_dir / CREDENTIALS_FILENAME)

    run_env_sync(env_path, services, creds, selected)

    update_manifest_sync_timestamp(vault_dir / MANIFEST_FILENAME)

    print(f"\n{green('Sync complete.')}")


def _run_check(vault_dir: Path, registry_path: Path) -> None:
    """Local file health: vault exists, permissions, field counts (backward compat)."""
    print(banner("Cuebert Vault Health Check"))

    creds_path = vault_dir / CREDENTIALS_FILENAME
    if not creds_path.is_file():
        print(f"  {red('Vault file not found')} at {creds_path}")
        print("  Run: python scripts/init-vault.py --interactive")
        sys.exit(1)

    if not check_permissions(creds_path):
        perms = oct(os.stat(creds_path).st_mode & 0o777)
        print(f"  {yellow(f'Permissions are {perms}, expected 0o600. Fixing...')}")
        fix_permissions(creds_path)

    local_path = vault_dir / SERVICES_LOCAL_FILENAME
    services = load_service_registry(registry_path, local_path)
    creds = load_yaml(creds_path)

    total = 0
    populated = 0

    for svc_key, svc_def in services.items():
        svc_creds = creds.get(svc_key, {})
        if not isinstance(svc_creds, dict):
            svc_creds = {}

        fields = svc_def.get("fields", [])
        filled = sum(1 for f in fields if svc_creds.get(f["name"]))
        total += len(fields)
        populated += filled

        if filled == len(fields):
            icon = green("OK")
        elif filled > 0:
            icon = yellow("PARTIAL")
        else:
            icon = red("EMPTY")

        name = svc_def.get("name", svc_key)
        print(f"  {icon} {name:30s}  {filled}/{len(fields)} fields")

    print(f"\n  Total: {populated}/{total} fields populated.")


def _run_add_service(
    vault_dir: Path,
    registry_path: Path,
    env_path: Path,
    service_key: str,
    *,
    skip_health: bool = False,
) -> None:
    """Add or update a single service in the project vault."""
    print(banner(f"Add Service: {service_key}"))

    local_path = vault_dir / SERVICES_LOCAL_FILENAME
    services = load_service_registry(registry_path, local_path)

    if service_key not in services:
        print(f"  {red('Unknown service:')} {service_key}")
        print(f"  Available: {', '.join(sorted(services.keys()))}")
        sys.exit(1)

    deps = order_by_dependency([service_key], services)
    auto_added = set(deps) - {service_key}
    if auto_added:
        names = [services[k].get("name", k) for k in auto_added]
        print(f"  {yellow('Dependencies:')} {', '.join(names)}")

    creds_path = vault_dir / CREDENTIALS_FILENAME
    existing = load_yaml(creds_path)
    all_creds: dict[str, Any] = dict(existing)

    for svc in deps:
        svc_creds = _prompt_service_credentials(svc, services[svc], all_creds)
        all_creds[svc] = svc_creds

        if not skip_health:
            health_cfg = services[svc].get("health_check")
            if health_cfg:
                check_service(svc, health_cfg, all_creds)

    save_yaml(creds_path, all_creds, secure=True)

    manifest = read_manifest(vault_dir / MANIFEST_FILENAME)
    current_selected = manifest.get("selected_services", [])
    new_selected = list(dict.fromkeys(current_selected + deps))

    vault_vars = collect_env_mapping(services, new_selected, all_creds)
    write_manifest(
        vault_dir / MANIFEST_FILENAME,
        selected_services=new_selected,
        vault_vars=vault_vars,
    )

    run_env_sync(env_path, services, all_creds, new_selected)
    print(f"\n{green('Service added successfully.')}")


def _run_list_services(registry_path: Path, local_path: Path | None = None) -> None:
    """Print all available services from the registry."""
    services = load_service_registry(registry_path, local_path)

    print(banner("Available Services"))
    for key, svc in services.items():
        name = svc.get("name", key)
        desc = svc.get("description", "")
        cat = svc.get("category", "")
        deps = svc.get("depends_on", [])
        dep_str = f" (requires: {', '.join(deps)})" if deps else ""
        print(f"  {bold(name)} [{dim(cat)}]{dep_str}")
        if desc:
            print(f"    {dim(desc)}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Cuebert Vault interactive setup and management.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/init-vault.py --interactive\n"
            "  python scripts/init-vault.py --verify\n"
            "  python scripts/init-vault.py --sync\n"
            "  python scripts/init-vault.py --add-service langsmith\n"
            "  python scripts/init-vault.py --list-services\n"
        ),
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--interactive", action="store_true", help="Full guided setup (default)")
    mode.add_argument("--verify", action="store_true", help="Re-run health checks")
    mode.add_argument("--sync", action="store_true", help="Re-sync vault to .env")
    mode.add_argument("--check", action="store_true", help="Local file health check")
    mode.add_argument("--add-service", metavar="KEY", help="Add a service to existing vault")
    mode.add_argument("--list-services", action="store_true", help="List available services")

    parser.add_argument("--vault-dir", type=Path, help="Override project vault directory")
    parser.add_argument("--registry", type=Path, help="Override master services.yaml path")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompts")
    parser.add_argument("--no-health", action="store_true", help="Skip health checks")
    parser.add_argument("--verbose", action="store_true", help="Show debug output")

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.no_color:
        set_color_enabled(False)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(name)s: %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING)

    vault_dir = args.vault_dir or (Path.cwd() / PROJECT_VAULT_REL)
    registry_path = args.registry or _find_registry(vault_dir)
    env_path = Path.cwd() / ".env"

    if args.verify:
        _run_verify(vault_dir, registry_path)
    elif args.sync:
        _run_sync(vault_dir, registry_path, env_path)
    elif args.check:
        _run_check(vault_dir, registry_path)
    elif args.add_service:
        _run_add_service(
            vault_dir, registry_path, env_path, args.add_service,
            skip_health=args.no_health,
        )
    elif args.list_services:
        local_path = vault_dir / SERVICES_LOCAL_FILENAME if vault_dir.is_dir() else None
        _run_list_services(registry_path, local_path)
    else:
        _run_interactive(
            vault_dir, registry_path, env_path,
            skip_health=args.no_health,
            auto_yes=args.yes,
        )


def _find_registry(vault_dir: Path) -> Path:
    """Locate the services.yaml registry file.

    Search order:
      1. Project vault's own services.yaml (shipped during install)
      2. Cuebert hub default location (``registry/services.yaml``)
    """
    project_registry = vault_dir / SERVICES_FILENAME
    if project_registry.is_file():
        return project_registry
    if DEFAULT_REGISTRY_PATH.is_file():
        return DEFAULT_REGISTRY_PATH
    return project_registry
