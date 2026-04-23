# depmap-toolkit

Dependency mapping and boundary analysis for Cuebert's two dependency domains.

## Tools

| Tool | Purpose |
|------|---------|
| `python_ast_map.py` | Generate Python import graph JSON from AST analysis (hub Python files) |
| `module_dep_scan.py` | Generate UE module dependency graph from `.Build.cs` / `.uplugin` (game projects) |
| `graph_cycles.py` | Find circular dependencies via Tarjan SCC algorithm (accepts either tool's output) |

## Usage

### Hub Python dependency map

```bash
python3 .cursor/skills/depmap-toolkit/tools/python_ast_map.py . .cursor/mcp-server .cursor/skills > dependency-map.json
```

### UE module dependency map

```bash
python3 .cursor/skills/depmap-toolkit/tools/module_dep_scan.py /path/to/game/Source > module-dependency-map.json
```

### Circular dependency detection

Pipe either tool's output to `graph_cycles.py`:

```bash
python3 .cursor/skills/depmap-toolkit/tools/python_ast_map.py . | python3 .cursor/skills/depmap-toolkit/tools/graph_cycles.py
```

## Standard

See `docs/_ai_system/standards/dependency-architecture.md` for the full two-domain model, staleness rules, and agent consumption patterns.
