---
description: "Ship Cook — cook-only phase for /ship (delegates to cook-package rule engine)"
---

# Ship Cook Slim

**First action:** Read `docs/_ai_system/agents/agent-ship-cook.md` completely, then follow its protocol.

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
Phase: ship-cook
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
  COOK_ENVELOPE: [agent-cook-package-game cook phase; skip_package=true]
  OUTPUT_PATHS: [list]
  WARNINGS: [list]
===========================
```

## Orchestrated Envelope Fields

When dispatched from the `/ship` harness coordinator (`agent-ship.md`), this subagent receives:

| Field | Source | Required |
|-------|--------|----------|
| PROJECT_PATH | Harness project resolution | Yes |
| TARGET_PLATFORM | Ship plan or harness config | Yes |
| TARGET_STORE | Ship plan or harness config | Yes |
| BUILD_CONFIG | Ship plan (default: Shipping) | Yes |
| CALLER | Harness identifier | Yes |
| PRIOR_PHASE | Pre-cook gate summary (prod-readiness result) | Yes |

## Constraints

- Delegate to cook-package-game rule engine; do not bypass it
- Do NOT invoke UAT or platform packaging directly
- Cook only; packaging is ship-package subagent
