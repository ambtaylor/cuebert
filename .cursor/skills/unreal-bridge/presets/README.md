# Unreal Remote Control preset fixtures (cuebert)

This directory mirrors the **workflows/** pattern used by `comfyui-toolkit`:
checked-in JSON that documents **expected** Remote Control API shapes for
round-trip testing and agent authoring. It is **not** a substitute for Unreal
`.uasset` Remote Control preset assets inside a UE project.

## Purpose

Epic’s Remote Control plugin exposes HTTP surfaces such as
`GET /remote/preset/<name>`. Cuebert stores **portable JSON snapshots** here so
harnesses can validate parsing, error envelopes, and future import/spawn tools
without requiring a live editor for every CI job.

## Naming convention

Use descriptive stems aligned with the hub project key and preset name:

`<project-key>_<PresetName>.json`

Example: `demo_ExamplePreset.json`

## Format

Each file should match the JSON shape returned by
`GET http://localhost:30010/remote/preset/<name>` (or the normalized subset
documented in `reference.md`) so fixtures can be replayed against client
parsers in tests.

## Testing

**M5-P1** ships **no** real preset JSON files (directory is intentionally
empty aside from this README). **M5-P4** will add sample fixtures and unit
tests that load them.

## Location

Files live under **this** skill directory
(`.cursor/skills/unreal-bridge/presets/`). Unreal’s on-disk preset assets remain
under your game project’s `Content/` tree as authored in the editor.

## See also

- `../SKILL.md` — operator-facing overview.
- `../reference.md` — HTTP contracts and envelope fields.
- `.cursor/skills/comfyui-toolkit/workflows/` — the same “bundled fixture
  directory” pattern for ComfyUI workflow graphs.
