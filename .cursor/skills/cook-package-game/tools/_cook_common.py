"""Shared helpers for cook-package-game: config, paths, mode, memory."""

from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from datetime import date
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_VAULT_MODE_KEY = "cook_package.mode"
_MAX_TEXT_BYTES = 10 * 1024 * 1024


def find_hub_root(start: Path | None = None) -> Path:
    """Locate repo root (directory containing ``.cuebert``)."""
    p = (start or Path(__file__).resolve()).resolve()
    for parent in [p, *p.parents]:
        if (parent / ".cuebert").is_dir():
            return parent
    raise FileNotFoundError("Could not locate Cuebert hub root (.cuebert).")


def default_config_path() -> Path:
    """Hub default YAML for cook-package-game."""
    return find_hub_root() / ".cuebert" / "config" / "cook-package-game.yaml"


def _vault_mode_raw() -> str | None:
    """Optional vault key ``cook_package.mode``."""
    try:
        from _vault import CUEBERT_VAULT_AVAILABLE, get_resolver

        if not CUEBERT_VAULT_AVAILABLE:
            return None
        v = get_resolver().get_credential(_VAULT_MODE_KEY)
        if v and str(v).strip():
            return str(v).strip().lower()
    except Exception as exc:
        logger.debug("vault cook_package.mode unavailable: %s", exc)
    return None


def _resolve_mode() -> str:
    """Return ``dry_run`` or ``live`` from env ``CUEBERT_COOK_PACKAGE_MODE`` or vault."""
    env = os.environ.get("CUEBERT_COOK_PACKAGE_MODE", "").strip().lower()
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
    """Load cook-package-game YAML; missing file returns minimal defaults."""
    path = Path(config_path).expanduser() if config_path else default_config_path()
    if not path.is_file():
        return {"version": 1, "defaults": {}, "platform_matrix": {}}
    with open(path, encoding="utf-8", errors="replace") as fh:
        data = yaml.safe_load(fh)
    return data if isinstance(data, dict) else {}


def _get_platform_config(config: dict[str, Any], platform: str) -> dict[str, Any] | None:
    """Return platform_matrix entry for *platform* or None if absent."""
    matrix = config.get("platform_matrix")
    if not isinstance(matrix, dict):
        return None
    row = matrix.get(platform)
    return dict(row) if isinstance(row, dict) else None


def _platform_runnable_status(row: dict[str, Any] | None) -> tuple[bool, str]:
    """Return (allowed, reason). ``on`` and ``supported`` allow live cook; ``skeleton`` skips."""
    if row is None:
        return False, "platform not listed in platform_matrix"
    st = str(row.get("status") or "").strip().lower()
    if st in {"on", "supported", "yes", "true", "1"}:
        return True, ""
    if st == "skeleton":
        return False, "platform_matrix status is skeleton (automated cook not supported in this milestone)"
    if st in {"off", "disabled", "no", "false", "0"}:
        return False, f"platform_matrix status is {st!r}"
    return False, f"platform_matrix status {st!r} is not supported for cook-package"


def _validate_project_path(path: str) -> tuple[str | None, str | None]:
    """Normalize *path* to realpath; ensure ``.uproject`` exists. Returns (resolved, error_message)."""
    try:
        p = Path(path).expanduser().resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        return None, f"project_path not resolvable: {exc}"
    s = str(p)
    if not s.endswith(".uproject"):
        return None, "project_path must end with .uproject"
    if not p.is_file():
        return None, "project_path is not a file"
    return s, None


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
    skills_dir = Path(__file__).resolve().parent.parent.parent
    mem_tools = skills_dir / "memory-toolkit" / "tools"
    if not mem_tools.is_dir():
        sys.stderr.write("cook-package-game: memory-toolkit not found; skip troubleshoot_commit\n")
        return {"status": "skipped", "error": "memory-toolkit not found"}

    inserted = False
    if str(mem_tools) not in sys.path:
        sys.path.insert(0, str(mem_tools))
        inserted = True
    try:
        from _memory_db import generate_embedding, get_db, _get_memory_mode

        wt_json = what_tried if isinstance(what_tried, str) else json.dumps(what_tried, ensure_ascii=False)
        rid = str(uuid.uuid4())
        day = date.today().isoformat()
        embed_text = "\n\n".join(
            part for part in (problem, wt_json, why_tried or "", what_worked or "") if part
        )
        embedding_blob = generate_embedding(embed_text)
        if embedding_blob is None and _get_memory_mode() == "text":
            logger.debug("memory_mode=text; skipping embedding for cook-package-game")

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
        logger.info("cook-package-game troubleshoot_commit: id=%s", rid)
        return {"status": "ok", "id": rid}
    except Exception as exc:
        sys.stderr.write(f"cook-package-game: troubleshoot_commit failed: {exc}\n")
        logger.warning("troubleshoot_commit_safe failed: %s", exc, exc_info=True)
        return {"status": "error", "error": str(exc)}
    finally:
        if inserted:
            try:
                sys.path.remove(str(mem_tools))
            except ValueError:
                pass
