"""Shared vault resolver factory for Cuebert MCP tools.

Adds ``lib/`` to ``sys.path`` so ``cuebert_vault`` is importable without
``pip install -e``, then provides a factory that builds a
:class:`FileVaultResolver` rooted at the hub.

When ``lib/cuebert_vault`` is not yet present (resolver deferred per M1 plan),
imports are skipped and callers should handle :data:`CUEBERT_VAULT_AVAILABLE`.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


def find_cuebert_root(start: Path) -> Path:
    """Walk upward from *start* to find the Cuebert hub root (.cuebert/ marker)."""
    current = start
    for _ in range(10):
        if (current / ".cuebert").is_dir():
            return current
        current = current.parent
    raise RuntimeError(
        f"Cannot find Cuebert hub root from {start}. "
        "Expected a parent directory containing .cuebert/"
    )


_HUB_ROOT = find_cuebert_root(Path(__file__).resolve().parent)
_LIB_DIR = _HUB_ROOT / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

CUEBERT_VAULT_AVAILABLE = False
FileVaultResolver: Any = None
HealthResult: Any = None
HealthStatus: Any = None
run_health_check: Any = None

try:
    from cuebert_vault import FileVaultResolver as _FileVaultResolver  # noqa: E402
    from cuebert_vault.health import (  # noqa: E402
        HealthResult as _HealthResult,
        HealthStatus as _HealthStatus,
        run_health_check as _run_health_check,
    )

    FileVaultResolver = _FileVaultResolver
    HealthResult = _HealthResult
    HealthStatus = _HealthStatus
    run_health_check = _run_health_check
    CUEBERT_VAULT_AVAILABLE = True
except ImportError:
    pass


def get_resolver(
    *,
    project_dir: str | None = None,
    project_key: str | None = None,
) -> Any:
    """Create a :class:`FileVaultResolver` with hub auto-discovery.

    Args:
        project_dir: Absolute path to a workspace project root (application
            repo or hub). If provided, that project's ``.cuebert/`` is used for
            project-tier resolution. Otherwise the hub itself is used.
        project_key: Explicit project key in the workspace manifest.
            Auto-discovered when *project_dir* is given.

    Returns:
        A configured resolver following the vault resolution chain.

    Raises:
        RuntimeError: If ``cuebert_vault`` is not installed under ``hub/lib/``.
    """
    if not CUEBERT_VAULT_AVAILABLE or FileVaultResolver is None:
        raise RuntimeError(
            "cuebert_vault is not installed. When lib/cuebert_vault exists, run: "
            "pip install -e <hub-root>/lib/cuebert_vault"
        )

    if project_dir:
        proj_cuebert = Path(project_dir) / ".cuebert"
    else:
        proj_cuebert = _HUB_ROOT / ".cuebert"

    return FileVaultResolver(
        project_dir=proj_cuebert,
        hub_dir=_HUB_ROOT,
        project_key=project_key,
    )


def redact(value: str, visible: int = 4) -> str:
    """Redact a credential value, showing only the first *visible* chars."""
    if len(value) <= visible:
        return "***"
    return value[:visible] + "***"


def health_result_to_dict(result: Any) -> dict[str, Any]:
    """Convert a :class:`HealthResult` dataclass to a JSON-safe dict."""
    return {
        "service": result.service,
        "status": result.status.value,
        "status_code": result.status_code,
        "latency_ms": result.latency_ms,
        "error": result.error,
    }
