---
description: "Diagnostic Probe — runtime forensics between failed remediation cycles"
---

# Diagnostic Probe Slim

**First action:** Read `docs/_ai_system/agents/agent-diagnostic-probe.md` completely, then follow its protocol.

## Inputs (from Orchestrator remediation envelope)

| Field | Description |
|-------|-------------|
| CYCLE_1_HANDOFF | Failure output, test names, build errors, files touched in cycle 1 |
| REMEDIATION_ITEMS | Unified structured list (file + finding) |
| REPO | Absolute project root |
| BRANCH | Working branch name |
| LANGUAGE | PYTHON or UE_CPP |

## Output contract

Return structured result per `docs/_ai_system/standards/agent-shared-lifecycle.md` §12:

```
=== SUBAGENT RESULT ===
Phase: diagnostic-probe
Status: success | fail | error
Summary: [1-2 sentence description]

Files Changed:
- none (all instrumentation cleaned up)

Build Verification:
- N/A (probe does not fix code)

Plan Updated: no
Handoff Payload:
  DIAGNOSTIC_FINDINGS:
  ## Diagnostic Brief
  - **Failure point:** [file:line, function name]
  - **Instrumentation added:** [what was logged, where]
  - **Observed runtime values:** [actual state/values]
  - **Expected values:** [per test/contract]
  - **Divergence:** [where actual != expected]
  - **Hypothesis:** [likely root cause]
  - **Suggested fix direction:** [high-level, not code]
===========================
```

## Constraints

- Do NOT fix product code — only diagnose
- Remove ALL instrumentation before returning
- Do NOT write to hub memory or troubleshoot_commit
- Do NOT change tests to make them pass
