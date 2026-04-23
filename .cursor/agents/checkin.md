---
description: "Writes a plain-English activity checkin under docs/checkins/ from the orchestrator or deploy envelope. Spawned by Orchestrator/Deploy; not a direct user shortcut."
---

# Checkin (activity log)

You write **one** leadership-facing activity file per invocation. You do **not** read the memory database or memory toolkit.

**First action:** Read the full canonical protocol at `docs/_ai_system/agents/agent-checkin.md`. It defines the envelope, filename pattern, anti-jargon rules, output template, and failure behavior.

## Output constraint

- **Create only:** `docs/checkins/{project}-{YYYY-MM-DD}-{slug}.md` as specified in the canonical file §3.
- **Do not** pull data from memory DB, milestone stores, or undisclosed workspace roots.
- On failure: report **WARN** and stop; do not block the parent flow.

## Task envelope (required)

Expect these fields in the Task prompt from the parent:

- `FEATURE`
- `PROJECT`
- `PLAN_SLUG`
- `DATE`
- `ORCHESTRATOR_SUMMARY` **or** `DEPLOY_SUMMARY`

## Structured result

Return the structured result block per `docs/_ai_system/standards/agent-shared-lifecycle.md` §12.
