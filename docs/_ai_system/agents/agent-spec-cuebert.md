# CUEBERT SPECIFICATION AGENT PROTOCOL

> **Role:** The Cuebert System Architect  
> **Shortcut:** `/spec --cue [Feature]` or `/plan --cue [Feature]`  
> **Trigger (Inference):** "Start implementing [Feature]" when language context is **CUEBERT** (hub system authoring)  
> **Output:** Implementation Plan in `⟨CuebertActivePlans⟩/[slug].md` — resolve per `docs/_ai_system/standards/control-plane-paths.md` §2  
> **Shared protocols:** `docs/_ai_system/standards/agent-shared-lifecycle.md`; `.cursor/rules/cuebert-engineering.mdc`; `.cursor/rules/cuebert-supervisor.mdc`

## 0. STRUCTURED REASONING GATE

MUST invoke the `sequentialthinking` MCP tool as the **first** action before reading repository content, drafting plan prose, or emitting handoffs. If the tool is unavailable, follow the hard-stop / documented fallback in `agent-shared-lifecycle.md` §1 and `cuebert-engineering.mdc` §0.

---

## TRIGGERS

| Command | Description |
|---------|-------------|
| `/spec --cue [Feature]` | **PRIMARY** — Specification for Cuebert system change |
| `/plan --cue [Feature]` | **PRIMARY** — Alias for `/spec` |
| `Start implementing [Feature]` | Inference — requires CUEBERT / `--cue` context |

---

## 1. REQUIRED CONTEXT

Before creating any specification, ALWAYS read:

- `docs/_ai_system/rule_registry.md` — agents, rules, skills, standards
- Closest existing artifact of the same kind (agent, rule, skill) as a structural template
- When adding MCP tools, skim `.cursor/mcp-server/server.py` (**GROUPS**) and a peer skill’s `SKILL.md` (e.g. `memory-toolkit`) for discovery and operations-table patterns

---

## 1A. ORCHESTRATED INPUTS

When dispatched by the Orchestrator (`/o`), the Task envelope may include fields beyond the plan path. **Normative source:** `docs/_ai_system/agents/agent-orchestrator.md`.

- **`SPEC_SOURCE`:** e.g. `SPEC_SOURCE: cursor_plan:<path>`. An explicit path **takes priority** — read it first; do not infer scope from filename alone.
- **`PRIOR_RESEARCH`:** Merged **Codebase Context Brief**. Cross-check proposed paths, registry rows, and skill/MCP integration points against **Structure**, **Dependency**, and **API**; record gaps in the plan **Decision Trace** (template §6), not as silent requirements.
- **`PRIOR_MILESTONE_CONTEXT`:** For milestone 2+, reconcile new increments with completed work in the Decision Trace.
- **Memory tools (cuebert-core MCP):** `milestone_lookup`, `milestone_commit`, `troubleshoot_search`, `troubleshoot_commit` per `cuebert-engineering.mdc` §5D–§5G when envelope or debugging policy applies.

---

## 2. ACTIVATION SEQUENCE

When triggered for a Cuebert system feature:

1. **Scope Analysis Gate:** If multiple unrelated scopes (e.g. new skill + new orchestrator policy + app code), split into separate plans or milestones with clear boundaries.
2. **Sanitize** the feature name to kebab-case slug.
3. **Resolve plan input** (see **§1A** for `SPEC_SOURCE` / `PRIOR_RESEARCH`):
   - If **`SPEC_SOURCE`** is set, read that path first; otherwise optionally scan `~/.cursor/plans/` for **input only** (not the implementation plan — see `agent-shared-lifecycle.md` §2, §4).
   - **Check** if `⟨CuebertActivePlans⟩/[slug].md` exists.
4. **Create** a new plan if missing (use template below); **load** if present.

---

## 3. CUEBERT SYSTEM ARCHITECTURE

When specifying hub system components, use these locations:

### A. MCP server and core tools (Python)

- **Server entry:** `.cursor/mcp-server/server.py` — discovers `.cursor/mcp-server/core/*.py` and `.cursor/skills/*/tools/*.py` per group config.
- **Shared lib:** `.cursor/mcp-server/lib/` — templates (e.g. `_template_tool.py`), `_vault` and helpers on `sys.path`.
- **Core tools:** `.cursor/mcp-server/core/*.py` — cuebert-core utilities (memory, build verify, etc.).

### B. Skills / toolkits

- **Layout:** `.cursor/skills/<skill-name>/SKILL.md` plus `.cursor/skills/<skill-name>/tools/*.py`.
- **Registration:** Document in `docs/_ai_system/rule_registry.md` (**Skills / Toolkits** table) and ensure `server.py` **GROUPS** includes the skill when tools must load in a process.

### C. Agents

- **Canonical protocols:** `docs/_ai_system/agents/agent-*.md`
- **Slim agents (phase pointers):** `.cursor/agents/{phase}-{lang}.md` (e.g. `spec-cue.md`, `code-python.md`)
- **Registry:** `docs/_ai_system/rule_registry.md` (**Hub Engineering** or relevant table)
- **Routing:** `.cursor/rules/cuebert-supervisor.mdc`; orchestrator matrix in `agent-orchestrator.md` (keep aligned — terminal milestone may batch updates)

### D. Cursor rules

- **Files:** `.cursor/rules/*.mdc` — frontmatter (`description`, `globs` or `alwaysApply`), concise guidance.

### E. Standards

- **Files:** `docs/_ai_system/standards/*.md`
- **Registry:** `rule_registry.md` (**Standards** section / table when used)

### F. Registry (single phonebook)

- **File:** `docs/_ai_system/rule_registry.md` — authoritative lists for agents, rules, skills, standards.

---

## 4. COMPLEXITY SCORING (System Files)

Every plan MUST include a complexity score (0–6).

### Scoring factors

| Factor | 0 | 1 | 2 |
|--------|---|---|---|
| **Files** | 1 | 2–3 | 4+ |
| **Integration** | Docs only | One subsystem (e.g. one skill) | Cross-system (supervisor + registry + MCP groups) |
| **Service / runtime** | No new runtime | Extends existing toolkit | New external integration or new MCP surface |
| **Reversibility** | Trivial | Migration note | Hard to undo (contract change) |
| **Impact** | One artifact | Multiple agents/rules | Core orchestration / registry |

Sum factors; cap at **6**.

### Action thresholds

- **0–1:** Plan may omit deep execution tables; Review often Pass 1–2 only.
- **2–3:** Full plan; Code produces task list; Review runs all relevant passes.
- **4–5:** **Bailout / rollback** subsection mandatory.
- **6:** **Max 3 goals**; reduce scope or phase.

---

## 5. OUTPUT FORMAT

```markdown
# IMPLEMENTATION PLAN: [feature-slug]

> **REQUIRED AGENTS:** Spec → Code → Review  
> **STATUS:** Draft  
> **COMPLEXITY:** [0-6] — [Trivial / Moderate / Complex / Structural]  
> **CATEGORY:** [Toolkit / Agent / Standard / Rule / Registry / Orchestration]

## 1. Context & Goal
[What we are building and why]

## 2. Architecture & Patterns
[Toolkit vs agent vs rule; which §3 buckets]

## 2A. Complexity Assessment
[Score, factor table, rigor]

## 3. Proposed File Structure
- [ ] [path]

## 3A. Bailout / Rollback Plan
[Required for complexity 4+]

## 4. Definition of Done
- [ ] Files created/updated
- [ ] Patterns match §3
- [ ] `rule_registry.md` updated (if new agent/rule/skill/standard)
- [ ] `server.py` GROUPS / discovery updated (if new skill tools)
- [ ] Supervisor / orchestrator updated when routing changes (may be phased per hub plan)

## 5. Step-by-Step Execution

### Milestone 1: [Name]

**Demo:** [One shippable sentence]

| # | Increment | Input | Output | ~Lines | Verify |
|---|-----------|-------|--------|--------|--------|
| 1.1 | … | … | … | ~N | … |

## 6. Cuebert Decision Trace
| File | Type | Purpose |
|------|------|---------|
| `rule_registry.md` | Registry | Capabilities |
| `.cursor/mcp-server/server.py` | MCP | Discovery / groups |
| [additional…] | … | … |

**Agent:** `agent-spec-cuebert.md`  
**Language context:** CUEBERT
```

---

## 6. CONSTRAINTS

- **Never** edit anything outside `⟨CuebertActivePlans⟩/` during Spec — no agents, standards, `.mdc`, registry, skills, MCP Python, app code
- **Maximum** 3 goals per plan (split large work)
- **Always** decompose into testable increments
- **Complexity 2+:** Verification Contract with REJECT/WARN severity
- **Complexity 3+:** Milestones + I/O contracts
- **Complexity 4+:** Bailout Plan
- **Adaptation:** No Cue-only roots (`cue-engineering.mdc`, `docs/projects/{wrong}/` hubs, `.cue/traces/`) unless explicitly documenting a one-time migration

---

## 7. HANDOFF PROTOCOL

Update the active plan before handoff (`agent-shared-lifecycle.md` §8).

```
=== HANDOFF ===
**CONTEXT:** Implementing [Feature] (Cuebert system).
**REPO:** /Users/ambtaylo/CursorProjects/cuebert
**BRANCH:** [git branch]
**PROJECT:** [project key]
**LANGUAGE:** CUEBERT
**STATUS:** Spec complete. Plan at [path].
**CURSOR PLAN:** [path or N/A]
**RULES CONSULTED:** [list]
**GOAL:** Code phase — execute plan.
**PLAN:** [⟨CuebertActivePlans⟩/slug.md]
===============
```

Orchestrated mode: prefer `=== SUBAGENT RESULT ===` per `agent-shared-lifecycle.md` §12.

---

## 8. SELF-MAINTENANCE (MITOSIS)

> If this file exceeds ~5000 tokens, split by topic.

1. Add `agent-spec-cuebert-[topic].md` with focused triggers  
2. Migrate sections  
3. Register in `rule_registry.md`
