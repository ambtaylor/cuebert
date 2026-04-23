---
description: "Ship Package — stage and package phase for /ship after cook"
---

# Ship Package Slim

**First action:** Read `docs/_ai_system/agents/agent-ship-package.md` completely, then follow its protocol.

## Inputs (from /ship harness envelope)

| Field | Description |
|-------|-------------|
| PROJECT_PATH | Absolute path to the game project |
| TARGET_PLATFORM | Build target platform |
| TARGET_STORE | Distribution target identifier |
| BUILD_CONFIG | Debug, Development, Shipping, etc. |
| CALLER | Harness or task identifier |

## Output contract

Return structured result per `docs/_ai_system/standards/agent-shared-lifecycle.md` section 12:

```
=== SUBAGENT RESULT ===
Phase: ship-package
Status: success | fail | error
Summary: [1-2 sentence description]
Files Changed: [list]
Build Verification: [pass | fail | skipped]
Handoff Payload:
  PACKAGE_ENVELOPE: [stage + package; skip_cook=true]
  STAGED_PATHS: [list]
  PACKAGE_PATH: [primary output path]
  WARNINGS: [list]
===========================
```

## Orchestrated Envelope Fields

When dispatched from the `/ship` harness coordinator, this subagent receives:

| Field | Source | Required |
|-------|--------|----------|
| PROJECT_PATH | Harness project resolution | Yes |
| TARGET_PLATFORM | Ship plan or harness config | Yes |
| TARGET_STORE | Ship plan or harness config | Yes |
| BUILD_CONFIG | Ship plan (default: Shipping) | Yes |
| CALLER | Harness identifier | Yes |
| PRIOR_PHASE | Cook phase summary (cook envelope) | Yes |
| COOK_OUTPUT_PATHS | Cook phase handoff payload | Yes |

## Constraints

- Delegate to agent-cook-package-game rule engine with skip_cook=true
- Do NOT re-run cook unless harness explicitly requests recovery
- Do NOT invoke UAT outside the delegated rule engine path
