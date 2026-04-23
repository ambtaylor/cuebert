# SUPERVISOR AGENT — Cuebert Thin Dispatcher

> **Role:** Route every user message to the correct protocol or subagent before any other work.  
> **Enforcement:** Cursor loads **`.cursor/rules/cuebert-supervisor.mdc`** (`alwaysApply: true`). This file is the **canonical markdown companion** for cross-links from `rule_registry.md` and other agents; behavior is defined in the `.mdc` rule text.

## 0. Language and domain routing (§0.5 mirror)

Supervisor **Language** in the Decision Block uses this table (explicit flags beat inference):

| Signal | Context | Priority |
|--------|---------|----------|
| `--python` in prompt | **PYTHON** | 1 (explicit) |
| Unreal / UE5 / `.uproject` / UCLASS / gameplay C++ | **UE_CPP** | 1–2 |
| “skill”, “MCP tool”, “agent protocol”, “cursor rule”, “registry”, “cuebert system” | **CUEBERT** | 2 (inferred) |
| Vault / credentials / secrets handling | **VAULT** (knowledge → `standards/vault-standard.md`) | 2 |
| Python tooling (FastAPI, pytest, hub scripts) | **PYTHON** | 2 |
| Working directory is hub `cuebert/` checkout | **CUEBERT** | 3 (default) |
| `project-profile.md` `primary_language` (when present) | Per profile | 3 |
| No signal | **PYTHON** | 4 (fallback for repo scripting) |

**Rules / standards (active):**

- **UE C++** → `.cursor/rules/cuebert-ue-cpp.mdc`
- **General engineering** → `.cursor/rules/cuebert-engineering.mdc`
- **Vault** → `docs/_ai_system/standards/vault-standard.md` (intake: `.cursor/rules/cuebert-vault-intake.mdc` when present)

## 1. What the Supervisor dispatches

| Kind | Shortcut / trigger | Main-chat protocol | Subagent (`generalPurpose`) |
|------|-------------------|--------------------|-----------------------------|
| Orchestrated hub engineering | `/o`, `/orchestrate` | `agent-orchestrator.md` | Phase Tasks per orchestrator §3 |
| Deploy harness | `/d`, `/deploy` | `agent-deploy.md` | Phase Tasks per deploy doc |
| Gaming | `/play`, `/ship`, `/asset` | `agent-play.md`, `agent-ship.md`, `agent-asset.md` | Harness-specific |
| Direct engineering | `/spec`, `/code`, `/review` | — | `.cursor/agents/spec-{lang}.md`, `code-{lang}.md`, `review-{lang}.md` with **lang** ∈ `python`, `cue`, `ue-cpp` (per flags §0.5) |
| Security | `/sec` | — | `.cursor/agents/security-auditor.md` → `agent-security.md` |
| Test | `/test` | — | `agent-test-python.md` |
| Research | *(no user shortcut)* | — | Orchestrator dispatches `agent-research.md` only |

**Forbidden:** Named `subagent_type` values matching `.cursor/agents/*.md` filenames (e.g. `orchestrate`, `code-python`). Use only `generalPurpose`, `explore`, `shell`, `browser-use`, `best-of-n-runner`. `/o` and `/d` **never** run as Task subagents.

## 2. References

- Full shortcut table, modifiers, MCP `sequentialthinking` pre-gate, Thin Handoff: **`.cursor/rules/cuebert-supervisor.mdc`**
- Registry: `docs/_ai_system/rule_registry.md`
- Orchestrator dispatch matrix: `docs/_ai_system/agents/agent-orchestrator.md` §3
