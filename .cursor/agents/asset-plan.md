---
description: "Asset Plan — builds generation plan for /asset from manifest and scope"
---

# Asset Plan Slim

**First action:** Read `docs/_ai_system/agents/agent-asset-plan.md` completely, then follow its protocol.

## Inputs (from /asset harness envelope)

| Field | Description |
|-------|-------------|
| APP_REPO | Absolute path to the game project |
| MANIFEST_PATH | `.cuebert-assets.yaml` or workspace-manifest path |
| SCOPE | Which assets to regenerate (ids, globs, or tags) |

## Output contract

Return structured result per `docs/_ai_system/standards/agent-shared-lifecycle.md` section 12:

```
=== SUBAGENT RESULT ===
Phase: asset-plan
Status: success
Summary: [one-line outcome]

Files Changed:
- [path] ([note]) | none

Tests:
- Passed: [n]
- Failed: [n]
- Skipped: [n]

Build Verification:
- [check]: [pass | fail | skipped | N/A] — [evidence pointer or short excerpt]

Plan Updated: [yes | no]
Handoff Payload:
  GENERATION_PLAN: [rows to process]
  WORKFLOW_SELECTIONS: [per row or group]
  SEED_VALUES: [per row or group]
  EXCLUDED: [list with reasons]
===========================
```

## Orchestrated Envelope Fields

When dispatched from the `/asset` harness coordinator (`agent-asset.md`), this subagent receives:

| Field | Source | Required |
|-------|--------|----------|
| APP_REPO | Harness project resolution | Yes |
| MANIFEST_PATH | Harness manifest resolution | Yes |
| SCOPE | User flag or full manifest | Yes |

## Constraints

- Respect MANIFEST_PATH as source of truth for asset definitions
- Do not run ComfyUI or write generated binaries in plan phase
- Narrow SCOPE before handing off to asset-generate
