# `/asset` Asset Pipeline Guards — Contract & Configuration

> **SYSTEM ROLE:** Authoritative specification for **Asset Pipeline Guards** that gate the **`/asset`** harness from **Pre-plan** through **Post-place**, and for the **evidence contract** consumed by coordinator envelopes, per-asset results, and memory hooks.  
> **Scope:** Contract, taxonomy, severity semantics, configuration schema, evidence and envelope shape, evaluation ordering, and relationship to **`comfyui-toolkit`** outputs. **No executable evaluator** is defined here — evaluators land in **M5–M6** (path validation, workflow resolution, ComfyUI exit semantics, lockfile atomicity).

---

## 0. Purpose & scope

**Asset Pipeline Guards** are **deterministic gates** that answer: “Is it safe and coherent to run **manifest-driven ComfyUI generation** and **write rasters into the game repository** right now?” They protect operators from **wasted GPU time**, **path mistakes**, **empty plans**, and **silent lockfile drift** while **`/asset`** remains **file-producing** and **pre-distribution**.

Guards are **not** a substitute for **human art direction**, **legal clearance** of training data, or **full image QA** (vision models are **M6**). They are **not** **`/play` Preview Guards** (editor reachability) or **`/ship` Ship Guards** (cook/cert/package). They are **not** the **`asset_manifest_validate`** tool itself — that validator is a **separate MCP entrypoint** whose findings **inform** **`guard.manifest.valid`** once wired.

This document owns the **guard ids**, **four gate classes**, **severity ladder**, **YAML configuration**, and **envelope contract** so later milestones plug **evaluators** into stable APIs without renaming concepts.

**M4-P3 posture:** All guards are **`spec only (M4-P3)`** — **no blocking `fail`** in production harnesses until evaluators ship **and** operators set **`global.spec_only_as_info: false`** with care.

---

## 1. Guard taxonomy

Guards fall into **four classes** by **when** they run relative to **Plan**, **Generate**, and **Place**. The harness runs them in a **fixed order** within each class (see **6. Decision tree**).

### 1.1 Pre-plan guards

Run **before** the harness mutates **trace directories** or invokes **`agent-asset-plan`** with side effects (future side-effect definition **M4-P4**). Typical checks:

- **`PROJECT_KEY`** resolves to a **`projects.<key>`** entry with usable **`path`** (**`guard.project.exists`**).
- The resolved **asset manifest** parses and satisfies **`asset-manifest`** schema + semantic rules (**`guard.manifest.valid`**).

**Intent:** Fail fast on **misregistration** or **invalid manifest** before any ComfyUI queue time.

### 1.2 Post-plan guards

Run **after** **`agent-asset-plan`** returns **`status: pass`**. Typical checks:

- The plan contains **at least one** actionable row for the session (**`guard.plan.non_empty`**).
- Every planned **generate** row names a **workflow** that resolves to an **allow-listed** graph on disk for the hub (**`guard.plan.workflow_available`**).

**Intent:** Avoid dispatching **`comfyui_generate_asset`** when the plan is empty or workflows are missing.

### 1.3 Post-generate guards

Run **after** each asset’s **`comfyui_generate_asset`** completes (or dry-run synthetic completes). Typical checks:

- Toolkit / wrapper **exit-shaped status** is success for that asset (**`guard.generate.exit_status`**).
- Output file size is within **sane** bounds to catch **0-byte** or **runaway** writes (**`guard.generate.file_size_sane`** — **`warn→fail`** posture configurable).

**Intent:** Catch **obviously broken** generations before copying bytes into **`Content/`**.

### 1.4 Post-place guards

Run **after** **`agent-asset-place`** completes for an asset. Typical checks:

- Final **`destination`** is **writable** and **inside** allowed project roots (**`guard.place.destination_writable`**).
- **Lockfile** contains the new row for that **`id`** with matching **`result_sha256`** (**`guard.place.lockfile_updated`**).

**Intent:** Ensure **on-disk truth** matches **declared intent** for the next **`skip_unchanged`** cycle.

### 1.5 Disambiguation vs other guard systems

| Concern | Asset Pipeline Guards (this doc) | `/play` Preview Guards | `/ship` Ship Guards |
|--------|-----------------------------------|------------------------|---------------------|
| **Role** | Gate **manifest → ComfyUI → Content/** | Gate **author → preview** | Gate **cook → package** |
| **Primary risk** | Bad paths, missing workflows, empty plans, bad rasters | Editor / compile waste | Distribution mistakes |
| **Artifact roots** | Hub **`traces/asset/`** + **`APP_REPO` Content/** | Hub **`traces/play/`** | Hub **`traces/ship/`** |
| **Overlap** | None normative — share **finding JSON shape** for tooling reuse |  |  |

---

## 2. Full catalog of eight guards

Each guard has a **stable `id`** (lowercase, dot-separated). **`class`** is one of: **`pre-plan`**, **`post-plan`**, **`post-generate`**, **`post-place`**. **`severity`** is the **default** effective severity when the guard is **fully implemented**. **`evidence type`** names the **primary** attachment kind for findings. **`implementation status`** is **`spec only (M4-P3)`** for **all rows** here; **M5–M6** own evaluators.

Harness callers **MUST** treat **`spec only (M4-P3)`** guards as **non-blocking `info`** until evaluators ship, **unless** a project manifest promotes severity (discouraged before evaluators exist). The global flag **`spec_only_as_info`** (see **`.cuebert/config/asset-guards.yaml` → `global`**) defaults to **`true`** so unfinished evaluators never accidentally **block** **`/asset`**.

| `id` | `class` | `severity` | Description | Evidence type | Implementation status |
|------|---------|------------|-------------|----------------|-------------------------|
| `guard.project.exists` | pre-plan | fail | **`PROJECT_KEY`** resolves under **`.cuebert/workspace-manifest.json` → `projects`**, **`path`** present, directory exists. | manifest | **spec only (M4-P3)**; impl **M5-P1** harness |
| `guard.manifest.valid` | pre-plan | fail | Resolved manifest YAML matches **`asset-manifest`** schema + semantic rules (duplicate ids, illegal destinations, effective workflow presence). | manifest | **spec only (M4-P3)**; impl **M5-P1** (reuse **`asset_manifest_validate`**) |
| `guard.plan.non_empty` | post-plan | fail | Plan envelope lists **≥1** asset with action **`generate`**, **`regenerate`**, or **`place_only`** when session is not an explicit **no-op** dry documentation run (**M4-P4** clarifies no-op). | json | **spec only (M4-P3)**; impl **M4-P4** |
| `guard.plan.workflow_available` | post-plan | fail | For every planned **generate** row, workflow basename resolves to **`workflows/*.json`** on hub per **`comfyui_list_workflows`** allow-list. | file | **spec only (M4-P3)**; impl **M5-P1** |
| `guard.generate.exit_status` | post-generate | fail | **`comfyui_generate_asset`** envelope reports **`status`** in the **success family** for that asset (exact enum per **`comfyui-toolkit`** `reference.md`). | json | **spec only (M4-P3)**; impl **M5-P1** |
| `guard.generate.file_size_sane` | post-generate | warn | Raster byte length **`warn_bytes_min ≤ size ≤ warn_bytes_max`** from YAML **`threshold`**; crossing upper bound may escalate **`fail`** when **`spec_only_as_info`** is false and evaluator supports it (**M6**). | file | **spec only (M4-P3)**; impl **M5–M6** |
| `guard.place.destination_writable` | post-place | fail | Destination directory exists or is creatable safely under **`APP_REPO`**; no **`..`** escape; final path under allowed engine root prefixes. | file | **spec only (M4-P3)**; impl **M5-P1** |
| `guard.place.lockfile_updated` | post-place | fail | **`.cuebert-assets.lock.yaml`** contains updated row for **`id`** with **`result_sha256`** matching placed bytes. | manifest | **spec only (M4-P3)**; impl **M4-P4** |

**Count:** **8** stable guard ids — **API surface** frozen for **M4-P3** config and **M5+** harness wiring.

### 2.1 Relationship to `asset_manifest_validate`

The MCP tool **`asset_manifest_validate`** (see **`asset-manifest.md` section 6**) is the **logical evaluator backend** for **`guard.manifest.valid`**. Until wired, the guard emits **`info`** findings referencing the **future** attachment path only — never a silent pass without narrative when harness is in **`audit`** mode (**M4-P4**).

### 2.2 Relationship to `comfyui_generate_asset`

**`guard.generate.exit_status`** and **`guard.generate.file_size_sane`** consume **`comfyui_generate_asset`** JSON envelopes and on-disk bytes under **`.cuebert/traces/asset/<timestamp>/generated/`** (or toolkit-default subtree — exact normative merge **M4-P4**).

### 2.3 Ordering within each class

**Pre-plan:** `guard.project.exists` **then** `guard.manifest.valid`.  
**Post-plan:** `guard.plan.non_empty` **then** `guard.plan.workflow_available`.  
**Post-generate:** `guard.generate.exit_status` **then** `guard.generate.file_size_sane` **per asset**.  
**Post-place:** `guard.place.destination_writable` **then** `guard.place.lockfile_updated` **per asset**.

Stable ordering matters for **deterministic CI transcripts** even before evaluators exist.

### 2.4 Per-guard evaluation sources (normative detail)

Each row names the **primary inputs** evaluators MUST consult when implementations land. Until then, these bullets define the **intended data plane** for harness authors.

#### `guard.project.exists`

- **Primary:** **`.cuebert/workspace-manifest.json`** — parse JSON, locate **`projects.<PROJECT_KEY>`**, read **`path`**.  
- **Secondary:** Filesystem **`stat`** on resolved **`APP_REPO`**.  
- **Failure examples:** missing key, **`path`** not a directory, symlink loop (platform-specific handling **M5**).  
- **Evidence:** absolute **`APP_REPO`**, manifest file path, excerpt of matching JSON object keys only (redact unrelated projects).

#### `guard.manifest.valid`

- **Primary:** resolved manifest bytes + **`asset_manifest_validate`** MCP envelope when tool is available.  
- **Secondary:** local **`jsonschema`** validation path when MCP is not in-process (**M4-P4**).  
- **Failure examples:** duplicate **`assets[].id`**, illegal **`destination`**, missing effective **`workflow`**.  
- **Evidence:** absolute **`manifest_path`**, validator **`findings`** array reference (not full prompt text in logs by default).

#### `guard.plan.non_empty`

- **Primary:** **`agent-asset-plan`** output envelope **`plan[]`**.  
- **Secondary:** CLI **`--only`** filter intersection — empty intersection after filters is a **planning error**, not a silent success.  
- **Failure examples:** all rows **`skip_unchanged`** when operator expected regeneration but forgot **`--force`**.  
- **Evidence:** **`to_generate`**, **`to_skip`** counts, first **10** planned ids for transcript size cap.

#### `guard.plan.workflow_available`

- **Primary:** hub **`comfyui_list_workflows`** scan results (or filesystem glob over **`workflows/*.json`** under **`comfyui-toolkit`** with identical sorting rules).  
- **Secondary:** manifest **`defaults.workflow`** merge per asset row.  
- **Failure examples:** typo **`icon_falt`** vs allow-listed **`icon_flat`**.  
- **Evidence:** missing stem list, suggested closest names (optional **M6** fuzzy helper — not normative in M4-P3).

#### `guard.generate.exit_status`

- **Primary:** MCP return payload from **`comfyui_generate_asset`**.  
- **Secondary:** sidecar **`envelope.json`** adjacent to generated raster when toolkit writes one.  
- **Failure examples:** **`dry_run`** boolean true when operator expected **`live`** — should surface as **`warn`** finding class **`mode_mismatch`**, not a fake pass (**M4-P4** policy).  
- **Evidence:** **`prompt_id`**, **`error_code`**, tail of toolkit log path.

#### `guard.generate.file_size_sane`

- **Primary:** byte **`stat.st_size`** on output raster in trace dir.  
- **Secondary:** PNG signature sniff **optional** (**M6**) — magic bytes **`89 50 4E 47`** for **`.png`**.  
- **Failure examples:** **0** bytes, **>50MiB** accidental raw dump.  
- **Evidence:** **`warn_bytes_min`**, **`warn_bytes_max`**, actual size, path.

#### `guard.place.destination_writable`

- **Primary:** normalized destination under **`APP_REPO`**, directory **`W_OK`** probe, engine root allow-list (`Content/`, `Assets/`, `res/` prefixes **M5** table).  
- **Secondary:** read-only mount detection (**M6**).  
- **Failure examples:** destination under **`Engine/`** vendor tree when disallowed.  
- **Evidence:** normalized path, **`APP_REPO`** root, errno / platform message.

#### `guard.place.lockfile_updated`

- **Primary:** parsed **`.cuebert-assets.lock.yaml`** after place phase.  
- **Secondary:** recomputed **`sha256`** over final **`Content/`** bytes.  
- **Failure examples:** lockfile write succeeded but row **`id`** mismatch; hash mismatch vs disk.  
- **Evidence:** lockfile path, row excerpt, expected vs actual digest.

---

## 3. Severity semantics

### 3.1 `fail`

- **Effect:** **Hard stop** for the current **gate point** per **`agent-asset.md` section 7**.  
- **Pre-plan / post-plan:** Coordinator **does not** dispatch **`agent-asset-generate`**.  
- **Post-generate / post-place:** Per-asset failure; default harness continues other assets unless **`--fail-fast`**.

When **`spec_only_as_info`** is **`true`**, **spec-only** evaluators **do not** produce effective **`fail`** — they downgrade to **`info`** (see **3.4**).

### 3.2 `warn`

- **Effect:** **Continue** the chain; finding MUST appear in the guard envelope.  
- **`guard.generate.file_size_sane`** is **`warn`**-first for suspicious sizes; future **`warn→fail`** escalation is **M6**-optional.

### 3.3 `info`

- **Effect:** **Audit-only** — does not block. Used for **skipped** guards, **dry-run** explanations, and **spec-only** placeholders.

### 3.4 `spec_only_as_info` default

Until an evaluator ships, the guard’s **contract** (id, class, evidence shape) is **stable**, but the harness **MUST NOT** treat unimplemented checks as failing **`fail`** accidentally. **Default:** when **`global.spec_only_as_info`** is **`true`**, unimplemented guards contribute **`severity: info`** findings (or explicit **skip/info** messages) per harness policy — **never** a silent **`pass`** with missing evidence for policy-critical claims.

Operators may set the flag to **`false`** only when **all** enabled guards in the session have **real evaluators** (typical **post-M6** hub posture).

### 3.5 Effective severity algorithm (normative sketch)

```text
configured_severity = yaml.guards[id].default_severity
if not guard.enabled:
    emit skipped info; return
if implementation_status is spec_only and global.spec_only_as_info:
    effective = info
else:
    effective = merge(plan.guards_override, manifest.assetGuards.overrides) # M5
emit finding with effective severity
```

---

## 4. Config file schema

### 4.1 Location & version

- **Path (hub):** **`.cuebert/config/asset-guards.yaml`**  
- **Version:** Top-level **`version: 1`** (**integer**). Tooling **MUST** reject unknown versions with a **loud, actionable error**. Additive keys within a version are allowed; **breaking** layout changes bump the integer.

### 4.2 Top-level shape (normative fields)

```yaml
version: 1
guards:
  <guard_id>:
    enabled: <bool>
    default_severity: fail | warn | info
    threshold: <object | null>   # optional; guard-specific
global:
  generate_max_duration_s: <int>
  total_max_duration_s: <int>
  spec_only_as_info: <bool>
```

- **`guards`:** Map keyed by **exact** guard **`id`**.  
- **`enabled`:** When **`false`**, the harness **skips** the guard (emits **`info`** “skipped” finding at harness discretion).  
- **`default_severity`:** Hub default **before** overrides.  
- **`threshold`:** Optional per-guard parameters; **must** be documented per guard in YAML comments and in section 2.

### 4.3 Global timing budgets

| Key | Meaning |
|-----|---------|
| **`generate_max_duration_s`** | Wall-clock cap for **one** **`comfyui_generate_asset`** invocation including poll loop. |
| **`total_max_duration_s`** | Wall-clock cap for **entire** `/asset` session from pre-plan through lockfile write. |

**Harness behavior on expiry:** mark asset **`failed_generate`** with **`error_code: timeout`**; continue or **`--fail-fast`** halt per **`agent-asset.md` section 7**.

### 4.4 Project overrides (future)

Projects **MAY** override per-guard effective severity in **`.cuebert/workspace-manifest.json`** under a future **`assetGuards.overrides`** map — **schema lands M5**; pattern mirrors **`play-preview-guards.md` section 4.3** and **`ship-guards.md`** override ideas.

### 4.5 Plan-level overrides

**`guards_override`** in the **asset plan** MUST be a **structural subset** of the **`asset-guards.yaml`** per-guard keys (**`enabled`**, **`default_severity`**, optional **`threshold`**). Merge rules (**last wins** vs **hub-first**) — **M4-P4**.

---

## 5. Evidence contract

### 5.1 Finding shape (JSON)

Each evaluator emits a **finding object**:

```json
{
  "guard_id": "guard.manifest.valid",
  "status": "pass",
  "severity": "info",
  "evidence": {
    "manifest_path": "/abs/path/.cuebert-assets.yaml",
    "validator_status": "pass"
  },
  "timestamp": "2026-04-20T12:00:00Z"
}
```

**Rules:**

- **`guard_id`:** MUST equal a catalog **`id`** from section 2.  
- **`status`:** **`pass` \| `warn` \| `fail` \| `skipped` \| `not_applicable`**.  
- **`severity`:** Effective severity after **`spec_only_as_info`** mapping.  
- **`evidence`:** Non-empty object for any **`fail`** or **`warn`**; **`info`** may cite lightweight pointers.

### 5.2 Empty-evidence policy

Mirror **`play-preview-guards.md`** / **`ship-guards.md`**: any claimed **`fail`** or **`warn`** without **non-vacuous evidence** invalidates the guard report — the harness MUST treat that as coordinator **`status: fail`** with a **`guard_report_malformed`** code (**M4-P4** wire-up).

### 5.3 Trace file layout (recommended)

| Path | Contents |
|------|----------|
| **`.cuebert/traces/asset/<timestamp>/guards/pre_plan.json`** | Findings list |
| **`.../guards/post_plan.json`** | Findings list |
| **`.../guards/post_generate/<asset_id>.json`** | Findings list |
| **`.../guards/post_place/<asset_id>.json`** | Findings list |

Exact filenames are **non-normative** until **M4-P4** chooses a single schema; **directory roots** are normative.

---

## 6. Decision tree

Pseudo-flow (compare **`ship-guards.md` section 7** and **`agent-asset.md` section 7**):

```text
1. PRE-PLAN GUARDS
   a. Load .cuebert/config/asset-guards.yaml + merge overrides (future).
   b. Run enabled pre-plan guards in stable order (section 2.3).
   c. If any effective severity == fail -> HALT (pre_plan_fail).
   d. Else continue.

2. PLAN (agent-asset-plan)
   a. If plan envelope.status != pass -> HALT.

3. POST-PLAN GUARDS
   a. If any effective fail -> HALT.

4. FOR EACH ASSET (generate path)
   a. Run comfyui_generate_asset when required.
   b. POST-GENERATE GUARDS
      - If effective fail -> mark asset failed; continue or --fail-fast HALT.

5. FOR EACH ASSET (place path)
   a. Run agent-asset-place.
   b. POST-PLACE GUARDS
      - If effective fail -> rollback per `agent-asset.md` section 13; mark failed.

6. LOCKFILE + MEMORY
   a. Coordinator writes lockfile + calls milestone_commit on success.
```

**Coordinator responsibility:** Roll up per-asset findings into **session-level** `guards.json` for memory + operator readability.

---

## 7. Non-goals

- **Not** multimodal **vision QA** of artistic quality — **M6**.  
- **Not** **`uasset`** import validation — **M5** Unreal bridge.  
- **Not** licensing / rights scanning of training corpora — legal process outside cuebert.  
- **Not** a replacement for **`asset_manifest_validate`** as a standalone operator tool — guards **wrap** validation in harness **gates** once evaluators exist.  
- **Not** GPU scheduling / farm fairness — environment concern.
- **Not** perforce / plastic / SVN lock orchestration — VCS remains operator-owned; guards may **warn** on read-only sandboxes (**M6**).  
- **Not** network egress policy beyond **ComfyUI base URL** — corporate proxies are site ops (**M5** runbooks).  
- **Not** automatic **`git add`** of new rasters — harness writes bytes; developers choose version control steps.  
- **Not** promotion to CDN or marketing DAM — **`/ship`** and publishing agents own distribution surfaces.

---

## 8. Cross-references

| Document / path | Relationship |
|-----------------|--------------|
| `docs/_ai_system/agents/agent-asset.md` | Parent coordinator — phase ordering, rollback, memory |
| `.cuebert/config/asset-guards.yaml` | Default hub config |
| `docs/_ai_system/standards/asset-manifest.md` | Manifest schema + validator tool |
| `.cursor/skills/comfyui-toolkit/SKILL.md` | MCP tools + dry-run semantics |
| `docs/_ai_system/standards/play-preview-guards.md` | Severity + evidence pattern reference |
| `docs/_ai_system/standards/ship-guards.md` | Multi-gate YAML + decision-tree reference |
| `docs/_ai_system/standards/control-plane-paths.md` | Trace roots + hub vs app paths |
| `docs/_ai_system/agents/agent-asset-plan.md` | Plan subagent consumer of section 1.2 |
| `docs/_ai_system/agents/agent-asset-generate.md` | Generate subagent consumer of section 1.3 |
| `docs/_ai_system/agents/agent-asset-place.md` | Place subagent consumer of section 1.4 |

---

## 9. Worked examples (illustrative findings)

These JSON fragments are **documentation shapes** for humans and future CI golden files — not live telemetry.

### 9.1 Pre-plan failure (`guard.manifest.valid`)

```json
{
  "guard_id": "guard.manifest.valid",
  "status": "fail",
  "severity": "info",
  "evidence": {
    "manifest_path": "/Users/me/Hello/.cuebert-assets.yaml",
    "code": "asset.duplicate_id",
    "duplicate_id": "hero_idle"
  },
  "timestamp": "2026-04-20T12:00:05Z"
}
```

### 9.2 Post-generate warn (`guard.generate.file_size_sane`)

```json
{
  "guard_id": "guard.generate.file_size_sane",
  "status": "warn",
  "severity": "warn",
  "evidence": {
    "path": ".cuebert/traces/asset/2026-04-20T12-00-00Z/generated/hero_portrait_1.png",
    "bytes": 512,
    "warn_bytes_min": 1024
  },
  "timestamp": "2026-04-20T12:03:10Z"
}
```

### 9.3 Post-place pass (`guard.place.lockfile_updated`)

```json
{
  "guard_id": "guard.place.lockfile_updated",
  "status": "pass",
  "severity": "info",
  "evidence": {
    "lockfile": "/Users/me/Hello/.cuebert-assets.lock.yaml",
    "id": "hero_idle",
    "result_sha256": "sha256:789..."
  },
  "timestamp": "2026-04-20T12:04:02Z"
}
```

---

## 10. Footer

**Status:** **M4-P3** — contract + catalog + YAML + evidence shapes only. **Evaluator implementations:** **M5–M6**. **Harness wiring + example trace:** **M4-P4**.
