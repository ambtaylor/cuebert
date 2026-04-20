# Cuebert

> A minimal fork of the [Cue](https://github.com/ambtaylor/cue) harness, skills, vault, and onboarding architecture, tailored for **gaming development** (Unreal Engine 5 first).

Cuebert ports Cue's plan-as-source-of-truth orchestration, MCP tool surface, vault credential resolution, and memory-toolkit persistence into a **gaming-native** language matrix (`UE-CPP | UE-BP | UNITY-CSHARP | GODOT-GDSCRIPT | GAME-AGNOSTIC`). It ships three harnesses — `/play`, `/ship`, and `/asset` — that replace Cue's `/o` and `/d` with workflows purpose-built for in-editor iteration, distribution packaging, and manifest-driven asset generation.

---

## Status

All **8 milestones** from the authoritative plan are complete. Supervisor routing (`/play`, `/ship`, `/asset`, `--preview`) is live as of M9. Guard evaluators and engine-specific automation depth remain milestone-gated per each harness doc.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                      CUEBERT HUB (.cuebert/)                        │
│                                                                      │
│  ┌──────────┐  ┌───────────────┐  ┌────────────┐  ┌──────────────┐  │
│  │  Vault    │  │  Registry     │  │  Memory DB │  │  Traces      │  │
│  │  (tiered  │  │  skills.yaml  │  │  SQLite    │  │  play/       │  │
│  │   YAML)   │  │  services.yaml│  │  FTS5/BM25 │  │  ship/       │  │
│  └──────────┘  └───────────────┘  └────────────┘  │  asset/       │  │
│                                                    └──────────────┘  │
├──────────────────────────────────────────────────────────────────────┤
│                        MCP SERVER (FastMCP)                          │
│                                                                      │
│  Groups: cuebert-core · cuebert-engine · cuebert-asset · cuebert-qa │
│                                                                      │
│  Core tools:          Memory tools:         Engine tools:            │
│   cuebert_system_check  milestone_lookup      unreal_build            │
│   vault_resolve          milestone_commit      unreal_cook             │
│   build_verify           troubleshoot_search   unreal_run_gauntlet     │
│   health_check           troubleshoot_commit   unreal_bridge_*         │
│                                                                      │
│  Asset tools:          QA tools:                                     │
│   comfyui_*              vision_qa_*                                  │
│   asset_manifest_*       prod_readiness_scan                          │
│                          qa_resilience_scan                           │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Harness Flows

Cuebert provides three main-chat harnesses. Each runs in the **main chat** (never as a spawned `subagent_type`), dispatching `generalPurpose` Tasks for phase work.

### `/play` — Fast Iteration Loop

Iterate on gameplay-visible changes and preview them in-editor (Unreal PIE, Unity Play Mode, Godot F5). No cook, no package, no cert.

```
  User: /play
       │
       ▼
  ┌─────────┐     ┌──────────┐     ┌───────────┐     ┌────────┐     ┌─────────┐
  │  PLAN   │────▶│  AUTHOR  │────▶│  PREVIEW  │────▶│   QA   │────▶│  MERGE  │
  │         │     │          │     │           │     │        │     │         │
  │ Change  │     │ Edit src │     │ PIE/Play  │     │ Log    │     │ Local   │
  │ list +  │     │ assets,  │     │ Mode +    │     │ scan + │     │ branch  │
  │ scope   │     │ code,    │     │ capture   │     │ visual │     │ commit  │
  │ decl.   │     │ content  │     │ screens   │     │ diff   │     │ (no     │
  │         │     │          │     │ + logs    │     │        │     │ push)   │
  └─────────┘     └──────────┘     └───────────┘     └────────┘     └─────────┘
       │                                │                                │
       │          Preview Guards        │                                │
       │          ┌─────────────────────┤                                │
       │          │ G-1 Engine reach    │                                │
       │          │ G-2 Compile sanity  │     On REJECT ──▶ BLOCKED     │
       │          │ G-3 Log patterns    │     (no merge, trace written)  │
       │          │ G-4 Asset refs      │                                │
       │          │ G-5 Scope contain   │                                │
       │          └─────────────────────┘                                │
       │                                                                │
       └── /play --preview: walk chain, zero spawns, report health ─────┘
```

**Session outcomes:** `running` | `blocked` | `not_applicable` | `complete`

### `/ship` — Distribution Build Pipeline

Produce a cooked, certified, packaged build suitable for distribution. Mandatory memory attestation on every run (success or failure).

```
  User: /ship
       │
       ▼
  ┌──────────────┐                          ┌──────────────┐
  │  PRE-COOK    │                          │  ATTEST      │
  │              │     On any FAIL ────────▶│  (always)    │
  │ Git clean    │     at any gate          │              │
  │ Engine ver   │                          │ envelope.json│
  │ Ship meta    │                          │ + memory     │
  │ Asset refs   │                          │ commit       │
  │              │                          └──────────────┘
  │ prod_        │                                 ▲
  │ readiness    │                                 │
  │ (REJECT gate)│                                 │
  └──────┬───────┘                                 │
         │ PASS                                    │
         ▼                                         │
  ┌──────────────┐                                 │
  │  COOK        │                                 │
  │              │                                 │
  │ agent-ship-  │                                 │
  │ cook ──▶     │   FAIL ────────────────────────▶│
  │ cook-package │                                 │
  │ -game        │                                 │
  └──────┬───────┘                                 │
         │ PASS                                    │
         ▼                                         │
  ┌──────────────┐                                 │
  │  POST-COOK   │                                 │
  │              │                                 │
  │ qa_resilience│   FAIL ────────────────────────▶│
  │ (REJECT gate)│                                 │
  │ Size budget  │                                 │
  │ Missing cook │                                 │
  └──────┬───────┘                                 │
         │ PASS                                    │
         ▼                                         │
  ┌──────────────┐                                 │
  │  PACKAGE     │                                 │
  │              │                                 │
  │ agent-ship-  │   FAIL ────────────────────────▶│
  │ package ──▶  │                                 │
  │ cook-package │                                 │
  │ -game        │                                 │
  └──────┬───────┘                                 │
         │ PASS                                    │
         ▼                                         │
  ┌──────────────┐                                 │
  │  CERT        │                                 │
  │  (advisory)  │  INFO/WARN only                 │
  │              │  ───────▶ never blocks ─────────│
  │ agent-cert-  │                                 │
  │ game         │                                 │
  └──────┬───────┘                                 │
         │                                         │
         ▼                                         │
  ┌──────────────┐                                 │
  │  UPLOAD      │                                 │
  │  (optional)  │  disabled by default            │
  │              │  requires upload_channel         │
  │  itch.io /   │  in ship plan                   │
  │  Steam /     │                                 │
  │  custom      │                                 │
  └──────┬───────┘                                 │
         │                                         │
         └────────────────────────────────────────▶┘
                                              ATTEST
```

**Ship Guards (14 stable ids):** `guard.git.clean`, `guard.git.untracked_cook_paths`, `guard.engine.version_match`, `guard.project.ship_metadata`, `guard.assets.referenced_in_cook`, `guard.cook.exit_code`, `guard.cook.size_budget`, `guard.cook.missing_assets`, `guard.cert.severity_floor`, `guard.cert.required_checklists`, `guard.cert.report_emitted`, `guard.package.exists`, `guard.package.checksum`, `guard.package.manifest`

### `/asset` — Manifest-Driven Asset Generation

Generate 2D raster assets via ComfyUI from a declarative YAML manifest, verify against pipeline guards, and place into the project content tree.

```
  User: /asset
       │
       ▼
  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
  │  PRE-PLAN    │────▶│     PLAN     │────▶│  POST-PLAN   │
  │  guards      │     │              │     │  guards      │
  │              │     │ Read manifest│     │              │
  │              │     │ Diff lockfile│     │              │
  │              │     │ Emit plan    │     │              │
  └──────────────┘     └──────────────┘     └──────┬───────┘
                                                   │ PASS
       ┌───────────────────────────────────────────┘
       │
       ▼ (for each asset in plan)
  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
  │   GENERATE   │────▶│ POST-GENERATE│────▶│    PLACE     │
  │              │     │ guards       │     │              │
  │ comfyui_     │     │              │     │ Backup old   │
  │ generate_    │     │ Dimensions   │     │ Atomic copy  │
  │ asset        │     │ Format       │     │ Verify hash  │
  │              │     │ File size    │     │              │
  │ ──▶ trace/   │     │              │     │ ──▶ Content/ │
  │   generated/ │     │              │     │              │
  └──────────────┘     └──────────────┘     └──────┬───────┘
                                                   │
       ┌───────────────────────────────────────────┘
       │
       ▼
  ┌──────────────┐     ┌──────────────┐
  │ POST-PLACE   │────▶│  LOCKFILE    │────▶ milestone_commit (mandatory)
  │ guards       │     │  UPDATE      │
  │              │     │              │
  │              │     │ .cuebert-    │
  │              │     │ assets.lock  │
  │              │     │ .yaml        │
  └──────────────┘     └──────────────┘
```

**Typical ordering:** `/asset` (generate art) → `/play` (preview in editor) → `/ship` (distribute)

---

## Harness Relationship

```
                    ┌─────────────────────────────────────────┐
                    │           CUEBERT SUPERVISOR             │
                    │   .cursor/rules/cuebert-supervisor.mdc   │
                    └──────────┬──────────┬──────────┬─────────┘
                               │          │          │
                    ┌──────────▼──┐ ┌─────▼─────┐ ┌─▼──────────┐
                    │   /asset    │ │   /play   │ │   /ship    │
                    │             │ │           │ │            │
                    │ Generate &  │ │ Edit &    │ │ Cook &     │
                    │ place 2D    │ │ preview   │ │ cert &     │
                    │ assets from │ │ in-editor │ │ package    │
                    │ manifest    │ │ (PIE)     │ │ for distro │
                    └─────────────┘ └───────────┘ └────────────┘
                          │               │              │
                          ▼               ▼              ▼
                    ┌─────────────────────────────────────────┐
                    │         SHARED INFRASTRUCTURE           │
                    │                                         │
                    │  Vault · MCP Tools · Memory Toolkit     │
                    │  Registry · Hub (.cuebert/) · Traces    │
                    └─────────────────────────────────────────┘
```

---

## Quick Start

```bash
git clone https://github.com/ambtaylor/cuebert.git
cd cuebert

# 1. Initialize vault (tiered YAML credential resolution)
python scripts/init-vault.py

# 2. Start MCP server (FastMCP with gaming GROUPS)
#    Configure in .cursor/mcp.json or your IDE's MCP settings

# 3. Verify hub health
#    Call cuebert_system_check(scope="all") via MCP → expect PASS

# 4. Onboard a game project
#    /onboard creates workspace-manifest.json entry + project profile
```

---

## Memory: Text-Only by Default

Cuebert's memory toolkit ships with **`CUEBERT_MEMORY_MODE=text`** as the default. This means:

- `troubleshoot_commit`, `milestone_commit`, etc. work immediately with **no embedding model required**.
- Ranking uses SQLite FTS5/BM25 (full-text search) only.
- The `embedding` column is nullable; rows are written with `embedding=NULL` in text mode.
- **Opt-in upgrade:** set `CUEBERT_MEMORY_MODE=hybrid` and configure an OpenAI-compatible embeddings endpoint in the vault to enable vector ranking. No DB migration required — old rows continue ranking via FTS, new rows get embeddings.

This makes Cuebert usable out of the box for contributors without access to an embeddings provider.

---

## Repository Structure

```
cuebert/
├── .cuebert/                          # Hub marker (replaces Cue's .cue/)
│   ├── registry/
│   │   └── skills.yaml                # Skill registration
│   ├── config/
│   │   ├── play-guards.yaml           # /play preview guard defaults
│   │   ├── ship-guards.yaml           # /ship guard defaults (14 ids)
│   │   ├── asset-guards.yaml          # /asset pipeline guard defaults
│   │   ├── cook-package-game.yaml     # Cook/package platform matrix
│   │   ├── cert-game.yaml             # Cert profile config
│   │   ├── prod-readiness-game.yaml   # Production readiness rules
│   │   └── qa-resilience-game.yaml    # QA resilience rules
│   ├── memory/
│   │   └── memory.db                  # SQLite FTS5 (created at runtime)
│   ├── traces/
│   │   ├── play/<timestamp>/          # /play session artifacts
│   │   ├── ship/<timestamp>/          # /ship envelopes + cook logs
│   │   └── asset/<timestamp>/         # /asset generation traces
│   └── workspace-manifest.json        # Project registry
│
├── .cursor/
│   ├── agents/                        # Slim dispatch envelopes (10+)
│   │   ├── play-author.md
│   │   ├── play-preview.md
│   │   ├── play-qa.md
│   │   ├── ship-cook.md
│   │   ├── ship-package.md
│   │   ├── ship-cert.md
│   │   ├── ship-upload.md
│   │   ├── asset-plan.md
│   │   ├── asset-generate.md
│   │   └── asset-place.md
│   ├── mcp-server/
│   │   ├── server.py                  # FastMCP server (gaming GROUPS)
│   │   ├── core/                      # Core MCP tools
│   │   └── lib/_vault.py              # Vault bridge
│   ├── skills/
│   │   ├── memory-toolkit/            # milestone_*, troubleshoot_*
│   │   ├── comfyui-toolkit/           # ComfyUI generation tools
│   │   ├── unreal-bridge/             # UE Remote Control bridge
│   │   ├── unreal-build/              # UBT/UAT build wrappers
│   │   ├── vision-qa/                 # Screenshot diff + perceptual hash
│   │   ├── qa-resilience-game/        # Perf/memory/crash scans
│   │   └── prod-readiness-game/       # Production readiness checks
│   └── rules/
│       └── cuebert-supervisor.mdc     # Supervisor + shortcut routing
│
├── docs/
│   ├── _ai_system/
│   │   ├── agents/                    # 21 canonical agent specs
│   │   ├── standards/                 # Guard specs, cook commands, etc.
│   │   └── examples/                  # Worked dry-run samples
│   └── projects/
│       └── _templates/                # Profile + plan templates
│
├── lib/cue_vault/                     # Vault resolver package
├── registry/services.yaml             # Service registry (repo root)
├── scripts/
│   ├── init-vault.py
│   ├── hydrate-vault.py
│   └── vault_installer/
└── .cursorrules                       # IDE rules
```

---

## Engine Support Matrix

| Engine | Tier | Automation | Status |
|--------|------|-----------|--------|
| **Unreal Engine 5** | **1** | PIE, Remote Control, UAT BuildCookRun, Gauntlet, vision QA | Full tooling (M1–M8) |
| **Unity** | **2** | Stubs + documented contracts | Post-M8 for first-class |
| **Godot** | **3** | Detection + stubs only | Post-M8 |

---

## Roadmap (8 Milestones)

| # | Milestone | Phases | What shipped | Status |
|---|-----------|--------|--------------|--------|
| M1 | Skeleton & supervisor | P1–P8 | Hub marker, vault, MCP server, memory-toolkit (text-only), `cuebert_system_check`, `.cursorrules`, onboard template | **complete** |
| M2 | `/play` harness | P1–P4 | `agent-play.md`, preview guards spec, subagent stubs, sample plan + dry run, `--preview` | **complete** |
| M3 | `/ship` harness | P1–P3 | `agent-ship.md`, ship guards (14 ids), cook/cert/package/upload stubs, INFO→REJECT bridge | **complete** |
| M4 | ComfyUI + asset agent | P1–P4 | `comfyui-toolkit`, `asset-manifest-toolkit`, `agent-asset.md`, pipeline guards, asset plan template | **complete** |
| M5 | Unreal bridge + UE C++ | P1–P4 | `unreal-bridge-toolkit`, `git-lfs-toolkit`, `agent-unreal`, live Remote Control write tools | **complete** |
| M6 | Build + Gauntlet + vision QA | P1–P4 | `unreal-build-toolkit`, `gauntlet-toolkit`, `vision-qa-toolkit`, gaming `build_verify` hooks | **complete** |
| M7 | QA resilience + gaming PR | P1–P3 | `qa-resilience-game`, `prod-readiness-game` (14 rules), strict `/ship` gates | **complete** |
| M8 | Cook + cert | P1–P3 | `cook-package-game` (UAT catalog), `cert-game` (12-checklist advisory), `/ship` guard wiring | **complete** |

**Post-plan:** M9 activated `/play`, `/ship`, `/asset` supervisor routing + `--preview` walkers. M10 added 10 subagent slim dispatchers.

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **`.cuebert/`** hub marker (not `.cue/`) | Clean separation from parent Cue workspace |
| **`registry/services.yaml` at repo root** | Matches `FileVaultResolver` hub layout |
| **Text-only memory by default** | Zero-dependency handoff; no embedding model required |
| **Skill `## Metadata` blocks** (not YAML frontmatter) | Follows Cue skill authoring pattern |
| **`generalPurpose` Tasks only** | Supervisor prohibits gaming-named `subagent_type` values |
| **Deep-merge vault resolution** | Tiered YAML files overlay; later tiers win |
| **`/ship` always commits to memory** | Distribution builds require durable audit trail |
| **Cert is advisory-only** | No vendor SDK; INFO/WARN findings, never blocks ship |

---

## Open Issues

| ID | Issue | Status |
|----|-------|--------|
| I-1 | Reconcile `workspace-manifest.json` "first match wins" text vs `FileVaultResolver` deep-merge | Open |
| I-2 | `build_verify` / `npm_auth_check` / `health_check` assume web stacks — stub or replace with engine profiles | Open (stub in M1, UE hooks in M6) |
| I-3 | Memory mode = text-only by default | **Decided** — implemented in M1-P6 |
| I-4 | `check-cursor-mcp-status.sh` is macOS + Cursor.app specific | Open — documented |

---

## Non-Goals

- Vendoring entire Cue into this repo
- React/Python/Angular phase agents
- DAC/AID/KACES/SFDC tracks
- Gameplay balance analytics or economy tuning
- Live-ops server fleet deployment
- Automatic binary signing or notarization

---

## License

TBD.
