#!/usr/bin/env python3
"""Standalone runner for memory_scan — invoke from shell, no MCP server needed.

Usage:
    # Dry run (discover transcripts, no LLM calls):
    python3 run_scan.py --dry-run

    # Scan 5 most recent transcripts:
    python3 run_scan.py --limit 5

    # Full scan:
    python3 run_scan.py

    # With custom transcript dir:
    python3 run_scan.py --transcripts-dir /path/to/transcripts

Environment variables:
    OPENAI_API_KEY       Required for real (non dry-run) scans
    OPENAI_BASE_URL      OpenAI-compatible proxy (default: https://api.openai.com)
    OPENAI_CHAT_MODEL    Chat model name (default: gpt-4o-mini)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import types
_fake_mcp = types.ModuleType("mcp")
_fake_server = types.ModuleType("mcp.server")
_fake_fastmcp = types.ModuleType("mcp.server.fastmcp")
_fake_fastmcp.FastMCP = type("FastMCP", (), {})
_fake_mcp.server = _fake_server
_fake_server.fastmcp = _fake_fastmcp
sys.modules.setdefault("mcp", _fake_mcp)
sys.modules.setdefault("mcp.server", _fake_server)
sys.modules.setdefault("mcp.server.fastmcp", _fake_fastmcp)

from _memory_db import get_db
from memory_scan import (
    _DEFAULT_TRANSCRIPTS_DIR,
    _chat_extract_items,
    _discover_jsonl,
    _has_transcript,
    _insert_troubleshooting_row,
    _parse_transcript,
    _since_epoch_cutoff,
    _transcript_id_from_path,
    _truncate_tail,
    _MIN_TRANSCRIPT_CHARS,
    _MAX_USER_CHARS,
    _LLM_SLEEP_SEC,
)
import time
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("run_scan")


def main() -> None:
    parser = argparse.ArgumentParser(description="Memory scan: backfill troubleshooting from transcripts")
    parser.add_argument("--transcripts-dir", default=_DEFAULT_TRANSCRIPTS_DIR)
    parser.add_argument("--project", default=None)
    parser.add_argument("--since", default=None, help="ISO date cutoff (e.g. 2025-01-01)")
    parser.add_argument("--limit", type=int, default=0, help="Max transcripts to process (0=all)")
    parser.add_argument("--dry-run", action="store_true", help="Discover and parse only, no LLM or DB writes")
    args = parser.parse_args()

    root = Path(args.transcripts_dir).expanduser()
    if not root.is_dir():
        log.error("Not a directory: %s", root)
        sys.exit(1)

    since_ts = _since_epoch_cutoff(args.since)
    paths = _discover_jsonl(root, since_ts, args.limit)
    log.info("Discovered %d JSONL transcripts in %s", len(paths), root)

    if not paths:
        log.info("Nothing to process.")
        return

    conn = get_db()
    stats = {
        "discovered": len(paths),
        "skipped_dup": 0,
        "skipped_short": 0,
        "llm_called": 0,
        "items_extracted": 0,
        "items_inserted": 0,
        "errors": 0,
    }

    for idx, path in enumerate(paths, 1):
        tid = _transcript_id_from_path(path)

        if _has_transcript(conn, tid):
            stats["skipped_dup"] += 1
            continue

        text = _parse_transcript(path)
        if len(text) < _MIN_TRANSCRIPT_CHARS:
            stats["skipped_short"] += 1
            continue

        if args.dry_run:
            log.info("[%d/%d] %s — %d chars (would scan)", idx, len(paths), tid[:12], len(text))
            continue

        truncated = _truncate_tail(text, _MAX_USER_CHARS)
        record_date = datetime.fromtimestamp(
            path.stat().st_mtime, tz=timezone.utc
        ).date().isoformat()

        try:
            items = _chat_extract_items(truncated)
        except Exception as exc:
            log.error("[%d/%d] LLM error %s: %s", idx, len(paths), tid[:12], exc)
            stats["errors"] += 1
            time.sleep(_LLM_SLEEP_SEC)
            continue

        stats["llm_called"] += 1
        stats["items_extracted"] += len(items)

        for it in items:
            try:
                if _insert_troubleshooting_row(
                    conn, it,
                    transcript_id=tid,
                    project=args.project,
                    record_date=record_date,
                    dry_run=False,
                ):
                    stats["items_inserted"] += 1
            except Exception as exc:
                log.error("Insert error %s: %s", tid[:12], exc)
                stats["errors"] += 1

        time.sleep(_LLM_SLEEP_SEC)

        if idx % 10 == 0:
            log.info("Progress: %d/%d — inserted %d items so far", idx, len(paths), stats["items_inserted"])

    conn.close()
    log.info("=== SCAN COMPLETE ===")
    log.info(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
