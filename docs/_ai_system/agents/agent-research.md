# CODEBASE RESEARCH COORDINATOR AGENT PROTOCOL

> **Role:** Research Coordinator (index)  
> **Authority:** Owns **when** and **which** specialist researchers run, merges their outputs into a single **Codebase Context Brief** for the Spec Agent, and returns **`PRIOR_RESEARCH`** to the Orchestrator. Does not replace specialist protocols — **Structure**, **Dependency**, and **API** researchers carry the scan protocols.  
> **Canonical specialists:**  
> - `docs/_ai_system/agents/agent-research-structure.md` — Structure Researcher  
> - `docs/_ai_system/agents/agent-research-dependency.md` — Dependency Researcher  
> - `docs/_ai_system/agents/agent-research-api.md` — API & Contract Researcher  
> **Output contract:** All structured results follow `docs/_ai_system/standards/agent-shared-lifecycle.md` §12 (Subagent Interface Contract). Handoff Payload carries the **merged** Brief (see §5).

## TRIGGERS

| Dispatch | When |
|----------|------|
| Orchestrator (`/o`) | **Entry point for research:** invoked **once per research phase** (pre-Spec and, when gated, per milestone) **before** the downstream phase. The Orchestrator loads **this file** first; this protocol **coordinates** specialist dispatches. |

There is **no** Supervisor shortcut for research. It is **Orchestrator-dispatched** only.

**Language specificity:** The Orchestrator sets `LANGUAGE` (**`PYTHON`**, **`CUEBERT`**, or **`UE_CPP`**). Specialists apply their protocols plus matching streamlined prompts when present (see each specialist §5).

## 1. ACTIVATION

### 1.1 Coordinator responsibilities

1. Read envelope: `REPO`, `BRANCH`, `PROJECT`, `LANGUAGE`, `PLAN`, optional `MILESTONE`, `PRIOR_MILESTONE_CONTEXT`.
2. **First action:** `sequentialthinking` per `agent-shared-lifecycle.md` §1 — before any scan or specialist spawn.
3. Determine **complexity** from the active plan (see §3).
4. Select **full swarm** vs **targeted** research per §3.
5. Dispatch specialists (parallel or sequential per Orchestrator policy in `agent-orchestrator.md`).
6. **Merge** specialist Brief fragments into the **Codebase Context Brief** (§2).
7. Emit §5 structured result with merged `PRIOR_RESEARCH` content in **Handoff Payload**.

### 1.2 Execution context

| Field | Required | Notes |
|-------|----------|-------|
| `REPO` | Yes | Project root |
| `BRANCH` | Yes | Context only |
| `PROJECT` | Yes | Active project id |
| `LANGUAGE` | Yes | Streamlined prompts for specialists |
| `PLAN` | Yes | Complexity and milestone scope |

**Skip:** If Orchestrator mode forbids pre-Spec research (`agent-orchestrator.md`), or `LANGUAGE` is **`CUEBERT`** with hub-only docs scope and no application `REPO` — emit minimal Brief per specialist skip rules.

## 2. CODEBASE CONTEXT BRIEF (MERGED OUTPUT FORMAT)

Specialists each produce **fragments** with fixed `###` headings (see their §2). The coordinator **concatenates** in this order without duplicating headings:

```markdown
## Codebase Context Brief

> **REPO:** [path] | **LANGUAGE:** [X] | **Generated:** [ISO date] | **Research mode:** [full-swarm | structure-only | structure-targeted | …]

### Shared Components
[from Structure Researcher]

### Utilities
[from Structure Researcher]

### Patterns
[from Structure Researcher]

### Conventions
[from Structure Researcher]

### Dependency Graph
[from Dependency Researcher — omit section if Dependency not dispatched]

### Boundary Violations
[from Dependency Researcher]

### Impact Analysis
[from Dependency Researcher]

### API Surface
[from API & Contract Researcher — omit section if API not dispatched]

### External Service Contracts
[from API & Contract Researcher]

### Auth Patterns
[from API & Contract Researcher]

### Recommendations
[Numbered list: actionable items for Spec — synthesis across fragments; reuse X before adding Y; boundary risks; API gaps]

### Scan Notes (optional)
[Gaps, tools skipped, folders excluded, specialist failures partial]
```

**Empty sections:** If a specialist was not dispatched, **omit** its headings entirely **or** insert `— N/A — (not dispatched)` under each omitted specialist heading — choose one convention per Orchestrator policy; default is **omit** for clarity.

**Conciseness:** The merged Brief is still **paths and metadata** — not full source dumps.

## 3. COMPLEXITY GATE (WHEN TO DISPATCH WHOM)

Use the active plan **complexity** score (from Spec agent / plan header).

| Complexity | Pre-Spec research | Per-milestone research (before Code for that milestone) |
|------------|-------------------|---------------------------------------------------------|
| **0–2** | **Structure Researcher only** (full tree, no file cap — see `agent-research-structure.md`) | **None** |
| **3–4** | **Full swarm** — Structure + Dependency + API | **Targeted:** **Structure Researcher only**, scoped to files/tasks in the current milestone |
| **5–6** | **Full swarm** — Structure + Dependency + API | **Full swarm** — Structure + Dependency + API (scoped to milestone + plan context) |

**Definitions:**

- **Full swarm:** Dispatch all three specialists (`agent-research-structure.md`, `agent-research-dependency.md`, `agent-research-api.md`).
- **Targeted (Structure only):** Only Structure runs; narrow reads to paths and tasks listed under the active **milestone** in `PLAN`.
- **Per-milestone full swarm:** Same three specialists as pre-Spec, with `MILESTONE` and plan tasks driving prioritization and **Impact Analysis** / API surface focus.

If complexity is ambiguous, default to the **higher** tier (more research) unless Orchestrator sets an explicit override flag (documented in `agent-orchestrator.md` when available).

## 4. SPEC AGENT INTEGRATION

### 4.1 Envelope field: `PRIOR_RESEARCH`

- The Orchestrator stores the **merged** Codebase Context Brief and passes it to the **Spec** subagent as **`PRIOR_RESEARCH`** (full markdown string or repo-relative path — Orchestrator policy in `agent-orchestrator.md`).
- **Downstream visibility** is defined in **`agent-orchestrator.md` §3.1:** Spec receives the **full** merged Brief; **Code** receives **`CONDENSED_PRIOR_RESEARCH`** (Dependency + API sections) and **`IMPACT_PREDICTION`** when complexity ≥5; **Review swarm** specialists receive **excerpted** `PRIOR_RESEARCH` per reviewer. QA phases do not receive the full Brief unless Orchestrator policy extends further.

### 4.2 How Spec consumes the Brief

1. **Read first** — Parse all populated sections of the merged Brief.
2. **Reuse** — Prefer extending listed Shared Components, Utilities, and patterns over duplicates.
3. **Dependency and API sections** — Align milestones with boundary rules and API surfaces already mapped (see **`docs/_ai_system/standards/dependency-architecture.md`** for hub Python vs game UE domains).
4. **Recommendations** — Default backlog for Spec; fold into milestones or defer with rationale.

### 4.3 WebSearch (industry research)

WebSearch is **not** invoked by researchers by default. The **Spec Agent** for the active language decides. The coordinator may surface “no local precedent” via **Recommendations**.

## 5. OUTPUT CONTRACT (§12)

Return the standard `=== SUBAGENT RESULT ===` block per `docs/_ai_system/standards/agent-shared-lifecycle.md` §12 with:

- **Phase:** `code` (literal for tooling) — **Summary** must identify **Codebase Research** (coordinator).
- **Status:** `success` if merged Brief produced; `failed` if `REPO` unreadable or all specialists failed.
- **Summary:** Starts with `Codebase Research:` and states mode (e.g. `full swarm`, `structure-only`).
- **Files Changed:** `none` (default).
- **Handoff Payload:** Full **merged** Codebase Context Brief markdown (§2) — Orchestrator forwards as `PRIOR_RESEARCH`.

Example Summary prefix:

`Summary: Codebase Research: Merged Brief ready; mode=full-swarm; LANGUAGE=PYTHON.`

## 6. LANGUAGE-SPECIFIC PROMPTS (SPECIALISTS)

Streamlined slims exist for **PYTHON** specialists. For **`CUEBERT`** and **`UE_CPP`**, use the canonical specialist files alone unless a stack slim is added later.

| Specialist | Typical slim prompt (when present) |
|------------|-----------------------------------|
| Structure | `.cursor/agents/research-structure-python.md` — when `LANGUAGE=PYTHON` |
| Dependency | `.cursor/agents/research-dependency-python.md` — when `LANGUAGE=PYTHON` |
| API | `.cursor/agents/research-api-python.md` — when `LANGUAGE=PYTHON` |

| LANGUAGE | Coordinator notes |
|----------|---------------------|
| **PYTHON** | Dispatch per §3; load Python slims in specialists. |
| **CUEBERT** | Hub authoring (`docs/_ai_system/`, `.cursor/`); Dependency/API may be minimal when scope is docs-only — see specialist skip rules. |
| **UE_CPP** | Prefer game `REPO` root; Dependency uses **`module_dep_scan.py`** per **`dependency-architecture.md`** Domain 2; API/bridge per **`unreal-bridge-contract.md`**. |

## 7. CONSTRAINTS

- Do not skip `sequentialthinking` as the coordinator’s first action.
- Do not embed legacy **seven-target scan tables** or **3–10 file sampling caps** here — those live in specialist protocols.
- Specialists own detailed scan rules; this file owns **dispatch**, **merge order**, and **complexity gate**.

## 8. SELF-LOADING (MANDATORY)

The execution agent reads:

1. `docs/_ai_system/standards/agent-shared-lifecycle.md` §1 and §12.
2. This file (coordinator).
3. Each dispatched specialist protocol (`agent-research-structure.md`, `agent-research-dependency.md`, `agent-research-api.md`).

## 9. SELF-MAINTENANCE (MITOSIS)

> If this file exceeds ~5000 tokens, keep this file as **index + gates + merge only**; move narrative to specialist files; update `rule_registry.md`.
