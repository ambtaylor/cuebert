---
name: comfyui-toolkit
description: Generate and iterate 2D game assets (textures, icons, concept art) via a local or remote ComfyUI server. Use when users ask to create/iterate/regenerate game art, mention ComfyUI, or want to populate a project's Content/Art/ directory.
version: 0.1.0
status: alpha
---

## Overview

The **comfyui-toolkit** skill exposes MCP tools that talk to a **ComfyUI** HTTP
API (`/prompt`, `/history`, `/view`) so agents can queue pre-authored workflow
graphs, inject prompts, poll for completion, and persist PNG outputs under the
Cuebert hub trace tree. It is the first **gaming-specific executable** toolkit
in the `cuebert-asset` MCP server group: it is meant for **2D raster assets**
(textures, HUD icons, concept stills) that ship next to Unreal or other engine
content.

The toolkit is deliberately **narrow**: it does **not** drive 3D mesh
generation, rigging, animation timelines, or engine packaging. Those concerns
belong to later milestones (Unreal bridge, asset manifests, gauntlet QA) or
stay out of ComfyUI entirely. It also does **not** ship turnkey workflow JSON in
M4-P1; graphs land under `workflows/` starting in **M4-P4**, while this phase
delivers a **dry-run-first** client so servers boot without a local ComfyUI
process.

Integration with the dedicated **asset agent** (`docs/_ai_system/agents/agent-asset-gen.md`, not yet ported in M4-P3) and **end-to-end generation with real prompts** (M4-P4) are **out of scope** for this milestone. What you get now is a stable **tool surface**, trace-path conventions, vault-aware URL resolution, and simulated envelopes when no server is reachable.

## When to use this skill

- Authoring or iterating **2D game art** (albedo-style textures, stylized icons, mood boards).
- Mention of **ComfyUI**, `/prompt`, or **local diffusion** for asset passes.
- Populating **`Content/Art/`** (or similar) with generated stills under human review.
- **Smoke-testing** asset pipelines in CI or Cursor without pinning a GPU box online (dry-run).
- **Mass texture variants** once workflows exist (same graph, different seeds/prompts).

## Prerequisites

- **Cuebert hub root** (directory containing `.cuebert/`) discoverable from the MCP tool process (same discovery pattern as other hub toolkits).
- **ComfyUI base URL** from environment **`CUEBERT_COMFYUI_BASE_URL`** or hub shared vault key **`comfyui.base_url`** (documented as the logical `shared/comfyui/base_url` tier in `vault-standard.md`). If neither is set, `comfyui_health_check` reports **`not_configured`** and the effective toolkit mode falls back to **`dry_run`** so startup never depends on a server.
- Default URL hint when nothing is configured: `http://127.0.0.1:8188` (not treated as configured until explicitly provided).
- Run **`comfyui_health_check`** before large batch jobs when operating in **`live`** mode.

## Operations

| MCP tool | One-line description | Typical input | Typical output |
|----------|----------------------|---------------|----------------|
| `comfyui_health_check` | Probe `/system_stats` and queue hints | _(none)_ | `status`, `base_url`, `mode`, `version`, `queue_remaining`, `error` |
| `comfyui_generate_asset` | Allow-listed workflow + prompt, poll, fetch | `workflow_name`, `prompt`, optional `seed`, `destination`, `params` | `status`, `prompt_id`, `assets`, `envelope_path`, `duration_ms`, `dry_run` |
| `comfyui_list_workflows` | Scan `workflows/*.json` in this skill | _(none)_ | `workflows[]` with `name`, `path`, `description`, `last_modified_iso`, `count` |
| `comfyui_asset_status` | Inspect `/history/<prompt_id>` or dry-run IDs | `prompt_id` | `status`, `assets`, `error`, `dry_run`, optional `error_code` |

For field-level detail, error codes, and HTTP semantics, see **`reference.md`**.

## Workflows

Named graphs live beside this file under **`workflows/`**. Only `*.json`
basenames returned by `comfyui_list_workflows` are accepted by
`comfyui_generate_asset` (path traversal and arbitrary uploads are rejected).

**M4-P1** ships an **empty** workflow directory so the MCP group loads cleanly.
**M4-P4** is scheduled to add real starter graphs (stubs until authored):

- `texture_tileable.json`
- `concept_character.json`
- `icon_flat.json`

Template substitution for selective node targeting is **deferred to M4-P4**;
today the client performs a **minimal stub** injection (prompt text into every
`CLIPTextEncode`, optional `KSampler` seed) when `CUEBERT_COMFYUI_MODE=live`.

## Outputs

Successful runs write raster files under:

`.cuebert/traces/asset/<UTC-timestamp>/<workflow_name>/<slug>.png`

A sidecar **envelope JSON** is written next to the asset as
`<destination>.json`, capturing workflow name, sanitized prompt, `prompt_id`,
completion status, `dry_run`, and output paths. Aggregated run metadata for
harnesses may also reference the same directory tree per
`docs/_ai_system/standards/control-plane-paths.md` (hub trace conventions).

## Dry-run mode

When **`CUEBERT_COMFYUI_MODE=dry_run`** is set **or** the toolkit is
**unconfigured** (no env base URL and no vault `comfyui.base_url`, with mode
unset defaulting to dry-run), tools **do not open outbound ComfyUI HTTP** except
where a tool is explicitly filesystem-only (`comfyui_list_workflows`). Health
checks return synthetic reachability, `submit_workflow` fabricates
`dryrun-<hash>` IDs, polling completes immediately, and `fetch_asset` writes a
**`.png.txt` placeholder** beside the requested basename (text-only, similar in
spirit to `CUEBERT_MEMORY_MODE=text` for memory tooling).

This keeps CI, Cursor MCP startup, and the future asset agent able to exercise
**real JSON envelopes** without pinning a GPU workstation.

## Memory hooks

No automatic calls into `memory-toolkit` are performed. Orchestrators may still
pair runs with `milestone_commit` / `troubleshoot_commit` when a campaign
requires traceability.

## See also

- `reference.md` — per-tool contracts, failure modes, env vars, security notes.
- `docs/_ai_system/standards/vault-standard.md` — vault resolution for `comfyui.base_url`.
- `docs/_ai_system/standards/control-plane-paths.md` — hub vs project plan paths (trace layout context).
- `docs/_ai_system/agents/agent-asset-gen.md` — asset agent protocol (**M4-P3**, not yet ported).

## Error handling

Tools return **JSON envelopes** with `status` / `error` / `error_code` fields
instead of raising to MCP clients, matching other cuebert toolkits. Logging uses
the standard library `logging` module (no `print`).

## Versioning

- **0.1.0 (alpha):** scaffold, client, four MCP tools, dry-run defaults,
  workflow directory placeholder.

## Maintainer notes

Keep dependencies **stdlib-first** (`urllib`); optional heavy deps are
intentionally avoided so hub Python environments stay lean. All outbound URLs
must remain on the configured host (redirects that change host are rejected).

When extending for M4-P4, preserve the allow-list contract: never accept raw
workflow JSON blobs from untrusted chat content without writing them to
`workflows/` under human review first.

## Quick start (live)

1. Install and launch ComfyUI locally (default `127.0.0.1:8188`).
2. Set `comfyui.base_url` in hub shared vault **or** export `CUEBERT_COMFYUI_BASE_URL`.
3. Set `CUEBERT_COMFYUI_MODE=live` if you had previously forced dry-run.
4. Drop an API-format graph JSON under `workflows/`.
5. Call `comfyui_list_workflows`, then `comfyui_generate_asset`.

## Quick start (dry-run / CI)

1. Omit vault/env configuration **or** export `CUEBERT_COMFYUI_MODE=dry_run`.
2. Start `cuebert-asset` MCP server — tools import cleanly.
3. Call `comfyui_health_check` (expect `not_configured` or `dry_run`) and
   `comfyui_list_workflows` (empty list until M4-P4).

## Security summary

- **No hard-coded credentials**; URLs come from env/vault only.
- **Allow-listed workflows** from this skill directory only.
- **Destination paths** must resolve under `.cuebert/traces/asset/`.
- **Prompts** are sanitized (control characters stripped, length capped at 4096).
- **No cross-host redirects** on HTTP clients used here.

## Glossary

- **Envelope:** JSON sidecar written next to generated assets for auditability.
- **Allow-list:** basename stems discovered via filesystem scan of `workflows/`.
- **Dry-run ID:** `prompt_id` values beginning with `dryrun-` synthesized locally.

## Compatibility

Designed for **Cuebert MCP** (`mcp.server.fastmcp.FastMCP`) and coexists with
`memory-toolkit` without touching SQLite. Compatible with
`CUEBERT_MEMORY_MODE=text` orchestration (no embedding side effects here).

## License / provenance

Ships as part of the Cuebert hub repository; follow repository root licensing.

## Changelog sketch

- **M4-P1:** Initial skill scaffold + MCP tools + client + docs.
- **M4-P3:** Asset agent wiring (external).
- **M4-P4:** Real workflows + richer prompt routing.

## FAQ

**Why does `comfyui_generate_asset` fail with `unknown_workflow`?**  
The `workflows/` directory is empty until M4-P4 ships graphs. Dry-run still validates names against that directory.

**Why `not_configured` on health?**  
No `CUEBERT_COMFYUI_BASE_URL` and no vault URL; set one to move to live probing.

**Can I target arbitrary URLs from the prompt string?**  
No. Only the configured base URL is contacted, and redirects cannot change host.

## Roadmap touchpoints

- **M4-P3:** Asset agent calls these tools with curated parameters.
- **M4-P4:** Authoritative workflow library + template substitution.
- **Later:** Optional queue backoff knobs if operators need throttling.

## Contact / ownership

Owned by the Cuebert gaming-system track; update `skills.yaml` and this file
together when operations change.
