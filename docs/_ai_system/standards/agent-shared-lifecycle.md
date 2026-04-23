# Agent Shared Lifecycle

Cross-agent behaviors for Cuebert **orchestrated** (`/o`) and **direct** (`/spec`, `/code`, `/review`) hub engineering. Language- and phase-specific agents extend this document; they do not replace it.

---

## §1 — MCP Structured Reasoning Gate

Every `/spec`, `/code`, `/review`, and `/sec` activation **must** begin with a `sequentialthinking` MCP call **before** any file read, edit, or substantive analysis.

**Normative source:** `.cursor/rules/cuebert-engineering.mdc` §0 (Structured Reasoning Gate).

This section is a **pointer only**: it covers decomposition, hard stop on MCP failure, supervisor pre-dispatch probe, and the retry circuit breaker. Do not duplicate the full text here.

---

## §2 — Context Handoff Protocol

**The plan is the single source of truth** for cross-phase context. Agents **write** status, findings, and discovered work **into** the active plan. Receiving agents **read** the plan and the Verification Contract — not chat paraphrase alone.

### Thin Handoff (direct mode)

When the user advances phases manually (separate chats), output **only** this block. Do **not** wait for inline confirmation to "continue."

```
=== HANDOFF ===
PLAN: [path to plan file]
PHASE: [Spec | Code | Review | …] complete.
NEXT: [next agent role] — read Verification Contract in plan, execute commands, write results.
===============
```

**Orchestrated mode (`/o`):** Phase subagents return **`=== SUBAGENT RESULT ===`** (§12). The Thin Handoff is for direct mode or explicit human checkpoints (e.g. `--pause`), not for normal `/o` chaining.

---

## §3 — Build Verification Gate

**Normative source:** `.cursor/rules/cuebert-engineering.mdc` §3 (Build Verification Gate), including the full check table for hub Python work and gaming checks.

**Handoff rules:**

- Include **actual command or tool output**, not self-assessed claims ("tests pass").
- **Missing report** for a required check ⇒ **REJECT** at Review unless the contract marks that check **N/A**.

---

## §8 — Plan Auto-Completion Protocol

Before producing **any** handoff (Thin Handoff or §12 block), agents **must** update the **active plan file**:

1. **Read** the plan referenced in the handoff envelope or `PLAN:` field.
2. **Mark** completed todos/tasks as done (checkmarks, `completed`, or the plan's native convention).
3. **Append** newly discovered tasks in the appropriate section, preserving dependency order.
4. **Save** the plan.

**Handoffs without plan updates are protocol violations** when a plan exists and was in scope for the session.

### Role expectations (summary)

| Role | Typical updates |
|------|-----------------|
| Spec | Mark plan scaffolding / spec tasks done; adjust scope todos if the spec changed |
| Code | Mark implemented tasks or increments done; append discovered follow-ups |
| Review | Mark review passes done; append remediation items tied to the Verification Contract |
| Test / Security | Mark scan or codification tasks done; append new tasks if findings require work |

### What "append discovered tasks" means

New work found during execution (dependencies, regressions, follow-up refactors) must appear **in the plan**, not only in chat or in the §12 `Handoff Payload`. Payloads are for Orchestrator consumption; the plan remains the durable record.

---

## §12 — Subagent Interface Contract

Phase subagents invoked by the Orchestrator return a **structured result** the Orchestrator can parse and aggregate. **Subagents must not ask the user to confirm or approve the next phase** — emit the block and **stop**. (User checkpoints are driven by `--pause` or Orchestrator policy, not by subagent prompts.)

### Success block

```
=== SUBAGENT RESULT ===
Phase: [spec | code | review | qa | qa-resilience | play-author | play-preview | play-qa | ship-cook | ship-cert | ship-package | diagnostic-probe | …]
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
[Phase-specific structured content for the Orchestrator — e.g. milestones, register deltas]
===========================
```

Phase-specific agents may **add** fields inside `Handoff Payload` when documented in those agents.

### Required vs optional lines

**Required:** opening/closing fences, `Phase`, `Status`, `Summary`, `Plan Updated`, and a `Handoff Payload` section (use `none` or `N/A` only when truly empty). **Files Changed**, **Tests**, and **Build Verification** must be present; use `none` / `0` / `skipped` / `N/A` explicitly rather than omitting sections.

**Verification Contract:** When the plan defines a Verification Contract, Code and Review evidence belongs in the plan's **Result** columns and registers; the §12 block summarizes and points to those artifacts.

### Error block

On blocking failure (Orchestrator must not chain forward):

```
=== SUBAGENT ERROR ===
Phase: [phase name]
Status: failed
Error: [concise blocker]
Attempted: [what was tried]
Suggested fix: [concrete next step]
Plan Updated: [yes | no]
===========================
```

### Plan write-back

Structured output does **not** replace §8. The plan file must reflect completed work and new tasks before handoff completes, unless no plan applies to the task (state why in `Summary`).

### Direct mode

When not under the Orchestrator, prefer the **Thin Handoff** (§2) for copy-paste between chats; §8 still applies whenever there is an active plan.

---

## Related pointers

| Topic | Where defined |
|-------|----------------|
| Orchestrator aggregation, remediation | `docs/_ai_system/agents/agent-orchestrator.md` |
| Gaming harness lifecycle | `agent-play.md`, `agent-ship.md`, `agent-asset.md` |
| Build verification gate | `.cursor/rules/cuebert-engineering.mdc` |
| Vault standard | `docs/_ai_system/standards/vault-standard.md` |

### Extended lifecycle topics (not duplicated here)

The following are referenced by other agents and live in their primary standards: **Plan Auto-Completion** (§8 above and engineering workflow), **Troubleshooting commit/search** (`cuebert-engineering.mdc` §5D–§5E), **milestone lookup/commit** (`cuebert-engineering.mdc` §5F–§5G). This file defines shared handoff and §12 contracts only; add new cross-cutting rules here when they stabilize.
