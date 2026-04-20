# ASSET PLAN — Manifest Diff & Execution Plan

> **Role:** `/asset` harness — **Plan** phase subagent (logical role)  
> **Parent protocol:** `docs/_ai_system/agents/agent-asset.md` — read **section 2 (Phase chain)**, **section 3 (Subagent roster)** row **`agent-asset-plan`**, and **section 8 (asset plan schema)** before executing. This document is the normative stub for that roster row.  
> **Dispatch:** Invoked only inside the **`/asset`** harness as a `Task(subagent_type: "generalPurpose")` whose first action is to read this file. The Cuebert Supervisor does **not** route `/asset` subagents directly; see `.cursor/rules/cuebert-supervisor.mdc` section 0 (`/asset` stub until harness wiring completes).

---

## 1. Role

You transform a resolved **asset manifest** plus optional **asset plan** companion YAML into an **ordered execution plan**: for each **`assets[].id`**, emit **`generate`**, **`skip_unchanged`**, **`regenerate`**, or **`place_only`** actions with machine-readable **reasons**. You **do not** call ComfyUI, **do not** copy files into **`Content/`**, and **do not** mutate the lockfile — you only **read** the prior **`.cuebert-assets.lock.yaml`** when present and compute the diff.

---

## 2. Inputs

| Input | Required | Description |
|-------|----------|-------------|
| **`PROJECT_KEY`** | Yes | Key under **`.cuebert/workspace-manifest.json` → `projects`**. |
| **`APP_REPO`** | Yes | Absolute application repository root. |
| **`MANIFEST_PATH`** | Yes | Absolute path to resolved **`.cuebert-assets.yaml`** (or override). |
| **`LOCKFILE_PATH`** | No | Absolute path to **`.cuebert-assets.lock.yaml`** when it exists; absent lockfile implies **first run** for all ids. |
| **`ASSET_PLAN`** | No | Parsed YAML object from companion plan ( **`only`**, **`force`**, **`skip_generate_for`**, **`dry_run`**, **`guards_override`** ). |
| **`CLI_ONLY`** | No | Comma-separated ids from **`--only`** when harness passes it. |
| **`CLI_FORCE`** | No | Boolean from **`--force`** — when true, all targeted rows become **`regenerate`** unless explicitly excluded by empty intersection rules (**M4-P4**). |

---

## 3. Outputs

| Output | Description |
|--------|-------------|
| **`plan[]`** | Ordered list of `{ id, action, reason }` objects (**section 7**). |
| **`total`**, **`to_generate`**, **`to_skip`** | Counts for coordinator summary and guard **`guard.plan.non_empty`**. |
| **`findings`** | Informational rows (for example **`reproducibility.seed_omitted`** echoes from manifest validator context). |
| **`status`** | **`pass`** when a coherent plan is produced; **`fail`** on unreadable manifest or contradictory filters. |

---

## 4. Scope guardrails

1. **Read-only:** Do **not** write **`Content/`**, do **not** call **`comfyui_generate_asset`**, do **not** edit **`.cuebert/`** hub meta except future append-only trace hooks owned by harness (**M4-P4**).  
2. **Determinism:** Sort **`plan[]`** by **`id`** ascending unless the harness supplies an explicit **`PLAN_ORDER`** field (**M5**).  
3. **No secret materialization:** Do not read vault; ComfyUI URLs are **Generate** phase concerns.  
4. **Manifest authority:** If **`MANIFEST_PATH`** cannot be parsed, return **`fail`** — do not guess ids from chat prose.  
5. **Lockfile version:** If lockfile **`version`** is unknown integer, **`fail`** with finding **`lockfile.version_unknown`** (**M4-P4** wire-up).

---

## 5. Hashing contract (stub)

Until the harness ships a shared **`cuebert-asset-hash`** library (**M5**), this subagent **declares** the following **logical** hashes recorded later in the lockfile:

| Hash | Inputs (conceptual) |
|------|---------------------|
| **`workflow_hash`** | Canonical bytes of resolved **`workflows/<name>.json`** on hub. |
| **`prompt_hash`** | UTF-8 bytes of positive **`prompt`** + **`negative_prompt`** after manifest merge. |
| **`params_hash`** | Stable JSON serialization of merged **`params`** (sorted keys). |

**M4-P3:** Emit **placeholder** `sha256:000…` only inside **dry documentation** — real hashing is **M4-P4**.

---

## 6. Protocol

Execute in order; do not skip steps.

1. **Load manifest** — Parse YAML; if invalid, **`status: fail`** with validator-shaped **`findings`**.  
2. **Resolve targeting** — Intersect manifest **`assets[].id`** with **`ASSET_PLAN.only`** when present; intersect again with **`CLI_ONLY`** when present. Empty intersection → **`fail`** **`plan.empty_filter`**.  
3. **Load lockfile** — If **`LOCKFILE_PATH`** missing, treat all targeted ids as **never generated** → default action **`generate`** (or **`regenerate`** when **`CLI_FORCE`**).  
4. **Per-id diff** — For each targeted id, compare manifest row fields to lockfile row when present:  
   - If **`CLI_FORCE`** true → **`regenerate`**, **`reason: forced`**.  
   - Else if any hash differs or **`seed`** changed or declared **`comfyui_version`** pin differs → **`regenerate`** with specific **`reason`**.  
   - Else if id listed in **`ASSET_PLAN.skip_generate_for`** → **`place_only`**, **`reason: skip_generate_for`**.  
   - Else → **`skip_unchanged`**, **`reason: hashes_match`**.  
5. **Emit envelope** — Return JSON per **section 7** plus human-readable one-paragraph summary for operators.

---

## 7. Output envelope (JSON shape)

```json
{
  "status": "pass",
  "project": "hello-level",
  "plan": [
    {"id": "hero_idle", "action": "generate", "reason": "seed_changed"},
    {"id": "barrel_01", "action": "skip_unchanged", "reason": "hashes_match"}
  ],
  "total": 5,
  "to_generate": 2,
  "to_skip": 3,
  "findings": []
}
```

**`action` enum:** **`generate`** | **`regenerate`** | **`skip_unchanged`** | **`place_only`**

**`reason` examples:** **`no_lockfile_row`**, **`seed_changed`**, **`prompt_changed`**, **`workflow_changed`**, **`params_changed`**, **`hashes_match`**, **`forced`**, **`skip_generate_for`**

---

## 8. Failure modes

| Failure | `status` | Representative `findings` code |
|---------|----------|-------------------------------|
| Manifest parse / schema fail | **`fail`** | **`manifest.parse_error`**, **`schema.validation_error`** |
| Workspace project missing | **`fail`** | **`project.not_in_workspace_manifest`** |
| Lockfile parse error | **`fail`** | **`lockfile.parse_error`** |
| Filter intersection empty | **`fail`** | **`plan.empty_filter`** |
| Internal inconsistency (duplicate ids after filters) | **`fail`** | **`asset.duplicate_id`** |

---

## 9. Relationship to Asset Pipeline Guards

**`guard.plan.non_empty`** and **`guard.plan.workflow_available`** (see **`docs/_ai_system/standards/asset-pipeline-guards.md`**) consume this envelope in **post-plan** gates. An empty **`plan[]`** with **`to_generate == 0`** and **`to_skip == total`** may still be **valid** when the operator ran a **verification-only** session — harness policy distinguishes **no-op** vs **error** in **M4-P4**.

---

## 10. Task envelope sketch (harness → Plan)

```text
## Cuebert /asset — Plan
**First action:** Read docs/_ai_system/agents/agent-asset-plan.md

PROJECT_KEY: [key]
APP_REPO: [absolute]
MANIFEST_PATH: [absolute]
LOCKFILE_PATH: [absolute or none]
ASSET_PLAN: [yaml snippet or json]
CLI_ONLY: [optional]
CLI_FORCE: [bool]
```

---

## 11. Cross-references

| Doc | Use |
|-----|-----|
| `agent-asset.md` | Coordinator ordering, flags, memory policy |
| `agent-asset-generate.md` | Consumer of **`plan[]`** rows that require ComfyUI |
| `agent-asset-place.md` | Consumer of placement-needed rows |
| `asset-manifest.md` | Schema + resolution order |
| `asset-pipeline-guards.md` | Post-plan guard expectations |

---

## 12. Negative examples (must REJECT)

- User asks Plan subagent to **“just copy PNGs into Content”** → **out of scope** — redirect to **`agent-asset-place`**.  
- User asks to **regenerate** without manifest change but **forgot** **`force`** → Plan correctly returns **`skip_unchanged`**; do not silently upgrade to **`regenerate`**.

---

## 13. Partial planning

If some ids are **valid** and others **fail** schema checks, the manifest validator should already have failed upstream — Plan assumes **manifest.valid** pre-plan guard passed. If Plan detects **new** per-row defects anyway, **`fail`** the entire envelope (no partial **`plan[]`** for half the file) unless a future **`--best-effort`** flag is documented (**M5**).

---

## 14. Operator visibility

Always echo **`MANIFEST_PATH`** and **`LOCKFILE_PATH`** (or **`none`**) in a short preamble so humans can copy paths into tickets.

---

## 15. Lockfile diff algorithm (normative sketch)

When **`LOCKFILE_PATH`** resolves to an existing file:

1. Parse YAML; require **`version: 1`** and matching **`project`** field vs **`PROJECT_KEY`** — mismatch → **`fail`** **`lockfile.project_mismatch`**.  
2. Build a map **`lock_index[id] → row`**.  
3. For each targeted manifest asset **`m`**:  
   - If **`m.id`** absent from **`lock_index`** → **`generate`**, **`reason: no_lockfile_row`**.  
   - Else compare **`workflow_hash`**, **`prompt_hash`**, **`params_hash`**, optional **`comfyui_version`**, and **`seed`** against recomputed candidate hashes (**M4-P4** supplies real hash functions).  
   - If any differ → **`regenerate`** with the **first** differing field named in **`reason`** (stable single-reason policy for telemetry).  
   - If none differ → **`skip_unchanged`**, **`reason: hashes_match`**.

When **`CLI_FORCE`** is **`true`**, short-circuit comparisons: every targeted id becomes **`regenerate`**, **`reason: forced`**, except ids explicitly excluded by harness-level **`--except`** flag (**M5** optional).

---

## 16. Interaction with `only` and `skip_generate_for`

**`ASSET_PLAN.only`** narrows the manifest universe. **`skip_generate_for`** is applied **after** action selection for ids that would have been **`regenerate`** or **`generate`**, converting them to **`place_only`** **only when** the harness has confirmed trace artifacts exist (**M4-P4** file checks). If artifacts are missing, Plan MUST **`fail`** that id with **`place_only_missing_trace`** rather than fabricate bytes.

---

## 17. Findings shape

Each entry in **`findings`** mirrors validator style:

```json
{"severity": "info", "code": "plan.note", "message": "Seed omitted for id barrel_01 — regeneration non-deterministic."}
```

**Severity** stays within **`info`** / **`warn`** for Plan — **`fail`** rolls up to top-level **`status: fail`** without duplicating per-row failure objects inside **`plan[]`** unless **`M5`** introduces **`row_status`** (**deferred**).

---

## 18. Determinism and ordering

**`plan[]` order:** ascending **`id`** lexicographic sort for stable transcripts. When manifest declares **`assets`** in intentional artistic order and team wants that preserved, harness MAY pass **`PRESERVE_MANIFEST_ORDER: true`** — default **`false`** for reproducible CI logs (**M4-P4** default choice).

---

## 19. Relationship to `asset_manifest_validate`

When the harness runs **`asset_manifest_validate`** before Plan, Plan SHOULD trust **`status: pass|warn`** and treat **`fail`** as precluded. If Plan is invoked standalone for debugging, it MAY re-run validation internally — duplicate validation is **`info`** finding **`plan.duplicate_validation`**.

---

## 20. Escalation to coordinator

Return **`warnings[]`** separate from **`findings`** only if harness contract **M4-P4** adds that field; until then, fold warnings into **`findings`** with **`severity: warn`**.

---

## 21. Operator messaging

Include a short markdown table summarizing **`to_generate`**, **`to_skip`**, and estimated wall time **`estimate_wall_s`** as **`null`** in M4-P3 (harness computes later using GPU class hints **M6**).

---

## 22. Compatibility with multi-repo workspaces

If **`APP_REPO`** is not inside the same multi-root folder visibility as **`HUB_REPO`**, Plan still operates on **absolute paths** supplied by harness — do not guess relative paths across roots.

---

## 23. Appendix — id normalization

Trim ASCII whitespace around ids; reject empty post-trim with **`fail`** **`asset.invalid_id`**.

---

## 24. Appendix — example `plan[]` with `place_only`

```json
[
  {"id": "hero_idle", "action": "regenerate", "reason": "prompt_changed"},
  {"id": "hero_portrait_1", "action": "place_only", "reason": "skip_generate_for"}
]
```

---

## 25. Revision history

**M4-P3:** initial protocol stub.

---

Status: **M4-P3** (protocol stub). Shared hashing + harness wiring: **M4-P4**. Evaluator-backed guards: **M5–M6**.
