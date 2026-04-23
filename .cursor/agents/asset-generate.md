---
description: "Asset Generate — runs ComfyUI generation per plan for /asset"
---

# Asset Generate Slim

**First action:** Read `docs/_ai_system/agents/agent-asset-generate.md` completely, then follow its protocol.

## Inputs (from /asset harness envelope)

| Field | Description |
|-------|-------------|
| APP_REPO | Absolute path to the game project |
| GENERATION_PLAN | Plan object from asset-plan phase |
| ARTIFACT_DIR | Writable directory for generation outputs |

## Output contract

Return structured result per `docs/_ai_system/standards/agent-shared-lifecycle.md` section 12:

```
=== SUBAGENT RESULT ===
Phase: asset-generate
Status: success | fail | error
Summary: [1-2 sentence description]
Files Changed: [list]
Build Verification: [pass | fail | skipped]
Handoff Payload:
  GENERATED_IMAGE_PATHS: [list]
  COMFYUI_JOB_STATUS: [per asset id]
  FAILED_ROWS: [list]
  ARTIFACT_DIR: [resolved path]
===========================
```

## Orchestrated Envelope Fields

When dispatched from the `/asset` harness coordinator, this subagent receives:

| Field | Source | Required |
|-------|--------|----------|
| APP_REPO | Harness project resolution | Yes |
| GENERATION_PLAN | Asset-plan phase handoff payload | Yes |
| ARTIFACT_DIR | Harness artifact path generation | Yes |
| PRIOR_PHASE | Plan phase summary | Yes |

## Constraints

- Use comfyui-toolkit MCP tools for queue and status
- Default to dry-run unless harness explicit opt-in for live jobs
- Write outputs only under ARTIFACT_DIR until asset-place confirms placement
