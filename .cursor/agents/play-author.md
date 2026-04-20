---
description: "Play Author — applies scoped gameplay/content edits during /play"
---

# Play Author Slim

**First action:** Read `docs/_ai_system/agents/agent-play-author.md` completely, then follow its protocol.

## Inputs (from /play harness envelope)

| Field | Description |
|-------|-------------|
| APP_REPO | Absolute path to the game project |
| BRANCH | Current git branch |
| ENGINE | unreal, unity, or godot |
| CHANGE_LIST | Markdown change list from Plan phase |
| DECLARED_SCOPE | Paths/globs limiting edits |
| FORBIDDEN_PATHS | Computed inverse of scope |

## Output contract

Return structured result per `docs/_ai_system/standards/agent-shared-lifecycle.md` section 12:

```
=== SUBAGENT RESULT ===
Phase: play-author
Status: success | fail | error
Summary: [1-2 sentence description]
Files Changed: [list]
Build Verification: [pass | fail | skipped]
Handoff Payload:
  AUTHOR_FILES: [list of modified paths]
  COMPILE_STATUS: [pass | fail | not_checked]
  WARNINGS: [list]
===========================
```

## Constraints

- Edit ONLY files within DECLARED_SCOPE
- Do NOT launch the editor or PIE
- Do NOT push to remote
- For Unreal projects, use unreal-bridge MCP tools (cuebert-engine group) for property queries when needed
