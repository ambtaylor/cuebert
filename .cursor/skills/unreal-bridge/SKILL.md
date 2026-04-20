---
name: unreal-bridge
description: Query and control a running Unreal Editor via Epic's Remote Control HTTP API (presets, properties, functions). Use when users ask to inspect an active UE editor, set properties on exposed actors, call exposed blueprint functions, or list registered assets. Pairs with the comfyui-toolkit for the /asset and /play harnesses.
version: 0.1.0
status: alpha
---

## 0. Purpose

The **unreal-bridge** skill bridges cuebert to a **running Unreal Editor** using
Epic’s built-in **Remote Control** HTTP API (`/remote/*` on port **30010** by
default). It supports **read-only inspection** (info, presets, exposed
metadata) and, in later milestones, **scoped writes** (property set, function
call) without shelling out to UAT or custom native plugins. The primary consumer
is the future **`agent-unreal`** bridge agent (**M5-P3**), invoked from **`/play`**
and **`/asset`** harnesses alongside `comfyui-toolkit`.

## 1. Prerequisites

- **Unreal Editor 5.0+** running on the local machine or a reachable host.
- **`Remote Control`**, **`Remote Control API`**, and (when using the stock web
  UI) **`Remote Control Web Interface`** plugins enabled in the `.uproject`.
- Default HTTP port **`30010`** reachable on the LAN (Epic defaults to LAN-only;
  cuebert does not publish this to the public internet).
- Optional: **`CUEBERT_UNREAL_BASE_URL`** environment variable or hub shared
  vault key **`unreal.base_url`** (logical `shared/unreal/base_url` tier in
  `vault-standard.md`).
- Optional: **`CUEBERT_UNREAL_MODE`** = `live` | `dry_run`. When unset and the
  base URL is **not** explicitly configured, the toolkit defaults to **`dry_run`**
  so MCP startup never requires an editor. When explicitly configured, the
  default mode is **`live`**; unreachable hosts surface as **`unreachable`** in
  `unreal_health_check` rather than silently mutating global mode.

## 2. Operations (MCP tool catalog)

| Tool | Purpose | Dry-run behavior |
|------|---------|-------------------|
| `unreal_health_check` | Probe `GET /remote/info`, confirm editor is up | Synthetic envelope: `version` **5.4.0-dry_run**, bundled plugin names |
| `unreal_list_presets` | List Remote Control presets in the project | Seeded fixture list (**3** presets) |
| `unreal_describe_preset` | Dump exposed properties + functions for a preset | Synthetic **2** properties + **1** function |
| `unreal_ping_actor` | Given preset + actor label, confirm exposure (read-only) | `{found: true, label: ...}` |

All tools return **structured JSON envelopes** (no thrown MCP errors for
expected failures). Live mode uses **stdlib `urllib`** only.

## 3. Dry-run mode

`unreal-bridge` behaves as **`dry_run`** when any of the following holds:

- **`CUEBERT_UNREAL_MODE=dry_run`** is set explicitly (or vault `unreal.mode`), or
- The Remote Control base URL is **not** explicitly configured (no env URL and
  no vault `unreal.base_url`; the `http://localhost:30010` hint alone does not
  count as configuration), which also forces **`dry_run`** when mode is unset, or
- The operator forces synthetic envelopes while iterating harnesses (same
  contract as `comfyui-toolkit`).

Synthetic envelopes include `"mode": "dry_run"` (where applicable) so
downstream agents can keep planning without a live editor. See **`reference.md`**
for exact field shapes.

## 4. Security

- **HTTP only** in **M5-P1** (websocket event stream deferred).
- **Localhost-by-default** posture: if the resolved `base_url` host is **not**
  loopback, `unreal_health_check` adds a **`warnings`** string but does **not**
  block calls (operators may intentionally target a LAN workstation).
- Epic’s stock Remote Control endpoint has **no authentication**; cuebert adds
  **no** auth shim. Use a reverse proxy if you need TLS or tokens.
- **No shell-out**, **no eval**, **no file writes** from this toolkit in P1
  (mutations land in **M5-P4**).
- **Request timeout** defaults to **10s**, overridable via env/vault, **hard-capped
  at 30s** regardless of environment values.
- **URL sanitization** accepts only **`http://`** and **`https://`** schemes,
  rejects **`file://`**, **`javascript:`**, etc., and rejects **userinfo**
  (`user:pass@host`) URLs outright.
- **Path / injection defense:** preset names and actor labels are validated with
  strict allow-lists before they are interpolated into paths or query strings.

## 5. Workflow / preset directory

Bundled JSON fixtures (for tests and documentation) live under
**`presets/`**, mirroring `comfyui-toolkit`’s **`workflows/`** directory. **M5-P1**
seeds the folder with **`README.md`** and **`.gitkeep`** only. **M5-P4** will add
real sample fixtures and expand parsers as Epic’s payloads evolve.

## 6. Memory hooks

**M5-P1** tools are **read-only** and do **not** call `memory-toolkit`. Future
**M5-P4** write paths (property set, function call, imports) will document
explicit `milestone_commit` / `troubleshoot_commit` pairing where state changes
must be auditable.

## 7. Examples

```python
# unreal_health_check() — dry-run harness (no editor required)
{"status": "dry_run", "base_url": "http://localhost:30010", "mode": "dry_run",
 "version": "5.4.0-dry_run", "plugins": ["RemoteControl", "..."], "error": null}
```

```python
# unreal_list_presets() — synthetic catalog
{"status": "dry_run", "preset_count": 3, "presets": [{"name": "ExamplePreset", ...}]}
```

```python
# unreal_describe_preset("ExamplePreset")
{"status": "dry_run", "preset_name": "ExamplePreset",
 "properties": [{"object_path": "/Game/...", "property_name": "RelativeLocation", ...}],
 "functions": [{"function_name": "ResetRound", "arg_count": 0, ...}]}
```

```python
# unreal_ping_actor("ExamplePreset", "HeroShip")
{"status": "dry_run", "found": true, "actor_label": "HeroShip"}
```

## 8. Non-goals

- Direct binary edits to `.uasset` / `.umap` files from cuebert (always let Unreal
  own on-disk content).
- **Cook / build / UAT orchestration** (handled by **`/ship`** and future **M8**
  automation).
- **PIE input injection** and automated gameplay driving (**M6 Gauntlet** scope).
- **Live shader graph editing** or material compilation control (**out of scope
  for M5**).
- Coordinating **multiple simultaneous editors** (P1 assumes **one** active
  target URL).

## 9. Cross-references

- **`reference.md`** — per-tool contracts, failure modes, env vars, vault keys.
- **`docs/_ai_system/agents/agent-unreal.md`** (M5-P3) — bridge agent protocol.
- **`docs/_ai_system/agents/agent-play-author.md`** (M2) — future consumer of
  import/spawn tools from **M5-P4**.
- **`docs/_ai_system/standards/asset-manifest.md`** (M4) — related asset hygiene
  for `/asset`.

## Quick start (live)

1. Open your game in **Unreal Editor 5.x** with **Remote Control API** enabled
   (see Epic documentation for plugin names and `.uproject` flags).
2. Confirm the HTTP listener is on the expected port (default **30010**).
3. Set **`CUEBERT_UNREAL_BASE_URL`** or hub vault **`unreal.base_url`** to the
   editor’s Remote Control base (for example `http://localhost:30010`).
4. Optionally export **`CUEBERT_UNREAL_MODE=live`** if you previously forced
   dry-run while debugging.
5. Call **`unreal_health_check`**, then **`unreal_list_presets`** and
   **`unreal_describe_preset`** against a preset you authored in-editor.

## Quick start (dry-run / CI)

1. Omit vault/env URL configuration **or** export **`CUEBERT_UNREAL_MODE=dry_run`**.
2. Start the **`cuebert-engine`** MCP group — `unreal-bridge` modules import without
   a running editor.
3. Call **`unreal_health_check`** (expect **`not_configured`** or **`dry_run`**) and
   **`unreal_list_presets`** (fixture catalog until you point at a live editor).

## Error handling

Tools return **JSON envelopes** with `status`, `error`, and mode metadata instead
of raising to MCP clients, consistent with other cuebert toolkits. Use
**`logging`** for server-side diagnostics (no `print` to stdout in steady-state
paths).

## Versioning

- **0.1.0 (alpha):** scaffold, shared client, four MCP tools, `presets/`
  placeholder, dry-run-first defaults.

## Compatibility

Designed for **Cuebert MCP** (`mcp.server.fastmcp.FastMCP`) and the
**`engine`** server group. Coexists with **`git-lfs-toolkit`** and does not
touch ComfyUI or memory SQLite.

## FAQ

**Why does `unreal_health_check` say `not_configured`?**  
No explicit base URL was set via env or vault; set one to opt into live probes.

**Why am I seeing `warnings` on an otherwise `ok` health result?**  
The resolved host is not loopback; this is informational (LAN studio setups).

**Can I drive arbitrary Blueprint graphs from chat text?**  
No. Only **exposed** fields and functions on **Remote Control presets** are
reachable; everything else stays inside Unreal’s normal edit workflows.

## 10. Footer

Status: **alpha (M5-P1)**. Four MCP tool stubs shipped. Live write operations land
in **M5-P4**. Websocket event streaming remains deferred to a future milestone.
