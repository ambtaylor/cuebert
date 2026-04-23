---
description: "Asset Place — imports and places generated assets into the project tree"
---

# Asset Place Slim

**First action:** Read `docs/_ai_system/agents/agent-asset-place.md` completely, then follow its protocol.

## Inputs (from /asset harness envelope)

| Field | Description |
|-------|-------------|
| APP_REPO | Absolute path to the game project |
| GENERATED_ASSETS | Paths from asset-generate phase |
| MANIFEST_PATH | `.cuebert-assets.yaml` or workspace-manifest path |

## Output contract

Return structured result per `docs/_ai_system/standards/agent-shared-lifecycle.md` section 12:

```
=== SUBAGENT RESULT ===
Phase: asset-place
Status: success | fail | error
Summary: [1-2 sentence description]
Files Changed: [list]
Build Verification: [pass | fail | skipped]
Handoff Payload:
  PLACED_PATHS: [list]
  IMPORT_STATUS: [per asset]
  UNREAL_REIMPORT: [calls made via unreal-bridge if applicable]
  GUARD_VIOLATIONS: [list if any]
===========================
```

## Orchestrated Envelope Fields

When dispatched from the `/asset` harness coordinator, this subagent receives:

| Field | Source | Required |
|-------|--------|----------|
| APP_REPO | Harness project resolution | Yes |
| GENERATED_ASSETS | Generate phase handoff payload | Yes |
| MANIFEST_PATH | Harness manifest resolution | Yes |
| PRIOR_PHASE | Generate phase summary | Yes |
| GENERATION_PLAN | Plan phase handoff (for destination mapping) | Optional |

## Constraints

- Write files into project Content/ tree (or engine-equivalent) per manifest
- For Unreal, perform re-import via unreal-bridge MCP tools when required
- Validate against asset pipeline guards before reporting success
