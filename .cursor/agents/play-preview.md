---
description: "Play Preview — runs preview/PIE and captures artifacts after /play author phase"
---

# Play Preview Slim

**First action:** Read `docs/_ai_system/agents/agent-play-preview.md` completely, then follow its protocol.

## Inputs (from /play harness envelope)

| Field | Description |
|-------|-------------|
| APP_REPO | Absolute path to the game project |
| ENGINE | unreal, unity, or godot |
| ENGINE_VERSION | Engine version string for tooling |
| ARTIFACT_DIR | `.cuebert/traces/play/<timestamp>/preview/` |
| AUTHOR_FILES | Modified paths from author phase |

## Output contract

Return structured result per `docs/_ai_system/standards/agent-shared-lifecycle.md` section 12:

```
=== SUBAGENT RESULT ===
Phase: play-preview
Status: success | fail | error
Summary: [1-2 sentence description]
Files Changed: [list if any]
Build Verification: [pass | fail | skipped]
Handoff Payload:
  SCREENSHOT_PATHS: [list]
  LOG_EXCERPTS: [paths or inline excerpts]
  PIE_SESSION_INFO: [session summary]
  PREVIEW_GUARDS: [PASS | FAIL per guard]
===========================
```

## Constraints

- Use unreal-bridge MCP tools to launch PIE when ENGINE is unreal
- Capture screenshots via vision-qa MCP tools when available
- Write artifacts only under ARTIFACT_DIR
- Do NOT modify source outside preview capture scope without harness direction
