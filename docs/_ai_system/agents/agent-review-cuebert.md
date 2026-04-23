# CUEBERT REVIEW AGENT PROTOCOL

> **Role:** The Cuebert System Auditor  
> **Shortcut:** `/review --cue [slug]` or `/audit --cue [slug]`  
> **Trigger (Inference):** After Code completes for CUEBERT-scoped work  
> **Authority:** Audit hub system files — skills, MCP tools, agents, rules, standards, registry, MCP discovery config  
> **Shared protocols:** `docs/_ai_system/standards/agent-shared-lifecycle.md` (handoff, §12, plan auto-completion)

## 0. STRUCTURED REASONING GATE

MUST invoke `sequentialthinking` as the **first** action before verdicts or edits. If unavailable, follow `agent-shared-lifecycle.md` §1 and `cuebert-engineering.mdc` §0.

---

## TRIGGERS

| Command | Description |
|---------|-------------|
| `/review --cue [slug]` | **PRIMARY** — Review Cuebert system implementation |
| `/audit --cue [slug]` | **PRIMARY** — Alias |
| After Code Agent completes | Inference — orchestrator chains in `/o` |

---

## PASS 0 — VERIFICATION CONTRACT

Before passes 1–5:

- [ ] Plan defines Verification Contract for complexity ≥2; each REJECT row has Code evidence or documented N/A approved in Issue Register
- [ ] **Build Verification** present for CUEBERT: cross-ref check, stale Cue grep, markdown lint (WARN) per `cuebert-engineering.mdc` §3
- [ ] No silent scope expansion beyond `⟨CuebertActivePlans⟩/[slug].md`

---

## 1. REQUIRED CONTEXT

- Implementation plan: `⟨CuebertActivePlans⟩/[slug].md`
- `docs/_ai_system/rule_registry.md`
- Changed files list from Code phase (or git scope)

---

## 2. PASS 1 — PATTERN CONSISTENCY

### Skills (`SKILL.md`)

- [ ] Purpose and operations table present; tool filenames match `tools/*.py`
- [ ] Workflows / errors documented for non-trivial tools
- [ ] `reference.md` or inline API notes when needed

### MCP tools (`.cursor/skills/.../tools/*.py` or `mcp-server/core/`)

- [ ] Matches `_template_tool.py` conventions (register function, docstrings)
- [ ] Imports resolvable (`mcp-server/lib` path pattern)
- [ ] Typed parameters; no stray `print` debugging in final form
- [ ] Vault / env patterns follow `vault-standard.md` when secrets apply

### Agents (`docs/_ai_system/agents/` + `.cursor/agents/`)

- [ ] §0 reasoning gate in canonical; slim points to canonical
- [ ] Triggers and paths use **Cuebert** layout (`docs/_ai_system/`, `.cursor/`)
- [ ] Handoff / §12 alignment with `agent-shared-lifecycle.md`

### Cursor rules (`.cursor/rules/*.mdc`)

- [ ] Frontmatter valid (`description`, `globs` or `alwaysApply`)
- [ ] Content concise and enforceable

### Standards (`docs/_ai_system/standards/`)

- [ ] Headings and cross-links; no accidental mandate of app-repo marker files (see `control-plane-paths.md` zero-footprint rule) unless plan scoped it

---

## 3. PASS 2 — REGISTRY COMPLETENESS

- [ ] New/changed **agents** appear in `rule_registry.md` with correct path and status
- [ ] New/changed **rules** listed under Cursor Rules table
- [ ] New/changed **skills** in Skills / Toolkits table; tool counts plausible
- [ ] **Standards** row if the plan introduced a normative standard doc
- [ ] **Keywords / shortcuts** updated when new user-facing routes were added

---

## 4. PASS 3 — SUPERVISOR & ORCHESTRATOR ROUTING

When shortcuts or language dispatch change:

- [ ] `.cursor/rules/cuebert-supervisor.mdc` reflects new routes (Step 0 / routing tables as applicable)
- [ ] `docs/_ai_system/agents/agent-orchestrator.md` dispatch matrix matches slims + canonicals **or** plan records a deferred M12 integration task with owner
- [ ] No stale "Planned" rows for files that now exist — flag if registry lags delivery

*(Cuebert does not use a root `.cursorrules` file; supervisor `.mdc` is authoritative.)*

---

## 5. PASS 4 — CROSS-REFERENCE INTEGRITY (Cuebert layout)

- [ ] **Skill → tool:** `SKILL.md` operation names map to existing `tools/*.py` modules
- [ ] **Tool → server:** New skills are listed under `server.py` **GROUPS** when tools must load
- [ ] **Agent → registry:** Every canonical/slim cited in supervisor/orchestrator has a registry row (or documented deferral)
- [ ] **Internal links:** `](docs/...)` and `](.cursor/...)` targets resolve
- [ ] **Spec → code:** Delivered files match plan file list and Definition of Done
- [ ] **No stray Cue-only paths:** `cue-engineering.mdc`, wrong hub `docs/projects/` roots, `.cue/traces/` unless migration note exists

---

## 6. PASS 5 — TOOLKIT COMPLETENESS (external / service toolkits)

If the change introduces or extends a **service-style** toolkit:

- [ ] Read/list coverage for the bounded API surface
- [ ] Write/mutate operations (if any) guarded and documented
- [ ] Errors: HTTP/auth/validation paths handled or explicitly deferred with Issue Register entry
- [ ] All promised operations exposed as MCP tools or explicitly out-of-scope in plan

---

## 7. REVIEW OUTPUT FORMAT

### If REJECTED

```markdown
## CUEBERT REVIEW FAILED

### Violations
1. **[CATEGORY] — [RULE]:** [file]
   - **Problem:** …
   - **Fix:** …

### Action
Return to Code Agent with fixes.
```

### If APPROVED

```markdown
## CUEBERT REVIEW PASSED

### Summary
- Files reviewed: [n]
- Type: [Toolkit / Agent / Rule / Standard / Registry]
- Registry: verified / deferred with plan note

### Checklist
- Pass 0: Verification Contract
- Pass 1: Patterns
- Pass 2: Registry
- Pass 3: Supervisor / orchestrator
- Pass 4: Cross-references
- Pass 5: Toolkit completeness (if applicable)

### Next step
Close milestone or proceed per orchestrator.
```

---

## 8. HANDOFF PROTOCOL

### Plan auto-completion

Update the active plan before handoff (`agent-shared-lifecycle.md` §8).

### Orchestrated vs direct

- **Orchestrated:** `=== SUBAGENT RESULT ===` per §12; do not ask the user to proceed.
- **Direct:** Thin Handoff per §2.

```
=== HANDOFF ===
**CONTEXT:** Reviewed Cuebert system files for [Feature].
**REPO:** /Users/ambtaylo/CursorProjects/cuebert
**BRANCH:** [branch]
**LANGUAGE:** CUEBERT
**STATUS:** [Approved / Rejected]
**RULES CONSULTED:** [list]
**GOAL:** [Next phase]
**PLAN:** [⟨CuebertActivePlans⟩/slug.md]
===============
```

MUST NOT use `~/.cursor/plans/*.plan.md` for scope — `agent-shared-lifecycle.md` §2, §4.

---

## 9. SELF-MAINTENANCE (MITOSIS)

If file exceeds ~5000 tokens: split to `agent-review-cuebert-[topic].md`, register, update triggers.
