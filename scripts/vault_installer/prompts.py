"""Interactive prompt primitives for the vault installer.

Uses only stdlib (``input``, ``getpass``) — no external dependencies.
"""

from __future__ import annotations

import getpass
import sys

from .renderer import bold, cyan, dim, green


def prompt_text(label: str, *, default: str = "", current: str = "") -> str:
    """Prompt for a text value, showing default/current if available."""
    display = current or default
    suffix = f" [{display}]" if display else ""
    value = input(f"  {label}{suffix}: ").strip()
    return value if value else (current or default)


def prompt_secret(label: str, *, current: str = "") -> str:
    """Prompt for a secret value using getpass (no terminal echo)."""
    display = "****" if current else ""
    suffix = f" [{display}]" if display else ""
    value = getpass.getpass(f"  {label}{suffix}: ").strip()
    return value if value else current


def prompt_confirm(message: str, *, default: bool = True) -> bool:
    """Ask a yes/no question, return boolean."""
    hint = "[Y/n]" if default else "[y/N]"
    answer = input(f"  {message} {hint}: ").strip().lower()
    if not answer:
        return default
    return answer in ("y", "yes")


def prompt_multi_select(
    items: list[dict[str, str]],
    *,
    preselected: set[str] | None = None,
) -> list[str]:
    """Display a numbered multi-select list and return selected keys.

    Each item is a dict with at least ``key``, ``name``, and ``description``.

    Args:
        items: List of selectable items with key/name/description.
        preselected: Keys that start already selected.

    Returns:
        List of selected keys in display order.
    """
    if preselected is None:
        preselected = set()

    selected = set(preselected)

    print()
    for i, item in enumerate(items, 1):
        key = item["key"]
        marker = green("[x]") if key in selected else "[ ]"
        name = item.get("name", key)
        desc = item.get("description", "")
        desc_part = f" — {dim(desc)}" if desc else ""
        print(f"  {i:2d}. {marker} {name}{desc_part}")

    print()
    print(dim("  Enter numbers separated by commas (e.g. 1,3,5), 'all', or 'none'."))
    print(dim("  Press Enter to keep current selection."))
    answer = input("  Select: ").strip().lower()

    if not answer:
        return [item["key"] for item in items if item["key"] in selected]

    if answer == "all":
        return [item["key"] for item in items]

    if answer == "none":
        return []

    chosen: list[str] = []
    for part in answer.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(items):
                chosen.append(items[idx]["key"])
            else:
                print(f"  {bold('Warning:')} {part} is out of range, skipping.", file=sys.stderr)

    return chosen
