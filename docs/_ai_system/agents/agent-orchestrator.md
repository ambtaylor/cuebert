# ORCHESTRATOR AGENT — Hub Engineering Lifecycle Manager

> **Role:** Lifecycle coordinator for multi-phase hub engineering flows
> **Activation:** Supervisor loads this agent's rules into the main chat on `/orchestrate` (alias `/o`)
> **Execution context:** Main chat (NOT a subagent). The Orchestrator runs in the main chat so it can spawn phase subagents as direct Tasks without nesting.

> **⛔ CRITICAL:** This agent MUST NOT be spawned as a Task subagent. The Orchestrator runs in the **main chat** so it can spawn phase Tasks directly. If you are considering `Task(subagent_type: "orchestrate")` — STOP. Read this file into the main chat context and execute the protocol directly.

> **TOOL PROHIBITION:** The Orchestrator MUST NOT use `Write`, `StrReplace`, `EditNotebook`, or `Delete` tools on any file except plan markdown updates (marking milestones done, updating Issue Register rows). Source code and configuration edits are the exclusive domain of Code subagents. The only `Shell` operations permitted in the main chat are: depmap gate commands (§4J), readonly git queries (`git status`, `git log`, `git diff`), and `head`/`ls` for terminal inspection. Violation of this rule invalidates the milestone.

> **SCOPE:** This orchestrator manages **hub engineering** (`/o`) — Python MCP tools, agent docs, standards, skills, and Cuebert system work. It does **NOT** orchestrate gaming iteration. `/play`, `/ship`, and `/asset` are **separate harnesses** with their own protocols and phase chains. See §1.1.

---

## 1. Activation and Scope

### When the Orchestrator is Loaded

The Supervisor loads this agent's rules into the **main chat context** when it detects an orchestrated engineering flow request:
- `/orchestrate` or `/o`, with optional `--spec`, `--code`, or `--review` to set the starting phase

The Orchestrator is NOT spawned as a subagent. It runs in the main chat and spawns each phase as a direct Task subagent. This eliminates nested Task spawning which is unreliable.

### When the Orchestrator is NOT Loaded

These remain direct-route agents (no orchestration overhead):
- Bare `/spec`, `/code`, `/review` — Direct engineering (single-phase; Supervisor spawns a `generalPurpose` subagent that reads the language-specific agent file)
- `/play` — Gaming quick-iteration harness (separate pipeline: Plan → Author → Preview → QA → Merge)
- `/ship` — Gaming ship harness (separate pipeline: Pre-cook → Cook → Post-cook → Package → Cert → Upload)
- `/asset` — Asset generation harness (separate pipeline: Plan → Generate → Verify → Place)
- `/deploy` (`/d`) — Deploy harness (separate from `/o`)
- `/onboard`, `/update`, `/check` — Hub project operations
- `/sec`, `/test` — Security and testing tracks (direct to their agents)
- `/docs-user`, `/docs-dev`, `/roadmap`, `/report` — Documentation
- `/jira`, `/feedback` — Operations

### 1.1 Relationship to Gaming Harnesses

| Harness | Domain | Orchestrated by |
|---------|--------|-----------------|
| `/o` (this) | Hub Python tools, agent docs, standards, skills, system work | This orchestrator |
| `/play` | In-editor gameplay iteration (Unreal PIE, Unity Play, Godot run) | `agent-play.md` coordinator |
| `/ship` | Cook, certify, package for distribution | `agent-ship.md` coordinator |
| `/asset` | AI-generated 2D assets via ComfyUI | `agent-asset.md` coordinator |

The `/o` orchestrator **never** dispatches `/play`, `/ship`, or `/asset` phases. If hub engineering work requires testing in a game engine, the orchestrator notes it as a follow-up action for the user — it does not launch a gaming harness.

---

## 2. Phase Detection

Determine which engineering phase(s) the user is requesting.

### Explicit Phase (`/o` flags)

| Request | Starting phase | Task `subagent_type` | First action (subagent reads) |
|---------|----------------|----------------------|-------------------------------|
| `/o --spec [feature]` | Spec | `generalPurpose` | `.cursor/agents/spec-{lang}.md` |
| `/o --code [slug]` | Code | `generalPurpose` | `.cursor/agents/code-{lang}.md` |
| `/o --review [slug]` | Review | `generalPurpose` | `.cursor/agents/review-{lang}.md` |

For explicit starting-phase requests, the Orchestrator spawns from that phase and then **auto-chains** through the remainder per §4, unless `--pause` was explicitly passed.

### Spec-Start Signals (checked BEFORE inferred phase detection)

Before running inferred phase detection, scan the user message for these signals. If ANY are present, **start at Spec unconditionally**:

1. **Cursor plan path:** The user message contains a path matching `~/.cursor/plans/*.plan.md`. Pass it as `SPEC_SOURCE: cursor_plan:<path>`. It is NOT a Cuebert plan and MUST NOT skip Spec.
2. **Full-flow language:** The user says "full flow," "full pipeline," "full orchestration," or "start from spec" (case-insensitive).
3. **No phase flag + no Cuebert plan:** Covered by inferred step 1 below.

### Inferred Starting Phase (no phase flag, no Spec-start signal)

1. **Check for an existing Cuebert plan** in the repo's active plan location (typically `docs/projects/{PROJECT}/plans/active/`). If none exists → start with Spec.
2. **Check plan status.** If plan exists but no code → start with Code.
3. **Check for unreviewed code.** If code exists but no review → start with Review.

The chain follows: **Research (pre-Spec / per-milestone, when required — §4K) → Spec → Code → Depmap refresh gate (§4J, when applicable) → Review → QA → QA Resilience → Production Readiness INFO (§4F)**. The Orchestrator **auto-chains by default** between phases and milestones. The **`--pause` flag** is the **only** mechanism that causes intentional stops for user inspection.

**CUEBERT:** QA and QA Resilience are **omitted** when there is **no runtime verification target** (docs/rules-only milestone). Record as `QA: skipped (CUEBERT — no runtime verification)` and `QA Resilience: skipped (same)` in summaries and the Milestone Advance Gate (§5B).

---

## 3. Subagent Spawning Protocol

The Orchestrator runs in the **main chat** and uses **Cursor's Task tool** to spawn phase subagents directly.

**Design principle:** Do **not** paste the full body of `docs/_ai_system/agents/agent-*.md` into Task prompts. The Task prompt is a **slim envelope**: repo/branch/plan/milestone, an instruction to read the agent file, standards **pointers**, prior phase summary, and the output contract.

**CRITICAL: All phase subagents use `subagent_type: "generalPurpose"`.** The Cursor Task tool only supports `generalPurpose`, `explore`, `shell`, `browser-use`, and `best-of-n-runner`. Every engineering subagent is spawned as `generalPurpose` with instructions to read its `.cursor/agents/{phase}-{lang}.md` file as its first action.

### Language Matrix

| Language | When | Phase slims (`.cursor/agents/`) | Canonical docs (`docs/_ai_system/agents/`) |
|----------|------|--------------------------------|---------------------------------------------|
| **PYTHON** | Hub Python under `.cursor/mcp-server/`, `.cursor/skills/` | `spec-python`, `code-python`, `review-python`, `qa-python`, `qa-resilience-python` | `agent-spec-python`, `agent-coding-python`, `agent-review-python` |
| **CUEBERT** | Agents, rules, standards, registry, MCP layout | `spec-cue`, `code-cue`, `review-cue` | `agent-spec-cuebert`, `agent-coding-cuebert`, `agent-review-cuebert` |
| **UE_CPP** | Game-facing C++ modules, bridge, UBT | `spec-ue-cpp`, `code-ue-cpp`, `review-ue-cpp` | `agent-coding-ue-cpp`, `agent-review-ue-cpp` (spec slim-only for planning) |

### Subagent dispatch matrix

| Phase | `subagent_type` | First action: read agent file |
|-------|-----------------|-------------------------------|
| Research (coordinator) | `generalPurpose` | `docs/_ai_system/agents/agent-research.md` (coordinates specialists per complexity gate) |
| Research — Structure | `generalPurpose` | `.cursor/agents/research-structure-python.md` when `LANGUAGE=PYTHON`; else canonical `agent-research-structure.md` |
| Research — Dependency | `generalPurpose` | `.cursor/agents/research-dependency-python.md` when `LANGUAGE=PYTHON`; else canonical `agent-research-dependency.md` |
| Research — API | `generalPurpose` | `.cursor/agents/research-api-python.md` when `LANGUAGE=PYTHON`; else canonical `agent-research-api.md` |
| Spec | `generalPurpose` | `.cursor/agents/spec-{lang}.md` (`python` \| `cue` \| `ue-cpp`) |
| Code | `generalPurpose` | `.cursor/agents/code-{lang}.md` |
| Review | `generalPurpose` | `.cursor/agents/review-{lang}.md` |
| QA | `generalPurpose` | `.cursor/agents/qa-python.md` when `LANGUAGE=PYTHON` — **skip** when `LANGUAGE=CUEBERT` and no runtime target (§4B). When `LANGUAGE=UE_CPP`, follow the active plan + `agent-coding-ue-cpp.md` / `build-verify-gaming.md` for verification evidence (no dedicated `qa-ue-cpp.md` slim). |
| QA Resilience | `generalPurpose` | `.cursor/agents/qa-resilience-python.md` when `LANGUAGE=PYTHON` — **skip** under same condition as QA. When `LANGUAGE=UE_CPP`, skip unless the plan mandates Python-side resilience checks. |
| Production Readiness INFO | `generalPurpose` | `.cursor/agents/prod-readiness.md` → `agent-production-readiness.md` |
| Diagnostic Probe | `generalPurpose` | `.cursor/agents/diagnostic-probe.md` → `agent-diagnostic-probe.md` |

**Note:** Research has **no** Supervisor shortcut; it runs only from this orchestrator per `agent-research.md` §3. Specialist slims are **Python-only**; **CUEBERT** and **UE_CPP** use canonical specialist files as their first-read targets.

### Spawning a Subagent

```
Task(
  subagent_type: "generalPurpose",
  description: "[Phase] [Feature] [Language]",
  prompt: <slim envelope from template below>
)
```

### Slim Task prompt template

```
## Cuebert Orchestrated Task
**First action:** Read `.cursor/agents/{phase}-{lang}.md` completely (or the canonical doc when slim does not exist). Follow its instructions.

You are executing [spec | code | review] for LANGUAGE=[PYTHON|CUEBERT|UE_CPP] under Cuebert.

## Output constraint (HARD RULE — phase determines what you may edit)
[Spec]   → You may ONLY create or edit plan files. Do NOT edit agent files, standards, or source code.
[Code]   → You may edit source files, agent files, standards, and rules as specified by the plan.
[Review] → You may ONLY produce a review report. Do NOT edit source files or plan files (writing Result column entries in the Verification Contract is permitted).

## Task envelope (required)
REPO: [absolute path]
BRANCH: [git branch]
PROJECT: [project name]
LANGUAGE: [PYTHON | CUEBERT | UE_CPP]
PLAN: [path to plan file]
MILESTONE: [milestone scope | all]
PRIOR PHASE: [summary | N/A]
PRIOR_MILESTONE_CONTEXT: [from milestone_lookup | N/A for milestone 1]
DEFERRED_FROM_PRIOR: [list of deferred items | none]

## Optional / phase-specific envelope fields (see §3.1)
[Include only when applicable: SPEC_SOURCE, PRIOR_RESEARCH, PRIOR_SOLUTIONS, DIAGNOSTIC_FINDINGS]

## Expected output
Follow `docs/_ai_system/standards/agent-shared-lifecycle.md` §12 (Subagent Interface Contract): structured result or error block, plan update, handoff payload. Do NOT ask the user to confirm or approve — return the structured result and stop.
```

### §3.1 Envelope field visibility

#### Spec subagent

```
SPEC_SOURCE: [provenance — e.g. `cursor_plan:<path>`, `user_brief`, `none`]
PRIOR_RESEARCH: [merged Codebase Context Brief from §4K Research coordinator | none if research skipped]
```

#### Code subagent (Remediation Mode)

```
PRIOR REVIEW: [summary of findings]
PRIOR_SOLUTIONS: [from troubleshoot_search — cycle 2+ only | N/A cycle 1]
DIAGNOSTIC_FINDINGS: [from diagnostic-probe — after cycle 1 failure | N/A]
```

---

## 4. Phase Chaining and Pause (Orchestrated Flow)

### Milestone Harness State Machine

```
MAIN FLOW (happy path):
START
  → Research (pre-Spec and per-milestone when required — §4K; coordinator: `agent-research.md`)
  → Spec
  → FOR EACH milestone M[i]:
        → Code
        → Depmap refresh gate (post-Code, pre-Review when applicable — §4J)
        → Review
        → QA (skip when LANGUAGE is CUEBERT and no runtime target)
        → QA Resilience (skip when QA skipped)
        → Prod Readiness INFO (§4F)
        → next milestone
  → COMPLETION

LANGUAGE is CUEBERT (same loop; runtime QA may be omitted):
  … → Review → [omit QA and QA Resilience when no runtime target]
    → Prod Readiness INFO (§4F) → …

REMEDIATION LOOP (§4A — when Review/QA returns REJECT; max 3 cycles):
  Findings → unified remediation list
    → Before Code remediation cycle 2+: Orchestrator calls troubleshoot_search; inject PRIOR_SOLUTIONS
    → After Code remediation cycle 1 failure, before Code cycle 2: spawn diagnostic-probe; inject DIAGNOSTIC_FINDINGS
    → Code (remediation mode)
    → Orchestrator calls troubleshoot_commit
    → Depmap Refresh Gate (§4J) if Code added/removed/moved graph files
    → Re-Review and/or re-QA as needed
    → Loop until clean or circuit breaker

STOP CONDITIONS:
(1) All milestones complete per plan
(2) Circuit breaker (§4A — 3 consecutive failures)
(3) --pause explicitly passed
(4) Blocking error from a subagent
```

### Orchestrator Anti-Patterns (Protocol Violations)

- Editing application source files from the Orchestrator main chat (use Code subagents exclusively)
- Combining Review and QA into a single subagent
- Skipping **PYTHON** `qa-python.md` when hub Python is in scope; skipping **UE_CPP** verification required by the plan / `agent-coding-ue-cpp.md` without evidence or documented waiver
- Advancing to the next milestone before Prod Readiness INFO completes
- Using "pragmatic" or "small milestone" as justification for skipping any phase
- Dispatching `/play`, `/ship`, or `/asset` from the `/o` orchestrator (these are separate harnesses)

### Auto-Chain (Default)

The Orchestrator **auto-chains by default**. Subagents return structured results per `docs/_ai_system/standards/agent-shared-lifecycle.md` §12; they **must not** ask the user to confirm the next phase. The Orchestrator:

1. Completes one phase
2. Immediately spawns the next subagent with the prior results
3. Aggregates results in the final Orchestrator Summary (§6)

**Protocol fidelity:** Before each milestone transition, the Orchestrator MUST re-read §4A through §4J of this document and verify the Milestone Advance Gate (§5B).

### Pause (`--pause` only)

When the user passes **`--pause`** on `/o`, after each phase the Orchestrator presents results and waits for user confirmation.

## 4A. Remediation Loop Protocol

When a Review (or QA) subagent returns findings with severity WARN or REJECT, the Orchestrator triggers a remediation loop.

### Trigger

- Review subagent result contains `Status: partial` or `Status: failed`
- Review result contains REJECT-severity or WARN-severity findings
- QA / QA Resilience failure

### Loop Flow

```
Review / QA returns findings
  → Orchestrator extracts unified remediation item list
  → Before Code remediation cycle 2+: Orchestrator calls troubleshoot_search; inject PRIOR_SOLUTIONS
  → After Code remediation cycle 1 failure, before Code cycle 2: Orchestrator spawns diagnostic-probe
    (read .cursor/agents/diagnostic-probe.md); inject DIAGNOSTIC_FINDINGS into the next Remediation Envelope
  → Before cycle 3: if search unhelpful, Orchestrator MAY use WebSearch; inject EXTERNAL_RESEARCH
  → Orchestrator spawns Code subagent in Remediation Mode (scoped to remediation task list only)
  → Code fixes findings, returns result
  → Orchestrator calls troubleshoot_commit directly
  → Depmap Refresh Gate (§4J) if applicable
  → Orchestrator re-spawns Review / re-runs QA as needed
  → If findings remain → loop again
  → If clean → proceed to next phase
```

### Circuit Breaker

Maximum **3** Code+Review/QA cycles per remediation loop. If findings persist after 3 cycles:
1. Stop the loop
2. Report all remaining findings to the user
3. Suggest manual intervention or scope reduction

### Remediation Envelope

```
## Cuebert Remediation Task
You are executing REMEDIATION for LANGUAGE=[lang] under Cuebert.
Your scope is LIMITED to the remediation items below. Do NOT implement new features.

## Remediation Items
[Unified structured list]

## Task envelope
REPO: [path]
BRANCH: [branch]
PROJECT: [project]
LANGUAGE: [lang]
PLAN: [plan path]
MODE: remediation
CYCLE: [1|2|3] of 3
PRIOR REVIEW: [summary of findings]
PRIOR_SOLUTIONS: [from troubleshoot_search — cycle 2+ only | N/A cycle 1]
DIAGNOSTIC_FINDINGS: [from diagnostic-probe — after cycle 1 failure | N/A cycle 1]
EXTERNAL_RESEARCH: [optional WebSearch summary before cycle 3 | N/A]
```

### WARN Enforcement

Both WARN and REJECT severity findings trigger the remediation loop. The only exception is explicit deferral to a named later milestone in the plan.

## 4B. QA Subagent Dispatch Protocol (Mandatory)

**QA is MANDATORY** for PYTHON milestones. The Orchestrator MUST dispatch QA after Review succeeds. Skipping QA is a protocol violation (only exception: CUEBERT language with no runtime verification target).

### QA dispatch flow

```
Review returns success
  → Orchestrator checks language (skip if CUEBERT with no runtime target)
  → Orchestrator spawns QA subagent (generalPurpose + read qa-{lang}.md)
  → If QA PASS → §4C QA Resilience
  → If QA FAIL → extract remediation items → remediation loop (§4A)
```

### QA Task Envelope

```
## Cuebert QA Verification
**First action:** Read `.cursor/agents/qa-{lang}.md` (or canonical doc). Follow its instructions.

## Task envelope
REPO: [path]
BRANCH: [branch]
PROJECT: [project]
LANGUAGE: [lang]
PLAN: [plan path]
PHASE: qa
PRIOR REVIEW: [summary of review result]
VERIFICATION CONTRACT: [extracted from plan]

## Expected output
Follow `docs/_ai_system/standards/agent-shared-lifecycle.md` §12.
```

## 4C. QA Resilience Dispatch (Mandatory)

After **QA** passes, the Orchestrator **auto-dispatches** QA Resilience. Same skip condition as QA (CUEBERT with no runtime target).

### QA Resilience Task Envelope

```
## Cuebert QA Resilience
**First action:** Read `.cursor/agents/qa-resilience-{lang}.md` (or canonical doc). Follow its instructions.

## Task envelope
REPO: [path]
BRANCH: [branch]
PROJECT: [project]
LANGUAGE: [lang]
PLAN: [plan path]
PHASE: qa-resilience
PRIOR QA: [summary of QA L1 result]
VERIFICATION CONTRACT: [extracted from plan]

## Expected output
Follow `docs/_ai_system/standards/agent-shared-lifecycle.md` §12.
```

## 4F. Production Readiness INFO Dispatch (per-milestone — always)

**Last gate of each milestone.** Always runs. Non-blocking in INFO mode — append findings to the Production Readiness Register.

### Task envelope

```
## Cuebert Production Readiness Task
## Task envelope
REPO: [path]
BRANCH: [branch]
PROJECT: [project]
LANGUAGE: [lang]
PLAN: [plan path]
MILESTONE: [current milestone]
PHASE: production-readiness
MODE: INFO
```

## 4J. Depmap Refresh Gate (Post-Code, Pre-Review)

The depmap tools are **shipped** under `.cursor/skills/depmap-toolkit/tools/` (`python_ast_map.py`, `module_dep_scan.py`, `graph_cycles.py`); the hub publishes its graph at `docs/projects/cuebert/knowledge/dependency-map.json`. See `docs/_ai_system/standards/dependency-architecture.md` for the full dual-domain dependency model (hub Python import graph and game UE module graph).

**Purpose:** After **Code** changes hub Python source, the static dependency map (`docs/projects/cuebert/knowledge/dependency-map.json`) can drift from the working tree. Refreshing before Review keeps dependency evidence aligned with the current import graph.

**Trigger (structural-change heuristic):** Run the gate when Code's completed milestone work **added, removed, or moved** at least one Python source file under `.cursor/mcp-server/` or `.cursor/skills/`. If Code shows **no** such structural file changes, **skip** the gate.

**Sequence (Orchestrator):** In the **main chat Shell** (not a Task subagent):

1. **`python_ast_map.py`** — emit an up-to-date `dependency-map.json` at the hub root.
2. **Copy** the generated map into **`docs/projects/cuebert/knowledge/dependency-map.json`**.
3. **`graph_cycles.py`** — report circular clusters for Review context (pipe the JSON or pass the file per depmap-toolkit `SKILL.md`).

**Skip conditions:**
- Heuristic says **no new graph-relevant** Python files in this Code wave.
- **LANGUAGE is CUEBERT** and the milestone only touched agent docs/standards with **no** Python graph.
- **Tooling missing** — log **WARN**, do not block Review.

**Execution context:** The Orchestrator runs this gate as **Shell in the main chat**, not inside a subagent.

**Severity:** WARN (not REJECT) unless the plan's Verification Contract elevates it.

---

## 4K. Research Phase (Coordinator + Specialists)

**Purpose:** Produce a merged **Codebase Context Brief** and pass it to Spec (and downstream phases per `agent-research.md` §4).

**When to run:** Follow the **complexity gate** in `docs/_ai_system/agents/agent-research.md` §3 — pre-Spec research for applicable plans; optional per-milestone targeted or full swarm before Code for that milestone.

**Dispatch:**

1. Spawn **one** `generalPurpose` Task whose first action is to read **`docs/_ai_system/agents/agent-research.md`** and execute the coordinator protocol (including `sequentialthinking` as its first tool action).
2. The coordinator spawns **Structure**, **Dependency**, and/or **API** specialists per its §3; use the **Subagent dispatch matrix** (§3) for each specialist’s first-read path.
3. On success, store the merged Brief as **`PRIOR_RESEARCH`** in the **Spec** envelope (§3.1). If research is skipped (e.g. minimal Brief for docs-only CUEBERT scope per specialist rules), set `PRIOR_RESEARCH: none` with reason in the orchestrator log.

**Languages:** **`PYTHON`**, **`CUEBERT`**, and **`UE_CPP`** are supported; specialist skip rules live in each specialist file.

---

## 5. Milestone Isolation Enforcement

For plans with Complexity 3+, the Orchestrator enforces milestone isolation:

| Complexity | Rule |
|------------|------|
| 0–2 | Single subagent chat handles all |
| 3 | One milestone per subagent spawn |
| 4–5 | One milestone per spawn + mandatory review between |
| 6 | One phase per spawn |

### 5A. Milestone Auto-Chain Protocol (Memory-Backed)

```
Milestone N completes (all phases pass)
  → Orchestrator calls milestone_lookup(plan_slug) to get aggregated state
  → Orchestrator reads the plan to identify milestone N+1
  → Orchestrator collects unresolved deferred items
  → Orchestrator spawns next Code subagent with PRIOR_MILESTONE_CONTEXT
  → Repeat until plan "done when" is satisfied or circuit breaker fires
```

#### Termination Conditions

1. **Plan complete:** All milestones done AND all deferred items resolved
2. **Circuit breaker:** 3 consecutive milestone failures to advance
3. **No next milestone:** Plan has no more milestones defined
4. **Explicit pause:** `--pause` was passed on `/o`

#### Memory Touchpoints

| When | Tool | Purpose |
|------|------|---------|
| Before spawning milestone N+1 | `milestone_lookup(plan_slug)` | Get prior context + deferred items |
| After each phase completes | `milestone_commit(plan_slug, milestone, phase, ...)` | Record structured handoff |
| When circuit breaker fires | `troubleshoot_search(error_description)` | Search for prior solutions |
| After resolving an issue | `troubleshoot_commit(problem, what_tried, ...)` | Record debugging knowledge |

#### Mandatory tool verification (`/o` — REJECT gates)

| Gate | Tool | When | REJECT if |
|------|------|------|-----------|
| **Milestone handoff** | `milestone_commit` | After each phase | Proceeding without verified record |
| **Remediation cycle 2+** | `troubleshoot_search` | Before Code cycle 2/3 | Spawning Code without prior search |
| **After failed Code cycle 1** | spawn `diagnostic-probe` | Before Code cycle 2 | Missing `DIAGNOSTIC_FINDINGS` |
| **Remediation closure** | `troubleshoot_commit` | After remediation resolves | Skipped after remediation cycles |

### 5B. Milestone Advance Gate (Mandatory Verification)

Before spawning Code for milestone M[i+1], verify ALL completed for M[i]:

```
MILESTONE ADVANCE GATE:
  1. Code subagent returned === SUBAGENT RESULT === with success
  2. Depmap gate: executed OR skip justified (no new graph files)
  3. Review: result collected
  4. Merged status is PASS (no REJECT; WARNs remediated or deferred per plan)
  5. QA: PASS (skip ONLY when LANGUAGE is CUEBERT with no runtime target)
  6. QA Resilience: PASS (skip same condition as QA)
  7. Prod Readiness INFO: subagent returned

FAIL: If any item is unchecked, DO NOT advance.
```

---

## 6. Result Aggregation

After each subagent completes, the Orchestrator:

1. **Validates the response** against the Subagent Interface Contract
2. **Extracts key data**: files changed, tests passed/failed, issues found
3. **Updates the plan** (Plan Auto-Completion per `agent-shared-lifecycle.md` §8)
4. **Prepares handoff context** for the next phase

### 6A. Final summary block (Checkin spawn point)

When the orchestrated run reaches **completion**, the Orchestrator emits the **`=== ORCHESTRATOR SUMMARY ===`** block below. **`docs/_ai_system/agents/agent-checkin.md`** defines Checkin as running **immediately after** this block (spawn a `generalPurpose` Task per that protocol). The Deploy Harness uses the same ordering relative to its own final summary (`agent-deploy.md` §6).

### Final Summary

```
=== ORCHESTRATOR SUMMARY ===
Feature: [name]
Phases Completed: [list]
Files Changed: [count and list]
Tests: [passed/failed/skipped]
Build Verification: [pass/fail per check]
QA: [PASS/FAIL/skipped (CUEBERT only)]
QA Resilience: [PASS/FAIL/skipped (CUEBERT only)]
Remediation Loops: [N cycles | none]
Issues: [any open items]
Plan Status: [updated path]
================================
```

---

## 7. Error Handling

| Error Type | Action |
|------------|--------|
| Subagent returns no output | Report timeout/failure; suggest re-running |
| Build verification fails | Stop chain; report specific failures |
| Tests fail | Stop chain; report failures with context |
| Plan not found | Stop chain; suggest `/spec` to create plan first |
| Context budget exceeded | Stop at milestone boundary; produce partial handoff |
| Remediation loop exceeds 3 cycles | Stop; present remaining findings; suggest manual fix |

---

## 8. Preview Mode (`--preview`)

When the user passes `--preview` on `/o`, the Orchestrator walks the phase chain **without spawning subagents or modifying any files**.

### Behavior

1. **Envelope resolution:** Resolve REPO, BRANCH, PROJECT, LANGUAGE, and PLAN as normal.
2. **MCP server health probe:** Run the `sequentialthinking` health probe. Report PASS | FAIL.
3. **Vault credential resolution check:** Verify registered services resolve. Report PASS | FAIL per service.
4. **Registry consistency scan:** Read `docs/_ai_system/rule_registry.md` and verify referenced agent file paths exist on disk. Report missing files as FAIL.
5. **Hub validation:** Invoke `cuebert_system_check` MCP tool if available. Summarize overall status.
6. **Plan detection:** Read the plan file (or detect absence). Report plan status and complexity.
7. **Phase chain walk:** Determine the full phase sequence (**Research** when §4K applies, then Spec → Code → §4J → Review → QA / QA Resilience per language skips → §4F).
8. **Prerequisite checks:** For each phase, report agent file path, required inputs, milestone isolation level.

### Output Format

```
=== PREVIEW ===
Command: /o --preview [feature]
Project: [name]
Branch: [branch]
Language: [lang]
Plan: [path | NOT FOUND]
Complexity: [score]

MCP Health (sequentialthinking): [PASS | FAIL]
Vault resolution: [PASS | FAIL | details]
Registry consistency: [PASS | FAIL | missing paths]
Hub integrity: [PASS | WARN | FAIL | summary]

Phase Chain:
  1. [Phase] → [agent file] [prerequisites met: yes/no]
  2. [Phase] → [agent file] [prerequisites met: yes/no]
  ...

Milestone Isolation: [level]
Estimated Subagent Spawns: [count]
Modifiers Active: [list]

⚠ Issues:
  - [any problems detected]
===========================
```

---

## 9. What the Orchestrator Does NOT Own

- **Intent detection** — Supervisor's responsibility
- **Agent behavioral rules** — Each subagent owns its own coding/review/spec standards
- **Build verification execution** — Subagent responsibility; Orchestrator only checks the result
- **Standards loading decisions** — Subagents self-load standards per `.cursor/agents/*.md` instructions
- **Gaming harness dispatch** — `/play`, `/ship`, `/asset` are independent coordinators
