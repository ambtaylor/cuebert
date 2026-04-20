# Asset sample run: hello-level — 3 hero portraits

**Project**: `hello-level` (Unreal 5.4 sample project)  
**Mode**: `dry_run: true` (`CUEBERT_COMFYUI_MODE=dry_run` — default in M4)  
**Plan file**: `docs/projects/hello-level/plans/asset/2026-04-20-add-hero-portraits.md`  
**Trace dir**: `.cuebert/traces/asset/example-2026-04-20T13-00-00Z/`  
**Commit**: M4-P4 worked example

Normative coordinator: [`docs/_ai_system/agents/agent-asset.md`](../agents/agent-asset.md). Subagents: [`agent-asset-plan.md`](../agents/agent-asset-plan.md), [`agent-asset-generate.md`](../agents/agent-asset-generate.md), [`agent-asset-place.md`](../agents/agent-asset-place.md). Guards: [`docs/_ai_system/standards/asset-pipeline-guards.md`](../standards/asset-pipeline-guards.md). Defaults: [`.cuebert/config/asset-guards.yaml`](../../.cuebert/config/asset-guards.yaml). Manifest: [`asset-manifest.md`](../standards/asset-manifest.md). Plan template: [`docs/projects/_templates/asset-plan-template.md`](../../projects/_templates/asset-plan-template.md).

---

## 1. Purpose

This document is a **documentation-only dry run** that walks the **M4 `/asset` harness** from **pre-plan guards** through **`milestone_commit`**, using a **hypothetical** Unreal project named **`hello-level`**. **No live ComfyUI server** is contacted when **`CUEBERT_COMFYUI_MODE=dry_run`** (or the toolkit is unconfigured). **No Cursor Tasks run.** All JSON envelopes and trace paths are **illustrative** but aligned with:

- [`docs/_ai_system/agents/agent-asset.md`](../agents/agent-asset.md) (parent protocol, phase chain §2, coordinator envelope §10, memory §14)
- [`docs/_ai_system/standards/asset-pipeline-guards.md`](../standards/asset-pipeline-guards.md) (eight guard ids, four gate classes, §2 ordering)
- [`.cuebert/config/asset-guards.yaml`](../../.cuebert/config/asset-guards.yaml) (`global.spec_only_as_info`, `generate_max_duration_s`)
- Subagent output contracts in [`agent-asset-plan.md`](../agents/agent-asset-plan.md) §7, [`agent-asset-generate.md`](../agents/agent-asset-generate.md) §9, [`agent-asset-place.md`](../agents/agent-asset-place.md) §7

Use this file as the **M4 integration narrative**: it ties **asset plan intent**, **all eight guards**, **subagent envelopes**, **lockfile mutation**, and **on-disk traces** together before **M5** (Unreal import bridge) and **M5–M6** (strict evaluators that can block at `fail` when `spec_only_as_info` is tuned off per project).

---

## 2. Scenario setup

### 2.1 Project

| Field | Value |
|-------|-------|
| **Project key** | `hello-level` |
| **Engine** | Unreal Engine **5.4** (hypothetical sample) |
| **Manifest note** | The committed hub [`.cuebert/workspace-manifest.json`](../../.cuebert/workspace-manifest.json) may still use sparse `projects`. This dry run assumes **`projects.hello-level.path`** resolves so **`guard.project.exists`** can read **`pass`** in the worked trace. |

### 2.2 Scenario

The team is adding **three new hero portraits** for a **character select** screen. The asset manifest declares them with **fixed seeds** for reproducibility. The first team run uses **`dry_run: true`** because **no one has configured** a reachable ComfyUI endpoint yet—Cuebert’s **default safety posture** mirrors the comfyui-toolkit dry-run policy ([`.cursor/skills/comfyui-toolkit/SKILL.md`](../../../.cursor/skills/comfyui-toolkit/SKILL.md) §Dry-run mode).

### 2.3 Guard catalog reference (all eight ids)

From [`.cuebert/config/asset-guards.yaml`](../../.cuebert/config/asset-guards.yaml) / [`asset-pipeline-guards.md`](../standards/asset-pipeline-guards.md) §2:

1. `guard.project.exists` — pre-plan  
2. `guard.manifest.valid` — pre-plan  
3. `guard.plan.non_empty` — post-plan  
4. `guard.plan.workflow_available` — post-plan  
5. `guard.generate.exit_status` — post-generate (per asset)  
6. `guard.generate.file_size_sane` — post-generate (per asset)  
7. `guard.place.destination_writable` — post-place (per asset)  
8. `guard.place.lockfile_updated` — post-place (per asset)  

**Verdict vocabulary** for findings: `pass`, `warn`, `fail`, `info` (per [`asset-pipeline-guards.md`](../standards/asset-pipeline-guards.md) and the `spec_only_as_info` policy).

### 2.4 Success criteria (asset harness)

- Pre-plan **`verdict: pass`** with both pre-plan guards **pass** (manifest validator tool from **M4-P2** backs **`guard.manifest.valid`** in this narrative).  
- Plan envelope shows **`to_generate: 3`**, **`to_skip: 0`** (no lockfile yet).  
- Post-plan **`guard.plan.non_empty`** **pass**; **`guard.plan.workflow_available`** recorded as **`info`** while `flux_portrait_v1.json` is missing from the empty **M4-P1** workflows directory—consistent with **`spec_only_as_info: true`**.  
- Each generate envelope: **`status: dry_run_synthetic`** per [`agent-asset-generate.md`](../agents/agent-asset-generate.md) §23; synthetic **`prompt_id`** prefix **`dry_run_`**.  
- Post-generate guards: **`guard.generate.exit_status`** treats dry-run synthetic as **success family**; **`guard.generate.file_size_sane`** observes **2MiB** synthetic placeholder policy.  
- Each place envelope: **`status: placed`**, **`final_sha256`** matches generate checksum.  
- Post-place guards **pass** for all three assets; **lockfile** lists three rows matching digests.  
- **`milestone_commit`** returns **`status: ok`**; coordinator rollup **`status: pass`**.

### 2.5 Plan file contents (inline YAML)

Path: `docs/projects/hello-level/plans/asset/2026-04-20-add-hero-portraits.md` (Markdown body would restate intent; **machine-readable overrides** are the block below).

```yaml
project: hello-level
only: []
except: []
force: false
skip_generate_for: []
dry_run: true
guards_override: {}
memory:
  commit_on_success: true
```

### 2.6 Manifest excerpt (three assets)

Illustrative rows only—full file would include `defaults` per [`asset-manifest-template.yaml`](../../projects/_templates/asset-manifest-template.yaml).

```yaml
version: 1
project: hello-level
engine: unreal
defaults:
  workflow: flux_portrait_v1
  destination_root: Content/Art/
  params:
    width: 1024
    height: 1024
    steps: 28
assets:
  - id: hero_warrior_portrait
    prompt: "Stylized warrior portrait, bust, warm key light, game UI headshot."
    destination: Content/Art/Heroes/hero_warrior_portrait.png
    workflow: flux_portrait_v1
    seed: 1001
  - id: hero_mage_portrait
    prompt: "Stylized mage portrait, bust, cool rim light, game UI headshot."
    destination: Content/Art/Heroes/hero_mage_portrait.png
    workflow: flux_portrait_v1
    seed: 1002
  - id: hero_rogue_portrait
    prompt: "Stylized rogue portrait, bust, neutral grading, game UI headshot."
    destination: Content/Art/Heroes/hero_rogue_portrait.png
    workflow: flux_portrait_v1
    seed: 1003
```

### 2.7 Workspace manifest fragment (`assetManifestPath`)

```json
{
  "projects": {
    "hello-level": {
      "path": "/abs/path/hello-level",
      "engine": "unreal",
      "engineVersion": "5.4.0",
      "assetManifestPath": "/abs/path/hello-level/.cuebert-assets.yaml"
    }
  }
}
```

---

## 3. Harness timeline (happy path)

Ordered traversal matches [`agent-asset.md`](../agents/agent-asset.md) §2 and [`asset-pipeline-guards.md`](../standards/asset-pipeline-guards.md) §2.3:

1. **PRE-PLAN GUARDS** — stable order: `guard.project.exists`, then `guard.manifest.valid`; on effective **`fail`**, abort with coordinator subcode **`pre_plan_fail`**.  
2. **PLAN** — dispatch **`agent-asset-plan`**; consume manifest + plan YAML + optional lockfile.  
3. **POST-PLAN GUARDS** — `guard.plan.non_empty`, `guard.plan.workflow_available`.  
4. **GENERATE (per asset)** — dispatch **`agent-asset-generate`** for each **`generate`** row; trace-local bytes or placeholders.  
5. **POST-GENERATE GUARDS (per asset)** — `guard.generate.exit_status`, `guard.generate.file_size_sane`.  
6. **PLACE (per asset)** — dispatch **`agent-asset-place`**; atomic write story per [`agent-asset-place.md`](../agents/agent-asset-place.md) §5–6.  
7. **POST-PLACE GUARDS (per asset)** — `guard.place.destination_writable`, `guard.place.lockfile_updated`.  
8. **LOCKFILE UPDATE** — coordinator writes **`.cuebert-assets.lock.yaml`** on **`APP_REPO`**.  
9. **MEMORY** — **`milestone_commit`** on full success (**mandatory** per [`agent-asset.md`](../agents/agent-asset.md) §14).  
10. **COORDINATOR ENVELOPE** — trace root **`envelope.json`** with **`status: pass`**.

Each subsection: **step**, **actor**, **conceptual inputs**, **representative JSON** (or pointer to committed fixture), **verdict / next**.

---

### 3.1 Step — User invokes `/asset`

**Actor:** Operator in main chat.  
**Input:** `/asset docs/projects/hello-level/plans/asset/2026-04-20-add-hero-portraits.md`  
**Behavior:** Supervisor routes to the **`/asset`** harness coordinator per [`.cursor/rules/cuebert-supervisor.mdc`](../../../.cursor/rules/cuebert-supervisor.mdc) shortcut policy (stub until wiring; this doc assumes **M4-P4** narrative routing to [`agent-asset.md`](../agents/agent-asset.md)).  
**Next:** **Pre-plan guards**.

---

### 3.2 Step — Pre-plan guards

**Actor:** harness guard runner (pre-plan class).  
**Sample input (conceptual):**

```text
PROJECT_KEY=hello-level
APP_REPO=/abs/path/hello-level
MANIFEST_PATH=/abs/path/hello-level/.cuebert-assets.yaml
GUARD_CONFIG=.cuebert/config/asset-guards.yaml
SPEC_ONLY_AS_INFO=true
```

**Sample output:** committed fixture **`.cuebert/traces/asset/example-2026-04-20T13-00-00Z/guards/pre_plan.json`** — both **`guard.project.exists`** and **`guard.manifest.valid`** report **`pass`** (validator tool from **M4-P2** assumed available in this clean narrative).  
**Phase verdict:** `pass`.  
**Next:** dispatch **`agent-asset-plan`**.

---

### 3.3 Step — `agent-asset-plan`

**Actor:** `agent-asset-plan`.  
**Sample output (`plan/envelope.json`):**

```json
{
  "status": "pass",
  "project": "hello-level",
  "plan": [
    {"id": "hero_mage_portrait", "action": "generate", "reason": "no_lockfile_row"},
    {"id": "hero_rogue_portrait", "action": "generate", "reason": "no_lockfile_row"},
    {"id": "hero_warrior_portrait", "action": "generate", "reason": "no_lockfile_row"}
  ],
  "total": 3,
  "to_generate": 3,
  "to_skip": 0,
  "findings": []
}
```

**Note:** [`agent-asset-plan.md`](../agents/agent-asset-plan.md) §18 default sorts **`plan[]`** by **`id`** ascending for stable transcripts—**mage**, **rogue**, **warrior** here.  
**Phase verdict:** `pass`.  
**Next:** **post-plan guards**.

---

### 3.4 Step — Post-plan guards

**Actor:** harness guard runner (post-plan class).  
**Highlights:**

- **`guard.plan.non_empty`** → **`pass`** (`to_generate == 3`).  
- **`guard.plan.workflow_available`** → **`info`** in this fixture: `flux_portrait_v1.json` is **not** on disk yet (empty **`workflows/`** in **M4-P1**); with **`global.spec_only_as_info: true`**, the harness **does not** halt the dry-run documentation path.

**Representative file:** `.cuebert/traces/asset/example-2026-04-20T13-00-00Z/guards/post_plan.json`.  
**Phase verdict:** `pass`.  
**Next:** **Generate loop**.

---

### 3.5 Step — `agent-asset-generate` (per asset)

**Actor:** `agent-asset-generate` (three invocations).  
**Common fields:** `WORKFLOW_NAME=flux_portrait_v1`, `DRY_RUN=true`, `TRACE_ROOT=.cuebert/traces/asset/example-2026-04-20T13-00-00Z/`.

**Representative (`generate/hero_warrior_portrait.json`):**

```json
{
  "id": "hero_warrior_portrait",
  "status": "dry_run_synthetic",
  "trace_png_path": ".cuebert/traces/asset/example-2026-04-20T13-00-00Z/generated/hero_warrior_portrait.png.txt",
  "checksum_sha256": "sha256:m4p4000000000000000000000000000000000000000000000000000000000003",
  "duration_ms": 14,
  "dry_run": true,
  "workflow": "flux_portrait_v1",
  "seed": 1001,
  "toolkit": {
    "prompt_id": "dry_run_warrior_7b2a9e0f",
    "tool_status": "pass"
  },
  "error_code": null,
  "notes": "Synthetic 2MiB placeholder path; CUEBERT_COMFYUI_MODE=dry_run."
}
```

**Phase verdict (batch):** `pass` for each asset in this happy path.  
**Next:** **post-generate guards** after each asset.

---

### 3.6 Step — Post-generate guards (per asset)

**Actor:** harness guard runner (post-generate class).  
**Ordering:** for each **`asset_id`**, evaluate **`guard.generate.exit_status`** then **`guard.generate.file_size_sane`** ([`asset-pipeline-guards.md`](../standards/asset-pipeline-guards.md) §2.3).

**Fixture:** `.cuebert/traces/asset/example-2026-04-20T13-00-00Z/guards/post_generate.json` — **six** rows total (**2 × 3**), all **`pass`**. **`guard.generate.exit_status`** accepts **`dry_run_synthetic`** as the dry-run success family; **`guard.generate.file_size_sane`** uses **2097152** bytes (**2MiB**) synthetic policy inside thresholds **`warn_bytes_min` / `warn_bytes_max`** from YAML.

**Phase verdict:** `pass`.  
**Next:** **`agent-asset-place`**.

---

### 3.7 Step — `agent-asset-place` (per asset)

**Actor:** `agent-asset-place`.  
**Representative (`place/hero_mage_portrait.json`):**

```json
{
  "id": "hero_mage_portrait",
  "status": "placed",
  "final_path": "Content/Art/Heroes/hero_mage_portrait.png",
  "final_sha256": "sha256:m4p4000000000000000000000000000000000000000000000000000000000001",
  "backup_path": null,
  "notes": "Dry-run copied placeholder bytes; atomic rename simulated."
}
```

**Phase verdict (batch):** `pass`.  
**Next:** **post-place guards**.

---

### 3.8 Step — Post-place guards (per asset)

**Actor:** harness guard runner (post-place class).  
**Fixture:** `.cuebert/traces/asset/example-2026-04-20T13-00-00Z/guards/post_place.json` — **six** rows (**2 × 3**), all **`pass`**.

**Phase verdict:** `pass`.  
**Next:** **lockfile update**.

---

### 3.9 Step — Lockfile update (harness-owned)

**Actor:** coordinator (not a named subagent).  
**Output:** `.cuebert-assets.lock.yaml` on **`APP_REPO`** — illustrative post-run snapshot committed as **`lockfile_after.yaml`** beside the trace for readers.

**Next:** **memory**.

---

### 3.10 Step — `milestone_commit`

**Actor:** memory-toolkit (harness invocation).  
**Sample output (`memory/envelope.json`):**

```json
{
  "schema_version": 1,
  "tool": "milestone_commit",
  "status": "ok",
  "memory_id": "mem_m4p4_asset_hello_level_20260420",
  "project_key": "hello-level",
  "milestone": "asset/2026-04-20-add-hero-portraits",
  "committed_at": "2026-04-20T13:12:08Z",
  "files_touched": "Content/Art/Heroes/hero_mage_portrait.png;Content/Art/Heroes/hero_rogue_portrait.png;Content/Art/Heroes/hero_warrior_portrait.png",
  "trace_dir": ".cuebert/traces/asset/example-2026-04-20T13-00-00Z/",
  "lockfile_path": "/abs/path/hello-level/.cuebert-assets.lock.yaml",
  "notes": "dry_run=true; lockfile rows appended for three hero portraits; no raw prompts stored."
}
```

**Phase verdict:** `pass`.  
**Next:** **coordinator rollup**.

---

### 3.11 Step — Coordinator envelope (trace root)

**Actor:** main-chat harness coordinator ([`agent-asset.md`](../agents/agent-asset.md) §5.2, §10).  
**Output:** `.cuebert/traces/asset/example-2026-04-20T13-00-00Z/envelope.json` — includes **`per_asset`** aligned with **`generate/`** and **`place/`** stems, **`lockfile_updated: true`**, **`memory_id`**, and a **`content_verification`** object that **simulates** post-copy checks under the Unreal **`Content/`** tree (no binary PNG bytes committed in the hub).

**Session outcome:** **`status: pass`** — suitable handoff to a follow-up **`/play`** preview when art should appear in-editor (**M5** bridge).

---

## 4. Envelopes (full reference shapes)

### 4.1 Plan envelope (already listed in §3.3)

See **`plan/envelope.json`** in the trace directory for the canonical on-disk bytes.

### 4.2 Generate envelopes (×3)

Files: `generate/hero_mage_portrait.json`, `generate/hero_rogue_portrait.json`, `generate/hero_warrior_portrait.json` — all **`dry_run: true`**, **`status: dry_run_synthetic`**, distinct **`prompt_id`** values prefixed **`dry_run_`**, seeds **1002 / 1003 / 1001**, digests **`...001 / ...002 / ...003`** respectively.

### 4.3 Place envelopes (×3)

Files: `place/hero_mage_portrait.json`, `place/hero_rogue_portrait.json`, `place/hero_warrior_portrait.json` — each **`status: placed`**, matching **`final_sha256`** to the generate envelope for the same **`id`**.

### 4.4 Coordinator top-level envelope

The canonical rollup is **`envelope.json`** at the trace root. It includes **`schema_version`**, **`asset_run_id`**, **`status: pass`**, **`dry_run: true`**, counts (**`generated_count`**, **`skipped_count`**, **`failed_count`**), **`per_asset`** (aligned with **`generate/`** and **`place/`** file stems), **`lockfile_updated`**, **`memory_id`**, **`phase_verdicts`**, a full **`artifacts`** map, **`content_verification`** (simulated **`Content/`** post-copy checks), and **`findings: []`** on the happy path—open the committed fixture rather than duplicating the full JSON here.

### 4.5 Memory commit envelope

See **`memory/envelope.json`** — shape in §3.10.

---

## 5. Failure variants (envelopes that change)

Each variant assumes the same scenario as §2 until the failure point.

---

### 5.A Manifest invalid YAML (`guard.manifest.valid`)

**Trigger:** A merge conflict left duplicate **`id:`** keys or a tab-indented YAML fragment that **PyYAML** rejects before schema validation.

**Harness path:** **PRE-PLAN** — first failing guard halts the chain; coordinator returns **`pre_plan_fail`**.

**`guards/pre_plan.json` (fragment):**

```json
{
  "schema_version": 1,
  "phase": "pre_plan",
  "verdict": "fail",
  "guards": {
    "pre_plan": [
      {
        "guard_id": "guard.project.exists",
        "class": "pre-plan",
        "severity": "pass",
        "message": "Project path ok."
      },
      {
        "guard_id": "guard.manifest.valid",
        "class": "pre-plan",
        "severity": "fail",
        "message": "asset_manifest_validate: YAML parse error at line 42.",
        "evidence": {
          "type": "manifest",
          "path": "/abs/path/hello-level/.cuebert-assets.yaml",
          "detail": "mapping values are not allowed here"
        }
      }
    ]
  }
}
```

**Coordinator rollup excerpt:**

```json
{
  "status": "fail",
  "abort_code": "pre_plan_fail",
  "failed_count": 0,
  "generated_count": 0,
  "findings": [
    {
      "guard_id": "guard.manifest.valid",
      "severity": "fail",
      "phase": "pre_plan",
      "message": "Fix manifest YAML before re-running /asset."
    }
  ]
}
```

**Operator next step:** repair **`.cuebert-assets.yaml`**, re-run **`asset_manifest_validate`**, then **`/asset`** again.

---

### 5.B Read-only destination (`guard.place.destination_writable`)

**Trigger:** The operator accidentally **`chmod a-w`** on **`Content/Art/Heroes/hero_mage_portrait.png`** while iterating; place attempts **mage** after **rogue** and **warrior** succeeded in a **continue-on-error** policy.

**Harness path:** **POST-PLACE** for **`hero_mage_portrait`** yields **`fail`**; harness **rolls back** that asset only (per [`agent-asset.md`](../agents/agent-asset.md) §13); others remain placed; lockfile omits the failed id or marks failure per **M4-P4** policy table.

**`guards/post_place.json` (fragment):**

```json
{
  "guard_id": "guard.place.destination_writable",
  "class": "post-place",
  "severity": "fail",
  "asset_id": "hero_mage_portrait",
  "message": "Destination not writable errno=EACCES.",
  "evidence": {
    "type": "file",
    "path": "Content/Art/Heroes/hero_mage_portrait.png",
    "detail": "chmod removed write bit"
  }
}
```

**Coordinator rollup excerpt:**

```json
{
  "status": "partial_pass",
  "failed_count": 1,
  "per_asset": [
    {"id": "hero_rogue_portrait", "status": "generated", "result_path": "Content/Art/Heroes/hero_rogue_portrait.png"},
    {"id": "hero_warrior_portrait", "status": "generated", "result_path": "Content/Art/Heroes/hero_warrior_portrait.png"},
    {"id": "hero_mage_portrait", "status": "failed_place", "result_path": null}
  ],
  "lockfile_updated": true
}
```

**Operator next step:** fix filesystem permissions; re-run **`/asset`** with **`--only hero_mage_portrait`** (or clear the read-only bit and **`force: true`** per policy).

---

### 5.C Live ComfyUI timeout mid-run (`agent-asset-generate`)

**Trigger:** Someone exports **`CUEBERT_COMFYUI_MODE=live`** mid-campaign; **`hero_rogue_portrait`** hits HTTP stall until **`generate_max_duration_s`** (**600** in [`.cuebert/config/asset-guards.yaml`](../../.cuebert/config/asset-guards.yaml)) elapses.

**Harness path:** **Generate** returns **`status: failed`**, **`error_code: timeout`** per [`agent-asset-generate.md`](../agents/agent-asset-generate.md) §7; post-generate **`guard.generate.exit_status`** **fails** for that id; default harness **continues** other assets unless **`--fail-fast`**.

**`generate/hero_rogue_portrait.json` (fragment):**

```json
{
  "id": "hero_rogue_portrait",
  "status": "failed",
  "trace_png_path": null,
  "duration_ms": 600000,
  "dry_run": false,
  "toolkit": {"prompt_id": null, "tool_status": "fail"},
  "error_code": "timeout",
  "notes": "Exceeded GENERATE_TIMEOUT_S ceiling."
}
```

**Coordinator rollup excerpt:**

```json
{
  "status": "warn",
  "failed_count": 1,
  "generated_count": 2,
  "per_asset": [
    {"id": "hero_rogue_portrait", "status": "failed_generate", "result_path": null}
  ]
}
```

**Operator next step:** restore **`dry_run`** for CI-safe iteration or raise timeout / fix server queue; re-run failed ids only.

---

## 6. What the user sees

The **main chat** transcript stays anchored on **`/asset`**: the coordinator prints a **short preamble** with **`PROJECT_KEY`**, resolved **`MANIFEST_PATH`**, and **`LOCKFILE_PATH`** or **`none`** echoing [`agent-asset-plan.md`](../agents/agent-asset-plan.md) §14 visibility rules. As each **gate class** finishes, the harness emits a **single-line rollup** per phase—**`pre_plan pass`**, **`post_plan pass (workflow_available info)`**, and so on—so operators scanning a long session can grep for **`fail`** without opening JSON first.

During **Generate**, progress shows **per-asset** lines (`[generate] hero_warrior_portrait dry_run_synthetic 14ms`) followed by the **paired guard probes** (`exit_status pass`, `file_size_sane pass`). **Place** mirrors that rhythm with **`placed`** and **`post_place`** pairs. The closing banner repeats **`trace_dir`**, whether **`lockfile_updated`**, and the **`memory_id`** from **`milestone_commit`**, ending with **`ASSET RUN PASS`** on the happy path.

If **`spec_only_as_info`** surfaces **`info`** rows (for example **missing workflow file**), the UI copy explains that the session **continued** because evaluators are **not yet strict**—matching the honest stub posture used in **M2** and **M3** sample runs.

---

## 7. Known drift / deferred items

- **`flux_portrait_v1.json`** does **not** ship under **`.cursor/skills/comfyui-toolkit/workflows/`** today (**M4-P1** empty directory). This sample’s **`guard.plan.workflow_available`** row is **`info`**, not a hard **`fail`**, until **`spec_only_as_info`** is flipped with real graphs on disk (**M5** authoring).  
- **Backup / rollback directory** naming collisions and **`fsync`** policy details are specified in [`agent-asset-place.md`](../agents/agent-asset-place.md) but **deferred** to live **M5** filesystem adapters.  
- **`x_comfyui_version_pin`** is echoed in **`lockfile_after.yaml`** as a lenient **`>=0.3.0`** illustrative pin—stricter pinning lands with production ComfyUI fleet management.  
- **Vision QA** and **automatic `.uasset`** import are **out of scope** for M4—see [`agent-asset.md`](../agents/agent-asset.md) §11.

---

## 8. Trace artifacts on disk (ASCII tree)

Committed example (JSON + YAML + Markdown only; **no** binary PNG in hub):

```text
example-2026-04-20T13-00-00Z/
├── README.md
├── envelope.json
├── lockfile_after.yaml
├── guards/
│   ├── pre_plan.json
│   ├── post_plan.json
│   ├── post_generate.json
│   └── post_place.json
├── plan/
│   └── envelope.json
├── generate/
│   ├── hero_mage_portrait.json
│   ├── hero_rogue_portrait.json
│   └── hero_warrior_portrait.json
├── place/
│   ├── hero_mage_portrait.json
│   ├── hero_rogue_portrait.json
│   └── hero_warrior_portrait.json
└── memory/
    └── envelope.json
```

Hub path prefix: `.cuebert/traces/asset/`. Matches [`control-plane-paths.md`](../standards/control-plane-paths.md) hub trace conventions.

---

## 9. How to use this example

- **Harness authors** should treat the **JSON** in **`guards/`**, **`plan/`**, **`generate/`**, **`place/`**, and **`memory/`** as **fixture contracts** when implementing **M4-P4+** parsers.  
- **Humans authoring plans** should start from [`asset-plan-template.md`](../../projects/_templates/asset-plan-template.md) and cross-check **guard expectations** against §3 and §5 here.  
- **When M5 lands**, promote this scenario to a **smoke `/asset`** against a real **`hello-level`** checkout: same manifest rows, **`dry_run: false`**, real **`comfyui_generate_asset`** HTTP, real **`Content/`** bytes.

---

## 10. Footer

**Status:** worked example, **M4-P4**. **Real run:** pending live ComfyUI setup + **M5** Unreal bridge integration. **Reference trace:** `.cuebert/traces/asset/example-2026-04-20T13-00-00Z/`.
