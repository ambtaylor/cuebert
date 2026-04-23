---
description: "Play QA — lightweight QA on preview artifacts after /play preview"
---

# Play QA Slim

**First action:** Read `docs/_ai_system/agents/agent-play-qa.md` completely, then follow its protocol.

## Inputs (from /play harness envelope)

| Field | Description |
|-------|-------------|
| PREVIEW_ARTIFACTS | Paths and metadata from preview phase |
| GUARD_REPORT | Structured preview guard results |
| APP_REPO | Absolute path to the game project |
| ENGINE | unreal, unity, or godot |

## Output contract

Return structured result per `docs/_ai_system/standards/agent-shared-lifecycle.md` section 12:

```
=== SUBAGENT RESULT ===
Phase: play-qa
Status: success | fail | error
Summary: [1-2 sentence description]
Files Changed: [list]
Build Verification: [pass | fail | skipped]
Handoff Payload:
  LOG_SCAN_SUMMARY: [findings]
  VISUAL_DIFF_SUMMARY: [findings]
  RECOMMENDATION: merge | retry_author | escalate
  NOTES: [list]
===========================
```

## Orchestrated Envelope Fields

When dispatched from the `/play` harness coordinator, this subagent receives:

| Field | Source | Required |
|-------|--------|----------|
| PREVIEW_ARTIFACTS | Preview phase handoff payload | Yes |
| GUARD_REPORT | Preview phase guard results | Yes |
| APP_REPO | Harness project resolution | Yes |
| ENGINE | Harness engine detection | Yes |
| PRIOR_PHASE | Preview phase summary | Yes |
| CHANGE_LIST | Plan phase output (for scope verification) | Optional |

## Constraints

- Use vision-qa MCP tools for image comparison when applicable
- Use qa-resilience-game MCP tools when available
- Lightweight checks only; full Gauntlet remains /ship territory
- Do not block merge without documenting rationale in RECOMMENDATION
