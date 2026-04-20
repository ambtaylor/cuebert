# Memory Toolkit — Agent Quick Reference

## Memory mode

| `CUEBERT_MEMORY_MODE` | Behavior |
|-----------------------|----------|
| `text` (default) | No embedding HTTP calls. Commits store `embedding=NULL`. Search is FTS5/BM25 only (`hybrid_search` with `query_embedding=None`). |
| `hybrid` | Embeddings computed on commit/search; vector + FTS merge when stored embeddings exist. |

Schema is unchanged between modes (`embedding BLOB` nullable). A DB created in `text` can later use `hybrid` without migration; new commits populate embeddings.

## When to use which tool

| Situation | Tool | Notes |
|-----------|------|-------|
| End of a harness milestone | `milestone_commit` | Upserts on `(plan_slug, milestone, phase)` |
| Start next milestone / need carry-over | `milestone_lookup` | Full plan loads `bridge` by default |
| Captured a fix worth reusing | `troubleshoot_commit` | In hybrid mode, builds embedding from problem + attempts + resolution; text mode skips embedding |
| Investigating a recurring failure | `troubleshoot_search` | Keyword + optional vector (hybrid only) |
| Validating recall / regression on memory search | `memory_eval` | Milestone checks always; troubleshooting recall needs `hybrid` + API key |

## `milestone_commit` inputs

- Required: `plan_slug`, `milestone`, `phase`
- JSON strings: `files_touched` (array), `deferred_items` (array of objects), `decisions` (array of objects), `errors_encountered` (array)
- Optional labels: `status`, `summary`, `project`, `language`, `agent`

Returns `{ "status": "ok", "id": "<uuid>" }`.

## `milestone_lookup` outputs

- `data.sessions`: rows from `milestones` (dict per row)
- `data.bridge` (optional): aggregated `deferred_items`, `decisions`, and de-duplicated `files_touched` with source milestone metadata

## `troubleshoot_commit` inputs

- Required: `problem`, `what_tried` (JSON array or string of `[{ "approach", "outcome" }]`)
- Optional: `why_tried`, `what_worked`, `tags`, `errors`, `files_touched`, traceability fields, `source` (`agent` default)

## `troubleshoot_search` outputs

- `data.results[]` includes `hybrid_score`, `vector_score`, `fts_score`, `fts_bm25`, and text fields (`what_tried` parsed to JSON when valid). In `text` mode, vector scores are zero and ranking follows FTS/BM25 only.
