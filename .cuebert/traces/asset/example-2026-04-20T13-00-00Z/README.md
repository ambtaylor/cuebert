# Illustrative `/asset` trace (documentation only)

This directory is a **curated, committed example** of what a Cuebert **`/asset`** harness dry run would materialize under `.cuebert/traces/asset/<timestamp>/` after coordinator wiring (**M4-P4** narrative) and future **M5–M6** evaluators.

**No live ComfyUI HTTP** was performed for this fixture. **No real GPU work.** Envelopes match [`docs/_ai_system/agents/agent-asset-plan.md`](../../../../docs/_ai_system/agents/agent-asset-plan.md), [`agent-asset-generate.md`](../../../../docs/_ai_system/agents/agent-asset-generate.md), and [`agent-asset-place.md`](../../../../docs/_ai_system/agents/agent-asset-place.md).

## Where to read the narrative

End-to-end dry run (four gate classes, eight guards, envelopes, failure variants):  
[`docs/_ai_system/examples/asset-sample-run-hello-level.md`](../../../../docs/_ai_system/examples/asset-sample-run-hello-level.md)

## How this relates to the spec

- Guard ids and ordering: [`docs/_ai_system/standards/asset-pipeline-guards.md`](../../../../docs/_ai_system/standards/asset-pipeline-guards.md) and [`.cuebert/config/asset-guards.yaml`](../../../config/asset-guards.yaml)
- Parent coordinator: [`docs/_ai_system/agents/agent-asset.md`](../../../../docs/_ai_system/agents/agent-asset.md)

## Files in this example

| Path | Role |
|------|------|
| `envelope.json` | Coordinator rollup after memory commit |
| `guards/pre_plan.json` | Pre-plan guards (`guard.project.exists`, `guard.manifest.valid`) |
| `guards/post_plan.json` | Post-plan guards (`guard.plan.non_empty`, `guard.plan.workflow_available`) |
| `guards/post_generate.json` | Post-generate guards, two rows per asset (six total) |
| `guards/post_place.json` | Post-place guards, two rows per asset (six total) |
| `plan/envelope.json` | `agent-asset-plan` output |
| `generate/*.json` | Per-asset generate envelopes (dry-run synthetic) |
| `place/*.json` | Per-asset placement envelopes |
| `lockfile_after.yaml` | Illustrative `.cuebert-assets.lock.yaml` after success |
| `memory/envelope.json` | `milestone_commit` return envelope |

## Git policy

Runtime traces under `.cuebert/traces/` are normally **ignored**. Paths matching `asset/example-*/` are **negated** in `.gitignore` so this reference layout ships with the hub.
