# DEPLOY HARNESS AGENT — Deployment Lifecycle Manager

> **Role:** Deployment readiness coordinator for the **Cuebert hub** (agents, rules, MCP tools, standards — not gaming `/ship`).
> **Activation:** Supervisor loads this agent's rules into the main chat on `/deploy` (alias `/d`)
> **Execution context:** Main chat (NOT a subagent). Same pattern as the Orchestrator (`agent-orchestrator.md`).
> **Relationship to `/o`:** The Deploy Harness is a **separate pipeline** from the Engineering Orchestrator. It is invoked explicitly when the user decides to prepare hub work for deployment. The Production Readiness Register (accumulated during `/o` runs as INFO-level findings) is the bridge between the two harnesses.
> **Relationship to `/ship`:** Gaming distribution uses **`agent-prod-readiness-game`** and **`docs/_ai_system/standards/prod-readiness-game-rules.md`** (pre-cook guards). This harness does **not** replace `/ship` or the gaming prod-readiness rule engine.

---

## 1. Activation and Scope

### When the Deploy Harness is Loaded

The Supervisor loads this agent's rules into the **main chat context** when it detects:
- `/deploy` or `/d`, with optional modifiers

The Deploy Harness is NOT spawned as a subagent. It runs in the main chat and spawns each phase as a direct Task subagent.

### When the Deploy Harness is NOT Loaded

All other commands (`/o`, `/spec`, `/code`, `/review`, `/sec`, `/test`, `/ship`, `/play`, etc.) use their own routing. The Deploy Harness only activates on `/d` or `/deploy`.

---

## 2. Phase Chain

The Deploy Harness runs **core phases 1–3**, then a **Checkin Log** phase (documentation-only, same model as `agent-orchestrator.md` §6A):

```
START → Production Readiness (REJECT mode) → Security → Memory Commit → Checkin Log → COMPLETION

STOP CONDITIONS:
(1) All phases complete (Checkin Log failure does not roll back deploy readiness — see §2 Checkin row)
(2) Production Readiness or Security returns REJECT-severity findings → STOP, report, suggest remediation
(3) --pause explicitly passed → checkpoint between phases
(4) --preview → preview only, no execution (see §7)
```

### Phase Descriptions

| # | Phase | Agent / Tool | Purpose | Gate |
|---|-------|-------------|---------|------|
| 1 | **Production Readiness** | `generalPurpose` → `.cursor/agents/prod-readiness.md` (canonical: `docs/_ai_system/agents/agent-production-readiness.md`) | Scan hub source and config for dev artifacts, debug flags, TODO markers, mock URLs, etc. Runs in **REJECT mode** — findings that were INFO during `/o` become blocking here. | REJECT on any finding |
| 2 | **Security** | `generalPurpose` → `.cursor/agents/security-auditor.md` | SAST, SCA, pattern scanning. Same as `/sec` but run as a deploy gate. | REJECT on Critical/High |
| 3 | **Memory Commit** | `milestone_commit` + `troubleshoot_commit` via **cuebert-core** MCP | Persist milestone and troubleshooting records to memory. Skipped with `--skip-memory`. | WARN only (non-blocking) |
| 4 | **Checkin Log** | `generalPurpose` → `.cursor/agents/checkin.md` (canonical: `docs/_ai_system/agents/agent-checkin.md`) | After **Memory Commit** (phase 3) completes, write one plain-English activity file under `docs/checkins/` from the deploy envelope. Runs **before** the Deploy Harness Summary (§6) and COMPLETION. Does **not** read the memory DB. | **WARN** on failure (non-blocking — deploy flow already complete) |

### Auto-Chain (Default)

The Deploy Harness auto-chains through all phases including Checkin Log by default. `--pause` inserts a checkpoint after each phase for user inspection.

---

## 3. Modifiers

| Modifier | Effect |
|----------|--------|
| `--pause` | Stop after each phase for user inspection |
| `--skip-memory` | Skip the Memory Commit phase (phase 3) |
| `--preview` | Preview the pipeline without executing (see §7) |

---

## 4. Subagent Spawning

Same protocol as `agent-orchestrator.md` §3: all phase subagents use `subagent_type: "generalPurpose"` with a slim Task envelope.

### Phase 1 — Production Readiness (REJECT) spawn

The Deploy Harness **MUST** spawn Production Readiness as a real Task (not a placeholder):

```
Task(
  subagent_type: "generalPurpose",
  description: "Deploy — Production Readiness (REJECT)",
  prompt: |
    ## Cuebert Deploy Harness Task
    **First action:** Read `.cursor/agents/prod-readiness.md` completely. Follow its instructions.

    You are executing Production Readiness as part of the Cuebert Deploy Harness (`/d`).

    ## Task envelope
    REPO: [absolute path]
    BRANCH: [git branch]
    PROJECT: [project name]
    LANGUAGE: [PYTHON | CUEBERT | UE_CPP]
    PLAN: [path to plan file]
    MODE: REJECT
    PHASE: deploy-production-readiness
    PRIOR PHASE: N/A
```

Canonical protocol and scan categories: `docs/_ai_system/agents/agent-production-readiness.md`.

### Checkin Log spawn (after Memory Commit, before §6 summary)

After **Memory Commit** (phase 3) completes, the Deploy Harness **SHOULD** spawn the **Checkin** subagent so a leadership-facing activity file can be written. **Do not** wait for the Deploy Harness Summary (§6): that summary is produced **after** the Checkin Log phase (phase 4) finishes (success or WARN). Same spawn model as `agent-orchestrator.md` §6A:

```
Task(
  subagent_type: "generalPurpose",
  description: "Deploy — Checkin activity log [PROJECT] [PLAN_SLUG]",
  prompt: <checkin envelope below>
)
```

**First action:** The subagent reads `.cursor/agents/checkin.md` completely, then follows `docs/_ai_system/agents/agent-checkin.md`.

**Envelope (slim Task prompt):** Include at minimum `FEATURE`, `PROJECT`, `PLAN_SLUG`, `DATE`, and **`DEPLOY_SUMMARY`** (authoritative text for phases completed through Memory Commit — a faithful excerpt or structured recap of Production Readiness, Security, and Memory Commit; the final §6 block may be appended after checkin) — not `ORCHESTRATOR_SUMMARY`. See `agent-checkin.md` for filename pattern and anti-jargon rules.

| Outcome | Severity | Behavior |
|---------|----------|----------|
| Checkin Task fails, times out, or returns an error | **WARN** | Log in the deploy completion context. **Do not** mark the deploy harness as failed — phases 1–3 already completed. |
| Checkin succeeds | — | Optional note that an activity file was written. |

### Deploy Harness Task Envelope Template

```
## Cuebert Deploy Harness Task
**First action:** Read [agent file] completely. Follow its instructions.

You are executing [phase] as part of the Cuebert Deploy Harness (`/d`).

## Task envelope
REPO: [absolute path]
BRANCH: [git branch]
PROJECT: [project name]
LANGUAGE: [PYTHON | CUEBERT | UE_CPP]
PLAN: [path to plan file]
MODE: deploy-gate
PRIOR PHASE: [summary of previous deploy phase result | N/A]

## Expected output
Return structured result with PASS/FAIL status and findings list.
```

---

## 5. Remediation and rollback

If Phase 1 (Production Readiness) or Phase 2 (Security) returns REJECT-severity findings:

1. **Stop the chain** — do not proceed to subsequent phases
2. **Report findings** with structured detail (file, line, severity, description)
3. **Suggest remediation:** Point the user to `/code` or `/o --code` to fix findings, then re-run `/d`

The Deploy Harness does NOT run its own remediation loop (unlike the Orchestrator's §4A). Remediation is done via the engineering pipeline (`/o` or direct `/code`), then `/d` is re-run.

**Rollback (organizational):** If the harness declared **NOT READY** after a merge or tag, treat prior good revision as the rollback target (revert PR, redeploy last known-good artifact, or restore branch) per team release policy. The harness records evidence in the summary block (§6) for audit.

---

## 6. Result Summary

Emit this block **after** phases 1–4 have finished in order (including Checkin Log), or after a blocking phase stops the chain before later phases:

```
=== DEPLOY HARNESS SUMMARY ===
Feature: [name]
Phases Completed: [list]
Production Readiness: [PASS | FAIL (N findings)]
Security: [PASS | FAIL (N findings)]
Memory Commit: [DONE | SKIPPED]
Checkin Log: [DONE | WARN (brief reason)]
Blocking Issues: [list or "none"]
Deploy Status: [READY | NOT READY]
================================
```

---

## 7. Preview Mode (`--preview`) — deploy verification and health checks

When `--preview` is passed, the Deploy Harness walks the phase chain **without executing** mutating work:

1. Resolve envelope (REPO, BRANCH, PROJECT, LANGUAGE, PLAN)
2. Run the **same system validation steps** as `agent-orchestrator.md` §8 (MCP health probe via `sequentialthinking`, vault resolution check, registry consistency scan, `cuebert_system_check` when available)
3. Report what each deploy phase would do and whether prerequisites are met (agent files on disk, security slim present, cuebert-core MCP reachable for memory tools unless `--skip-memory`)
4. Do NOT spawn subagents, edit files, or mutate state. MCP calls are limited to read-only validation as in §8.

Output uses the same **PREVIEW** shape as `agent-orchestrator.md` §8 with the deploy-specific phase chain (Production Readiness → Security → Memory Commit → Checkin Log).

---

## 8. What the Deploy Harness Does NOT Own

- **Code fixes** — Use `/o` or `/code` to fix issues found by the deploy pipeline
- **Plan creation** — Plans are created by `/spec`; the deploy harness reads them
- **Build verification** — Build gates are part of the engineering pipeline (`/o`), not the deploy harness
- **QA execution** — QA runs during `/o`; the deploy harness assumes QA has already passed
- **Gaming ship / store upload** — Use `/ship` and `agent-ship.md`; gaming prod-readiness rules live under **`docs/_ai_system/standards/prod-readiness-game-rules.md`**

---

## 9. Handoff Protocol

The Deploy Harness does not produce a traditional handoff block. Its output is the Deploy Harness Summary (§6). If the deploy is NOT READY, the summary includes actionable remediation guidance.

---

## 10. Self-Maintenance (Mitosis)

> **TOKEN WATCH:** If this file exceeds ~5000 tokens, split detailed Production Readiness scan categories into `agent-production-readiness.md` only (keep this file as harness routing).
