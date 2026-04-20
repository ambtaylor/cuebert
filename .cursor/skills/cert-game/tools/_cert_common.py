"""Shared helpers for cert-game: config, INI/JSON IO, mode, memory."""

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

_VAULT_MODE_KEY = "cert_game.mode"
_MAX_BYTES = 10 * 1024 * 1024


def find_hub_root(start: Path | None = None) -> Path:
    """Locate repo root (directory containing ``.cuebert``)."""
    p = (start or Path(__file__).resolve()).resolve()
    for parent in [p, *p.parents]:
        if (parent / ".cuebert").is_dir():
            return parent
    raise FileNotFoundError("Could not locate Cuebert hub root (.cuebert).")


def default_config_path() -> Path:
    """Hub default YAML for cert-game."""
    return find_hub_root() / ".cuebert" / "config" / "cert-game.yaml"


def _vault_mode_raw() -> str | None:
    try:
        from _vault import CUEBERT_VAULT_AVAILABLE, get_resolver

        if not CUEBERT_VAULT_AVAILABLE:
            return None
        v = get_resolver().get_credential(_VAULT_MODE_KEY)
        if v and str(v).strip():
            return str(v).strip().lower()
    except Exception as exc:
        logger.debug("vault cert_game.mode unavailable: %s", exc)
    return None


def _resolve_mode() -> str:
    """Return ``dry_run`` or ``live`` from env ``CUEBERT_CERT_MODE`` or vault."""
    env = os.environ.get("CUEBERT_CERT_MODE", "").strip().lower()
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
    """Load hub cert-game YAML."""
    path = Path(config_path).expanduser() if config_path else default_config_path()
    if not path.is_file():
        return {"version": 1, "checklists": {}, "advisory_always": True}
    with open(path, encoding="utf-8", errors="replace") as fh:
        data = yaml.safe_load(fh)
    return data if isinstance(data, dict) else {}


def _merge_project_config(hub_cfg: dict[str, Any], project_root: Path) -> dict[str, Any]:
    """Merge optional ``<project>/.cuebert/cert.yaml`` over hub config (shallow checklists merge)."""
    out = dict(hub_cfg)
    proj_path = project_root / ".cuebert" / "cert.yaml"
    if not proj_path.is_file():
        return out
    try:
        with open(proj_path, encoding="utf-8", errors="replace") as fh:
            extra = yaml.safe_load(fh)
    except OSError:
        return out
    if not isinstance(extra, dict):
        return out
    hc = out.get("checklists")
    ec = extra.get("checklists")
    if isinstance(hc, dict) and isinstance(ec, dict):
        merged = dict(hc)
        merged.update(ec)
        out["checklists"] = merged
    elif isinstance(ec, dict):
        out["checklists"] = ec
    return out


def _read_ini_safe(path: Path, max_size: int = _MAX_BYTES) -> configparser.ConfigParser:
    """Parse a UE INI file with ``strict=False`` and size guard."""
    try:
        st = path.stat()
    except OSError as exc:
        raise OSError(f"stat_failed: {exc}") from exc
    if st.st_size > max_size:
        raise OSError("file_too_large")
    cp = configparser.ConfigParser(strict=False, interpolation=None, allow_no_value=True)
    cp.optionxform = str
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    cp.read_file(StringIO(raw), source=str(path))
    return cp


def _read_json_safe(path: Path, max_size: int = _MAX_BYTES) -> Any:
    """Load JSON with size guard."""
    try:
        st = path.stat()
    except OSError as exc:
        raise OSError(f"stat_failed: {exc}") from exc
    if st.st_size > max_size:
        raise OSError("file_too_large")
    return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))


def _coerce_severity(raw: str | None) -> str:
    """Return only ``info`` or ``warn`` (cert-game contract: never reject/critical)."""
    s = (raw or "info").strip().lower()
    if s in {"reject", "critical", "error", "block", "fail"}:
        return "warn"
    if s == "warn":
        return "warn"
    return "info"


def checklist_entry(config: dict[str, Any], checklist_id: str) -> dict[str, Any]:
    """Return merged checklist block from config or empty dict."""
    ch = config.get("checklists")
    if not isinstance(ch, dict):
        return {}
    row = ch.get(checklist_id)
    return dict(row) if isinstance(row, dict) else {}


def checklist_on(entry: dict[str, Any]) -> bool:
    st = str(entry.get("status") or "on").strip().lower()
    return st != "off"


def checklist_applies(
    entry: dict[str, Any],
    *,
    target_store: str,
    target_platform: str,
) -> bool:
    """Honor ``applies_to`` filters when present."""
    at = entry.get("applies_to")
    if not isinstance(at, dict):
        return True
    ts = at.get("target_store")
    if isinstance(ts, list) and target_store.lower() not in [str(x).lower() for x in ts]:
        return False
    tp = at.get("target_platform")
    if isinstance(tp, list) and target_platform not in tp:
        return False
    return True


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
        sys.stderr.write("cert-game: memory-toolkit not found; skip troubleshoot_commit\n")
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
            logger.debug("memory_mode=text; skipping embedding for cert-game")

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
        logger.info("cert-game troubleshoot_commit: id=%s", rid)
        return {"status": "ok", "id": rid}
    except Exception as exc:
        sys.stderr.write(f"cert-game: troubleshoot_commit failed: {exc}\n")
        logger.warning("troubleshoot_commit_safe failed: %s", exc, exc_info=True)
        return {"status": "error", "error": str(exc)}
    finally:
        if inserted:
            try:
                sys.path.remove(str(mem_tools))
            except ValueError:
                pass


def validate_project_file(project_path: str) -> tuple[str | None, str | None]:
    """Resolve ``.uproject`` path or return (None, error)."""
    try:
        p = Path(project_path).expanduser().resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        return None, f"project_path not resolvable: {exc}"
    s = str(p)
    if not s.endswith(".uproject") or not p.is_file():
        return None, "project_path must be an existing .uproject file"
    return s, None


def validate_optional_dir(path: str | None) -> tuple[str | None, str | None]:
    """Resolve optional directory path."""
    if path is None or not str(path).strip():
        return None, None
    try:
        p = Path(path).expanduser().resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        return None, f"build_path not resolvable: {exc}"
    if not p.is_dir():
        return None, "build_path is not a directory"
    return str(p), None
