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
  AUTHOR_FILES: [list of modified paths]
  COMPILE_STATUS: [pass | fail | not_checked]
  WARNINGS: [list]
===========================
```

## Orchestrated Envelope Fields

When dispatched from the `/play` harness coordinator (`agent-play.md`), this subagent receives:

| Field | Source | Required |
|-------|--------|----------|
| APP_REPO | Harness project resolution | Yes |
| BRANCH | Harness git detection | Yes |
| ENGINE | Harness engine detection | Yes |
| CHANGE_LIST | Plan phase output | Yes |
| DECLARED_SCOPE | Plan phase output | Yes |
| FORBIDDEN_PATHS | Computed from scope | Yes |
| PRIOR_PHASE | Plan phase summary | Yes |

## Constraints

- Edit ONLY files within DECLARED_SCOPE
- Do NOT launch the editor or PIE
- Do NOT push to remote
- For Unreal projects, use unreal-bridge MCP tools (cuebert-engine group) for property queries when needed
