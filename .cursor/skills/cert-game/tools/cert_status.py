"""MCP tool: cert-game status (mode, config, checklist catalog)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from _cert_common import _load_config, _resolve_mode, default_config_path

# Twelve M10-P3 checklist ids (parallel to cert_scan.CHECKLIST_ORDER).
CHECKLIST_IDS: tuple[str, ...] = (
    "legal.eula_present",
    "legal.privacy_policy_present",
    "legal.age_rating_configured",
    "metadata.game_description_set",
    "metadata.version_string_set",
    "metadata.store_assets_present",
    "technical.min_os_version_set",
    "technical.controller_support_declared",
    "technical.resolution_settings_valid",
    "technical.audio_settings_valid",
    "packaging.redistrib_included",
    "packaging.install_size_documented",
)


def cert_status(config_path: str | None = None) -> dict[str, Any]:
    """Return cert mode, config path, checklist ids, and store options from platform scope."""
    cfg_path = str(Path(config_path).expanduser().resolve()) if config_path else str(default_config_path())
    mode = _resolve_mode()
    cfg = _load_config(config_path)
    ch = cfg.get("checklists")
    configured = sorted(ch.keys()) if isinstance(ch, dict) else []

    matrix_hint = ["steam", "epic", "gog", "itchio", "internal"]

    advisory = bool(cfg.get("advisory_always", True))

    return {
        "mode": mode,
        "config_path": cfg_path,
        "checklist_ids_shipped": list(CHECKLIST_IDS),
        "checklist_ids_in_config": configured,
        "target_store_options": matrix_hint,
        "advisory_always": advisory,
        "spec_only_as_info": bool(cfg.get("spec_only_as_info", False)),
    }
