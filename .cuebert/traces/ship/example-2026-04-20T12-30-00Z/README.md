# Illustrative `/ship` trace (documentation only)

This directory tree is a **curated, committed example** of what a real Cuebert `/ship` harness run would materialize under `.cuebert/traces/ship/<timestamp>/` after **M8** wires cook, cert, package, and optional upload automation.

**No UAT cook executed** for this fixture. **No binary packages** are checked in; `package/envelope.json` records **paths and SHA-256 placeholders** only.

## Where to read the narrative

End-to-end dry run (phases, guard decision tree, failure modes):  
`docs/_ai_system/examples/ship-sample-run-hello-level.md`

## How this relates to the spec

- Guard identifiers and severity defaults: `.cuebert/config/ship-guards.yaml` and `docs/_ai_system/standards/ship-guards.md`
- Cook / cert / package / upload envelope shapes: `docs/_ai_system/agents/agent-ship-cook.md` §8, `agent-ship-cert.md` §7, `agent-ship-package.md` §8, `agent-ship-upload.md` §8
- Parent phase chain: `docs/_ai_system/agents/agent-ship.md` §3 and §7

## Files in this example

| Path | Role |
|------|------|
| `envelope.json` | Session rollup the harness would write after post-package / upload decision |
| `guards/pre_cook.json` | Pre-cook guard findings |
| `guards/post_cook.json` | Post-cook guard findings |
| `guards/post_cert.json` | Post-cert guard findings |
| `guards/post_package.json` | Post-package guard findings |
| `cook/envelope.json` | Cook phase structured result |
| `cook/engine.log` | Synthetic cook log (illustrative) |
| `cert/envelope.json` | Cert structured result |
| `cert/report.md` | Human-readable cert report |
| `package/envelope.json` | Package list + manifest pointer |
| `upload/envelope.json` | Upload skip marker (`upload_channel: none`) |

## Git policy

Runtime traces under `.cuebert/traces/` are normally **ignored**. Paths matching `ship/example-*/` are **negated** in `.gitignore` so this smoke-test layout can ship with the hub.
