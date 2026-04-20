"""Shared helpers for prod-readiness-game: config, INI/uproject IO, memory."""

from __future__ import annotations

import configparser
import json
import logging
import os
import sys
import uuid
from datetime import date
from io import StringIO
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_VAULT_MODE_KEY = "prod_readiness.mode"
_MAX_TEXT_BYTES = 10 * 1024 * 1024

# readiness.* rule_id -> prod-readiness-game.yaml catalogue key
RULE_CONFIG_ALIASES: dict[str, str] = {
    "readiness.debug_symbols_stripped": "packaging.pdb_excluded_in_shipping",
    "readiness.shipping_config": "packaging.shipping_config_required",
    "readiness.console_output_disabled": "security.verbose_logging_disabled",
    "readiness.crash_reporter_enabled": "packaging.crash_reporter_included",
    "readiness.pak_file_signing": "packaging.shipping_config_required",
    "readiness.encryption_enabled": "security.verbose_logging_disabled",
    "readiness.version_set": "metadata.game_version_parseable",
    "readiness.display_name_set": "metadata.game_name_set",
    "readiness.default_map_set": "metadata.game_version_parseable",
    "readiness.splash_screens_set": "content.no_placeholder_assets",
    "readiness.icon_set": "metadata.game_name_set",
    "readiness.privacy_policy_url": "metadata.copyright_notice",
    "readiness.age_rating_configured": "metadata.copyright_notice",
    "readiness.banned_plugins_absent": "perf.no_shippable_dev_tools",
}


def find_hub_root(start: Path | None = None) -> Path:
    """Locate repo root (directory containing ``.cuebert``)."""
    p = (start or Path(__file__).resolve()).resolve()
    for parent in [p, *p.parents]:
        if (parent / ".cuebert").is_dir():
            return parent
    raise FileNotFoundError("Could not locate Cuebert hub root (.cuebert).")


def default_config_path() -> Path:
    """Hub default YAML for prod-readiness-game."""
    return find_hub_root() / ".cuebert" / "config" / "prod-readiness-game.yaml"


def _vault_mode_raw() -> str | None:
    """Optional vault key ``prod_readiness.mode`` (placeholder)."""
    try:
        from _vault import CUEBERT_VAULT_AVAILABLE, get_resolver

        if not CUEBERT_VAULT_AVAILABLE:
            return None
        v = get_resolver().get_credential(_VAULT_MODE_KEY)
        if v and str(v).strip():
            return str(v).strip().lower()
    except Exception as exc:
        logger.debug("vault prod_readiness.mode unavailable: %s", exc)
    return None


def _resolve_mode() -> str:
    """Return ``dry_run`` or ``live`` from env or vault."""
    env = os.environ.get("CUEBERT_PROD_READINESS_MODE", "").strip().lower()
    if env in {"dry_run", "dry-run"}:
        return "dry_run"
    if env in {"live", "on", "1", "true"}:
        return "live"
    vault = _vault_mode_raw()
    if vault in {"dry_run", "dry-run"}:
        return "dry_run"
    if vault in {"live", "on", "1", "true"}:
        return "live"
    return "live"


def _load_config(config_path: str | None = None) -> dict[str, Any]:
    """Load merged hub YAML; missing file returns minimal defaults."""
    path = Path(config_path).expanduser() if config_path else default_config_path()
    if not path.is_file():
        return {"version": 1, "rules": {}, "spec_only_as_info": False}
    with open(path, encoding="utf-8", errors="replace") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def rule_entry_for(rule_id: str, config: dict[str, Any]) -> dict[str, Any]:
    """Return rule block for *rule_id* or its catalogue alias from YAML."""
    rules = config.get("rules") or {}
    if not isinstance(rules, dict):
        return {}
    if rule_id in rules and isinstance(rules[rule_id], dict):
        return dict(rules[rule_id])
    alias = RULE_CONFIG_ALIASES.get(rule_id, "")
    if alias and alias in rules and isinstance(rules[alias], dict):
        return dict(rules[alias])
    return {}


def _rule_on(rule_id: str, config: dict[str, Any]) -> bool:
    entry = rule_entry_for(rule_id, config)
    st = (entry.get("status") or "on").strip().lower()
    return st != "off"


def rule_applies(
    rule_id: str,
    config: dict[str, Any],
    *,
    target_platform: str,
    target_store: str,
    build_config: str,
) -> bool:
    """Honor YAML ``applies_to`` filters when present."""
    entry = rule_entry_for(rule_id, config)
    at = entry.get("applies_to")
    if not isinstance(at, dict):
        alias = RULE_CONFIG_ALIASES.get(rule_id, "")
        rules = config.get("rules") or {}
        if (
            alias
            and isinstance(rules, dict)
            and alias in rules
            and isinstance(rules[alias], dict)
        ):
            at = rules[alias].get("applies_to")
    if not isinstance(at, dict):
        return True
    if "target_platform" in at and isinstance(at["target_platform"], list):
        if target_platform not in at["target_platform"]:
            return False
    if "target_store" in at and isinstance(at["target_store"], list):
        if target_store not in at["target_store"]:
            return False
    if "build_config" in at and isinstance(at["build_config"], list):
        if build_config not in at["build_config"]:
            return False
    return True


def _read_ini_file(path: Path) -> configparser.ConfigParser:
    """Parse a UE INI file with lenient rules (``strict=False``)."""
    cp = configparser.ConfigParser(
        strict=False,
        interpolation=None,
        allow_no_value=True,
    )
    cp.optionxform = str
    raw, err = read_text_capped(path)
    if err:
        raise OSError(err)
    assert raw is not None
    cp.read_file(StringIO(raw), source=str(path))
    return cp


def read_text_capped(path: Path, max_bytes: int = _MAX_TEXT_BYTES) -> tuple[str | None, str | None]:
    """Read UTF-8 text up to *max_bytes* or return ``(None, error_code)``."""
    try:
        st = path.stat()
    except OSError:
        return None, "stat_failed"
    if st.st_size > max_bytes:
        return None, "file_too_large"
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace"), None
    except OSError:
        return None, "read_failed"


def _read_uproject(path: Path) -> dict[str, Any]:
    """Parse a ``.uproject`` JSON file (bounded size)."""
    raw, err = read_text_capped(path)
    if err:
        raise OSError(err)
    assert raw is not None
    return json.loads(raw)


def resolve_project_root(project_path: str) -> Path:
    """Directory containing the Unreal project (parent of ``.uproject``)."""
    p = Path(project_path).expanduser().resolve()
    if p.suffix.lower() == ".uproject":
        return p.parent
    return p


def find_uproject(root: Path) -> Path | None:
    """Locate a ``*.uproject`` under *root* (shallow)."""
    if root.suffix.lower() == ".uproject" and root.is_file():
        return root
    for c in root.glob("*.uproject"):
        if c.is_file():
            return c
    return None


def ensure_under_project(path: Path, project_root: Path) -> bool:
    """Return True if *path* is the same as or under *project_root* (after resolve)."""
    try:
        pr = project_root.resolve()
        pc = path.resolve()
        pc.relative_to(pr)
        return True
    except (ValueError, OSError):
        return False


def troubleshoot_commit_safe(
    problem: str,
    what_tried: Any,
    *,
    why_tried: str | None = None,
    what_worked: str | None = None,
    tags: str | None = None,
    project: str | None = None,
    agent: str | None = None,
    plan_slug: str | None = None,
) -> dict[str, Any]:
    """Best-effort memory insert; never raises."""
    skills_dir = Path(__file__).resolve().parents[2]
    mem_tools = skills_dir / "memory-toolkit" / "tools"
    if not mem_tools.is_dir():
        sys.stderr.write("prod-readiness-game: memory-toolkit not found; skip troubleshoot_commit\n")
        return {"status": "skipped", "error": "memory-toolkit not found"}

    inserted = False
    if str(mem_tools) not in sys.path:
        sys.path.insert(0, str(mem_tools))
        inserted = True
    try:
        from _memory_db import generate_embedding, get_db, _get_memory_mode

        wt_json = what_tried if isinstance(what_tried, str) else json.dumps(
            what_tried,
            ensure_ascii=False,
        )
        rid = str(uuid.uuid4())
        day = date.today().isoformat()
        embed_text = "\n\n".join(
            part for part in (problem, wt_json, why_tried or "", what_worked or "") if part
        )
        embedding_blob = generate_embedding(embed_text)
        if embedding_blob is None and _get_memory_mode() == "text":
            logger.debug("memory_mode=text; skipping embedding for prod-readiness-game")

        conn = get_db()
        conn.execute(
            """
                INSERT INTO troubleshooting (
                  id, date, project, agent, language, problem, what_tried,
                  why_tried, what_worked, tags, errors, files_touched,
                  plan_slug, milestone, transcript_id, source, embedding
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
            (
                rid,
                day,
                project,
                agent,
                None,
                problem,
                wt_json,
                why_tried,
                what_worked,
                tags,
                None,
                None,
                plan_slug,
                None,
                None,
                "agent",
                embedding_blob,
            ),
        )
        conn.commit()
        conn.close()
        logger.info("prod-readiness-game troubleshoot_commit: id=%s", rid)
        return {"status": "ok", "id": rid}
    except Exception as exc:
        sys.stderr.write(f"prod-readiness-game: troubleshoot_commit failed: {exc}\n")
        logger.warning("troubleshoot_commit_safe failed: %s", exc, exc_info=True)
        return {"status": "error", "error": str(exc)}
    finally:
        if inserted:
            try:
                sys.path.remove(str(mem_tools))
            except ValueError:
                pass
