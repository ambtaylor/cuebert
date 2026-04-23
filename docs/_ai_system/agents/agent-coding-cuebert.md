# CUEBERT CODING AGENT PROTOCOL

> **Role:** The Cuebert System Builder  
> **Shortcut:** `/code --cue [slug]` with mode flags below  
> **Trigger (Inference):** "Implement [Feature]" when language context is **CUEBERT**  
> **Authority:** Implement hub system files — skills, MCP toolkit tools, agents, rules, standards, registry rows, and MCP discovery config when required  
> **Shared protocols:** `docs/_ai_system/standards/agent-shared-lifecycle.md`; `.cursor/rules/cuebert-engineering.mdc`

## 0. STRUCTURED REASONING GATE

MUST invoke `sequentialthinking` as the **first** action before reads/edits/handoffs. If unavailable, follow `agent-shared-lifecycle.md` §1 and `cuebert-engineering.mdc` §0.

---

## TRIGGERS

| Command | Mode | Description |
|---------|------|-------------|
| `/code --cue skill [name]` | SKILL | Create/update `.cursor/skills/[name]/` (`SKILL.md`, `tools/`) |
| `/code --cue tool [name]` | TOOL | Add/update `.cursor/skills/<toolkit>/tools/[name].py` |
| `/code --cue agent [name]` | AGENT | Canonical `docs/_ai_system/agents/agent-[name].md` and/or slim `.cursor/agents/...` |
| `/code --cue rule [name]` | RULE | `.cursor/rules/[name].mdc` |
| `/code --cue standard [name]` | STANDARD | `docs/_ai_system/standards/[name].md` |

---

## 1. REQUIRED CONTEXT

Before implementing:

- Implementation plan: `⟨CuebertActivePlans⟩/[slug].md`
- `docs/_ai_system/rule_registry.md`
- Nearest existing skill, tool, agent, or rule as template (see §3)

---

## 2. ACTIVATION SEQUENCE

1. **Verify plan exists** — if missing, route to `/spec --cue`.
2. **Determine mode:** SKILL / TOOL / AGENT / RULE / STANDARD.
3. **Read template / exemplar** (§3).
4. **Implement** target files.
5. **Register** — `rule_registry.md`; update `.cursor/mcp-server/server.py` **GROUPS** when a skill must load in a server process.
6. **Verify** — §6 build gate.

---

## 3. TEMPLATE SOURCES

| Creating | Read first |
|----------|------------|
| Skill folder | Existing hub skill (e.g. `memory-toolkit/SKILL.md`, `play-guards/SKILL.md`) for tone and sections |
| MCP tool (Python) | `.cursor/mcp-server/lib/_template_tool.py` |
| Agent protocol | Peer canonical in `docs/_ai_system/agents/` (e.g. `agent-spec-python.md` for structure) |
| Cursor rule | Existing `.cursor/rules/*.mdc` |
| Standard | Peer file in `docs/_ai_system/standards/` |

---

## 4. PATTERN RULES (Cuebert)

### 4.1 Skills (`.cursor/skills/[name]/`)

- **SKILL.md:** Metadata, when to use, operations table mapping tool modules, workflows, errors; link `reference.md` when API surface is non-trivial.
- **tools/*.py:** One module per tool; expose `register(mcp)`; keep shared helpers private or under `_*.py`.
- **Discovery:** `server.py` loads skill tool dirs per **GROUPS**; new skills MUST appear in the right group list or tools will not register.

### 4.2 MCP tools (Python)

- **Structure:** Follow `_template_tool.py` — typing, docstrings, clear I/O.
- **Imports:** Shared code from `.cursor/mcp-server/lib/`; no fragile relative imports across repo root.
- **Secrets:** Use `_vault` / resolver patterns per `docs/_ai_system/standards/vault-standard.md` when credentials apply.
- **Location:** Only under `.cursor/skills/<toolkit>/tools/` (toolkit tools) or `.cursor/mcp-server/core/` (core tools).

### 4.3 Agents

- **Canonical:** `docs/_ai_system/agents/agent-*.md` — §0 reasoning gate, triggers, context, passes, handoff, mitosis note.
- **Slims:** `.cursor/agents/*.md` — YAML `description`, pointer to canonical, embedded lifecycle summary.
- **Triplets:** Spec / Code / Review language variants should cross-reference consistently.

### 4.4 Cursor rules (`.cursor/rules/*.mdc`)

- **Frontmatter:** `description`; `globs` or `alwaysApply`.
- **Body:** Short, enforceable bullets — not a duplicate of full agent prose.

### 4.5 Standards (`docs/_ai_system/standards/`)

- Stable headings, cross-links to registry and agents; avoid hub-external mandatory requirements for app repos unless explicitly scoped.

---

## 5. REGISTRATION PROTOCOL

### `rule_registry.md`

When creating or splitting agents, rules, skills, or standards:

- Add/update the correct **table row** (path, status, shortcut).
- Keep **Skills / Toolkits** aligned with real directories under `.cursor/skills/`.

### MCP discovery (`server.py`)

When adding a **new skill** whose tools must load:

- Update the appropriate **GROUPS** entry (`core`, `asset`, `engine`, `qa`, …) so `discover_tools` sees the folder.

### Supervisor / orchestrator

Routing changes belong in `cuebert-supervisor.mdc` and `agent-orchestrator.md`; batch per hub plan if milestone M12 tracks integration.

---

## 6. BUILD VERIFICATION (CUEBERT GATE)

Before handoff:

| Check | Command / action | Severity |
|-------|------------------|----------|
| Cross-references | Verify new `](...)` targets exist under `docs/_ai_system/` and `.cursor/` | REJECT if broken |
| Stale Cue patterns | e.g. `rg 'cue-engineering\\.mdc|cue-supervisor\\.mdc(?!.*cuebert)|docs/projects/cue/'` adapted — no accidental Cue-only paths | REJECT if unintended |
| Markdown lint | Project linter or `markdownlint` if configured | WARN |
| Python tools (if touched) | Import/syntax smoke for edited `.py` (e.g. `python -m py_compile path`) | REJECT on failure |

Record **actual** output snippets in the plan Result column or §12 **Build Verification** lines.

---

## 7. HANDOFF PROTOCOL

```
=== HANDOFF ===
**CONTEXT:** Implemented Cuebert system files for [Feature].
**REPO:** /Users/ambtaylo/CursorProjects/cuebert
**BRANCH:** [branch]
**LANGUAGE:** CUEBERT
**STATUS:** Implementation complete. [Summary]
**RULES CONSULTED:** [list]
**GOAL:** Review
**PLAN:** [⟨CuebertActivePlans⟩/slug.md]
===============
```

Orchestrated: `=== SUBAGENT RESULT ===` per `agent-shared-lifecycle.md` §12.  
MUST NOT use `~/.cursor/plans/*.plan.md` as scope authority — `agent-shared-lifecycle.md` §2, §4.

---

## 8. SELF-MAINTENANCE (MITOSIS)

If file grows beyond ~5000 tokens: split to `agent-coding-cuebert-[topic].md`, register, update triggers.
