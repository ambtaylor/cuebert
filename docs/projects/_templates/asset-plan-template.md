# /asset plan: {PROJECT} — {SHORT-TITLE}

**Project key**: `{project-key}`  
**Engine**: unreal | unity | godot  
**Created**: YYYY-MM-DD  
**Author**: @username  
**Status**: draft | reviewed | approved

Normative harness protocol: [`docs/_ai_system/agents/agent-asset.md`](../../_ai_system/agents/agent-asset.md). Guard catalog and evidence contract: [`docs/_ai_system/standards/asset-pipeline-guards.md`](../../_ai_system/standards/asset-pipeline-guards.md). Default severities: [`.cuebert/config/asset-guards.yaml`](../../../.cuebert/config/asset-guards.yaml). Manifest schema: [`docs/_ai_system/standards/asset-manifest.md`](../../_ai_system/standards/asset-manifest.md). YAML manifest template: [`asset-manifest-template.yaml`](asset-manifest-template.yaml). Workspace registration: [`.cuebert/workspace-manifest.json`](../../../.cuebert/workspace-manifest.json) and [`docs/_ai_system/standards/control-plane-paths.md`](../../_ai_system/standards/control-plane-paths.md). Worked example: [`docs/_ai_system/examples/asset-sample-run-hello-level.md`](../../_ai_system/examples/asset-sample-run-hello-level.md).

---

## 1. Asset intent

{One paragraph: what assets are being (re)generated and why. Tie to gameplay need if applicable—for example HUD icons for a new screen, hero portraits for character select, or environment tiles for a biome pass.}

---

## 2. Scope

- Specific asset IDs being touched (or **all manifest assets** when the plan targets the full inventory).
- `only: [...]` or `except: [...]` filters if applicable (must stay consistent with CLI `--only` when both are used; empty `only` in plan overrides means **all** targeted by manifest plus harness defaults).

---

## 3. Reference inputs

- **Manifest path** — default `<project-root>/.cuebert-assets.yaml`; override only when registered via `projects.<key>.assetManifestPath` in the workspace manifest (see [`asset-manifest.md`](../../_ai_system/standards/asset-manifest.md) section 4).
- **Concept art / mood boards** — paths under `Content/Refs/` (or engine-equivalent) in the application repo; link repo-relative paths only.
- **Prior successful run lockfile** — `.cuebert-assets.lock.yaml` at project root for skip/regenerate decisions (see [`agent-asset.md`](../../_ai_system/agents/agent-asset.md) section 9).

---

## 4. Success criteria

- All selected assets regenerate cleanly (or correctly **skip_unchanged** when hashes match and policy allows).
- **No guard fails** at effective severity after merges (see [`asset-pipeline-guards.md`](../../_ai_system/standards/asset-pipeline-guards.md) section 6–7).
- **Final checksums** in the lockfile updated for every **placed** asset id in this session.
- **In-editor visual check** optional; defer routine spot-checks to **`/play`** after placement.

---

## 5. Plan overrides

Companion YAML consumed by the coordinator (shape aligns with [`agent-asset.md`](../../_ai_system/agents/agent-asset.md) section 8). Inline comments document non-obvious fields.

```yaml
project: {project-key}              # MUST match PROJECT_KEY and manifest `project`
only: []                          # empty list = all manifest assets (subject to CLI --only)
except: []                        # optional subtractive filter when harness supports it (M5+)
force: false                      # true = ignore lockfile cache, regenerate everything selected
skip_generate_for: []             # ids: generate nothing; use cached/trace asset for placement only
dry_run: true                     # default in M4-P4; false once live ComfyUI is configured and approved
guards_override: {}               # per-guard severity overrides; structural subset per asset-pipeline-guards.md
memory:
  commit_on_success: true         # MANDATORY default; set false only for one-off experiments (discouraged)
```

---

## 6. Memory hooks

On **success**, the harness records via **`milestone_commit`** (mandatory on full pass per [`agent-asset.md`](../../_ai_system/agents/agent-asset.md) section 14): project key, plan milestone slug (for example `asset/2026-04-20-add-hero-portraits`), list of asset ids touched, lockfile path, and a **hash or short digest** of the post-run lockfile for audit—not full raw prompts (security).

---

## 7. Non-goals

- **Not** running **`/play`** or **`/ship`** as part of this plan (separate harness sessions).
- **Not** committing raw prompt text or negative prompts to memory (RAG leakage risk; use ids and paths only).
- **Not** adjusting ComfyUI workflow JSON graphs under review—that belongs in a **separate PR** on the hub [`comfyui-toolkit`](../../../.cursor/skills/comfyui-toolkit/SKILL.md) `workflows/` tree.

---

## 8. Related harness plan templates

Peer iteration and distribution harnesses use parallel Markdown plan shapes:

- [`play-plan-template.md`](play-plan-template.md) — `/play` scope globs, preview map, QA success criteria ([`agent-play.md`](../../_ai_system/agents/agent-play.md)).  
- [`ship-plan-template.md`](ship-plan-template.md) — `/ship` semver, platforms, cert profile, upload channel ([`agent-ship.md`](../../_ai_system/agents/agent-ship.md)).

**Ordering reminder:** run **`/asset`** before **`/play`** when new rasters must land under **`Content/`**; run **`/play`** before **`/ship`** when editor-visible behavior must be frozen before packaging.

---

Status: draft. Consumed by [`agent-asset.md`](../../_ai_system/agents/agent-asset.md). Guards per [`asset-pipeline-guards.md`](../../_ai_system/standards/asset-pipeline-guards.md). Sample run: [`asset-sample-run-hello-level.md`](../../_ai_system/examples/asset-sample-run-hello-level.md).
