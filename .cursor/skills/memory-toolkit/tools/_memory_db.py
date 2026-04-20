"""Shared SQLite + embedding utilities for the memory-toolkit.

Stores milestones and troubleshooting records under ``<cuebert-root>/.cuebert/memory/memory.db``.
FTS5 external content index is kept in sync via triggers on ``troubleshooting``.
"""

from __future__ import annotations

import json
import math
import os
import sqlite3
import struct
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def _get_memory_mode() -> str:
    """Resolve cuebert memory mode.

    Returns:
        "text" (default): FTS5/BM25 only. No embedding calls.
        "hybrid": FTS5 + vector ranking. Requires embeddings endpoint.
    """
    mode = os.environ.get("CUEBERT_MEMORY_MODE", "text").strip().lower()
    if mode not in ("text", "hybrid"):
        # Unknown mode falls back to text (fail safe for handoffs)
        return "text"
    return mode


MEMORY_MODE = _get_memory_mode()

_EMBEDDING_MODEL = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
_EMBEDDING_DIM = 1536


def _resolve_embedding_url() -> str:
    """Resolve the embeddings endpoint from env or Cuebert vault (cx_playground).

    Only used in hybrid mode (``generate_embedding`` returns early in text mode).

    Priority: ``OPENAI_BASE_URL`` env → vault ``cx_playground.endpoint``
    (appends ``/embeddings``) → default OpenAI.
    """
    if _get_memory_mode() == "text":
        raise RuntimeError(
            "Embedding URL resolution requires CUEBERT_MEMORY_MODE=hybrid.",
        )
    base = os.environ.get("OPENAI_BASE_URL")
    if base:
        return f"{base.rstrip('/')}/embeddings"
    try:
        from _vault import get_resolver
        endpoint = get_resolver().get_credential("cx_playground.endpoint")
        if endpoint:
            return f"{endpoint.rstrip('/')}/embeddings"
    except Exception:
        pass
    return "https://api.openai.com/v1/embeddings"


def find_cuebert_root(start: Path | None = None) -> Path:
    """Walk parents from *start* until a directory containing ``.cuebert`` is found."""
    p = (start or Path(__file__).resolve()).resolve()
    for parent in [p, *p.parents]:
        if (parent / ".cuebert").is_dir():
            return parent
    raise FileNotFoundError(
        "Could not locate Cuebert repo root (no .cuebert directory in parent chain).",
    )


def get_db() -> sqlite3.Connection:
    """Open SQLite at ``.cuebert/memory/memory.db`` under the Cuebert repo root.

    Creates the database file, WAL mode, tables, FTS5 index, and sync triggers.
    """
    root = find_cuebert_root()
    mem_dir = root / ".cuebert" / "memory"
    mem_dir.mkdir(parents=True, exist_ok=True)
    db_path = mem_dir / "memory.db"
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS milestones (
          id TEXT PRIMARY KEY,
          plan_slug TEXT NOT NULL,
          milestone TEXT NOT NULL,
          project TEXT,
          language TEXT,
          agent TEXT,
          phase TEXT,
          status TEXT,
          files_touched TEXT,
          deferred_items TEXT,
          decisions TEXT,
          summary TEXT,
          errors_encountered TEXT,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(plan_slug, milestone, phase)
        );

        CREATE TABLE IF NOT EXISTS troubleshooting (
          id TEXT PRIMARY KEY,
          date TEXT NOT NULL,
          project TEXT,
          agent TEXT,
          language TEXT,
          problem TEXT NOT NULL,
          what_tried TEXT NOT NULL,
          why_tried TEXT,
          what_worked TEXT,
          tags TEXT,
          errors TEXT,
          files_touched TEXT,
          plan_slug TEXT,
          milestone TEXT,
          transcript_id TEXT,
          source TEXT DEFAULT 'agent',
          embedding BLOB,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS troubleshooting_fts USING fts5(
          problem, what_tried, why_tried, what_worked, tags, errors,
          content='troubleshooting', content_rowid='rowid'
        );
        """,
    )
    _ensure_fts_triggers(conn)
    conn.commit()
    return conn


def _ensure_fts_triggers(conn: sqlite3.Connection) -> None:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='trigger' AND name='troubleshooting_ai'",
    )
    if cur.fetchone():
        return
    conn.executescript(
        """
        CREATE TRIGGER troubleshooting_ai AFTER INSERT ON troubleshooting BEGIN
          INSERT INTO troubleshooting_fts(rowid, problem, what_tried, why_tried, what_worked, tags, errors)
          VALUES (new.rowid, new.problem, new.what_tried, new.why_tried, new.what_worked, new.tags, new.errors);
        END;

        CREATE TRIGGER troubleshooting_ad AFTER DELETE ON troubleshooting BEGIN
          INSERT INTO troubleshooting_fts(troubleshooting_fts, rowid, problem, what_tried, why_tried, what_worked, tags, errors)
          VALUES('delete', old.rowid, old.problem, old.what_tried, old.why_tried, old.what_worked, old.tags, old.errors);
        END;

        CREATE TRIGGER troubleshooting_au AFTER UPDATE ON troubleshooting BEGIN
          INSERT INTO troubleshooting_fts(troubleshooting_fts, rowid, problem, what_tried, why_tried, what_worked, tags, errors)
          VALUES('delete', old.rowid, old.problem, old.what_tried, old.why_tried, old.what_worked, old.tags, old.errors);
          INSERT INTO troubleshooting_fts(rowid, problem, what_tried, why_tried, what_worked, tags, errors)
          VALUES (new.rowid, new.problem, new.what_tried, new.why_tried, new.what_worked, new.tags, new.errors);
        END;
        """,
    )


def _resolve_openai_key() -> str:
    """Resolve OpenAI API key from environment or Cuebert vault (cx_playground)."""
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    try:
        from _vault import get_resolver
        resolver = get_resolver()
        key = resolver.get_credential("cx_playground.api_key")
        if key:
            return key
    except Exception:
        pass
    raise ValueError(
        "OPENAI_API_KEY not found in environment or vault "
        "(tried cx_playground.api_key).",
    )


def generate_embedding(text: str) -> bytes | None:
    """Return a float32 embedding as bytes, or None in text-only mode.

    Text mode (default): returns None; callers must handle None gracefully.
    Hybrid mode: calls the configured embeddings endpoint.
    """
    if _get_memory_mode() == "text":
        return None
    api_key = _resolve_openai_key()
    embedding_url = _resolve_embedding_url()
    payload = json.dumps({
        "model": _EMBEDDING_MODEL,
        "input": text,
    }).encode("utf-8")
    req = urllib.request.Request(
        embedding_url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ValueError(f"OpenAI embeddings HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"OpenAI embeddings request failed: {exc}") from exc

    data = json.loads(raw)
    err = data.get("error")
    if err:
        raise ValueError(f"OpenAI API error: {err}")
    emb = data.get("data", [{}])[0].get("embedding")
    if not isinstance(emb, list) or not emb:
        raise ValueError("OpenAI response missing embedding vector.")
    if len(emb) != _EMBEDDING_DIM:
        raise ValueError(
            f"Unexpected embedding length {len(emb)} (expected {_EMBEDDING_DIM}).",
        )
    floats = [float(x) for x in emb]
    return struct.pack(f"{len(floats)}f", *floats)


def cosine_similarity(a: bytes, b: bytes) -> float:
    """Cosine similarity for two float32-packed vectors (pure Python)."""
    fa = struct.unpack(f"{len(a) // 4}f", a)
    fb = struct.unpack(f"{len(b) // 4}f", b)
    if len(fa) != len(fb) or not fa:
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(fa, fb):
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


def _fts5_escape_token(token: str) -> str:
    return '"' + token.replace('"', '""') + '"'


def _build_fts_query(query: str) -> str:
    parts = [p for p in query.split() if p.strip()]
    if not parts:
        return '""'
    return " OR ".join(_fts5_escape_token(p) for p in parts[:32])


def hybrid_search(
    conn: sqlite3.Connection,
    query: str,
    query_embedding: bytes | None,
    filters: dict[str, Any],
    limit: int,
) -> list[dict[str, Any]]:
    """BM25 (FTS5) + optional vector cosine merge.

    - In text mode (``query_embedding`` is None): FTS5/BM25 only; ``vec_scores`` stays empty;
      combined score = ``0.4 * fts_score`` for each hit.
    - In hybrid mode (``query_embedding`` is bytes): full hybrid as before
      (``0.6 * vec + 0.4 * fts``).
    """
    if limit < 1:
        limit = 10
    project = filters.get("project")
    tags = filters.get("tags")

    filter_parts: list[str] = []
    filter_params: list[Any] = []

    if project:
        filter_parts.append("t.project IS ?")
        filter_params.append(project)

    if tags:
        tag_list = tags if isinstance(tags, list) else [tags]
        for tag in tag_list:
            if tag:
                filter_parts.append("IFNULL(t.tags, '') LIKE ?")
                filter_params.append(f"%{tag}%")

    extra_where = ""
    if filter_parts:
        extra_where = " AND " + " AND ".join(filter_parts)

    fts_query = _build_fts_query(query)
    fts_scores: dict[str, float] = {}
    fts_bm25: dict[str, float] = {}

    if fts_query != '""':
        sql_fts = f"""
          SELECT t.id, bm25(troubleshooting_fts) AS b
          FROM troubleshooting_fts
          JOIN troubleshooting AS t ON t.rowid = troubleshooting_fts.rowid
          WHERE troubleshooting_fts MATCH ?{extra_where}
          ORDER BY b ASC
          LIMIT ?
        """
        fts_params: list[Any] = [fts_query, *filter_params, min(limit * 8, 200)]
        cur = conn.execute(sql_fts, fts_params)
        rows = cur.fetchall()
        if rows:
            bs = [float(r["b"]) for r in rows]
            b_min, b_max = min(bs), max(bs)
            span = (b_max - b_min) or 1.0
            for r in rows:
                bid = str(r["id"])
                b = float(r["b"])
                fts_bm25[bid] = b
                fts_scores[bid] = (b_max - b) / span

    vec_scores: dict[str, float] = {}
    if query_embedding is not None:
        sql_vec = f"""
          SELECT t.id, t.embedding
          FROM troubleshooting AS t
          WHERE t.embedding IS NOT NULL{extra_where}
        """
        for row in conn.execute(sql_vec, filter_params):
            emb = row["embedding"]
            if not emb:
                continue
            vid = str(row["id"])
            vec_scores[vid] = cosine_similarity(query_embedding, emb)

    all_ids = set(fts_scores) | set(vec_scores)
    if not all_ids:
        return []

    combined: list[tuple[str, float]] = []
    for sid in all_ids:
        v = vec_scores.get(sid, 0.0)
        f = fts_scores.get(sid, 0.0)
        combined.append((sid, 0.6 * v + 0.4 * f))

    combined.sort(key=lambda x: x[1], reverse=True)
    top_ids = [i for i, _ in combined[:limit]]

    placeholders = ",".join("?" for _ in top_ids)
    sql_fetch = f"""
      SELECT * FROM troubleshooting WHERE id IN ({placeholders})
    """
    id_to_row: dict[str, sqlite3.Row] = {
        str(r["id"]): r for r in conn.execute(sql_fetch, top_ids)
    }

    out: list[dict[str, Any]] = []
    for sid in top_ids:
        r = id_to_row.get(sid)
        if r is None:
            continue
        d = dict(r)
        d["hybrid_score"] = next(s for i, s in combined if i == sid)
        d["vector_score"] = vec_scores.get(sid)
        d["fts_score"] = fts_scores.get(sid)
        d["fts_bm25"] = fts_bm25.get(sid)
        out.append(d)
    return out
