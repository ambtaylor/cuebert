# Memory Toolkit

## Metadata

- **Name:** `memory-toolkit`
- **Description:** Local SQLite memory for milestone handoffs and troubleshooting recall (FTS5 + optional vector ranking). Defaults to **text-only** mode (`CUEBERT_MEMORY_MODE=text`): no embedding API or model configuration required; hybrid vector ranking is opt-in via `CUEBERT_MEMORY_MODE=hybrid`.
- **Service:** *(local `.cuebert/memory/memory.db` — no remote service for milestones or text-mode search)*
- **Triggers:** memory, milestone handoff, troubleshooting, harness loop, deferred items, hybrid search
- **Version:** 1.0 (cuebert)

## Operations

| Operation | MCP Tool | Parameters | Returns |
|-----------|----------|------------|---------|
| Save milestone | `milestone_commit` | `plan_slug`, `milestone`, `phase`, optional JSON/text fields | `{status, id}` |
| Load milestones | `milestone_lookup` | `plan_slug`, optional `milestone`, `include_bridge` | `{status, data: {sessions, bridge?}}` |
| Save troubleshooting | `troubleshoot_commit` | `problem`, `what_tried`, optional context fields | `{status, id}` |
| Search troubleshooting | `troubleshoot_search` | `query`, optional `project`, `tags`, `limit` | `{status, data: {results, count}}` |
| Benchmark memory quality | `memory_eval` | optional `clean` (default true: seed, run, wipe eval rows) | `{status, milestone_precision, troubleshooting_recall?, weights, clean}` |

## Prerequisites

- Cuebert repo root discoverable via a parent `.cuebert/` directory from the toolkit path.
- **`CUEBERT_MEMORY_MODE=text` (default):** no embedding configuration; `troubleshoot_commit` / `troubleshoot_search` use FTS5/BM25 only (embeddings stored as NULL until you switch modes).
- **`CUEBERT_MEMORY_MODE=hybrid`:** `OPENAI_API_KEY` (or vault) required for embedding calls (`troubleshoot_commit`, `troubleshoot_search`, troubleshooting portion of `memory_eval`, and transcript backfill paths that compute embeddings).
- SQLite with FTS5 enabled (standard in modern Python builds).

## Memory modes (I-3)

- **`text`:** `generate_embedding` is a no-op (returns `NULL` on commit); search ranks by FTS5/BM25 only (`vector_score` is zero in merged scoring). Same DB schema as hybrid; rows without embeddings participate in FTS ranking only.
- **`hybrid`:** Full vector + BM25 merge (0.6 vector + 0.4 FTS) when embeddings are present.

## Workflow

1. **Milestone handoff:** agents call `milestone_commit` with structured JSON strings for files, deferrals, decisions, and errors.
2. **Orchestrator context:** call `milestone_lookup` with `plan_slug`; omit `milestone` to load the full plan timeline and aggregated bridge fields.
3. **Debugging recall:** after resolving an issue, call `troubleshoot_commit` with the full attempt list (`what_tried`) and reasoning.
4. **Fuzzy lookup:** before retry loops, call `troubleshoot_search` with a natural-language query; in hybrid mode with embeddings, results blend vector similarity (0.6) with FTS5 BM25 (0.4). In text mode, ranking is FTS5/BM25 only.

## Error Handling

All tools return `{status: "error", error: "<message>"}` on failure; they do not raise to MCP clients.

## Reference Files

- `reference.md` — Field shapes, bridge aggregation, memory modes, and score notes.
- `tools/_memory_db.py` — Schema, triggers, embeddings, and hybrid search helpers.
