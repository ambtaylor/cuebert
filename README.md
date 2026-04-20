# Cuebert

> A minimal fork of the [Cue](https://github.com/ambtaylor/cue) harness, skills, vault, and onboarding architecture, tailored for **gaming development** (Unreal Engine 5 first).

## Status

**Bootstrap in progress.** This repository is being populated milestone-by-milestone from the authoritative plan at `docs/projects/cue/plans/active/cuebert-gaming-system.md` (in the parent `cue` workspace).

## Quick start

```bash
git clone https://github.com/ambtaylor/cuebert.git
cd cuebert
# Subsequent milestones will add: .cuebert/ hub marker, MCP servers, skills, vault, and the /play + /ship harnesses.
```

## Memory: text-only by default

Cuebert's memory toolkit ships with **`CUEBERT_MEMORY_MODE=text`** as the default. This means:

- `troubleshoot_commit`, `milestone_commit`, etc. work immediately with **no embedding model required**.
- Ranking uses SQLite FTS5/BM25 (full-text search) only.
- The `embedding` column is nullable; rows are written with `embedding=NULL` in text mode.
- **Opt-in upgrade:** set `CUEBERT_MEMORY_MODE=hybrid` and configure an OpenAI-compatible embeddings endpoint in the vault to enable vector ranking. No DB migration required — old rows continue ranking via FTS, new rows get embeddings.

This makes cuebert usable out of the box for contributors without access to an embeddings provider.

## License

TBD.

## Roadmap (8 milestones)

| # | Milestone | Status |
|---|---|---|
| M1 | Skeleton & supervisor | in progress |
| M2 | `/play` harness | pending |
| M3 | `/ship` harness | pending |
| M4 | ComfyUI + asset agent | pending |
| M5 | Unreal bridge + UE C++ | pending |
| M6 | Build + Gauntlet + vision QA | pending |
| M7 | QA resilience + gaming PR | pending |
| M8 | Cook + cert | pending |

See the authoritative plan for phase-level breakdown.
