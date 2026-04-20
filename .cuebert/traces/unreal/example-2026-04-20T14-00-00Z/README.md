# Illustrative Unreal bridge trace (documentation only)

This directory is a **curated, committed example** of what a Cuebert **`/play`** harness dry run would materialize under `.cuebert/traces/unreal/<timestamp>/` after **`agent-unreal-mutate`** wiring (**M5-P4** narrative).

**No live Unreal Editor HTTP** was performed for this fixture. **No Remote Control PUT** on a real port. Envelopes align with [`docs/_ai_system/agents/agent-unreal.md`](../../../../docs/_ai_system/agents/agent-unreal.md), [`agent-unreal-mutate.md`](../../../../docs/_ai_system/agents/agent-unreal-mutate.md), and [`unreal-bridge-contract.md`](../../../../docs/_ai_system/standards/unreal-bridge-contract.md).

## Where to read the narrative

End-to-end dry run (scope checks, two mutate envelopes, memory hooks, failure variants):  
[`docs/_ai_system/examples/unreal-bridge-sample-run-hello-level.md`](../../../../docs/_ai_system/examples/unreal-bridge-sample-run-hello-level.md)

## How this relates to the spec

- Scope matrix: [`agent-unreal.md`](../../../../docs/_ai_system/agents/agent-unreal.md) §6.1  
- Error catalog: [`unreal-bridge-contract.md`](../../../../docs/_ai_system/standards/unreal-bridge-contract.md) §4  
- MCP tools: [`.cursor/skills/unreal-bridge/SKILL.md`](../../../../.cursor/skills/unreal-bridge/SKILL.md)

## Files in this example

| Path | Role |
|------|------|
| `envelope.json` | Session rollup after both ops |
| `set_property/envelope.json` | `unreal_set_property` tool output (hero light intensity) |
| `call_function/envelope.json` | `unreal_call_function` tool output (`StartPIE`) |
| `mutations.jsonl` | Two audit lines per [`unreal-bridge-contract.md`](../../../../docs/_ai_system/standards/unreal-bridge-contract.md) §6 |
| `memory/*.json` | Simulated `troubleshoot_commit` return envelopes |
| `scope_check/*.json` | Scope enforcement snapshots |
| `preset_snapshot.json` | Frozen copy of `hello-level-example.json` |
| `guards/*.json` | Pre/post guard envelopes |
| `findings.json` | Optional harness findings list (empty here) |

## Git policy

Runtime traces under `.cuebert/traces/` are normally **ignored**. Paths matching `unreal/example-*/` are **negated** in `.gitignore` so this reference layout ships with the hub.
