# Cuebert machine schemas

This directory holds **JSON Schema** documents used by hub tooling and MCP
validators so manifests, plans, and structured envelopes stay **machine-checked**
against a single source of truth. Human-readable prose for each contract lives
under `docs/_ai_system/standards/`; schemas here make those contracts
**executable** in CI, Cursor MCP, and future harnesses.

## Current schemas

| File | JSON Schema | Manifest `version` | Introduced |
|------|-------------|-------------------|------------|
| `asset-manifest.schema.json` | draft-07 | `1` (integer; const in schema) | M4-P2 |

## Schema versioning

- **Breaking changes** bump the **major integer** in the manifest or envelope
  `version` field **and** the conceptual `$id` URL suffix (for example
  `asset-manifest-v2.json` when the format breaks compatibility).
- **Additive changes** within the same major version add **optional** keys only;
  validators and producers must remain backward-compatible for older clients
  until the ecosystem cuts over.
- **Cuebert tooling** reads the top-level `version` from each YAML/JSON
  instance and **errors on unknown values** rather than silently accepting drift.

## Future schemas (planned, not shipped here)

- `play-plan.schema.json` — structured `/play` plan bodies (M2 already ships a
  Markdown template; JSON Schema deferred until a canonical JSON interchange
  exists).
- `ship-plan.schema.json` — `/ship` cook plans (M3 template today; schema
  deferred alongside cook harness JSON).
- Additional envelope schemas may land with gauntlet / vision QA milestones
  (M6+) as those tools stabilize.

## Usage

- **Authoring:** Start from `docs/projects/_templates/` templates, then validate
  with the MCP tool named in the matching standards document.
- **Validation:** Prefer hub-local paths under `.cuebert/schemas/` so offline
  CI and Cursor agree on the same file revision as the git SHA.

---

**Status:** introduced **M4-P2** (asset manifest schema + `asset_manifest_validate`).
