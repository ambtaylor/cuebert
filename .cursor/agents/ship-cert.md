---
description: "Ship Cert — advisory certification checks for /ship (INFO/WARN only)"
---

# Ship Cert Slim

**First action:** Read `docs/_ai_system/agents/agent-ship-cert.md` completely, then follow its protocol.

## Inputs (from /ship harness envelope)

| Field | Description |
|-------|-------------|
| BUILD_PATH | Path to built package or staging root |
| TARGET_PLATFORM | Build target platform |
| TARGET_STORE | Distribution target identifier |
| BUILD_CONFIG | Debug, Development, Shipping, etc. |

## Output contract

Return structured result per `docs/_ai_system/standards/agent-shared-lifecycle.md` section 12:

```
=== SUBAGENT RESULT ===
Phase: ship-cert
Status: success | fail | error
Summary: [1-2 sentence description]
Files Changed: [list]
Build Verification: [pass | fail | skipped]
Handoff Payload:
  CERT_ENVELOPE: [cert-game advisory; severity INFO | WARN only]
  FINDINGS: [list]
  NEVER_REJECT: true
===========================
```

## Constraints

- Advisory only: findings are INFO or WARN; never REJECT or halt ship
- Surface all findings in CERT_ENVELOPE for human review
- Do not mutate build outputs except where protocol requires logging artifacts
