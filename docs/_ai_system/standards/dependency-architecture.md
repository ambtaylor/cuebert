# Dependency Architecture Standard

> **SYSTEM ROLE:** Defines how Cuebert-managed projects express **architectural boundaries**, generate **dependency maps**, and enforce **import rules** across two dependency domains: hub Python tools and game project UE modules.
> **Applies To:** Hub agents, `/o` orchestrator, `/play` author phases, workspace onboarding.
> **Companion tools:** `python_ast_map.py` (hub Python), `module_dep_scan.py` (UE modules), `graph_cycles.py` (cycle detection).

---

## 1. Why Boundaries Matter

**Architectural boundaries** prevent coupling from eroding through incremental imports. Automated validation makes violations **visible at build time** and gives agents **structured evidence** for Code pre-flight, Review, and QA checks.

---

## 2. Two Dependency Domains

Cuebert operates across two distinct dependency graphs. Both require scanning, staleness tracking, and orchestrator gates.

### Domain 1 — Hub Python Imports (for `/o`)

| Aspect | Detail |
|--------|--------|
| **Scope** | ~73+ Python files across `.cursor/mcp-server/` and `.cursor/skills/*/tools/` |
| **Graph tool** | `python_ast_map.py` — AST-based import graph scanner |
| **Map location** | `docs/projects/cuebert/knowledge/dependency-map.json` |
| **When it drifts** | `/o` Code adds/moves/removes Python modules |
| **Validation** | `py_compile` + import validation; cycle detection via `graph_cycles.py` |

### Domain 2 — Game Project UE Modules (for `/play`)

| Aspect | Detail |
|--------|--------|
| **Scope** | `.Build.cs` files (`PublicDependencyModuleNames`, `PrivateDependencyModuleNames`) and `.uplugin` (`Plugins[].Name`) |
| **Graph tool** | `module_dep_scan.py` — `.Build.cs` / `.uplugin` parser |
| **Map location** | `docs/projects/{game}/knowledge/module-dependency-map.json` |
| **When it drifts** | `/play` Author adds new gameplay modules or plugins |
| **Validation** | UBT build + module dependency check via `module_dep_scan.py` |

---

## 3. Two-Channel Integration Model

Neither channel introduces new cross-agent state machines beyond existing plan + knowledge patterns.

**Channel A — Static knowledge (read-only reference)**
- **Location:** `docs/projects/{name}/knowledge/dependency-map.json` (hub) or `module-dependency-map.json` (game)
- **Use:** Spec impact analysis, risk notes, Verification Contract scoping
- **Consumption:** Same as other project knowledge files. Agents **read**; they do not treat the file as authoritative for "current build passes."

**Channel B — Live validation (CLI)**
- **Hub Python:** `py_compile` + import validation at workspace root
- **Game UE:** UBT build validation via `unreal-build` skill
- **Use:** Code pre-flight, Review evidence, QA independent re-run
- **Consumption:** Run validation tools. Exit code and structured output are evidence for the Verification Contract.

**QA does not trust the stored map for pass/fail** — it re-runs Channel B against the working tree.

---

## 4. Staleness Model

### 4.1 `dependency-map.json` / `module-dependency-map.json` metadata

Generated maps SHOULD include at least:

- `generated_at` — ISO-8601 UTC timestamp
- `tool` — e.g. `python-ast-map` or `ue-module-dep-scan`
- `project` — logical project name
- `summary` — counts (modules, edges, violations if applicable)

### 4.2 Orchestrator / agent behavior

**In orchestrated flows (`/o`):** The Orchestrator **auto-refreshes** the hub Python map when Code adds, removes, or moves graph-relevant files, **after** Code and **before** Review — see `agent-orchestrator.md` **§4J** (Depmap Refresh Gate).

**In `/play` flows:** The Play Author agent should run `module_dep_scan` when `.Build.cs` or `.uplugin` files change — documented in `agent-play.md`, not in the `/o` orchestrator.

**In direct flows (no `/o` or `/play`):** The **Code** agent MUST refresh the map manually when structural changes apply.

During structured reasoning, if `generated_at` is **older** than the latest commit touching import-heavy paths (or if the map is missing), the Spec agent SHOULD:
- Flag **"impact analysis may be stale"** in the plan
- Add a Verification Contract note that the Code agent **refreshes** the map before relying on fine-grained file lists

---

## 5. Agent Consumption Patterns

### 5.1 Spec

- Read `dependency-map.json` (Channel A) when scoping impact and cross-boundary risk.
- Call out staleness per §4.2 when relevant.

### 5.2 Code

- Before handoff: run validation (Channel B); fix violations or document grandfathered baseline.
- **Hub map refresh (MUST when import graph structure changes):** Run `python_ast_map`, copy output into hub knowledge, run `graph_cycles` for circular dependency detection.
- **Game module refresh (MUST when UE module dependencies change):** Run `module_dep_scan`, copy output into project knowledge.
- Record **actual CLI output** in the plan Result column — not self-assessed claims.

### 5.3 Review

- Confirm validation evidence exists and matches the contract; REJECT if REJECT-severity dependency rows are empty or contradicted.
- Optionally cross-check Channel A for unexpected coupling.

### 5.4 QA

- Run validation independently (Channel B), analogous to re-running `pytest` or `build_verify`.

---

## 6. File Locations (Conventions)

| Artifact | Hub Path | Game Project Path |
|----------|----------|-------------------|
| Python dependency map | `docs/projects/cuebert/knowledge/dependency-map.json` | N/A |
| UE module dependency map | N/A | `docs/projects/{game}/knowledge/module-dependency-map.json` |
| Python AST map tool | `.cursor/skills/depmap-toolkit/tools/python_ast_map.py` | N/A |
| UE module scan tool | `.cursor/skills/depmap-toolkit/tools/module_dep_scan.py` | N/A |
| Cycle detection tool | `.cursor/skills/depmap-toolkit/tools/graph_cycles.py` | Same tool, different input |

---

## 7. Operations (depmap-toolkit)

| Operation | Purpose |
|-----------|---------|
| `python_ast_map` | Generate Python import graph JSON from AST analysis |
| `module_dep_scan` | Generate UE module dependency graph from `.Build.cs` / `.uplugin` |
| `graph_cycles` | Find circular dependencies via Tarjan SCC algorithm |

---

## 8. Relationship to Other Standards

- **`cuebert-engineering.mdc` §3** — Build Verification Gate includes Check 4.5 (dependency boundary validation) and Check 4.6 (depmap refresh).
- **`agent-shared-lifecycle.md`** — Plan remains the source of truth for verification evidence.
- **`agent-orchestrator.md` §4J** — Depmap Refresh Gate (post-Code, pre-Review) for hub Python domain.

---

## 9. Failure and Grandfathering

If tooling cannot run immediately:

1. Capture **WARN** in the plan with a resolution milestone.
2. Do not silently weaken REJECT-severity contract rows without Spec amendment.
3. Tooling missing → log WARN, do not block Review (same severity as `cuebert-engineering.mdc` Check 4.6).

---

## 10. Command Cheat Sheet

### Hub Python

```bash
# Generate dependency map
python3 .cursor/skills/depmap-toolkit/tools/python_ast_map.py . .cursor/mcp-server .cursor/skills

# Copy to hub knowledge
cp dependency-map.json docs/projects/cuebert/knowledge/dependency-map.json

# Check for circular dependencies
python3 .cursor/skills/depmap-toolkit/tools/python_ast_map.py . .cursor/mcp-server .cursor/skills | \
  python3 .cursor/skills/depmap-toolkit/tools/graph_cycles.py
```

### Game UE Modules

```bash
# Generate module dependency map
python3 .cursor/skills/depmap-toolkit/tools/module_dep_scan.py /path/to/game/Source

# Copy to project knowledge
cp module-dependency-map.json docs/projects/{game}/knowledge/module-dependency-map.json

# Check for circular module dependencies
python3 .cursor/skills/depmap-toolkit/tools/module_dep_scan.py /path/to/game/Source | \
  python3 .cursor/skills/depmap-toolkit/tools/graph_cycles.py
```
