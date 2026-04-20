# Cuebert Configuration

This folder is the **cuebert hub** for this workspace. It holds version info, the workspace manifest, the skill registry, the vault, memory DB, and traces.

## Hub layout

| Path | Populated by | Description |
|------|---|---|
| `.cuebert/version.json` | M1-P2 | Version tracking + feature flags |
| `.cuebert/workspace-manifest.json` | M1-P2 | Hub, projects, vault resolution, memory mode |
| `.cuebert/README.md` | M1-P2 | This file |
| `.cuebert/registry/skills.yaml` | M1-P2 | Skill catalog (Supervisor Step 0.6 keyword matching) |
| `.cuebert/vault/` | M1-P3 | Vault storage (gitignored) |
| `.cuebert/memory/memory.db` | M1-P6 | SQLite memory DB (gitignored) |
| `.cuebert/traces/` | later | LangSmith-style traces (gitignored) |

### Game-project LFS template

- `docs/projects/_templates/game-project-gitattributes.template` — verbatim `.gitattributes` block for downstream game projects.
- `scripts/install-game-lfs.sh <project-path>` — helper to install the template and run `git lfs install` in the target repository.
- See `docs/_ai_system/standards/game-project-lfs.md` for full guidance.
- Auto-installed (with user prompt) during `/onboard` for Unreal / Unity / Godot projects (see `docs/_ai_system/agents/agent-ops-onboard.md` §3.1).

## Workspace manifest (`workspace-manifest.json`)

Project entries under `projects` include a filesystem **`path`** (relative to this hub checkout) plus engine metadata as documented in `docs/_ai_system/agents/agent-ops-onboard.md`. Optional fields include:

- **`assetManifestPath`** (string, optional) — path **relative to the game project root** (not the hub) to the per-project **asset manifest YAML** that declares ComfyUI-generated raster outputs. When omitted, tooling falls back to **`<project-root>/.cuebert-assets.yaml`** when that file exists. See **`docs/_ai_system/standards/asset-manifest.md`**.

## Root-level companions

| Path | Populated by | Description |
|------|---|---|
| `registry/services.yaml` | M1-P2 | Master service registry (same shape as Cue's root-level `registry/services.yaml`) |

## Credentials setup

Cuebert uses a vault (M1-P3) for credentials, not a `credentials.local.json`. Once M1-P3 lands, see `docs/_ai_system/standards/vault.md` for the init-vault flow.

## Memory mode

Default: `CUEBERT_MEMORY_MODE=text`. See top-level `README.md` "Memory: text-only by default" section.

## Version sync

`.cuebert/version.json` tracks the cuebert version. The `forkedFrom` field records the Cue baseline used at bootstrap.
