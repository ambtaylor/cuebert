# Asset manifest — schema & integration

> **SYSTEM ROLE:** Authoritative specification for the **per-project asset manifest** that declares which **2D raster assets** the M4 pipeline (ComfyUI via `comfyui-toolkit` + future asset agent **M4-P3**) should generate, **how** they are produced (workflow, prompts, seeds, parameters), and **where** outputs land inside the **game project** source tree (for example Unreal `Content/`).  
> **Scope:** YAML contract, JSON Schema validation, workspace-manifest wiring, reproducibility expectations, validation severities, and evolution rules. **Not** engine-native asset databases, 3D, audio, animation, or commerce.

---

## 0. Purpose & scope

The **asset manifest** is the declarative bridge between **Cuebert’s `/play` loop**
(and the broader gaming control plane) and a **registered game project’s**
`Content/` tree (or Unity `Assets/`, Godot `res://` equivalents). It answers, in
machine-readable form:

- **Which** generated stills exist as first-class pipeline outputs (not
  hand-painted source art registered elsewhere).
- **Which ComfyUI workflow graph** (allow-listed JSON on the hub) produces each
  still.
- **What textual and numeric inputs** (prompt, negative prompt, seed,
  sampler-related params) define a reproducible generation intent.
- **Where** each PNG (or future HDR **EXR**) should be written **relative to
  the application repository root** so engine packaging and source control
  policies apply normally.

Manifest files are **per application repository**, not per hub-only meta tree.
They are discovered through **`.cuebert/workspace-manifest.json`** on the
Cuebert hub: each `projects.<key>` entry MAY name an explicit
`assetManifestPath` (project-relative). When that field is absent, tooling
falls back to the convention **`<project-root>/.cuebert-assets.yaml`** if the
file exists. The manifest **never** lives exclusively inside the cuebert hub
repository for a real game title; the hub only **points** at it.

**Canonical convention:** `<project-root>/.cuebert-assets.yaml`  
**Canonical schema:** `.cuebert/schemas/asset-manifest.schema.json`  
**Human template:** `docs/projects/_templates/asset-manifest-template.yaml`

---

## 1. Design goals

| Goal | Meaning |
|------|---------|
| **Reproducible** | Given the same manifest row, frozen workflow JSON on disk, pinned ComfyUI minor line, explicit **seed**, and merged **params**, operators should expect **bit-identical PNG bytes** modulo the explicit non-determinism list in §5. |
| **Opinionated** | One workflow + one effective prompt + optional seed + merged params **equals one asset row**. Batching is modeled as **multiple rows**, never as hidden batch arrays inside a row. |
| **Human-editable** | YAML is the primary authoring surface; JSON is validation-only. |
| **Machine-validated** | A **draft-07 JSON Schema** ships in `.cuebert/schemas/` and is enforced by the `asset_manifest_validate` MCP tool (this milestone). |
| **Stackable** | Projects MAY attach arbitrary gameplay metadata under **`x_*`** keys at the top level, under `defaults`, or under each asset without breaking schema validation (values are opaque to core Cuebert). |

---

## 2. Top-level schema (normative YAML shape)

```yaml
version: 1
project: <project-key>              # must match key in workspace-manifest.json
engine: unreal | unity | godot
defaults:
  workflow: <workflow-name>         # falls back if asset omits workflow
  params: { ... }                   # base params merged into each asset
  destination_root: Content/Art/    # project-relative (trailing slash)
assets:
  - id: <stable-string-id>          # unique within this manifest
    workflow: <workflow-name>       # overrides default
    prompt: >
      Multi-line prompt text.
    negative_prompt: >              # optional
      ...
    seed: 123456                    # optional, but reproducible if set
    params:                         # overrides default params
      sampler: euler
      steps: 20
      cfg_scale: 7.5
      width: 1024
      height: 1024
    destination: Content/Art/Heroes/hero_idle.png   # project-relative
    tags: [character, hero]         # optional
    references:                     # optional
      - path: Content/Refs/hero_concept.png
        role: pose
      - path: Content/Refs/mood_board.png
        role: style
    x_gameplay: { ... }             # opaque project-defined extension
```

**Normative rules embedded in the shape above:**

- `assets` MUST contain **at least one** entry.
- Every asset MUST include **`id`**, **`prompt`**, and **`destination`**.
- Either **`defaults.workflow`** or each asset’s **`workflow`** MUST yield a
  non-empty **effective workflow name** after merge (see §3); the JSON Schema
  intentionally does **not** encode that cross-field constraint — the MCP
  validator enforces it as **`manifest.workflow_missing`** (`fail`).
- `destination` MUST end with **`.png`** today; **`.exr`** is reserved for HDR
  stills in **M5+** once the pipeline supports linear HDR hand-off.

---

## 3. Field reference

### 3.1 Top-level fields

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `version` | integer | **yes** | none | Format version. **Only `1`** is valid for this schema generation. Future integers are **breaking**. |
| `project` | string | **yes** | none | Logical project key; **MUST** match the registering key under `.cuebert/workspace-manifest.json` → `projects`. |
| `engine` | enum string | **yes** | none | One of **`unreal`**, **`unity`**, **`godot`**. Drives path idioms in documentation and future engine adapters. |
| `defaults` | map | no | none | Baseline **`workflow`**, **`params`**, and **`destination_root`** applied when per-asset fields omit them. |
| `assets` | sequence of maps | **yes** | none | Non-empty ordered list of declared outputs. |
| `x_*` | any | no | none | **Extension namespace** — ignored semantically by core validation except an **`info`** finding noting presence (see §6). |

### 3.2 `defaults` map

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `workflow` | string | no | none | Basename of an allow-listed workflow JSON file (`*.json` stem) living under `comfyui-toolkit/workflows/` on the hub **unless** a future milestone introduces an alternate workflows directory declaration. |
| `params` | map | no | none | Shallow parameter bag merged under each asset’s `params` (asset wins on key collision). Values SHOULD be JSON-serializable scalars or shallow maps as ComfyUI node `inputs` expect. |
| `destination_root` | string | no | none | Project-relative directory prefix, **trailing slash recommended** (for example `Content/Art/`). Used for **advisory** containment checks: destinations outside this prefix emit **`path.outside_destination_root`** (`warn`) when set. |
| `x_*` | any | no | none | Opaque defaults-level extensions. |

### 3.3 Per-asset fields (`assets[]`)

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `id` | string | **yes** | none | Stable identifier, **`^[a-z0-9_-]{1,64}$`**, **unique** within the manifest file. |
| `workflow` | string | no | `defaults.workflow` | Overrides default workflow basename when present and non-empty. |
| `prompt` | string | **yes** | none | Primary positive prompt. **Non-empty**; **maximum 4096 characters** after YAML load (matches `comfyui-toolkit` sanitization cap). |
| `negative_prompt` | string | no | none | Optional negative / unconditioning text; same **4096** character bound as `prompt`. |
| `seed` | integer | no | none | RNG seed for samplers that honor it. **When omitted**, regeneration is explicitly **non-deterministic** across runs even if all else is fixed (see §5). |
| `params` | map | no | none | Overrides merged over `defaults.params`. |
| `destination` | string | **yes** | none | **Project-relative** path ending in **`.png`** or **`.exr`**. MUST **not** be absolute. MUST **not** contain `..` path segments. SHOULD stay under `defaults.destination_root` when that field is set. |
| `tags` | sequence of strings | no | none | **Flat** labels for reporting and future filters — **no nested structures** inside `tags`. |
| `references` | sequence of maps | no | none | Optional stills used as human or model references; each item has **`path`** (project-relative, no `..`) and **`role`** (free-form short string, e.g. `pose`, `style`). |
| `x_*` | any | no | none | Opaque per-asset gameplay or tooling extensions. |

### 3.4 Validation rules (summary)

| Rule | Severity | Code (representative) |
|------|----------|------------------------|
| Missing required YAML keys / JSON Schema violation | `fail` | `schema.*` / `schema.validation_error` |
| Duplicate `assets[].id` | `fail` | `asset.duplicate_id` |
| `destination` absolute or contains `..` | `fail` | `security.absolute_destination` / `security.path_traversal_destination` |
| No effective workflow (`defaults.workflow` + per-asset merge empty) | `fail` | `manifest.workflow_missing` |
| `seed` omitted for an asset | `warn` | `reproducibility.seed_omitted` |
| Effective workflow stem not found in local `workflows/*.json` scan | `warn` | `workflow.not_found_local` |
| `destination` outside `defaults.destination_root` prefix | `warn` | `path.outside_destination_root` |
| Any `x_*` key present (tracked only) | `info` | `extension.x_keys_present` |

---

## 4. Integration with `workspace-manifest.json`

### 4.1 `projects.<key>.assetManifestPath`

The hub file **`.cuebert/workspace-manifest.json`** carries authoritative **disk**
and **logical** registration for each game title. In addition to existing fields
documented in `docs/_ai_system/agents/agent-ops-onboard.md` (for example `path`,
`engine`, `language`), each project entry MAY include:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `assetManifestPath` | string | **no** | Project-relative path from the **application repository root** to this YAML manifest (for example `cuebert-assets.yaml` or `Config/cuebert-assets.yaml`). |

### 4.2 Resolution order (normative)

When the M4 toolchain resolves which manifest to load for `project_key`:

1. **Explicit tool argument** `manifest_path` (if provided to
   `asset_manifest_validate` or future asset agent calls) after **path
   normalization** — MUST resolve under the **registered project root** **or**
   the **Cuebert hub root** (defense-in-depth against arbitrary reads).
2. Else **`projects.<key>.assetManifestPath`** from the workspace manifest (hub
   JSON), interpreted as **relative to the application repository root** named
   by `projects.<key>.path`.
3. Else the **convention fallback** **`<project-root>/.cuebert-assets.yaml`**.
4. If **no file exists** at the resolved location → consumers treat the project
   as **`not_configured`** for asset-manifest-driven operations: status
   **`not_configured`**, no fatal error for the overall hub, and **M4 asset
   operations skip** that project until a manifest appears.

### 4.3 Onboarding expectations (M1 / agent-ops)

The gaming profile template at **`docs/projects/_templates/gaming-profile.md`**
does **not** gain a new mandatory section in **M4-P2**. Instead, **onboarding
protocols** (`docs/_ai_system/agents/agent-ops-onboard.md`, future **M1-P8**
hardening) **SHOULD** prompt the operator for an **`assetManifestPath`** (or
confirm the `.cuebert-assets.yaml` convention) whenever **ComfyUI-driven asset
generation** is in scope for the title. This keeps hub `profile.md` readable
while still surfacing the decision at registration time.

### 4.4 Relationship to control-plane paths

See **`docs/_ai_system/standards/control-plane-paths.md`** for the invariant that
Cuebert **does not** silently scaffold mandatory trees inside app repos. The
asset manifest is **opt-in** content owned by the game team; the hub only
**references** it through `workspace-manifest.json`.

---

## 5. Reproducibility contract

### 5.1 Promise

When **all** of the following are held constant:

- This manifest row (prompts, merged params, declared workflow name),
- The **frozen workflow graph JSON** bytes on disk for that name,
- A **fixed ComfyUI minor version** line on the executing workstation or farm
  slot,
- A **fixed explicit `seed`** value on that row,
- And a **fixed GPU model + driver major line** as observed in practice,

…then regeneration SHOULD yield **bit-identical PNG bytes** for that row within
the same ComfyUI **minor** version family. This is a **best-effort engineering
promise**, not a mathematical guarantee across all custom nodes.

### 5.2 Known non-determinism sources

| Source | Effect |
|--------|--------|
| **Floating-point ordering** | Minor numerical drift across **driver** or **CUDA/ROCm** updates can change sampling noise even with a fixed seed on some stacks. |
| **ComfyUI version drift** | **Major or minor** ComfyUI upgrades may change sampler behavior, node defaults, or denoising schedules. |
| **Missing `seed`** | Each regeneration may differ **by design** — validators emit **`reproducibility.seed_omitted`** (`warn`). |
| **Custom nodes** | Third-party nodes may introduce non-deterministic kernels or external network calls — outside core Cuebert guarantees. |

### 5.3 Mitigation convention

Projects **SHOULD** declare an opaque top-level string such as:

```yaml
x_comfyui_version_pin: "0.3.0"
```

The **asset agent (M4-P3)** is expected to **compare** this pin against the live
server-reported ComfyUI version (from `comfyui_health_check` or `/system_stats`)
before unattended batch regeneration. The core schema **does not interpret**
this key; it is **advisory** and carried under `x_*` rules.

---

## 6. Validation (`asset_manifest_validate`)

### 6.1 Tooling surface

The **`asset_manifest_validate`** MCP tool (shipped under
`.cursor/skills/comfyui-toolkit/tools/asset_manifest_validate.py`) loads the
resolved YAML, validates against **`.cuebert/schemas/asset-manifest.schema.json`**,
then applies **semantic rules** not expressible in JSON Schema alone (duplicate
ids, effective workflow presence, local workflow allow-list membership,
destination containment hints).

### 6.2 Envelope shape (stable keys)

Returns a JSON-serializable dict:

| Key | Type | Notes |
|-----|------|-------|
| `status` | string | `pass` \| `warn` \| `fail` \| `not_configured` |
| `manifest_path` | string or null | Absolute resolved path when known |
| `project_root` | string or null | Resolved application repository root |
| `schema_version` | int or null | Mirrors YAML `version` when parse succeeds |
| `asset_count` | int | Count of `assets` entries after parse |
| `findings` | list of maps | Each finding has `severity`, `code`, `path`, `message` |
| `summary` | string | One-line human outcome |

### 6.3 Severity ladder

| Severity | Meaning |
|----------|---------|
| **`fail`** | Hard validation failure — schema breach, security rejection, duplicate ids, missing effective workflow, illegal destination. |
| **`warn`** | Allowed to proceed for diagnostics, but operators SHOULD remediate — missing seed, unknown local workflow stem, destination outside declared `destination_root`, missing optional `jsonschema` Python package (falls back to minimal structural checks). |
| **`info`** | Informational only — for example project missing from workspace manifest (`not_configured` overall), manifest file absent (`not_configured`), or **`x_*`** extensions noted. |

### 6.4 Security posture (tooling)

- **No `yaml.load`** — only **`yaml.safe_load`** when PyYAML is present.
- **No `eval`**, no subprocesses, no outbound network I/O for validation.
- **Manifest size cap:** **1 MiB** maximum; larger files are **`fail`** with
  `security.manifest_too_large`.
- **Path containment:** explicit `manifest_path` arguments MUST normalize to a
  path **inside** the registered project root **or** the cuebert hub checkout
  root; otherwise **`fail`** / `security.path_outside_project`.

### 6.5 Optional Python dependencies

The validator **prefers** `PyYAML` and `jsonschema` when installed in the MCP
interpreter environment. **They are not added to `requirements.txt`** — hub
Python stays lean. Missing **PyYAML** is a **`fail`** (`runtime.pyyaml_missing`)
because YAML manifests cannot be parsed safely without it. Missing
**`jsonschema`** is a **`warn`** (`runtime.jsonschema_missing`) with a **minimal
stdlib structural check** as fallback.

---

## 7. Evolution & versioning

1. **`version: 1`** is the only supported integer today. **Unknown versions are
   errors** in validators (loud failure, no partial acceptance).
2. **Additive** fields inside `version: 1` MAY appear in later patch milestones
   as **optional** keys without bumping `version`, provided JSON Schema is
   updated in the same commit.
3. **Breaking** layout or semantic changes require **`version: 2`** (or higher),
   a new JSON Schema file / `$id`, and coordinated updates to MCP tools and the
   asset agent.
4. The JSON Schema **`$id`** uses a conceptual HTTPS URL
   (`https://cuebert.dev/schemas/asset-manifest-v1.json`); it **does not need to
   resolve** over the network for offline validation.

---

## 8. Non-goals

- **Not** a replacement for Unreal `.uasset` / Unity prefabs / Godot `.tres`
  native content databases — generated PNGs are **inputs** to those systems, not
  replacements.
- **Not** a texture baking or material graph compiler — **M5+** owns bake-style
  pipelines if they appear.
- **Not** audio, skeletal animation, curves, or **3D mesh** generation — **out
  of M4** scope by charter.
- **Not** an asset store, licensing ledger, or commerce integration.

---

## 9. Cross-references

| Document / path | Relationship |
|-----------------|--------------|
| `.cuebert/schemas/asset-manifest.schema.json` | Machine schema (draft-07). |
| `docs/projects/_templates/asset-manifest-template.yaml` | Copy-paste starter. |
| `.cursor/skills/comfyui-toolkit/SKILL.md` | Parent skill; operations table lists `asset_manifest_validate`. |
| `.cuebert/workspace-manifest.json` | Declares `projects.<key>.path` and optional `assetManifestPath`. |
| `docs/_ai_system/standards/play-preview-guards.md` | Style reference for severity vocabulary and stable ids. |
| `docs/_ai_system/standards/control-plane-paths.md` | Hub vs app repo path resolution invariants. |
| `docs/_ai_system/agents/agent-ops-onboard.md` | Workspace manifest authoring during `/onboard`. |

---

## 10. Footer

**Status:** **M4-P2** — schema + JSON Schema + MCP validator.  
**Asset agent integration:** **M4-P3**.  
**Worked plan template:** **M4-P4**.  
**ComfyUI toolkit HTTP + dry-run client:** landed in **M4-P1**.  
**Document history:** initial publication **2026-04-20** (**M4-P2**).

---

## Appendix A — Example: effective workflow merge

Given:

```yaml
defaults:
  workflow: texture_tileable
assets:
  - id: a
    prompt: "…"
    destination: Content/Art/a.png
  - id: b
    workflow: icon_flat
    prompt: "…"
    destination: Content/Art/b.png
```

- Asset **`a`** uses **`texture_tileable`**.
- Asset **`b`** uses **`icon_flat`**, overriding the default.

If **`defaults.workflow`** were omitted and asset **`a`** also omitted
`workflow`, the effective workflow for **`a`** would be **empty** → validator
**`fail`** (`manifest.workflow_missing`).

---

## Appendix B — Example: destination containment

```yaml
defaults:
  destination_root: Content/Art/
assets:
  - id: ok
    prompt: "…"
    destination: Content/Art/Heroes/ok.png
  - id: stray
    prompt: "…"
    destination: Plugins/Stray/stray.png
```

- **`ok`** produces **no** containment warning.
- **`stray`** triggers **`path.outside_destination_root`** (`warn`) because
  `Plugins/Stray/stray.png` does not sit under the `Content/Art/` prefix.

This is **advisory**: some teams intentionally ship marketing captures under
`Plugins/` or `Raw/` trees. Warnings exist to catch accidental drift, not to ban
valid layouts.

---

## Appendix C — Finding codes (API surface)

The MCP validator emits **stable, lowercase, dot-separated** codes. Treat renames
as **semver-major** events for automation.

| Code | Typical severity |
|------|------------------|
| `project.not_in_workspace_manifest` | `info` |
| `project.invalid_entry` | `fail` |
| `project.path_missing` | `fail` |
| `project.root_not_directory` | `warn` |
| `manifest.not_found` | `info` |
| `manifest.parse_error` | `fail` |
| `manifest.stat_failed` | `fail` |
| `security.manifest_too_large` | `fail` |
| `security.path_outside_project` | `fail` |
| `security.path_traversal_manifest` | `fail` |
| `security.absolute_destination` | `fail` |
| `security.path_traversal_destination` | `fail` |
| `runtime.pyyaml_missing` | `fail` |
| `runtime.jsonschema_missing` | `warn` |
| `schema.validation_error` | `fail` |
| `schema.missing_required_field` | `fail` |
| `schema.version_unknown` | `fail` |
| `schema.invalid_root` | `fail` |
| `schema.invalid_engine` | `fail` |
| `schema.assets_required` | `fail` |
| `schema.asset_not_object` | `fail` |
| `schema.invalid_asset_id` | `fail` |
| `schema.prompt_length` | `fail` |
| `schema.file_missing` | `fail` |
| `schema.invalid_json` | `fail` |
| `hub.root_not_found` | `fail` |
| `asset.duplicate_id` | `fail` |
| `manifest.workflow_missing` | `fail` |
| `workflow.not_found_local` | `warn` |
| `reproducibility.seed_omitted` | `warn` |
| `path.outside_destination_root` | `warn` |
| `extension.x_keys_present` | `info` |

---

## Appendix D — Engine path idioms (informative)

| `engine` value | Typical raster roots (informative only) |
|----------------|-------------------------------------------|
| `unreal` | `Content/...` — aligns with UE asset tree conventions. |
| `unity` | `Assets/...` — aligns with Unity project layout. |
| `godot` | `res://` mapped to repository-relative `res/` or project-defined art dirs. |

Validators **do not** rewrite destinations per engine in **M4-P2**; engine-aware
rewrites belong in **M4-P3** if truly needed.

---

## Appendix E — Relationship to traces

Successful ComfyUI generations initiated from the hub still record **trace
artifacts** under `.cuebert/traces/asset/...` per `comfyui-toolkit` docs. The
**asset manifest** is orthogonal: it is the **intent catalog** inside the game
repo, while traces are the **execution audit** on the hub. Future milestones may
cross-link trace `envelope.json` files back to `assets[].id` values.

---

## Appendix F — Glossary

| Term | Definition |
|------|------------|
| **Effective workflow** | `coalesce(asset.workflow, defaults.workflow)` with empty strings treated as absent. |
| **Project root** | Filesystem root of the application repository: resolved from `projects.<key>.path` relative to the hub checkout. |
| **Hub root** | Filesystem root of the cuebert repository containing `.cuebert/`. |

---

## Appendix G — YAML authoring tips

- Prefer **folded blocks** (`>`) for long prompts to keep diffs readable.
- Keep **`id` values stable** across renames of `destination` so future trace
  correlation remains possible.
- Treat **`tags`** as a **controlled vocabulary** per team even though the
  schema allows any short strings.

---

## Appendix H — Compatibility with `comfyui_generate_asset`

The MCP tool **`comfyui_generate_asset`** validates workflow names against the
**hub-local** `workflows/*.json` list. The asset manifest validator performs the
**same style of existence check** for advisory **`workflow.not_found_local`**
warnings when graphs have not yet been checked in (**M4-P4** ships starter
graphs). This alignment prevents silent drift between “manifest says generate”
and “toolkit cannot submit”.

---

## Appendix I — QA harness expectations (forward-looking)

Future `/play` QA harnesses **may** import manifest-derived lists to assert that
every declared `destination` exists on disk **after** an asset pass. That logic
is **not** part of **M4-P2**; this document only defines the **contract** those
harnesses will consume.

---

## Appendix J — Idempotence guidance for operators

Re-running generation for the same manifest row **should** be safe when seeds
and versions align: overwrite the same `destination` PNG in place, then let
Perforce / Git / Plastic workflows handle binary diff and locks as they already
do for artist-supplied PNGs. Prompt bodies are **UTF-8**; keep manifests to a
**few hundred rows** for maintainability. Validators follow **`comfyui-toolkit`**
envelope norms (**M4-P1**): structured returns instead of uncaught MCP
exceptions, with unexpected internal faults logged at **`ERROR`** via the
standard `logging` module.
