"""ANSI terminal rendering — colors, tables, banners.

Respects ``NO_COLOR`` env var and ``--no-color`` flag.
Falls back to plain text when the terminal does not support ANSI.
"""

from __future__ import annotations

import os
import sys


def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return False
    term = os.environ.get("TERM", "")
    if term == "dumb":
        return False
    return True


_COLOR_ENABLED = _supports_color()


def set_color_enabled(enabled: bool) -> None:
    global _COLOR_ENABLED  # noqa: PLW0603
    _COLOR_ENABLED = enabled


class _Ansi:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"


def _c(code: str, text: str) -> str:
    if not _COLOR_ENABLED:
        return text
    return f"{code}{text}{_Ansi.RESET}"


def bold(text: str) -> str:
    return _c(_Ansi.BOLD, text)


def green(text: str) -> str:
    return _c(_Ansi.GREEN, text)


def yellow(text: str) -> str:
    return _c(_Ansi.YELLOW, text)


def red(text: str) -> str:
    return _c(_Ansi.RED, text)


def cyan(text: str) -> str:
    return _c(_Ansi.CYAN, text)


def dim(text: str) -> str:
    return _c(_Ansi.DIM, text)


def banner(title: str) -> str:
    return f"\n{'=' * 3} {bold(title)} {'=' * 3}\n"


def section(title: str) -> str:
    return f"\n--- {bold(title)} ---"


def status_icon(status: str) -> str:
    icons = {
        "pass": green("PASS"),
        "fail": red("FAIL"),
        "skip": yellow("SKIP"),
    }
    return icons.get(status, status)


def health_result_line(
    service_name: str,
    status: str,
    status_code: int | None = None,
    latency_ms: int | None = None,
    error: str | None = None,
) -> str:
    icon = status_icon(status)
    parts = [f"  {service_name:30s} {icon}"]
    if status_code is not None:
        parts.append(f"({status_code}")
        if latency_ms is not None:
            parts.append(f", {latency_ms}ms)")
        else:
            parts.append(")")
    elif latency_ms is not None:
        parts.append(f"({latency_ms}ms)")
    if error and status != "pass":
        parts.append(f" — {dim(error)}")
    return " ".join(parts)
