# Illustrative `/play` trace (documentation only)

This directory tree is a **curated, committed example** of what a real Cuebert `/play` harness run would materialize under `.cuebert/traces/play/<timestamp>/` after **M5–M6** wire editor automation, compile hooks, and guard evaluators.

**No Unreal Editor was launched** for this fixture. **No binary screenshots** are checked in; see `preview/screenshots/frame_0001.png.txt` for the placeholder contract.

## Where to read the narrative

End-to-end dry run (phases, guard decision tree, failure modes):  
`docs/_ai_system/examples/play-sample-run-hello-level.md`

## How this relates to the spec

- Guard identifiers and severity defaults: `.cuebert/config/play-guards.yaml` and `docs/_ai_system/standards/play-preview-guards.md`
- Author / Preview / QA envelope shapes: `docs/_ai_system/agents/agent-play-author.md` §7, `agent-play-preview.md` §9, `agent-play-qa.md` §7
- Parent phase chain: `docs/_ai_system/agents/agent-play.md` §3

## Files in this example

| Path | Role |
|------|------|
| `envelope.json` | Session rollup the harness would write after QA |
| `guards/pre_author.json` | Pre-author guard findings |
| `guards/post_author.json` | Post-author / pre-preview guard findings |
| `guards/post_preview.json` | Post-preview guard findings |
| `author/envelope.json` | Author phase result |
| `preview/envelope.json` | Preview phase metadata |
| `preview/engine.log` | Synthetic editor log (illustrative) |
| `preview/screenshots/frame_0001.png.txt` | Text stand-in for a PNG capture |
| `qa/envelope.json` | Lightweight QA verdict |

## Git policy

Runtime traces under `.cuebert/traces/` are normally **ignored**. Paths matching `play/example-*/` are **negated** in `.gitignore` so this smoke-test layout can ship with the hub.
