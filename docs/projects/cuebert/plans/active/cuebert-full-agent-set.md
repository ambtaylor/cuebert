# Cuebert Full Agent Set

## Metadata

| Field | Value |
|-------|-------|
| **Title** | Cuebert full engineering agent set (Python, CUEBERT, UE_CPP, supporting harness) |
| **Complexity** | **5** (~33 new files + ~4 updates; ~6,800 lines; multi-language; cross-repo port from Cue) |
| **Primary language** | **CUEBERT** (system docs, rules, registry — this plan is executed under hub engineering for `_ai_system` and `.cursor` artifacts) |
| **Branch** | `master` |
| **Repo** | `/Users/ambtaylo/CursorProjects/cuebert` |
| **Plan status** | **Complete** — M1–M12 delivered (registry, supervisor companion, orchestrator §4K/§6A, security severity alignment, task log closed). |

### Done-when criteria

1. **Python hub pipeline** — Slim agents (`spec-python`, `code-python`, `review-python`, `qa-python`, `qa-resilience-python`, `research-python`) and canonical agents (`agent-spec-python`, `agent-coding-python`, `agent-review-python`) exist, are adapted from Cue, and cross-link cuebert paths/rules only.
2. **CUEBERT system-authoring pipeline** — Slims (`spec-cue`, `code-cue`, `review-cue`) and canonicals (`agent-spec-cuebert`, `agent-coding-cuebert`, `agent-review-cuebert`) describe cuebert layout (MCP server, skills, agents, `docs/_ai_system/`).
3. **UE_CPP pipeline** — Slims (`code-ue-cpp`, `review-ue-cpp`, `spec-ue-cpp`) and canonicals (`agent-coding-ue-cpp`, `agent-review-ue-cpp`) exist; `.cursor/rules/cuebert-ue-cpp.mdc` exists with appropriate `alwaysApply` / globs for `.cpp`/`.h`/`.Build.cs`.
4. **Supporting agents** — Research coordinator + three specialists, production readiness, security, deploy, test, checkin (slims + canonicals as specified) ported and adapted.
5. **Integration** — `rule_registry.md` marks engineering agents **Active** with paths; orchestrator dispatch matrix has no stale “(when created)” gaps; supervisor text matches reality (including `cuebert-engineering.mdc` and post-M7 `cuebert-ue-cpp.mdc`).
6. **Verification** — Final Review passes against this plan’s **Verification Contract**; Issue Register either empty or all rows closed with evidence.

---

## Overview

Cuebert already has **orchestration infrastructure** (orchestrator, shared lifecycle, diagnostic probe, engineering rule, dependency architecture, depmap toolkit) and **gaming harness** agents (`/play`, `/ship`, `/asset`). It does **not** have the **engineering phase agents** that the supervisor and orchestrator expect for `/o`, `/spec`, `/code`, `/review`, `/sec`, `/test`, `/d`, research swarms, deploy, checkin, and production readiness.

This plan delivers:

- **PYTHON** agents — port from Cue (`/Users/ambtaylo/CursorProjects/cue`) with systematic path and branding substitutions.
- **CUEBERT** agents — adapt from Cue’s CUE system-authoring agents; rewrite file-pattern and registration sections for cuebert.
- **UE_CPP** agents — **new** content grounded in cuebert gaming docs (`unreal-bridge-contract.md`, `build-verify-gaming.md`, `agent-play-author.md`, etc.) and UE5 C++ conventions.
- **Supporting agents** — research, security, deploy, test, checkin, production readiness — port from Cue with domain strip (no React/Angular/KACES-only paths).
- **Fixups** — supervisor copy, `rule_registry.md`, orchestrator matrix, QA skip rules for `LANGUAGE: CUEBERT` vs runtime languages.

**Source locations (reference only — not edited in this plan phase):**

| Role | Cue | Cuebert |
|------|-----|---------|
| Slim agents | `cue/.cursor/agents/` | `cuebert/.cursor/agents/` |
| Canonical agents | `cue/docs/_ai_system/agents/` | `cuebert/docs/_ai_system/agents/` |
| Registry | — | `cuebert/docs/_ai_system/rule_registry.md` |

---

## Milestones

> Sizing follows `cuebert-engineering.mdc`: each milestone is **300–800 lines** of deliverable output (new or materially edited), with **3–8 increments** where practical. Line estimates below use **measured** Cue sources where available; UE_CPP and new slims use engineering estimates.

### Milestone 1 — Python slim agents: Spec / Code / Review

**Demo sentence:** After M1, `/spec`, `/code`, and `/review` supervisor shortcuts can load **Python** slim agents that point at cuebert-local paths and rules.

| Increment | Deliverable | Est. lines | Notes |
|-----------|-------------|------------|-------|
| 1.1 | `.cursor/agents/spec-python.md` | ~129 | Port from Cue `spec-python.md` |
| 1.2 | `.cursor/agents/code-python.md` | ~229 | Port from Cue `code-python.md` |
| 1.3 | `.cursor/agents/review-python.md` | ~206 | Port from Cue `review-python.md` |

**Dependencies:** None.  
**Roll-up:** ~564 lines.

---

### Milestone 2 — Python slim agents: QA / Resilience / Research + Spec canonical

**Demo sentence:** QA and research slims exist for Python hub work, and the **agent-spec-python** canonical defines Spec-phase behavior for cuebert.

| Increment | Deliverable | Est. lines | Notes |
|-----------|-------------|------------|-------|
| 2.1 | `.cursor/agents/qa-python.md` | ~150 | Port |
| 2.2 | `.cursor/agents/qa-resilience-python.md` | ~52 | Port |
| 2.3 | `.cursor/agents/research-python.md` | ~37 | Coordinator slim; port |
| 2.4 | `docs/_ai_system/agents/agent-spec-python.md` | ~425 | Port; apply adaptation checklist |

**Dependencies:** M1 (slim naming consistency / cross-links).  
**Roll-up:** ~664 lines.

---

### Milestone 3 — Python Code canonical

**Demo sentence:** Code-phase behavior for hub Python (tests, build gate, depmap, memory tools) is fully specified in cuebert.

| Increment | Deliverable | Est. lines | Notes |
|-----------|-------------|------------|-------|
| 3.1 | `docs/_ai_system/agents/agent-coding-python.md` | ~876 | Port from Cue; heavy path/tool substitution; remove Cisco-only/API cruft per Cursor plan |

**Dependencies:** M2.  
**Roll-up:** ~876 lines (upper band; single-file milestone acceptable per decomposition table for ≤1200 with monitoring).

---

### Milestone 4 — Python Review canonical

**Demo sentence:** Review-phase passes and gates for Python hub work align with `cuebert-engineering.mdc` and shared lifecycle.

| Increment | Deliverable | Est. lines | Notes |
|-----------|-------------|------------|-------|
| 4.1 | `docs/_ai_system/agents/agent-review-python.md` | ~585 | Port; strip React roadmap / Cue Decision Trace |

**Dependencies:** M3.  
**Roll-up:** ~585 lines.

---

### Milestone 5 — CUEBERT system-authoring agents (slims + canonicals)

**Demo sentence:** `/spec`–`/code`–`/review` for **system authoring** (agents, rules, standards, skills) use dedicated CUEBERT agents and cuebert file layouts.

| Increment | Deliverable | Est. lines | Notes |
|-----------|-------------|------------|-------|
| 5.1 | `.cursor/agents/spec-cue.md` | ~31 | Port from Cue; triggers/`--cue` context for cuebert |
| 5.2 | `.cursor/agents/code-cue.md` | ~60 | New slim → canonical (Cue has no slim) |
| 5.3 | `.cursor/agents/review-cue.md` | ~60 | New slim → canonical |
| 5.4 | `docs/_ai_system/agents/agent-spec-cuebert.md` | ~190 | Adapt from `agent-spec-cue.md`; §3 file patterns for `.cursor/mcp-server/`, `.cursor/skills/`, `docs/_ai_system/` |
| 5.5 | `docs/_ai_system/agents/agent-coding-cuebert.md` | ~135 | Adapt from `agent-coding-cue.md`; registry + build verification for docs |
| 5.6 | `docs/_ai_system/agents/agent-review-cuebert.md` | ~168 | Adapt from `agent-review-cue.md`; Pass 1–5 for cuebert registry/supervisor |

**Dependencies:** M4 (pattern from Python canonicals).  
**Roll-up:** ~644 lines.

---

### Milestone 6 — UE_CPP: slims + `cuebert-ue-cpp.mdc` rule

**Demo sentence:** Supervisor can route UE C++ work to dedicated slims; cursor applies UE C++ standards when editing game module files.

| Increment | Deliverable | Est. lines | Notes |
|-----------|-------------|------------|-------|
| 6.1 | `.cursor/agents/code-ue-cpp.md` | ~90 | New |
| 6.2 | `.cursor/agents/review-ue-cpp.md` | ~90 | New |
| 6.3 | `.cursor/agents/spec-ue-cpp.md` | ~80 | New; lower dispatch frequency |
| 6.4 | `.cursor/rules/cuebert-ue-cpp.mdc` | ~90 | New; macros, GC, naming, scope guardrails, logging |

**Dependencies:** M5 (conventions for doc cross-links).  
**Roll-up:** ~350 lines.

---

### Milestone 7 — UE_CPP canonical agents

**Demo sentence:** Code and Review canonicals encode bridge contract, UBT evidence, UObject safety, and module boundaries for UE_CPP.

| Increment | Deliverable | Est. lines | Notes |
|-----------|-------------|------------|-------|
| 7.1 | `docs/_ai_system/agents/agent-coding-ue-cpp.md` | ~350 | New; bridge + build-verify + play-author surfaces |
| 7.2 | `docs/_ai_system/agents/agent-review-ue-cpp.md` | ~280 | New; five-pass review per Cursor plan |

**Dependencies:** M6.  
**Roll-up:** ~630 lines.

---

### Milestone 8 — Research swarm (coordinator + specialists + slims)

**Demo sentence:** Orchestrator can run structure / dependency / API research with merged **Codebase Context Brief** for `LANGUAGE` including **CUEBERT**, **PYTHON**, and **UE_CPP** (matrix updated in M12).

| Increment | Deliverable | Est. lines | Notes |
|-----------|-------------|------------|-------|
| 8.1 | `docs/_ai_system/agents/agent-research.md` | ~171 | Port; language matrix |
| 8.2 | `docs/_ai_system/agents/agent-research-structure.md` | ~127 | Port (Cue measured) |
| 8.3 | `docs/_ai_system/agents/agent-research-dependency.md` | ~128 | Port |
| 8.4 | `docs/_ai_system/agents/agent-research-api.md` | ~116 | Port |
| 8.5 | Specialist slims | ~120 | New e.g. `research-structure-python.md`, `research-dependency-python.md`, `research-api-python.md` (Cue uses framework-specific slims; cuebert uses Python/UE-neutral naming per orchestrator policy) |

**Dependencies:** M7.  
**Roll-up:** ~662 lines.

---

### Milestone 9 — Deploy + Production readiness

**Demo sentence:** Deploy harness and production-readiness hub align with cuebert’s pipeline (no Jira gate unless reintroduced later).

| Increment | Deliverable | Est. lines | Notes |
|-----------|-------------|------------|-------|
| 9.1 | `docs/_ai_system/agents/agent-deploy.md` | ~204 | Port; adapt chain vs Cue |
| 9.2 | `.cursor/agents/prod-readiness.md` | ~30 | Port slim |
| 9.3 | `docs/_ai_system/agents/agent-production-readiness.md` | ~206 | Port; scan categories for Python + UE_CPP |

**Dependencies:** M8.  
**Roll-up:** ~440 lines.

---

### Milestone 10 — Security auditor

**Demo sentence:** `/sec` resolves to security slim + canonical with language matrix for **PYTHON** and **UE_CPP** only.

| Increment | Deliverable | Est. lines | Notes |
|-----------|-------------|------------|-------|
| 10.1 | `.cursor/agents/security-auditor.md` | ~241 | Port |
| 10.2 | `docs/_ai_system/agents/agent-security.md` | ~438 | Port |

**Dependencies:** M9.  
**Roll-up:** ~679 lines.

---

### Milestone 11 — Test + Checkin agents

**Demo sentence:** Test promotion / exploration protocol and checkin gate exist without KACES-only or React/Angular assumptions.

| Increment | Deliverable | Est. lines | Notes |
|-----------|-------------|------------|-------|
| 11.1 | `docs/_ai_system/agents/agent-test-python.md` | ~520 | Port; strip KACES-only modes; focus Explore/Codify/Promote |
| 11.2 | `.cursor/agents/checkin.md` | ~29 | Port slim |
| 11.3 | `docs/_ai_system/agents/agent-checkin.md` | ~126 | Port |

**Dependencies:** M10.  
**Roll-up:** ~675 lines.

---

### Milestone 12 — Supervisor, registry, orchestrator matrix, QA skip rules

**Demo sentence:** All “Planned” engineering agents in `rule_registry.md` are **Active**; orchestrator dispatch table matches files on disk; supervisor no longer claims missing rules; QA skip conditions documented for **CUEBERT** vs **PYTHON** / **UE_CPP**.

| Increment | Deliverable | Est. lines | Notes |
|-----------|-------------|------------|-------|
| 12.1 | `cuebert-supervisor.mdc` + `docs/_ai_system/agents/agent-supervisor.md` | ~40 | Stale §0.5 placeholders removed; canonical supervisor doc for registry; PYTHON / CUEBERT / UE_CPP routing |
| 12.2 | `docs/_ai_system/rule_registry.md` | ~40 | Planned → Active + paths; research/deploy/security/test/checkin rows; `docs/reports/security/` first-use note |
| 12.3 | `docs/_ai_system/agents/agent-orchestrator.md` | ~50 | §4K Research; §6A Checkin anchor; dispatch matrix + language matrix; CUEBERT QA skip + UE_CPP QA notes |
| 12.4 | Cross-doc QA skip / `LANGUAGE: CUEBERT` | ~30 | Orchestrator §2 + §4 chain; `agent-security` / `security-auditor` B506 + `:latest` = **Medium** (gate may still REJECT) |

**Dependencies:** M11 (all agents exist before registry finalization).  
**Roll-up:** ~160 lines (edits across ~4 files; **terminal integration milestone** — below 300 lines of *new* prose but required to ship the set; treat as configuration + doc sync increment).

---

## Verification Contract

| Required item | Severity | Evidence |
|---------------|----------|----------|
| Every new/edited agent file starts with **Structured Reasoning Gate** (`sequentialthinking`) per `agent-shared-lifecycle.md` §1 / `cuebert-engineering.mdc` §0 | **REJECT** (Review Pass 0) | Spot-check: §1/activation in each canonical; slim points to canonical |
| **Plan present** with milestones + this contract | **REJECT** | This file path cited in handoffs |
| **No broken internal links** (`docs/_ai_system/`, `.cursor/`) | **REJECT** | Automated or manual link sweep; broken `](...)` → fix |
| **No stale Cue-only paths** (`docs/projects/{wrong}`, `cue-engineering.mdc`, `.cue/traces/`, Jira hooks) unless explicitly stubbed | **REJECT** | Grep evidence in Review |
| **`rule_registry.md`** entries for all delivered agents = **Active** with correct paths | **REJECT** | Diff + registry table |
| **`agent-orchestrator.md`** dispatch matrix matches slims + canonicals | **REJECT** | Diff excerpt |
| **Supervisor** reflects actual rule files | **REJECT** | Diff excerpt |
| **Adaptation checklist** applied on all Cue ports | **REJECT** | Review checklist sign-off in plan or Issue Register |
| Markdown lint (agents / plans) | **WARN** | Optional linter output attached |
| **Cross-reference check** (integration verify for CUEBERT docs) | **REJECT** if orphan agents referenced | Inventory: each registry row resolves to a file |
| **Build Verification Gate** for *runnable* Python touched in same change-set | **REJECT** when hub Python code (not doc-only) | Per `cuebert-engineering.mdc` §3 — N/A for pure markdown agent drops *unless* paired with code |
| **`milestone_commit` / `troubleshoot_*`** references use **cuebert-core** MCP naming | **WARN** | Consistency grep |
| UE_CPP agents reference **bridge contract** + **build-verify-gaming** | **REJECT** | Pass 0 on `agent-coding-ue-cpp.md` / `agent-review-ue-cpp.md` |

---

## Adaptation checklist (Cue → Cuebert ports)

Apply to all ported markdown:

| # | Find / pattern | Replace / action |
|---|----------------|------------------|
| 1 | `docs/projects/{PROJECT}/plans/active/` (Cue patterns) | `docs/projects/cuebert/plans/active/` (and dynamic `{PROJECT}` only where still valid) |
| 2 | `cue-engineering.mdc` | `cuebert-engineering.mdc` |
| 3 | `cue-supervisor.mdc` | `cuebert-supervisor.mdc` |
| 4 | `agent-shared-lifecycle.md` | Keep path under `docs/_ai_system/standards/` (already in cuebert) |
| 5 | `agent-orchestrator.md` | Cuebert version (already exists) |
| 6 | Jira hooks: `agent-ops-jira.md`, `.jira/pending/` | Remove; stub only if product owner requests |
| 7 | `.cue/traces/` Decision Trace | Remove or rename to `.cuebert/traces/` if adopted |
| 8 | React / Angular cross-references | Remove (QA matrices, research slims, etc.) |
| 9 | `LANGUAGE: CUE` skip conditions | `LANGUAGE: CUEBERT` (and add **PYTHON** / **UE_CPP** where applicable) |
| 10 | `control-plane-paths.md` | `docs/_ai_system/standards/control-plane-paths.md` (cuebert) |
| 11 | Memory tools | `milestone_commit`, `milestone_lookup`, `troubleshoot_commit`, `troubleshoot_search` via **cuebert-core** MCP |
| 12 | `⟨CueActivePlans⟩` or Cue branding | Cuebert plan paths / naming |
| 13 | Cisco-specific API / internal-only runbooks (if any in coding agent) | Remove or replace with cuebert depmap / generic guidance |
| 14 | KACES / `cue-feedback` (test agent) | Remove or gate — not cuebert’s default |

---

## Issue Register

| ID | Date | Milestone | Description | Owner | Status | Resolution / evidence |
|----|------|-----------|-------------|-------|--------|-------------------------|
| — | — | — | — | — | — | — |

---

## Task log (execution)

| # | Task | Files (lines) | Tests | Status | Notes |
|---|------|---------------|-------|--------|-------|
| M1.1 | Python slim — Spec | `.cursor/agents/spec-python.md` (127) | N/A (markdown) | done | Port from Cue; adaptation checklist; `⟨CuebertActivePlans⟩`; no Jira / `.cue` / Cue-only paths |
| M1.2 | Python slim — Code | `.cursor/agents/code-python.md` (227) | N/A (markdown) | done | Memory tools via **cuebert-core** MCP; depmap aligned to `dependency-architecture.md` + `cuebert-engineering.mdc` §3 |
| M1.3 | Python slim — Review | `.cursor/agents/review-python.md` (202) | N/A (markdown) | done | Canonical `agent-review-python.md` forward-ref **M4**; Pass 1 dependency rules per cuebert standard |
| M2.1 | Python slim — QA | `.cursor/agents/qa-python.md` (150) | N/A (markdown) | done | Global baseline Python-only; no React/Angular matrix; depmap + pytest/ruff/mypy |
| M2.2 | Python slim — QA Resilience | `.cursor/agents/qa-resilience-python.md` (52) | N/A (markdown) | done | L2 references `qa-python.md` result format; orchestrator §4C |
| M2.3 | Python slim — Research | `.cursor/agents/research-python.md` (39) | N/A (markdown) | done | `agent-research.md` forward-ref **M8** documented in slim |
| M2.4 | Python canonical — Spec | `docs/_ai_system/agents/agent-spec-python.md` (427) | N/A (markdown) | done | `⟨CuebertActivePlans⟩`; Jira/`.cue` removed; cuebert-engineering + cuebert-supervisor; cuebert-core MCP note §1A |
| M3.1 | Python canonical — Code | `docs/_ai_system/agents/agent-coding-python.md` (880) | N/A (markdown) | done | Port from Cue; Cisco/Jira/React/Zod stripped; depmap toolkit paths; `LANGUAGE: CUEBERT` gate note; Decision Trace + optional `.cuebert/traces/`; cuebert-core MCP for memory tools |
| M4.1 | Python canonical — Review | `docs/_ai_system/agents/agent-review-python.md` (527) | N/A (markdown) | done | Port from Cue; Pass 0 Verification Contract + `cuebert-engineering.mdc` §3 BVG; depmap (`python_ast_map.py`, `graph_cycles.py`, `dependency-architecture.md`); thresholds from `agent-coding-python.md` §2; Jira/roadmap/React trace removed; Cuebert Decision Trace + optional `.cuebert/traces/` |
| M5.1 | CUEBERT slim — Spec | `.cursor/agents/spec-cue.md` (25) | N/A (markdown) | done | Port from Cue `spec-cue.md`; `⟨CuebertActivePlans⟩`; canonical `agent-spec-cuebert.md`; MCP gate per `cuebert-engineering.mdc` §0 |
| M5.2 | CUEBERT slim — Code | `.cursor/agents/code-cue.md` (47) | N/A (markdown) | done | New slim → `agent-coding-cuebert.md`; CUEBERT BVG (cross-ref, stale Cue grep, md lint advisory) |
| M5.3 | CUEBERT slim — Review | `.cursor/agents/review-cue.md` (43) | N/A (markdown) | done | New slim → `agent-review-cuebert.md`; Pass 0–5 summary + registry/supervisor pointers |
| M5.4 | CUEBERT canonical — Spec | `docs/_ai_system/agents/agent-spec-cuebert.md` (217) | N/A (markdown) | done | Adapt from Cue `agent-spec-cue.md`; §3 layout (mcp-server, skills, agents, rules, standards, registry); Jira/React removed; `LANGUAGE: CUEBERT` handoff |
| M5.5 | CUEBERT canonical — Code | `docs/_ai_system/agents/agent-coding-cuebert.md` (150) | N/A (markdown) | done | Adapt from `agent-coding-cue.md`; `server.py` GROUPS + `rule_registry.md`; CUEBERT verify table |
| M5.6 | CUEBERT canonical — Review | `docs/_ai_system/agents/agent-review-cuebert.md` (189) | N/A (markdown) | done | Adapt from `agent-review-cue.md`; Pass 0–5 for cuebert; no `.cursorrules`; cross-ref + Cue-path rejection |
| M6.1 | UE_CPP slim — Code | `.cursor/agents/code-ue-cpp.md` (82) | N/A (markdown) | done | New; canonical forward-ref **M7** `agent-coding-ue-cpp.md`; bridge + build-verify + play-author §5.1; SR gate |
| M6.2 | UE_CPP slim — Review | `.cursor/agents/review-ue-cpp.md` (70) | N/A (markdown) | done | New; canonical forward-ref **M7** `agent-review-ue-cpp.md`; five passes; SR gate |
| M6.3 | UE_CPP slim — Spec | `.cursor/agents/spec-ue-cpp.md` (68) | N/A (markdown) | done | New; planning focus; M7 canonical forward-ref; scope + Build.cs table |
| M6.4 | UE_CPP rule | `.cursor/rules/cuebert-ue-cpp.mdc` (79) | N/A (markdown) | done | New; globs `**/*.cpp`, `**/*.h`, `**/*.Build.cs`; macros, GC, scope, logging, IWYU |
| M7.1 | UE_CPP canonical — Code | `docs/_ai_system/agents/agent-coding-ue-cpp.md` (322) | N/A (markdown) | done | New; SR gate, DECLARED_SCOPE surfaces, UObject/GC, modules, bridge contract, BVG/Gauntlet, handoff §12 |
| M7.2 | UE_CPP canonical — Review | `docs/_ai_system/agents/agent-review-ue-cpp.md` (271) | N/A (markdown) | done | New; Pass 0–5 (BVG+contract, module, UObject, scope, naming, integration), PASS/WARN/REJECT, SUBAGENT ERROR on REJECT |
| M7.3 | UE_CPP slims — cross-link | `.cursor/agents/code-ue-cpp.md` (82), `review-ue-cpp.md` (71), `spec-ue-cpp.md` (68) | N/A (markdown) | done | Canonical pointers updated; review slim pass order matches canonical; spec slim cites canonical sections |
| M8.1 | Research — coordinator | `docs/_ai_system/agents/agent-research.md` (177) | N/A (markdown) | done | Port from Cue; LANGUAGE **PYTHON** / **CUEBERT** / **UE_CPP**; React/Angular removed; `dependency-architecture.md` cross-ref; Python specialist slims in §6 |
| M8.2 | Research — structure | `docs/_ai_system/agents/agent-research-structure.md` (126) | N/A (markdown) | done | Port; UE_CPP + hub scan targets; LANGUAGE table; depmap N/A here |
| M8.3 | Research — dependency | `docs/_ai_system/agents/agent-research-dependency.md` (134) | N/A (markdown) | done | **`python_ast_map.py`**, **`module_dep_scan.py`**, **`graph_cycles.py`**; dual-domain **`dependency-architecture.md`**; CUEBERT docs-only skip |
| M8.4 | Research — API | `docs/_ai_system/agents/agent-research-api.md` (116) | N/A (markdown) | done | MCP + hub routes; **`unreal-bridge-contract.md`** for UE_CPP; no orphan Cue-only symmetry file ref |
| M8.5 | Research — Python slims | `.cursor/agents/research-structure-python.md` (35), `research-dependency-python.md` (37), `research-api-python.md` (35) | N/A (markdown) | done | **`cuebert-engineering.mdc` §0** SR gate; point to canonicals + depmap toolkit |
| M9.1 | Deploy harness | `docs/_ai_system/agents/agent-deploy.md` (204) | N/A (markdown) | done | Cuebert `/d` chain: PR REJECT → Security → Memory → Checkin; Jira removed; preview §7 = `agent-orchestrator.md` §8 + `cuebert_system_check`; `/ship` + `prod-readiness-game-rules.md` called out; LANGUAGE PYTHON \| CUEBERT \| UE_CPP |
| M9.2 | Prod readiness slim | `.cursor/agents/prod-readiness.md` (32) | N/A (markdown) | done | SR + canonical pointer; gaming scan split noted (`agent-prod-readiness-game` / `prod-readiness-game-rules.md`) |
| M9.3 | Prod readiness canonical | `docs/_ai_system/agents/agent-production-readiness.md` (219) | N/A (markdown) | done | Hub-focused categories (Python, CUEBERT, UE_CPP); React/Angular/Jest/Storybook stripped; cross-ref **`docs/_ai_system/standards/prod-readiness-game-rules.md`**; forward-ref Security/Checkin slims **M10–M11** |
| M10.1 | Security — slim | `.cursor/agents/security-auditor.md` (247) | N/A (markdown) | done | Port from Cue; `/sec`; PYTHON + UE_CPP matrix only; React/JS removed; `⟨CuebertActivePlans⟩` + `control-plane-paths.md` §2; Cuebert severity; `cuebert-ue-cpp.mdc`, `unreal-bridge-contract.md`; §12 handoff |
| M10.2 | Security — canonical | `docs/_ai_system/agents/agent-security.md` (435) | N/A (markdown) | done | Port from Cue; scanner matrix PYTHON + UE_CPP; React/Go/npm stripped; UE SCA (`Build.cs`, `uplugin`, `.uproject`) + patterns; `sequentialthinking` first action; `agent-deploy.md` gate alignment; mitosis targets `agent-security-ue-cpp.md` |
| M11.1 | Test — canonical (Python) | `docs/_ai_system/agents/agent-test-python.md` (498) | N/A (markdown) | done | Port from Cue; KACES / `cue-feedback` / Feedback mode removed; Explore/Codify/Promote only; `.cuebert/registry/skills.yaml`; `⟨CuebertActivePlans⟩` + `control-plane-paths.md`; BVG §3.5 (`cuebert-engineering.mdc` §3, `agent-coding-python.md` §4); `/code --cue` toolkit paths; vault-standard pointer |
| M11.2 | Checkin — slim | `.cursor/agents/checkin.md` (29) | N/A (markdown) | done | Port from Cue; canonical §3 filename derivation (no `docs/checkins/README.md` dependency); `agent-shared-lifecycle.md` §12 |
| M11.3 | Checkin — canonical | `docs/_ai_system/agents/agent-checkin.md` (132) | N/A (markdown) | done | Port from Cue; `PROJECT` examples → cuebert/workspace keys; orchestrator/deploy paths hub-local; create `docs/checkins/` if missing |
| M12.1 | Supervisor integration | `.cursor/rules/cuebert-supervisor.mdc`, `docs/_ai_system/agents/agent-supervisor.md` (new) | N/A (markdown) | done | §0.5 rules point to active `cuebert-ue-cpp.mdc` / `cuebert-engineering.mdc`; registry cross-link path; `/sec` slim pointer |
| M12.2 | Rule registry — hub engineering | `docs/_ai_system/rule_registry.md` | N/A (markdown) | done | All M1–M11 hub agents Active + canonical/slim paths; research swarm; deploy/test/checkin; security report dir note |
| M12.3 | Orchestrator — matrix + §6A + §4K | `docs/_ai_system/agents/agent-orchestrator.md` | N/A (markdown) | done | Fixes bogus `§6A` ref (now real subsection); Research phase; removes “planned” slims; CUEBERT QA skip explicit; UE_CPP QA routing note |
| M12.4 | Security severity WARN alignment | `.cursor/agents/security-auditor.md`, `docs/_ai_system/agents/agent-security.md` | N/A (markdown) | done | B506 + `FROM :latest` = **Medium** in slim; canonical unchanged for B506/:latest; REJECT as gate guidance only; audit dir mkdir note |

**M9 adaptation checklist (Cue → Cuebert):** Items 1–14 applied on all three ported files (paths → `docs/projects/cuebert/plans/active/`, `cuebert-engineering.mdc` / `cuebert-supervisor.mdc`, no Jira / `.cue` / Cue-only deploy chain, no React/Angular matrices, `LANGUAGE: CUEBERT` + PYTHON/UE_CPP, `control-plane-paths.md` full path, memory tools → **cuebert-core** MCP, Cuebert branding, Cisco/KACES stripped where present, `⟨CuebertActivePlans⟩` N/A in these agents).

**M10 adaptation checklist (Cue → Cuebert):** Items 1–14 applied on both ported files: plan roots → `docs/projects/cuebert/plans/active/` + `⟨CuebertActivePlans⟩` via `docs/_ai_system/standards/control-plane-paths.md` §2; `cuebert-engineering.mdc` / `cuebert-supervisor.mdc` / shared lifecycle references; no Jira or `.cue/traces`; React / Angular / npm audit and Go scanning removed; `LANGUAGE` envelope **PYTHON** / **CUEBERT** / **UE_CPP** called out where context matters; no stray `control-plane-paths.md` bare path; Cue → **Cuebert** severity naming; `⟨CuebertActivePlans⟩` replaces Cue branding; no Cisco-only runbooks; no KACES / `cue-feedback`; project-profile **when present**; memory tools N/A in these two files.

**M11 adaptation checklist (Cue → Cuebert):** Items 1–14 applied on all three ported files: active plans → `⟨CuebertActivePlans⟩` / `docs/_ai_system/standards/control-plane-paths.md` §2; `cuebert-engineering.mdc` §0/§3 (SR gate + BVG) and `agent-coding-python.md` §4 for pytest; hub registry **`.cuebert/registry/skills.yaml`** (not `cue/.cue/`); `/code --cue` for toolkit/skill work; no Jira; no `.cue/traces`; no React/Angular; item 14 — **KACES**, **`cue-kaces-feedback`**, and **Feedback mode** stripped from test agent; Cisco **`init-vault.py`** replaced with **`vault-standard.md`**; memory toolkit excluded from checkin; orchestrator/deploy refs as **`docs/_ai_system/agents/...`**; **`cuebert-core`** `build_verify` named in test agent BVG; promotion references **`agent-coding-cuebert.md`** / **`_template_tool.py`** instead of missing Cue-only standards.

---

## References

- Input spec: `cursor_plan:/Users/ambtaylo/.cursor/plans/cuebert_full_agent_set_77d31cef.plan.md`
- Cue sources: `/Users/ambtaylo/CursorProjects/cue/.cursor/agents/`, `/Users/ambtaylo/CursorProjects/cue/docs/_ai_system/agents/`
- Standards: `docs/_ai_system/standards/agent-shared-lifecycle.md` §8 (plan updates), §12 (subagent results)
- Workflow: `.cursor/rules/cuebert-engineering.mdc` §3 (build gate), §4 (enforcement)
