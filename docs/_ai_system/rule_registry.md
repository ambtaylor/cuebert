# CUEBERT RULE REGISTRY

> **SYSTEM ROLE:** The "Phonebook" of Agent Capabilities.
> **MAINTENANCE:** Agents MUST register new files here immediately after Mitosis (file splitting).
> **VERSION:** 1.0

## How This Works

1. **Supervisor reads this file** to find the correct agent for user intent
2. **Language Context** (from Supervisor §0.5) determines which language variant to load
3. **Agents update this file** when they split (Mitosis Protocol)
4. **Capabilities are keywords** that help match user requests to agents

---

## Gaming Harness Agents (Coordinators)

> **Execution context:** All harness coordinators run as **main-chat protocol** — never spawned as Task subagents.

| Agent | Shortcut | Capability / Topic | File Path | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Play Harness** | `/play` | Fast iteration: Plan → Author → Preview → QA → Merge | `docs/_ai_system/agents/agent-play.md` | ✅ Active |
| **Ship Harness** | `/ship` | Cook, certify, package, upload | `docs/_ai_system/agents/agent-ship.md` | ✅ Active |
| **Asset Harness** | `/asset` | AI asset generation via ComfyUI | `docs/_ai_system/agents/agent-asset.md` | ✅ Active |

## Gaming Subagents (Phase Agents)

> **Execution context:** Spawned by harness coordinators via `Task(subagent_type: "generalPurpose")`.

| Agent | Parent Harness | Capability / Topic | File Path (Canonical) | Slim Path | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Play Author** | `/play` | Scoped gameplay/content edits | `agent-play-author.md` | `.cursor/agents/play-author.md` | ✅ Active |
| **Play Preview** | `/play` | PIE launch, screenshot capture, log excerpts | `agent-play-preview.md` | `.cursor/agents/play-preview.md` | ✅ Active |
| **Play QA** | `/play` | Visual diff, console log scan, guard checks | `agent-play-qa.md` | `.cursor/agents/play-qa.md` | ✅ Active |
| **Ship Cook** | `/ship` | UAT BuildCookRun invocation | `agent-ship-cook.md` | `.cursor/agents/ship-cook.md` | ✅ Active |
| **Ship Package** | `/ship` | Create distributable archive | `agent-ship-package.md` | `.cursor/agents/ship-package.md` | ✅ Active |
| **Ship Cert** | `/ship` | Platform certification checklists (advisory) | `agent-ship-cert.md` | `.cursor/agents/ship-cert.md` | ✅ Active |
| **Ship Upload** | `/ship` | Store upload (Steam, Epic, GOG, itch.io) | `agent-ship-upload.md` | `.cursor/agents/ship-upload.md` | ✅ Active |
| **Asset Plan** | `/asset` | Manifest validation, diff against lockfile | `agent-asset-plan.md` | `.cursor/agents/asset-plan.md` | ✅ Active |
| **Asset Generate** | `/asset` | ComfyUI image generation | `agent-asset-generate.md` | `.cursor/agents/asset-generate.md` | ✅ Active |
| **Asset Place** | `/asset` | Place approved assets into Content/ tree | `agent-asset-place.md` | `.cursor/agents/asset-place.md` | ✅ Active |

## Hub Engineering Agents (Orchestrator Track — `/o`)

> **Execution context:** Orchestrator runs as main-chat protocol; phase agents spawned via `Task(subagent_type: "generalPurpose")`. Canonical protocols live under `docs/_ai_system/agents/`; streamlined loaders under `.cursor/agents/`.
>
> **Security report artifacts:** `docs/reports/security/` is created on first use (e.g. `sec-[slug]-[timestamp].md` per `agent-security.md` / `.cursor/agents/security-auditor.md`). No committed placeholder is required.

| Agent | Shortcut | Language | Capability / Topic | Canonical path | Slim path | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Supervisor (canonical doc)** | *(routes all)* | All | Routing, language detection, MCP pre-gate | `docs/_ai_system/agents/agent-supervisor.md` | `.cursor/rules/cuebert-supervisor.mdc` (enforced) | ✅ Active |
| **Orchestrator** | `/o` | PYTHON / CUEBERT / UE_CPP | Lifecycle, research gate, phase chain, remediation | `docs/_ai_system/agents/agent-orchestrator.md` | — | ✅ Active |
| **Research coordinator** | *(Orchestrator only)* | PYTHON / CUEBERT / UE_CPP | Pre-Spec / per-milestone Codebase Context Brief | `docs/_ai_system/agents/agent-research.md` | `.cursor/agents/research-python.md` *(optional when `LANGUAGE=PYTHON`; all languages read canonical first per §4K)* | ✅ Active |
| **Research — Structure** | *(via coordinator)* | PYTHON / CUEBERT / UE_CPP | Layout, conventions, shared components | `docs/_ai_system/agents/agent-research-structure.md` | `.cursor/agents/research-structure-python.md` | ✅ Active |
| **Research — Dependency** | *(via coordinator)* | PYTHON / CUEBERT / UE_CPP | Import/module graph, boundaries | `docs/_ai_system/agents/agent-research-dependency.md` | `.cursor/agents/research-dependency-python.md` | ✅ Active |
| **Research — API** | *(via coordinator)* | PYTHON / CUEBERT / UE_CPP | MCP routes, external contracts, bridge | `docs/_ai_system/agents/agent-research-api.md` | `.cursor/agents/research-api-python.md` | ✅ Active |
| **Diagnostic Probe** | *(remediation only)* | PYTHON / UE_CPP | `DIAGNOSTIC_FINDINGS` before Code cycle 2+ | `docs/_ai_system/agents/agent-diagnostic-probe.md` | `.cursor/agents/diagnostic-probe.md` | ✅ Active |
| **Spec (Python)** | `/spec --python` | PYTHON | Architecture, planning, hub tool design | `docs/_ai_system/agents/agent-spec-python.md` | `.cursor/agents/spec-python.md` | ✅ Active |
| **Code (Python)** | `/code --python` | PYTHON | Hub MCP tools, skills, Python implementation | `docs/_ai_system/agents/agent-coding-python.md` | `.cursor/agents/code-python.md` | ✅ Active |
| **Review (Python)** | `/review --python` | PYTHON | Quality gate, types, tests | `docs/_ai_system/agents/agent-review-python.md` | `.cursor/agents/review-python.md` | ✅ Active |
| **QA (Python)** | *(Orchestrator `/o`)* | PYTHON | pytest / ruff / mypy / depmap evidence | *(see `agent-coding-python.md` §4)* | `.cursor/agents/qa-python.md` | ✅ Active |
| **QA Resilience (Python)** | *(Orchestrator `/o`)* | PYTHON | L2 resilience checks | *(orchestrator §4C)* | `.cursor/agents/qa-resilience-python.md` | ✅ Active |
| **Spec (Cuebert)** | `/spec --cue` | CUEBERT | Agent protocols, rules, standards authoring | `docs/_ai_system/agents/agent-spec-cuebert.md` | `.cursor/agents/spec-cue.md` | ✅ Active |
| **Code (Cuebert)** | `/code --cue` | CUEBERT | System docs, registry, MCP layout | `docs/_ai_system/agents/agent-coding-cuebert.md` | `.cursor/agents/code-cue.md` | ✅ Active |
| **Review (Cuebert)** | `/review --cue` | CUEBERT | Registry, cross-links, doc completeness | `docs/_ai_system/agents/agent-review-cuebert.md` | `.cursor/agents/review-cue.md` | ✅ Active |
| **Spec (UE C++)** | `/spec --ue-cpp` *(rare)* | UE_CPP | C++ / module planning | — *(slim-only)* | `.cursor/agents/spec-ue-cpp.md` | ✅ Active |
| **Code (UE C++)** | `/code --ue-cpp` | UE_CPP | Game C++ modules, bridge contract | `docs/_ai_system/agents/agent-coding-ue-cpp.md` | `.cursor/agents/code-ue-cpp.md` | ✅ Active |
| **Review (UE C++)** | `/review --ue-cpp` | UE_CPP | UObject safety, modules, five-pass review | `docs/_ai_system/agents/agent-review-ue-cpp.md` | `.cursor/agents/review-ue-cpp.md` | ✅ Active |
| **Production Readiness (hub)** | `/d` phase 1; `/o` §4F INFO | PYTHON / CUEBERT / UE_CPP | Dev-artifact / config scan | `docs/_ai_system/agents/agent-production-readiness.md` | `.cursor/agents/prod-readiness.md` | ✅ Active |
| **Deploy harness** | `/d` | PYTHON / CUEBERT / UE_CPP | PR readiness → security → memory → checkin | `docs/_ai_system/agents/agent-deploy.md` | — | ✅ Active |
| **Security** | `/sec`; `/d` phase 2 | PYTHON / UE_CPP (+ infra for all) | SAST / SCA / pattern / infra | `docs/_ai_system/agents/agent-security.md` | `.cursor/agents/security-auditor.md` | ✅ Active |
| **Test (Python hub)** | `/test` | PYTHON | Explore / Codify / Promote | `docs/_ai_system/agents/agent-test-python.md` | — | ✅ Active |
| **Checkin** | *(after `/o` or `/d`)* | All | Leadership activity log | `docs/_ai_system/agents/agent-checkin.md` | `.cursor/agents/checkin.md` | ✅ Active |

## Specialized Agents

| Agent | Shortcut | Capability / Topic | File Path | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Onboard** | `/onboard` | Project registration, hub setup, workspace manifest | `agent-ops-onboard.md` | ✅ Active |
| **Unreal Bridge** | *(via play/asset subagents)* | Editor health, property queries, function calls | `agent-unreal.md` | ✅ Active |
| **Unreal Probe** | *(via play subagents)* | Read-only Remote Control queries for live editor state | `agent-unreal-probe.md` | ✅ Active |
| **Unreal Mutate** | *(via play-author)* | Write operations to editor state | `agent-unreal-mutate.md` | ✅ Active |
| **Prod Readiness (Gaming)** | *(via /ship pre-cook)* | Shipping config scan (REJECT gate) | `agent-prod-readiness-game.md` | ✅ Active |
| **QA Resilience (Gaming)** | *(via /ship post-cook)* | Frame hitches, memory leaks, crashes | `agent-qa-resilience-game.md` | ✅ Active |
| **Cert (Gaming)** | *(via /ship cert phase)* | Platform certification checklists (advisory) | `agent-cert-game.md` | ✅ Active |
| **Cook Package** | *(via /ship cook)* | UAT orchestration with platform matrix | `agent-cook-package-game.md` | ✅ Active |

---

## Skills / Toolkits

> **Location:** `.cursor/skills/` — each skill folder contains a `SKILL.md` and `tools/` directory.

| Skill | MCP Server | Tools | Capabilities | Status |
| :--- | :--- | ---: | :--- | :--- |
| `memory-toolkit` | cuebert-core | 6 | Milestone tracking, troubleshooting history, full-text search | ✅ Active |
| `comfyui-toolkit` | cuebert-asset | 5 | ComfyUI health, image generation, workflow listing, manifest validation | ✅ Active |
| `unreal-bridge` | cuebert-engine | 6 | Editor health, preset queries, property reads/writes, function calls | ✅ Active |
| `unreal-build` | cuebert-engine | 5 | UBT/UAT compilation, cook, commandlets, Gauntlet, log tailing | ✅ Active |
| `cook-package-game` | cuebert-engine | 2 | Cook + package via UAT with platform matrix | ✅ Active |
| `vision-qa` | cuebert-qa | 4 | Screenshot comparison, perceptual hashing, histogram analysis | ✅ Active |
| `qa-resilience-game` | cuebert-qa | 2 | Frame hitches, memory leaks, crashes, streaming stalls | ✅ Active |
| `prod-readiness-game` | cuebert-qa | 2 | Shipping config scan | ✅ Active |
| `cert-game` | cuebert-qa | 2 | Platform certification checklists (Steam, Epic, GOG, itch.io) | ✅ Active |
| `play-guards` | cuebert-qa | 1 | `/play` preview guards (G-1 through G-5) | ✅ Active |
| `ship-guards` | cuebert-qa | 1 | `/ship` pipeline gates | ✅ Active |
| `asset-guards` | cuebert-asset | 1 | `/asset` pipeline guards (format, dimensions, duplicates) | ✅ Active |
| `depmap-toolkit` | *(local;* `.cursor/skills/depmap-toolkit/`*)* | 3 | Hub Python + game UE dependency mapping: `python_ast_map.py`, `module_dep_scan.py`, `graph_cycles.py` (`SKILL.md` + `tools/`) | ✅ Active |

---

## Cursor Rules (.mdc)

| Rule File | Activation | Scope | Status |
| :--- | :--- | :--- | :--- |
| `cuebert-supervisor.mdc` | alwaysApply | Thin router, shortcuts, language detection, MCP gate | ✅ Active |
| `cuebert-engineering.mdc` | alwaysApply | Scope analysis, decomposition, build gates, memory gates | ✅ Active |

---

## Standards & Protocols

| Standard | Purpose | File Path | Status |
| :--- | :--- | :--- | :--- |
| **Agent Shared Lifecycle** | Handoff protocol, §12 structured results, plan auto-completion | `standards/agent-shared-lifecycle.md` | ✅ Active |
| **Dependency Architecture** | Dual-domain dependency mapping (hub Python + game UE modules) | `standards/dependency-architecture.md` | ✅ Active |
| **Build Verify (Gaming)** | Gaming-aware build verification (Unreal check chain) | `standards/build-verify-gaming.md` | ✅ Active |
| **Play Preview Guards** | G-1 through G-5 guard specs | `standards/play-preview-guards.md` | ✅ Active |
| **Ship Guards** | Ship pipeline gate specs | `standards/ship-guards.md` | ✅ Active |
| **Asset Pipeline Guards** | Asset format, dimension, duplicate guards | `standards/asset-pipeline-guards.md` | ✅ Active |
| **Cook Package Commands** | UAT command reference for cook/package | `standards/cook-package-commands.md` | ✅ Active |
| **Cert Game Checklists** | Platform certification checklists | `standards/cert-game-checklists.md` | ✅ Active |
| **Prod Readiness Rules** | Shipping configuration scan rules | `standards/prod-readiness-game-rules.md` | ✅ Active |
| **QA Resilience Rules** | Performance and stability scan rules | `standards/qa-resilience-game-rules.md` | ✅ Active |
| **Asset Manifest** | `.cuebert-assets.yaml` schema | `standards/asset-manifest.md` | ✅ Active |
| **Unreal Bridge Contract** | Remote Control API contract | `standards/unreal-bridge-contract.md` | ✅ Active |
| **Vault Standard** | Credential resolution, tiered overlay | `standards/vault-standard.md` | ✅ Active |
| **Control Plane Paths** | Path conventions for plans, knowledge, profiles | `standards/control-plane-paths.md` | ✅ Active |
| **Game Project LFS** | Git LFS conventions for game assets | `standards/game-project-lfs.md` | ✅ Active |

All paths relative to `docs/_ai_system/`.

---

## MCP Dependencies

| MCP Server | Tool Provided | Required By | Status |
| :--- | :--- | :--- | :--- |
| **sequential-thinking** | `sequentialthinking` | All engineering agents (Spec, Code, Review, Security) | ✅ Required |
| **cuebert-core** | vault_resolve, health_check, build_verify, memory tools | Hub operations, all harnesses | ✅ Required |
| **cuebert-engine** | unreal_bridge, unreal_build, cook_package | `/play`, `/ship` | ✅ Required |
| **cuebert-asset** | comfyui_toolkit, asset_guards | `/asset` | ✅ Required |
| **cuebert-qa** | vision_qa, qa_resilience, prod_readiness, cert, play_guards, ship_guards | QA phases across all harnesses | ✅ Required |

---

## Capability Keywords

> **PRIORITY:** Match shortcuts FIRST, then language flags, then inference keywords.

### Gaming Track
| Shortcut | Inference Keywords | Agent |
|----------|-------------------|-------|
| `/play` | `play`, `iterate`, `preview`, `PIE`, `in-editor`, `gameplay loop`, `level tweak` | Play Harness |
| `/ship` | `ship`, `cook`, `package`, `distribute`, `build`, `certify`, `cert` | Ship Harness |
| `/asset` | `asset`, `texture`, `ComfyUI`, `generate art`, `2D`, `manifest` | Asset Harness |

### Hub Engineering Track
| Shortcut | Inference Keywords | Agent |
|----------|-------------------|-------|
| `/o` | `orchestrate`, `full flow`, `full pipeline`, `spec code review` | Orchestrator |
| `/spec` | `plan`, `architecture`, `design`, `feature spec` | Spec Agent |
| `/code` | `implement`, `code`, `build tool`, `MCP tool`, `skill` | Code Agent |
| `/review` | `review`, `audit`, `check quality` | Review Agent |

### Operations Track
| Shortcut | Inference Keywords | Agent |
|----------|-------------------|-------|
| `/onboard` | `onboard`, `register project`, `add project` | Onboard Agent |

---

## Mitosis Registration Protocol

When an agent splits into a new file:

1. **Create** the new agent file with appropriate rules
2. **Add entry** to the appropriate table above
3. **Update** Capability Keywords table if new keywords apply
4. **Announce:** "Performed Mitosis. Registered `[file]` in rule_registry.md"
