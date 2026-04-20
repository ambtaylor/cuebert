"""Service selection and dependency resolution.

Loads the master service registry, presents a categorized multi-select
to the user, and expands the selection to include transitive dependencies.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .prompts import prompt_multi_select
from .renderer import bold, cyan, dim, yellow
from .vault_io import load_yaml

logger = logging.getLogger(__name__)

CATEGORY_ORDER = ["auth", "ai", "data", "devops"]
CATEGORY_LABELS = {
    "auth": "Authentication",
    "ai": "AI / LLM",
    "data": "Data Sources",
    "devops": "DevOps",
}


def load_service_registry(
    master_path: Path,
    local_path: Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Load the master services.yaml, optionally merging local extensions.

    Args:
        master_path: Path to the canonical ``services.yaml``.
        local_path: Optional path to a project's ``services-local.yaml``.

    Returns:
        Merged dict of ``{service_key: service_definition}``.
    """
    raw = load_yaml(master_path)
    services: dict[str, dict[str, Any]] = raw.get("services", {})

    if local_path and local_path.is_file():
        local_raw = load_yaml(local_path)
        local_svcs = local_raw.get("services", {})
        services.update(local_svcs)

    return services


def resolve_dependencies(
    selected: list[str],
    services: dict[str, dict[str, Any]],
) -> list[str]:
    """Expand a selection to include transitive ``depends_on`` chains.

    Detects cycles and raises ``ValueError`` with the cycle path.

    Args:
        selected: User-selected service keys.
        services: The full service registry.

    Returns:
        Expanded list in dependency-first order.
    """
    resolved: list[str] = []
    visited: set[str] = set()
    in_stack: set[str] = set()

    def _visit(key: str, path: list[str]) -> None:
        if key in visited:
            return
        if key in in_stack:
            cycle = " → ".join(path + [key])
            raise ValueError(f"Dependency cycle detected: {cycle}")

        in_stack.add(key)
        svc = services.get(key, {})
        for dep in svc.get("depends_on", []):
            _visit(dep, path + [key])
        in_stack.discard(key)
        visited.add(key)
        resolved.append(key)

    for key in selected:
        _visit(key, [])

    return resolved


def order_by_dependency(
    selected: list[str],
    services: dict[str, dict[str, Any]],
) -> list[str]:
    """Return selected services ordered so dependencies come first."""
    return resolve_dependencies(selected, services)


def group_by_category(
    services: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    """Return a flat list of items grouped by category for the picker.

    Each item has ``key``, ``name``, ``description``, and ``category``.
    """
    buckets: dict[str, list[dict[str, str]]] = {cat: [] for cat in CATEGORY_ORDER}

    for key, svc in services.items():
        cat = svc.get("category", "data")
        item = {
            "key": key,
            "name": svc.get("name", key),
            "description": svc.get("description", ""),
            "category": cat,
        }
        buckets.setdefault(cat, []).append(item)

    flat: list[dict[str, str]] = []
    for cat in CATEGORY_ORDER:
        flat.extend(buckets.get(cat, []))
    for cat, items in buckets.items():
        if cat not in CATEGORY_ORDER:
            flat.extend(items)

    return flat


def run_service_picker(
    services: dict[str, dict[str, Any]],
    *,
    preselected: set[str] | None = None,
) -> list[str]:
    """Interactive service picker with dependency resolution.

    Args:
        services: The full service registry.
        preselected: Service keys already selected (e.g. from existing manifest).

    Returns:
        Resolved list of service keys in dependency order.
    """
    items = group_by_category(services)

    print(f"\n{bold('Which systems does this project need?')}")
    raw_selected = prompt_multi_select(items, preselected=preselected)

    if not raw_selected:
        print("  No services selected.")
        return []

    expanded = resolve_dependencies(raw_selected, services)

    auto_added = set(expanded) - set(raw_selected)
    if auto_added:
        names = [services[k].get("name", k) for k in auto_added]
        print(f"\n  {yellow('Note:')} Auto-included dependencies: {', '.join(names)}")

    return expanded
