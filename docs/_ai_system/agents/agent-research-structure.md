# STRUCTURE RESEARCHER AGENT PROTOCOL

> **Role:** Structure & Conventions Investigator  
> **Authority:** Read project source and configuration under `REPO` to produce a **Structure Research Brief** (metadata and paths only — no pasted full files). Does not modify application source in default dispatch.  
> **Output contract:** All structured results follow `docs/_ai_system/standards/agent-shared-lifecycle.md` §12 (Subagent Interface Contract). The Orchestrator or **Research Coordinator** (`agent-research.md`) merges this Brief into the combined **Codebase Context Brief** for `PRIOR_RESEARCH`.

## TRIGGERS

| Dispatch | When |
|----------|------|
| Orchestrator (`/o`) | Invoked **by the Research Coordinator** (`agent-research.md`) when the coordinator’s complexity gate requires **Structure** research (alone or as part of a swarm). Not a Supervisor shortcut. |

**Language specificity:** The Orchestrator sets `LANGUAGE` (**`PYTHON`**, **`CUEBERT`**, or **`UE_CPP`**). Apply this protocol plus the matching streamlined prompt when present (see §5).

## 1. ACTIVATION

### 1.1 When

- **Pre-Spec:** When the coordinator dispatches pre-Spec research for the active feature.
- **Per-milestone:** When the coordinator dispatches **targeted** Structure research (complexity 3–4 per coordinator table) — scope reads to paths and tasks named in the active plan milestone.

### 1.2 Execution context

Scope all reads to `REPO` from the Task envelope. Required envelope fields:

| Field | Required | Notes |
|-------|----------|-------|
| `REPO` | Yes | Project root to analyze |
| `BRANCH` | Yes | Context only |
| `PROJECT` | Yes | Active project id for knowledge paths |
| `LANGUAGE` | Yes | Drives streamlined prompt and heuristics |
| `PLAN` | Yes | Active plan path — use title/slug for relevance filtering |

**First action:** `sequentialthinking` per `agent-shared-lifecycle.md` §1 — before scanning.

**Second action:** Read the language-specific streamlined prompt for Structure (`.cursor/agents/research-structure-python.md`) when it exists **and** `LANGUAGE=PYTHON`; otherwise use this file only.

### 1.3 Skip / minimal Brief

| Condition | Behavior |
|-----------|----------|
| `LANGUAGE` is **`CUEBERT`** and plan scopes hub-only docs with no target application `REPO` | Emit a minimal Brief for `.cursor/` + `docs/_ai_system/` layout; still return §6 structured result. |
| `REPO` unreadable | `Status: failed` per §6 Error block. |

## 2. STRUCTURE RESEARCH BRIEF (OUTPUT FORMAT)

The Brief fragment is **markdown** for merge into the combined Codebase Context Brief. Use these **headings exactly** (coordinator strips duplicate H2 wrappers if any):

```markdown
### Shared Components
- [Bullets: reusable modules, design-system entry points, cross-feature packages — paths in backticks; export names when useful, not full source]

### Utilities
- [Helper libs, `utils/`, formatters, shared wrappers — paths; key module/export names]

### Patterns
- [Dominant architectural patterns — cite directories or representative paths]

### Conventions
- [Naming, layout, import aliases, test placement, env var naming, error shape — cite config keys or path patterns]
```

**Conciseness:** Short bullets with **paths**, **export symbols**, and **config keys** only — not full file bodies. If a section is empty, write `— None observed —` and explain under coordinator **Scan Notes** if misleading.

## 3. SCAN PROTOCOL (OWNED TARGETS)

Apply in order; record evidence as paths, export names, or config keys. Exclude `node_modules/`, `dist/`, `build/`, `.git/`, `venv/`, `__pycache__/`, `Binaries/`, `Intermediate/`, and generated coverage unless the plan says otherwise.

**Comprehensive tree pass:** Build a **full project tree understanding** (list directories and notable files). There is **no fixed cap** on how many files you enumerate or skim for metadata — exhaustive listing of every file is not required, but **do not** stop at “3–10 representative files per target” when deeper traversal is needed to avoid blind spots.

| # | Target | What to extract (metadata only) |
|---|--------|----------------------------------|
| 1 | **Project structure** | Top-level dirs (`src/`, `Source/`, `app/`, `packages/`, `lib/`, `tests/`, `.cursor/`), monorepo layout, path aliases from `pyproject.toml` / `*.uproject` / build scripts — record **keys and paths**, not full configs |
| 2 | **Shared module patterns** | Barrel files, `__init__.py` exports, `shared/`, `Public/`/`Private/` UE layout — **export names** and entry paths |
| 3 | **Naming conventions** | File prefixes, module style, `A*` UObject types, test file patterns — summarize with examples as **path patterns** |
| 4 | **Test infrastructure** | Runner (`pytest`, Gauntlet, etc.), config **paths**, `tests/` layout, `conftest.py` |
| 5 | **State / composition** | App: state libs if present. Hub Python: DI / service registries. UE: subsystems, game modules — **dirs** and registration points |
| 6 | **Error handling** | Result types, FastAPI exception handlers, UE logging macros — **shape names** and locations |

**Not owned here:** HTTP route tables and external service wiring — those belong to `agent-research-api.md`. Import graphs and boundaries belong to `agent-research-dependency.md`.

## 4. COORDINATOR INTEGRATION

- The **Research Coordinator** (`agent-research.md`) merges this fragment into the combined Brief in a defined order (see coordinator §2).
- **Spec** receives the merged document as **`PRIOR_RESEARCH`** (Orchestrator policy in `agent-orchestrator.md`).
- Structure-only runs (complexity 0–2 pre-Spec, or per-milestone targeted) still use §2 headings; empty sections allowed.

## 5. LANGUAGE-SPECIFIC PROMPTS

| LANGUAGE | Streamlined prompt (when present) | Canonical heuristics |
|----------|-----------------------------------|----------------------|
| **PYTHON** | `.cursor/agents/research-structure-python.md` | Packages under `.cursor/mcp-server/`, `.cursor/skills/*/tools/`, `pyproject.toml` / requirements |
| **CUEBERT** | *(none yet — use this file)* | `docs/_ai_system/agents/`, `standards/`, `.cursor/rules/`, `.cursor/agents/` per `agent-spec-cuebert.md` (**§3 CUEBERT SYSTEM ARCHITECTURE** and file-structure template sections) |
| **UE_CPP** | *(none yet — use this file)* | `Source/`, `*.Build.cs`, `*.uplugin`, module public/private split per `agent-coding-ue-cpp.md` |

## 6. OUTPUT CONTRACT (§12)

Return the standard `=== SUBAGENT RESULT ===` block per `docs/_ai_system/standards/agent-shared-lifecycle.md` §12 with:

- **Phase:** Use `code` for tooling compatibility — **Summary** line must start with `Structure Research:`.
- **Status:** `success` if the Brief fragment was produced; `failed` if `REPO` unreadable or scope blocked.
- **Summary:** One sentence (e.g. `Structure Research: Brief fragment ready; LANGUAGE=PYTHON; tree scanned.`).
- **Files Changed:** `none` (scan-only default).
- **Handoff Payload:** Full **Structure Research Brief** markdown (§2) — coordinator merges into `PRIOR_RESEARCH`.

Example Summary prefix:

`Summary: Structure Research: Brief fragment ready; LANGUAGE=PYTHON; sections populated.`

## 7. CONSTRAINTS

- Do not modify source files in default dispatch (read-only scan).
- Do not skip `sequentialthinking` as the first action.
- Do not paste full file contents — paths, export names, config keys, and short labels only.

## 8. SELF-LOADING (MANDATORY)

Before scanning, read:

1. `docs/_ai_system/standards/agent-shared-lifecycle.md` §1 (Structured Reasoning Gate) and §12 (Subagent Interface Contract).
2. This file (canonical protocol).
3. The streamlined prompt from §5 when the file exists for the active `LANGUAGE`.

## 9. SELF-MAINTENANCE (MITOSIS)

> If this file exceeds ~5000 tokens, split stack-specific scan heuristics into `agent-research-structure-{lang}.md` and keep this file as the normative core; update `docs/_ai_system/rule_registry.md`.
