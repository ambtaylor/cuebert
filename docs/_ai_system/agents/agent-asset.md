# ASSET HARNESS — 2D Raster Generation & Placement Protocol

> **Role:** Asset-pipeline harness coordinator for manifest-driven ComfyUI generation and project-tree placement  
> **Shortcut:** `/asset`  
> **Activation:** When implemented (M4-P4+ harness wiring; evaluators M5–M6), the Cuebert Supervisor loads this protocol into the **main chat** on `/asset` — same architectural rule as `/o` and `/d`: the harness MUST NOT be spawned as a named `subagent_type` Task; it runs in the main chat so it can chain phase spawns reliably. See `.cursor/rules/cuebert-supervisor.mdc` section 0 (Shortcut Scan) and the `subagent_type` prohibition.  
> **Execution context:** Main chat (NOT a nested orchestrator subagent). Until M4-P4, the Supervisor responds that the harness is not yet wired; this document is the **normative spec** for that wiring.

> **CRITICAL — M4-P3 scope:** This file is **documentation only**. No `.cursor/agents` slims, no Python/shell harness runner, and no live ComfyUI orchestration exist for `/asset` in M4-P3. Subagent names below are **protocol stubs** for M4-P4 sample runs and M5+ engine adapters.

---

## 0. Purpose

`/asset` is Cuebert’s shortcut for **generating or regenerating 2D game assets** declared in a project’s **asset manifest**. The coordinator reads **`<project-root>/.cuebert-assets.yaml`** (or the path declared in **`.cuebert/workspace-manifest.json` → `projects.<key>.assetManifestPath`** per `docs/_ai_system/standards/asset-manifest.md` section 4), determines **which assets** to (re)generate, delegates to **ComfyUI** via **`.cursor/skills/comfyui-toolkit/SKILL.md`** (`comfyui_generate_asset` and related MCP tools), **verifies** outputs against the pipeline guard contract, and **places** validated rasters under the application repository’s content tree (for example Unreal **`Content/`**).

Unlike **`/play`**, which is an **in-editor iteration loop** that produces **preview artifacts** under hub traces without mandating binary writes into the game repo’s distribution intent, **`/asset` is file-producing** — it writes **PNG** (and reserved **EXR**) bytes into the **game project** working tree at manifest-declared **`destination`** paths. Unlike **`/ship`**, it is **pre-distribution** and targets **development-time art passes**, not cook, cert, package, or storefront upload. **`/asset` is a peer of `/play`** in the **iteration layer**: art is generated or refreshed, then operators typically **`/play`** to see results in engine.

**Design posture:** M4-P3 defines **protocol, guards catalog, YAML defaults, and JSON envelopes** only. **Live runner wiring** is **M4-P4+**; **guard evaluators** that can block at **`fail`** severity land in **M5–M6** while **`global.spec_only_as_info: true`** keeps today’s spec from accidentally halting real pipelines.

---

## 1. Relationship to `/play` and `/ship`

| Harness | Produces | Destructive? | Runs engine? | Distribution? |
|---------|----------|--------------|--------------|----------------|
| **`/play`** | In-editor preview artifacts (screenshots, logs) under hub traces | **No** (no mandatory binary promotion into `Content/` from the harness contract) | **Yes** (PIE / Play Mode / run project) | **No** |
| **`/asset`** | **Image files** under project **`Content/`** (or engine-equivalent roots) | **Yes** — overwrites **PNG/EXR** at declared destinations | **No** (generation is ComfyUI + file copy) | **No** |
| **`/ship`** | Distribution **package** + cook outputs | **Yes** (cook trees, staged binaries) | **Yes** (cook subprocess family) | **Yes** (optional upload when plan opts in) |

**Typical ordering:** **`/asset`** often runs **before** **`/play`** when new art is needed (**generate → preview in engine**). It also runs **after** a human **edits the manifest** (prompt tweak, seed change, workflow rename) to **regenerate** targeted rows.

**Peer summary:** **`/play`** = fast visible iteration without ship stakes. **`/ship`** = auditable path to **binaries another human can run** without the workspace. **`/asset`** = **deterministic raster intent** from the manifest, bridged to **ComfyUI** and **on-disk placement**.

---

## 2. Phase chain

**Default happy-path ordering:**

```text
pre-plan guards → plan → post-plan guards → generate (per-asset) → post-generate guards → place → post-place guards → manifest lock update → memory commit
```

### 2.1 Plan (`agent-asset-plan`)

- **Goal:** Read the **asset manifest** and optional **asset plan** companion YAML; diff manifest rows against **`.cuebert-assets.lock.yaml`** when present; emit an **ordered plan** of per-asset actions (**generate**, **skip_unchanged**, **regenerate**, **place_only** when `skip_generate_for` applies).  
- **Inputs:** `PROJECT_KEY`, resolved manifest path, optional CLI filters (`--only`, `--force`, `--dry-run`), plan file fields (`only`, `skip_generate_for`, `guards_override`).  
- **Outputs:** Plan envelope JSON (see `docs/_ai_system/agents/agent-asset-plan.md` section 7).  
- **Implementation:** **M4-P3** stub; deterministic diff rules **M4-P4**; harness **M5+**.

### 2.2 Generate (`agent-asset-generate`)

- **Goal:** For each planned **generate** row, invoke **`comfyui_generate_asset`** with sanitized prompts, merged params, resolved workflow name, and a **trace-scoped destination** under **`.cuebert/traces/asset/<timestamp>/generated/`** — **not** the final `Content/` path (placement is a separate subagent).  
- **Gating:** Post-plan guards **PASS** per section 7 effective severities.  
- **Implementation:** **M4-P3** stub; MCP wiring **M4-P4**; timeouts per **`.cuebert/config/asset-guards.yaml` → `global.generate_max_duration_s`**.

### 2.3 Place (`agent-asset-place`)

- **Goal:** Validate **manifest `destination`**, create **backups** when overwriting, **atomically copy** validated bytes from trace `generated/` into the project tree, **verify checksum**, append **lockfile** rows.  
- **Gating:** Post-generate guards **PASS** for the asset batch (per-asset failures follow section 7).  
- **Implementation:** **M4-P3** stub; atomic copy policy **M4-P4**.

### 2.4 Lockfile update (harness-owned)

- **Goal:** Rewrite **`<project-root>/.cuebert-assets.lock.yaml`** with **version**, **`generated_at`**, per-asset **`workflow_hash`**, **`prompt_hash`**, **`params_hash`**, **`seed`**, **`result_path`**, **`result_sha256`**, **`comfyui_version`** (see section 9).  
- **Skippable:** **No** on full success path — lockfile is the **skip-regeneration** oracle for the next run.

### 2.5 Memory commit (harness-owned)

- **Goal:** **`milestone_commit` on success** (section 14) — **mandatory**, mirroring **`/ship`** policy, unlike **`/play`**. Partial success and failure behaviors are section 14.

### 2.6 Plan directives that skip phases

The **asset plan** YAML MAY include:

- **`skip_generate_for: [id, ...]`** — harness runs **place** from existing trace artifacts or cached prior outputs per **M4-P4** rules (doc stub only in M4-P3).  
- **`dry_run: true`** — no ComfyUI **live** HTTP where toolkit honors **`CUEBERT_COMFYUI_MODE`**; synthetic envelopes still produced for walk-through (**M4-P4**).

### 2.7 Session outcomes (normative vocabulary)

| State | Meaning | Next action |
|-------|---------|-------------|
| **`running`** | A phase Task or harness step is in flight. | Wait; avoid duplicate generation for the same session id. |
| **`blocked`** | A guard at **`fail`** effective severity halted the chain (or placement rollback exhausted). | Operator inspects trace + guard envelope; fixes manifest, plan, or disk permissions; re-runs `/asset`. |
| **`partial`** | Some assets **generated and placed**, others **failed**; lockfile updated only for successful ids unless policy says otherwise (**M4-P4**). | Review `per_asset` in coordinator envelope; remediate failed ids. |
| **`complete`** | All targeted assets reached **placed** state; lockfile consistent; memory commit succeeded. | Continue with **`/play`** preview or human review. |

### 2.8 Harness position in the cuebert chain

```text
/asset  →  /play  →  /ship  →  (optional) /cook …
```

**Narrative:** Art passes feed **editor-visible** iteration; **ship** remains the **distribution** gate.

---

## 3. Subagent roster

The `/asset` harness dispatches **`Task(subagent_type: "generalPurpose")`** roles whose **first action** is to read the canonical doc for that row — identical prohibition family as **`/play`** and **`/ship`**: never **`orchestrate`** or gaming-named Cursor auto-types as **`subagent_type`**.

| Subagent | File | Role |
|----------|------|------|
| **`agent-asset-plan`** | `docs/_ai_system/agents/agent-asset-plan.md` | Read manifest, diff against last-run **lockfile**, produce **ordered asset plan**. |
| **`agent-asset-generate`** | `docs/_ai_system/agents/agent-asset-generate.md` | Invoke **`comfyui_generate_asset`** per asset; collect **trace-local** artifacts + checksums. |
| **`agent-asset-place`** | `docs/_ai_system/agents/agent-asset-place.md` | Copy **validated** images into project **`Content/`** tree; manage **backups** + **lockfile** rows. |

**Orchestrator rule:** These are **logical roles** invoked by the **main-chat** harness coordinator (the “asset harness brain”), not standalone supervisor routes.

### 3.1 Dispatch rules (M4-P4+)

| Rule | Detail |
|------|--------|
| **Task type** | Always **`generalPurpose`** unless a future milestone documents **`shell`** isolation for ComfyUI log streaming only. |
| **Harness location** | `/asset` coordinator runs in **main chat** per `.cursor/rules/cuebert-supervisor.mdc`. |
| **Chaining** | Default **auto-chain** Plan → Generate loop → Place → Lockfile → Memory unless **`--pause`** (future parity with `/o` section 8 semantics — **M4-P4**). |
| **Parallelism** | **No** parallel **`comfyui_generate_asset`** calls for the **same asset id** in one session; batching across **distinct ids** is harness policy **M5** (GPU memory safety). |

---

## 4. Inputs

### 4.1 Primary inputs

| Input | Required | Description |
|-------|----------|-------------|
| **`PROJECT_KEY`** | Yes | Key under **`.cuebert/workspace-manifest.json` → `projects`**; resolves **`APP_REPO`** and optional **`assetManifestPath`**. |
| **Asset manifest YAML** | Yes | Resolved per `docs/_ai_system/standards/asset-manifest.md` section 4.2 unless **`--manifest`** supplies an allowed override path. |
| **Asset plan** | Recommended | Companion YAML or markdown+YAML front-matter declaring **`only`**, **`force`**, **`skip_generate_for`**, **`dry_run`**, **`guards_override`**, **`memory`** — see section 8. |
| **`HUB_REPO`** | Yes | Absolute path to cuebert hub checkout (trace roots, workflows directory, guard configs). |
| **`APP_REPO`** | Yes | Absolute path to application repository root (`projects.{key}.path`). |

### 4.2 CLI-style flags (normative names; parser M4-P4)

| Flag | Effect |
|------|--------|
| **`--manifest <path>`** | One-off regeneration manifest path; must normalize under **`APP_REPO`** or hub allow-list per **`asset_manifest_validate`** security rules. |
| **`--force`** | Treat all targeted rows as **`regenerate`** even when lockfile hashes match. |
| **`--only id1,id2`** | Restrict planning to listed **`assets[].id`** values. |
| **`--dry-run`** | Walk guards + plan + synthetic generate envelopes; **no** live ComfyUI HTTP when toolkit mode is **`dry_run`** (**M4-P1** default behavior when unconfigured). |
| **`--fail-fast`** | First post-generate **`fail`** stops subsequent asset generates (default: continue other assets). |

### 4.3 Workspace manifest fields

Beyond **`path`** and optional **`assetManifestPath`**, the harness MAY read **`engine`**, **`engine_version`**, and future **`assetGuards.overrides`** (analogous to play/ship guard override ideas — **M5** prose) for severity merges.

---

## 5. Outputs

### 5.1 Primary outputs

| Output | Location / description |
|--------|------------------------|
| **Placed rasters** | **`APP_REPO`** paths from manifest **`destination`** fields (e.g. **`Content/Art/...png`**). |
| **Session trace** | **`.cuebert/traces/asset/<timestamp>/`** — per-asset envelopes, guard findings, **`generated/`**, **`backups/`**, **`guards.json`**. |
| **Lockfile** | **`<project-root>/.cuebert-assets.lock.yaml`** — committed to **git**; small, deterministic (section 9). |

### 5.2 Coordinator envelope

Top-level JSON shape (section 10) is written to **`envelope.json`** under the trace root for Attest-style audits (mirrors **`/ship`** **`envelope.json`** philosophy).

### 5.3 Secondary outputs

| Output | Description |
|--------|-------------|
| **`milestone_commit`** | **Mandatory on full success**; optional on partial / failure per section 14. |
| **`troubleshoot_commit`** | On **`fail`** outcomes with novel errors — **recommended** for RAG loops (section 14). |

### 5.4 Trace layout (recommended)

| Path under `.cuebert/traces/asset/<timestamp>/` | Contents |
|-------------------------------------------------|----------|
| **`plan/plan.json`** | Serialized plan envelope from **`agent-asset-plan`**. |
| **`generated/<asset_id>.png`** | Raster bytes (or placeholder when dry-run) before placement. |
| **`place/place.json`** | Per-asset placement results + backup paths. |
| **`guards/`** | Guard evaluator envelopes per gate (**`pre-plan`**, **`post-plan`**, **`post-generate`**, **`post-place`**). |
| **`backups/<asset_id>.bak`** | Prior bytes when overwriting existing destinations. |

**Example trace path (future):** **`.cuebert/traces/asset/example-*`** lands in **M4-P4** per plan; traces remain **git-ignored** by default in hub policy.

### 5.5 Hub vs application repo boundaries

Raster **bytes** are authored into **`APP_REPO`** content paths. **Traces** remain **hub-resident** under **`.cuebert/traces/asset/`** per **`docs/_ai_system/standards/control-plane-paths.md`**.

---

## 6. Asset pipeline guards

**Authoritative spec:** **`docs/_ai_system/standards/asset-pipeline-guards.md`**. **Defaults:** **`.cuebert/config/asset-guards.yaml`**.

| Gate class | When run | Count |
|------------|----------|-------|
| **Pre-plan** | Before manifest/plan resolution mutates state | **2** guards |
| **Post-plan** | After **`agent-asset-plan`** envelope is accepted | **2** guards |
| **Post-generate** | After each asset’s **`comfyui_generate_asset`** completes | **2** guards |
| **Post-place** | After **`agent-asset-place`** for an asset | **2** guards |

**Total:** **8** stable guard ids — **API surface** frozen in **M4-P3**.

**M4-P3 evaluators:** **None** — all rows are **`spec only (M4-P3)`**; with **`global.spec_only_as_info: true`**, harnesses treat unimplemented evaluators as **`info`** findings so **`fail`** cannot block live pipelines until **M5–M6**.

### 6.1 Severity vocabulary

Mirrors **`play-preview-guards.md`** / **`ship-guards.md`**: **`fail`**, **`warn`**, **`info`** with harness mapping in section 7.

---

## 7. Decision tree

**Standard severity resolution:**

1. Load **`.cuebert/config/asset-guards.yaml`**.  
2. Merge optional **`guards_override`** from the asset plan (structural subset only — **M4-P4** merge rules).  
3. Merge future **`workspace-manifest.json`** per-project overrides when schema lands (**M5**).  
4. For each enabled guard, compute **effective severity**: respect **`spec_only_as_info`** mapping for **spec-only** evaluators (**info** only in M4-P3 default posture).

**Harness pseudo-flow:**

```text
PRE-PLAN GUARDS
  If any effective fail → abort code pre_plan_fail (or manifest-specific subcode).
  Else continue.

PLAN (agent-asset-plan)
  If envelope.status != pass → abort.

POST-PLAN GUARDS
  If any effective fail → abort.

FOR EACH asset in plan (respect --fail-fast):
  If action is skip → record skipped_unchanged; continue.
  If action requires generate:
      RUN agent-asset-generate
      POST-GENERATE GUARDS on that asset
      If effective fail → mark asset failed; continue or halt if --fail-fast.
  If placement required:
      RUN agent-asset-place
      POST-PLACE GUARDS
      If effective fail → rollback placement for that asset (section 13); mark failed.

LOCKFILE UPDATE
  Write .cuebert-assets.lock.yaml for all successful placements.

MEMORY
  On full success → mandatory milestone_commit (section 14).
  On partial → policy table in section 14.
  On total failure → troubleshoot_commit recommended.
```

**Abort codes (illustrative, stable keys for tooling):** **`pre_plan_fail`**, **`post_plan_fail`**, **`generate_fail`**, **`place_fail`**, **`lockfile_write_fail`**, **`memory_commit_fail`**.

---

## 8. Inputs: asset plan schema

`/asset` consumes a **PLAN** artifact declaring **intent** on top of the manifest’s **inventory** (same philosophical split as **`/ship`** requiring a ship plan, not just a raw engine).

**Authoritative template path (stub):** **`docs/projects/_templates/asset-plan-template.yaml`** — **real template lands M4-P4**.

**Normative example:**

```yaml
# Companion to .cuebert/plans/asset/2026-04-20-add-hero-portraits.md
# OR inline under docs/projects/<project>/plans/asset/...
project: hello-level
only: [hero_idle, hero_portrait_1]
force: false
skip_generate_for: []
dry_run: false
guards_override: {}
memory:
  commit_on_success: true
```

**Field notes:**

- **`project`:** MUST match **`PROJECT_KEY`** and manifest **`project`** field.  
- **`only`:** When absent, plan targets **all manifest assets** subject to lockfile diff unless **`--only`** narrows further.  
- **`force`:** Operator override mirroring **`--force`**.  
- **`skip_generate_for`:** List of ids that should **reuse** existing generated bytes in the trace dir (**M4-P4** copy rules).  
- **`guards_override`:** Map of **`guard_id` → {enabled, default_severity, threshold}`** subset.  
- **`memory.commit_on_success`:** When **`false`**, still discouraged for production policy — harness MAY treat as **`warn`** finding (**M5** policy).

---

## 9. Lockfile

**Path:** **`<project-root>/.cuebert-assets.lock.yaml`**

**Normative example:**

```yaml
version: 1
project: hello-level
generated_at: 2026-04-20T12:00:00Z
assets:
  - id: hero_idle
    workflow_hash: sha256:abc...
    prompt_hash: sha256:def...
    params_hash: sha256:123...
    seed: 42
    result_path: Content/Art/Heroes/hero_idle.png
    result_sha256: sha256:789...
    comfyui_version: "0.3.0"
```

**Purpose:** **`agent-asset-plan`** compares **hashes** + **`seed`** + **`comfyui_version`** to decide **`skip_unchanged`** vs **`regenerate`**. The lockfile is **small**, **deterministic**, and **committed** so CI and humans can audit what bytes correspond to which intent.

**Collision note:** If two different prompts share the same **`id`**, that is a **developer error** in manifest authoring — the lockfile row is **last writer wins**; the harness does **not** attempt content-addressed de-duplication across ids.

---

## 10. Outputs: envelope shape

**Coordinator top-level envelope (JSON):**

```json
{
  "status": "pass",
  "project": "hello-level",
  "generated_count": 2,
  "skipped_count": 3,
  "failed_count": 0,
  "per_asset": [
    {"id": "hero_idle", "status": "generated", "result_path": "Content/Art/Heroes/hero_idle.png"},
    {"id": "barrel_01", "status": "skipped_unchanged", "reason": "hashes_match"}
  ],
  "trace_dir": ".cuebert/traces/asset/2026-04-20T12-00-00Z",
  "lockfile_updated": true,
  "memory_id": "abc123..."
}
```

**`status` values (coordinator):** **`pass`** | **`warn`** | **`fail`** — **`warn`** when non-fatal guard **`warn`** findings exist but all **`fail`**-class gates resolved without halt policy.

**`per_asset.status` examples:** **`generated`**, **`skipped_unchanged`**, **`failed_generate`**, **`failed_place`**, **`rolled_back`**.

---

## 11. Engine support

**M4 posture:** **Engine-agnostic** — the harness writes **image files** to project-relative paths declared in the manifest. No **`.uasset`** creation is implied.

| Milestone | Extension |
|-----------|-----------|
| **M5** | Unreal-specific **import** bridge (optional auto **`.uasset`** wrappers) — see Unreal bridge docs when published. |
| **M6** | **Vision QA** hooks comparing renders to references. |
| **M7+** | Unity/Godot-specific placement adapters if path rewriting is required beyond manifest strings. |

---

## 12. Non-goals

| Non-goal | Redirect |
|----------|----------|
| **Audio, animation, 3D meshes, shader graphs** | Out of **M4** charter — future engine toolkits. |
| **Live editor hot-reload** into Unreal | **M5** editor integration territory. |
| **Scheduled CI batch without human gate** | **`/asset`** is **interactive-first**; CI patterns are future ops docs. |
| **Licensing / attribution metadata** | Future milestone; manifest **`tags`** are not a license ledger. |
| **Remote ComfyUI beyond base URL + optional token** | **`comfyui-toolkit`** vault/env model; no bespoke OAuth in M4. |
| **Cook / package / cert** | **`/ship`** |

---

## 13. Rollback

**Per-asset placement rollback:** If **`agent-asset-place`** fails after a partial write, the harness restores the **prior file** from **`.cuebert/traces/asset/<timestamp>/backups/`** when the **prior checksum** is known from the **pre-run lockfile** **`result_sha256`**. If no prior file existed, rollback deletes the partial destination.

**Atomicity:** Placement MUST use **write-to-temp + rename** into final **`destination`** (subagent doc mirrors **`agent-asset-place.md`**).

**Generate failures:** No project-tree mutation for that asset; trace may retain partial downloads for forensics — operator deletes if needed.

---

## 14. Memory hooks (MANDATORY on success)

Unlike **`/play`**, **`/asset` requires `milestone_commit` on successful completion** of the coordinator’s **`status: pass`** path (mirrors **`/ship`** section 13 policy difference vs **`/play`**).

**Illustrative Python-shaped call (documentation only):**

```python
milestone_commit(
  project_key="hello-level",
  milestone="asset/2026-04-20-add-hero-portraits",
  status="completed",
  files_touched="Content/Art/Heroes/hero_idle.png;Content/Art/Heroes/hero_portrait_1.png",
  notes="comfyui_generate_asset dry_run=false; lockfile updated",
)
```

| Event | Tool | Minimum payload |
|-------|------|-----------------|
| **Success** | **`milestone_commit`** | **`project_key`**, **`milestone`** slug from plan, **`files_touched`**, **`trace_dir`**, lockfile path |
| **Partial** | **`milestone_commit`** or **`troubleshoot_commit`** | Harness policy **M4-P4** — at minimum record **`failed_count`** + **`per_asset`**. |
| **Failure** | **`troubleshoot_commit`** | Abort code, first failing **`guard_id`**, trace path |

**Failure RAG:** Any coordinator **`fail`** SHOULD also enqueue a **`troubleshoot_commit`** entry when the failure mode is novel (same spirit as **`/ship`**).

---

## 15. Security notes

- **Prompt injection:** Manifest prompts may contain **user-authored** text; **`comfyui_generate_asset`** MUST reuse the **M4-P1** **`_comfyui_client`** sanitizer paths documented in **`comfyui-toolkit`** before HTTP submit.  
- **Path traversal:** **`destination`** MUST reject **`..`**, absolute paths outside **`APP_REPO`**, and Windows device paths — validator rules in **`asset-manifest.md`** section 3.4; placement re-validates.  
- **Secrets:** ComfyUI **tokens** live in **vault** / env per **`vault-standard.md`** — never in the manifest.  
- **Lockfile integrity:** Treat tampering as out-of-scope threat model for M4; operators use git history.

---

## 16. Cross-references

| Doc | Relationship |
|-----|--------------|
| `docs/_ai_system/standards/asset-manifest.md` | Schema consumed by Plan + Place |
| `docs/_ai_system/standards/asset-pipeline-guards.md` | Guard taxonomy + evidence contract |
| `.cuebert/config/asset-guards.yaml` | Default severities + thresholds |
| `.cursor/skills/comfyui-toolkit/SKILL.md` | MCP tools invoked by Generate |
| `docs/_ai_system/agents/agent-asset-plan.md` | Plan subagent stub |
| `docs/_ai_system/agents/agent-asset-generate.md` | Generate subagent stub |
| `docs/_ai_system/agents/agent-asset-place.md` | Place subagent stub |
| `docs/_ai_system/agents/agent-play.md` | Peer iteration harness |
| `docs/_ai_system/agents/agent-ship.md` | Peer distribution harness |
| `docs/_ai_system/standards/control-plane-paths.md` | Trace + plan path conventions |
| `docs/_ai_system/agents/agent-ops-onboard.md` | Workspace manifest onboarding |
| `.cursor/rules/cuebert-supervisor.mdc` | `/asset` shortcut stub |

---

## 17. Footer

**Status:** **M4-P3** — coordinator spec + subagent stubs + guards catalog + default YAML. **Plan template + sample run:** **M4-P4**. **Unreal import bridge:** **M5**. **Vision QA:** **M6**. **Live guard evaluators that block at `fail`:** **M5–M6** once **`spec_only_as_info`** is flipped project-by-project with real evaluators deployed.
