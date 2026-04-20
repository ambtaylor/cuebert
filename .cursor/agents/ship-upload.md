---
description: "Ship Upload — store upload subagent for /ship (dry-run by default)"
---

# Ship Upload Slim

**First action:** Read `docs/_ai_system/agents/agent-ship-upload.md` completely, then follow its protocol.

## Inputs (from /ship harness envelope)

| Field | Description |
|-------|-------------|
| PACKAGE_PATH | Path to package artifact for upload |
| UPLOAD_CHANNEL | itch.io, steam, custom, or none |
| CREDENTIALS_PATH | Vault-backed credentials reference |

## Output contract

Return structured result per `docs/_ai_system/standards/agent-shared-lifecycle.md` section 12:

```
=== SUBAGENT RESULT ===
Phase: ship-upload
Status: success | fail | error
Summary: [1-2 sentence description]
Files Changed: [list]
Build Verification: [pass | fail | skipped]
Handoff Payload:
  UPLOAD_STATUS: success | skipped_dry_run | fail
  CHANNEL: [resolved channel]
  ARTIFACT_REF: [store-specific ref if any]
  NOTES: [list]
===========================
```

## Constraints

- Disabled by default: use dry-run unless harness explicit opt-in
- Load secrets only via vault; never echo credentials
- Do not upload when UPLOAD_CHANNEL is none without harness confirmation
