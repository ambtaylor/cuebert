# ASSET GENERATE — ComfyUI Invocation & Trace Artifacts

> **Role:** `/asset` harness — **Generate** phase subagent (logical role)  
> **Parent protocol:** `docs/_ai_system/agents/agent-asset.md` — read **section 2.2 (Generate)**, **section 6 (guards)**, and **section 12 (non-goals)** before executing. This document is the normative stub for the **`agent-asset-generate`** roster row.  
> **Dispatch:** Only from the **`/asset`** harness. **`subagent_type`** remains **`generalPurpose`** per parent section 3.1 — never gaming-named Cursor auto-types.

---

## 1. Role

You invoke **`comfyui_generate_asset`** once per **planned asset** that requires a fresh raster, passing **sanitized** prompts and merged parameters per **`comfyui-toolkit`**. You persist outputs under the **session trace tree** (for example **`.cuebert/traces/asset/<timestamp>/generated/<id>.png`**) and return a **structured per-asset envelope** with checksums or failure reasons. You **do not** copy into the game **`Content/`** tree — that is **`agent-asset-place`**.

---

## 2. Inputs

| Input | Required | Description |
|-------|----------|-------------|
| **`ASSET_ID`** | Yes | Stable manifest id. |
| **`WORKFLOW_NAME`** | Yes | Allow-listed workflow basename. |
| **`PROMPT`** / **`NEGATIVE_PROMPT`** | Yes / No | Strings after manifest merge; may be large — handle per toolkit caps. |
| **`SEED`** | No | Integer when reproducibility is desired. |
| **`PARAMS`** | No | Merged map forwarded to toolkit **`params`**. |
| **`TRACE_ROOT`** | Yes | Absolute **`.cuebert/traces/asset/<timestamp>/`** directory. |
| **`DESTINATION_REL`** | Yes | Manifest **`destination`** (used for logging + lockfile preview only) — **trace write basename** is derived from **`ASSET_ID`**, not from raw destination path segments that could confuse auditors. |
| **`DRY_RUN`** | No | When **`true`**, skip live ComfyUI HTTP if toolkit honors hub **`CUEBERT_COMFYUI_MODE=dry_run`** defaults. |
| **`GENERATE_TIMEOUT_S`** | No | Per-asset wall clock; default from **`.cuebert/config/asset-guards.yaml` → `global.generate_max_duration_s`**. |
| **`HUB_REPO`** | Yes | For workflow resolution and toolkit-relative paths. |

---

## 3. Outputs

| Output | Description |
|--------|-------------|
| **`trace_png_path`** | Absolute path to raster (or **`.png.txt`** placeholder in dry-run). |
| **`checksum_sha256`** | Digest over final bytes when bytes exist. |
| **`toolkit_envelope_path`** | Sidecar JSON from toolkit when present. |
| **`duration_ms`** | Wall time for this asset generation. |
| **`status`** | **`generated`**, **`failed`**, **`dry_run_synthetic`**. |

---

## 4. Scope guardrails

1. **No placement** — never **`shutil.copy`** into **`APP_REPO`**; Generate stays under **`TRACE_ROOT`**.  
2. **Allow-listed workflows only** — reject unknown workflow names before HTTP (**post-plan guard** should already catch; double-check defensively).  
3. **Sanitization** — MUST route prompts through the same sanitizer stack as **`_comfyui_client`** (**M4-P1**) before submit.  
4. **No hub meta edits** — do not modify **`docs/_ai_system/`** or **`.cursor/rules/`**.  
5. **Single-asset focus** — one Task invocation handles **one** id unless harness explicitly batches (**M5** policy).

---

## 5. Artifact storage

**Normative layout (M4-P3 recommendation):**

```text
.cuebert/traces/asset/<timestamp>/generated/<ASSET_ID>.png
.cuebert/traces/asset/<timestamp>/generated/<ASSET_ID>.envelope.json
```

When **`comfyui-toolkit`** chooses a workflow subdirectory layout for standalone runs, the **harness normalizer** (**M4-P4**) MAY relocate bytes into the above shape before Place — document **`trace_png_path`** accordingly in the envelope.

---

## 6. Dry-run semantics

When **`CUEBERT_COMFYUI_MODE=dry_run`** (explicit env) **or** toolkit is **unconfigured** per **`comfyui_health_check`**, **`comfyui_generate_asset`** returns synthetic **`prompt_id`** values and **does not** open outbound ComfyUI HTTP except where a tool is filesystem-only.

**Subagent behavior:**

- Still produce **`status: dry_run_synthetic`** (or **`generated`** with **`dry_run: true`** flag — pick one canonical spelling in **M4-P4** wire-up).  
- Still compute checksum over **placeholder** bytes when policy requires non-empty files.  
- Record **`mode: dry_run`** prominently in **`findings`** for downstream QA.

---

## 7. Timeout and abort

| Condition | Behavior |
|-----------|----------|
| **Toolkit timeout** | Return **`failed`**, **`error_code: timeout`**, preserve partial downloads if any. |
| **Non-success toolkit status** | Map toolkit **`error_code`** verbatim when present. |
| **User cancel** | Best-effort stop polling; return **`failed`**, **`error_code: aborted`**. |

Hard ceiling defaults to **`global.generate_max_duration_s`** in **`asset-guards.yaml`**.

---

## 8. Protocol

1. **Sanitize prompts** — Apply **`_comfyui_client`** sanitizer (**M4-P1** reference); reject oversize strings with **`fail`** before network.  
2. **Build toolkit args** — `workflow_name`, `prompt`, optional `negative_prompt`, `seed`, merged `params`, and a **trace-local output hint** consistent with toolkit contract (`reference.md`).  
3. **Submit** — Call **`comfyui_generate_asset`** MCP tool; capture JSON envelope.  
4. **Poll / fetch** — Implicit inside toolkit call; if toolkit exposes split phases in future, follow **`reference.md`**.  
5. **Checksum** — Hash resulting bytes when not dry-run placeholder policy.  
6. **Emit envelope** — Section 9 JSON + human-readable **one paragraph** summary.

---

## 9. Output envelope (JSON shape)

```json
{
  "id": "hero_idle",
  "status": "generated",
  "trace_png_path": ".cuebert/traces/asset/2026-04-20T12-00-00Z/generated/hero_idle.png",
  "checksum_sha256": "sha256:789...",
  "duration_ms": 8420,
  "dry_run": false,
  "toolkit": {
    "prompt_id": "abc123",
    "tool_status": "pass"
  },
  "error_code": null,
  "notes": null
}
```

**Failure shape:**

```json
{
  "id": "hero_idle",
  "status": "failed",
  "trace_png_path": null,
  "checksum_sha256": null,
  "duration_ms": 1200,
  "dry_run": false,
  "toolkit": {"prompt_id": null, "tool_status": "fail"},
  "error_code": "workflow_not_found",
  "notes": "See toolkit envelope for details."
}
```

---

## 10. Failure modes

| Mode | Meaning |
|------|---------|
| **`workflow_not_found`** | Basename absent from **`comfyui_list_workflows`**. |
| **`comfyui_unreachable`** | Network / HTTP errors in live mode. |
| **`validation_error`** | Toolkit rejected merged params. |
| **`timeout`** | Exceeded **`GENERATE_TIMEOUT_S`**. |
| **`sanitizer_rejected`** | Prompt exceeded length / disallowed pattern (**M4-P1** rules). |

---

## 11. Relationship to post-generate guards

**`guard.generate.exit_status`** reads **`status` / `tool_status`**. **`guard.generate.file_size_sane`** reads **`trace_png_path`** byte size. See **`asset-pipeline-guards.md`**.

---

## 12. Non-goals

| Non-goal | Redirect |
|----------|----------|
| **Copy into `Content/`** | `agent-asset-place.md` |
| **Lockfile write** | Coordinator harness |
| **`milestone_commit`** | Coordinator harness (`agent-asset.md` section 14) |
| **Vision QA** | **M6** |
| **Unreal import** | **M5** |

---

## 13. Task envelope sketch (harness → Generate)

```text
## Cuebert /asset — Generate
**First action:** Read docs/_ai_system/agents/agent-asset-generate.md

ASSET_ID: [id]
WORKFLOW_NAME: [stem]
TRACE_ROOT: [absolute]
DRY_RUN: [bool]
...merged prompt fields...
```

---

## 14. Cross-references

| Doc | Use |
|-----|-----|
| `.cursor/skills/comfyui-toolkit/SKILL.md` | Tool table + dry-run policy |
| `comfyui-toolkit/reference.md` | Field-level MCP contracts |
| `agent-asset-plan.md` | Upstream actions |
| `agent-asset-place.md` | Downstream copy |
| `asset-pipeline-guards.md` | Post-generate gates |

---

## 15. Engine notes

Raster dimensions and color space are **params-driven** — no engine-specific branches in Generate for **M4**.

---

## 16. Prompt sanitization details

Before **`comfyui_generate_asset`**:

- Enforce **4096** character cap on positive and negative prompts post-merge (**`asset-manifest.md`**).  
- Strip **NUL** bytes and other disallowed Unicode categories per **`comfyui-toolkit`** sanitizer table (**M4-P1**).  
- Log **redacted** one-line summary (first 120 chars) to trace **`generate.log`** — never full prompts in shared logs when **`CUEBERT_COMFYUI_REDACT_PROMPTS=true`** (**M5** env).

---

## 17. Params merge reminder

Effective params are **`merge(defaults.params, asset.params)`** with shallow dict merge — identical rule as manifest spec. Generate MUST NOT invent defaults absent from manifest.

---

## 18. Negative prompt omission

When **`NEGATIVE_PROMPT`** absent, omit field from toolkit call rather than sending empty string — some graphs treat empty string as meaningful (**M4-P4** graph QA).

---

## 19. Relationship to traces (`comfyui-toolkit`)

Toolkit default writes nested directories per workflow name; harness **may flatten** to **`generated/<id>.png`** for simpler Place inputs — if so, include **`trace_layout: flattened`** boolean in envelope (**M4-P4**).

---

## 20. Partial bytes handling

If HTTP fetch ends mid-stream, delete partial **`trace_png_path`** and return **`failed`**, **`error_code: truncated_download`**.

---

## 21. Concurrency note

Do not run two generates for same **`ASSET_ID`** sharing one **`TRACE_ROOT`** concurrently — undefined last-writer behavior.

---

## 22. Engine version echo

Echo **`ENGINE`** and **`ENGINE_VERSION`** from manifest into envelope metadata object **`host.project_engine`** for downstream memory (**M5**).

---

## 23. Example dry-run envelope

```json
{
  "id": "hero_idle",
  "status": "dry_run_synthetic",
  "trace_png_path": ".cuebert/traces/asset/2026-04-20T12-00-00Z/generated/hero_idle.png.txt",
  "checksum_sha256": null,
  "duration_ms": 4,
  "dry_run": true,
  "toolkit": {"prompt_id": "dryrun-a1b2", "tool_status": "pass"},
  "error_code": null,
  "notes": "Synthetic envelope — no GPU work performed."
}
```

---

## 24. Example live success envelope (documentation only)

```json
{
  "id": "hero_idle",
  "status": "generated",
  "trace_png_path": ".cuebert/traces/asset/2026-04-20T12-00-00Z/generated/hero_idle.png",
  "checksum_sha256": "sha256:deadbeef...",
  "duration_ms": 92134,
  "dry_run": false,
  "toolkit": {"prompt_id": "real-uuid", "tool_status": "pass"},
  "error_code": null,
  "notes": null
}
```

---

## 25. Cross-check with post-generate guards

After envelope emission, harness evaluates **`guard.generate.exit_status`** then **`guard.generate.file_size_sane`** using **`threshold.warn_bytes_min|max`** from YAML.

---

## 26. Operator troubleshooting hooks

When **`failed`**, include **`retry_hint`** string when safe (for example **`workflow_not_found` → run `comfyui_list_workflows` and fix manifest`**).

---

## 27. Revision history

**M4-P3:** initial protocol stub.

---

Status: **M4-P3** (protocol stub). Harness MCP wiring + unified trace layout: **M4-P4**.
