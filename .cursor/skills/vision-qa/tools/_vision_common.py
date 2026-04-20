"""Shared vision-qa helpers: paths, mode, vault, pixel budget, memory commits."""

from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from datetime import date
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_ALLOWED_EXT = frozenset({".png", ".jpg", ".jpeg", ".webp", ".tga", ".bmp"})
_MAX_DIM = 8192
_MAX_TOTAL_DECOMP_PX_DEFAULT = 128_000_000
_VAULT_PILLOW_KEY = "vision_qa.pillow_enabled"

_DEFAULT_MAX_MB = 50


def max_image_bytes() -> int:
    raw = os.environ.get("CUEBERT_VISION_QA_MAX_IMAGE_MB", "").strip()
    if raw:
        try:
            mb = int(raw)
            if 1 <= mb <= 500:
                return mb * 1024 * 1024
        except ValueError:
            pass
    return _DEFAULT_MAX_MB * 1024 * 1024


def vision_qa_mode_env() -> str | None:
    v = os.environ.get("CUEBERT_VISION_QA_MODE", "").strip().lower()
    return v if v else None


def pillow_env_override_off() -> bool:
    v = os.environ.get("CUEBERT_VISION_QA_PILLOW_OK", "").strip().lower()
    return v in {"0", "false", "no", "off"}


def vault_pillow_enabled() -> bool | None:
    """Return None if unset; False to force stdlib path; True to prefer Pillow."""
    try:
        from _vault import CUEBERT_VAULT_AVAILABLE, get_resolver

        if not CUEBERT_VAULT_AVAILABLE:
            return None
        v = get_resolver().get_credential(_VAULT_PILLOW_KEY)
        if v is None:
            return None
        s = str(v).strip().lower()
        if s in {"1", "true", "yes", "on"}:
            return True
        if s in {"0", "false", "no", "off"}:
            return False
    except Exception as exc:
        logger.debug("vault vision_qa.pillow_enabled unavailable: %s", exc)
    return None


def effective_tool_mode(
    *,
    paths_must_exist: list[str],
    require_pillow_for_non_png: bool,
    pillow_available: bool,
) -> str:
    if vision_qa_mode_env() == "dry_run":
        return "dry_run"
    for p in paths_must_exist:
        err, _rp = validate_image_path(p)
        if err:
            return "dry_run"
    if require_pillow_for_non_png and not pillow_available:
        return "dry_run"
    return "live"


def effective_dir_tool_mode(
    *,
    dir_a: str,
    dir_b: str,
    require_pillow_for_non_png: bool,
    pillow_available: bool,
) -> str:
    """Like ``effective_tool_mode`` but for directory paths."""
    if vision_qa_mode_env() == "dry_run":
        return "dry_run"
    err_a, _ = validate_dir_path(dir_a)
    err_b, _ = validate_dir_path(dir_b)
    if err_a or err_b:
        return "dry_run"
    if require_pillow_for_non_png and not pillow_available:
        return "dry_run"
    return "live"


def validate_image_path(path: str) -> tuple[str | None, Path | None]:
    """Return (error_code, realpath) or (None, Path) on success."""
    if not path or not isinstance(path, str):
        return "vision.invalid_path", None
    try:
        p = Path(path).expanduser()
        rp = p.resolve(strict=True)
    except (OSError, RuntimeError):
        return "vision.path_not_found", None
    if not rp.is_file():
        return "vision.not_a_file", None
    ext = rp.suffix.lower()
    if ext not in _ALLOWED_EXT:
        return "vision.extension_not_allowed", None
    try:
        st = rp.stat()
    except OSError:
        return "vision.stat_failed", None
    mb = max_image_bytes()
    if st.st_size > mb:
        return "vision.file_too_large", None
    return None, rp


def validate_dir_path(path: str) -> tuple[str | None, Path | None]:
    if not path or not isinstance(path, str):
        return "vision.invalid_path", None
    try:
        p = Path(path).expanduser()
        rp = p.resolve(strict=True)
    except (OSError, RuntimeError):
        return "vision.path_not_found", None
    if not rp.is_dir():
        return "vision.not_a_directory", None
    return None, rp


def check_dimensions(width: int, height: int) -> str | None:
    if width < 1 or height < 1:
        return "vision.invalid_dimensions"
    if width > _MAX_DIM or height > _MAX_DIM:
        return "vision.dimensions_exceeded"
    return None


def pixel_budget_for_image(width: int, height: int) -> int:
    return width * height


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
    """Best-effort memory insert mirroring ``troubleshoot_commit``; never raises."""
    skills = Path(__file__).resolve().parents[2]
    mem_tools = skills / "memory-toolkit" / "tools"
    if not mem_tools.is_dir():
        sys.stderr.write(
            "vision-qa: memory-toolkit not found; skip troubleshoot_commit\n",
        )
        return {"status": "skipped", "error": "memory-toolkit not found"}

    inserted = False
    if str(mem_tools) not in sys.path:
        sys.path.insert(0, str(mem_tools))
        inserted = True
    try:
        from _memory_db import generate_embedding, get_db, _get_memory_mode

        wt_json = what_tried if isinstance(what_tried, str) else json.dumps(
            what_tried, ensure_ascii=False,
        )
        rid = str(uuid.uuid4())
        day = date.today().isoformat()
        embed_text = "\n\n".join(
            part for part in (problem, wt_json, why_tried or "", what_worked or "") if part
        )
        embedding_blob = generate_embedding(embed_text)
        if embedding_blob is None and _get_memory_mode() == "text":
            logger.debug("memory_mode=text; skipping embedding for vision-qa")

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
        logger.info("vision-qa troubleshoot_commit: id=%s", rid)
        return {"status": "ok", "id": rid}
    except Exception as exc:
        sys.stderr.write(f"vision-qa: troubleshoot_commit failed: {exc}\n")
        logger.warning("troubleshoot_commit_safe failed: %s", exc, exc_info=True)
        return {"status": "error", "error": str(exc)}
    finally:
        if inserted:
            try:
                sys.path.remove(str(mem_tools))
            except ValueError:
                pass
