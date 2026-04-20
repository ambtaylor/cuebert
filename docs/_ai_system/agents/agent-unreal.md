# UNREAL BRIDGE — Engine Remote Control Coordinator

> **Role:** Non-user-facing **bridge agent** between Cuebert’s **`/play`** and **`/asset`** harnesses and a running Unreal Editor’s **Remote Control HTTP API**, mediated exclusively by the **`.cursor/skills/unreal-bridge`** MCP toolkit (**M5-P1**).  
> **Shortcut:** **None** — `agent-unreal` is **not** Supervisor-routed; it is dispatched by harness coordinators and documented harness subagents only.  
> **Activation:** Logical coordinator invoked when a harness envelope requests a **single** Remote Control operation (`probe` or `mutate`). This document is the **normative protocol stub** for **M5-P3**; a live harness runner that chains these calls remains **future** wiring.

> **CRITICAL — M5-P3 scope:** This file is **documentation only**. It defines **protocol**, **scope matrices**, **envelopes**, and **memory policy**. It does **not** register a Cursor agent file, spawn Tasks by itself, or implement HTTP clients (those live in **`unreal-bridge`** tools). **Live write MCP tools** (`unreal_set_property`, `unreal_call_function`) are **M5-P4**; **`agent-unreal-mutate.md`** is **SPEC ONLY** until then.

---

## 0. Purpose

`agent-unreal` is the **single auditable choke point** for Unreal Editor queries and **scoped** writes initiated from Cuebert gaming harnesses. It is the bridge between:

- Cuebert **`/play`** and **`/asset`** harness phases (main-chat coordinators per `agent-play.md` and `agent-asset.md`), and  
- The **`unreal-bridge`** MCP toolkit (health, presets, describe, ping in **M5-P1**; writes **M5-P4**).

**Single source of truth for:**

- **HTTP connection management** — base URL resolution, mode (`live` / `dry_run` / `auto`), timeouts, and size caps per **`unreal-bridge/SKILL.md`** and **`reference.md`**.  
- **Scope enforcement** — which **`op_kind`** values are legal for which **`caller`** identities **before** any write is attempted (see §6).  
- **Dry-run fallback** — when the editor is unreachable and policy is **`auto`**, the bridge **does not** pretend a write occurred; it returns a **`dry_run`** envelope consistent with toolkit fixtures.  
- **Result normalization** — one stable **`agent-unreal`** envelope shape so `/play` and `/asset` phases do not each invent Remote Control JSON parsing rules (UE minor version differences stay inside the toolkit).

**Does NOT:**

- Take **user chat** commands directly (no **`/unreal`** shortcut; see `.cursor/rules/cuebert-supervisor.mdc` bridge dispatch note).  
- **Mutate `.uasset` bytes on disk** from cuebert — the engine owns content; cuebert issues **preset-scoped** Remote Control operations only.  
- **Coordinate multiple editors** — one **`base_url`** target per invocation; multi-workstation orchestration is out of scope for **M5**.

---

## 1. Relationship to `/play` and `/asset`

| Harness phase | Typical `agent-unreal` role | Example |
|---------------|----------------------------|---------|
| `/play` pre-author guards | **probe** | Confirm editor running before authoring change (`unreal_health_check` semantics). |
| `/play` author | **probe** | Verify target actor exists in preset (`ping_actor`, `describe_preset`). |
| `/play` preview | **mutate** | Call **`PIE.StartPlay()`**-class exposed **`UFunction`** (**M5-P4** implements HTTP PUT path). |
| `/play` post-preview | **probe** | Pull editor log status (**future**; not defined in **M5-P3**). |
| `/asset` post-place | **mutate** | Call reimport-style **`UFunction`** on newly placed PNGs under **`Content/`** (**M5-P4**). |
| `/asset` post-generate | **probe** | Confirm destination path is visible to UE content/registry views where deterministically probe-able (`describe_preset` / metadata — exact probe **M5+**). |

**Orchestration rule:** Harnesses MUST NOT spawn **multiple** concurrent `agent-unreal` **mutate** operations against the same **`base_url`** in one session tick; Epic’s Remote Control is effectively **single-threaded** on the editor side. Serialize mutations at the harness level.

---

## 2. Phase chain (internal)

Every `agent-unreal` invocation is a **single operation** — no multi-step chain like `/ship`.

```text
validate_scope → connect (or dry-run) → execute (probe OR mutate) → normalize → emit envelope
```

- **`validate_scope`** — reject illegal **`caller` + `op_kind`** pairs **before** network I/O (§6).  
- **`connect (or dry-run)`** — honor **`CUEBERT_UNREAL_MODE`** and toolkit defaults (**§7**).  
- **`execute`** — delegate to **`agent-unreal-probe`** or **`agent-unreal-mutate`** protocol (**§3**).  
- **`normalize`** — map toolkit JSON into **`agent-unreal`** envelope (**§5**, **§12**).  
- **`emit envelope`** — return structured result to caller; append **`mutation_audit`** when applicable (**§8**).

---

## 3. Subagent roster

| Subagent | File | Role | Status |
|----------|------|------|--------|
| **`agent-unreal-probe`** | `docs/_ai_system/agents/agent-unreal-probe.md` | Read-only HTTP **GET**-backed MCP calls: **`list_presets`**, **`describe_preset`**, **`ping_actor`** | **M5-P3** spec; **live** calls via **`unreal_list_presets`**, **`unreal_describe_preset`**, **`unreal_ping_actor`**, plus **`unreal_health_check`** for connectivity/version |
| **`agent-unreal-mutate`** | `docs/_ai_system/agents/agent-unreal-mutate.md` | Write HTTP **PUT**-backed operations: **`set_property`**, **`call_function`** | **M5-P3 SPEC ONLY**; MCP tools **`unreal_set_property`**, **`unreal_call_function`** land **M5-P4** |

**Dispatch pattern:** The **`/play`** or **`/asset`** harness (main chat) treats `agent-unreal` as a **logical coordinator**: one **`generalPurpose`** Task MAY implement both “routing” and probe execution in early milestones, but **mutations** MUST remain behind **`agent-unreal-mutate.md`** rules once writes exist (**M5-P4**).

---

## 4. Inputs

Harnesses construct a **request object** (fields below). Names are **stable** for future JSON wiring.

| Field | Required | Description |
|-------|----------|-------------|
| **`operation`** | Yes | **`probe`** or **`mutate`**. |
| **`caller`** | Yes | One of: **`agent-play-author`**, **`agent-play-preview`**, **`agent-asset-generate`**, **`agent-asset-place`**, **`user-direct-debug`**. |
| **`op_kind`** | Yes | One of: **`list_presets`**, **`describe_preset`**, **`ping_actor`**, **`set_property`**, **`call_function`**. Must match **`operation`** (probe kinds vs mutate kinds). |
| **`args`** | Yes | Operation-specific map (preset name, actor label, property name, function name, payloads — see subagent docs). |
| **`scope`** | Yes | Must include **`preset_name`** when the op targets a preset; **`allowed_mutations`** is an **explicit list** required for **`mutate`** (see **`unreal-bridge-contract.md`** §2.2 and **`agent-unreal-mutate.md`** §11). |
| **`dry_run`** | No | **`auto`** (default), **`true`**, or **`false`**. **`auto`** means: attempt **live** per toolkit rules; if unreachable, fall back to **`dry_run`** with a **`warn`**-class finding in the envelope. |

**`user-direct-debug`:** Permitted **only** when the active harness plan sets **`debug.agent_unreal: true`**; otherwise the coordinator returns **`status: "blocked"`** (`unreal.scope_rejected`).

---

## 5. Outputs (summary)

Top-level **`agent-unreal`** envelope (conceptual JSON; full field types in §12):

| Field | Description |
|-------|-------------|
| **`status`** | **`pass`**, **`dry_run`**, **`error`**, or **`blocked`**. |
| **`operation`** | Echo **`probe`** or **`mutate`**. |
| **`op_kind`** | Echo stable op id. |
| **`result`** | Toolkit-normalized payload (preset list, describe body, ping body, or mutation summary). |
| **`mode`** | **`live`** or **`dry_run`**. |
| **`base_url`** | Resolved Remote Control base URL string. |
| **`editor_version`** | From **`unreal_health_check`** / describe path, or **`5.x.x-dry_run`** synthetic. |
| **`mutation_audit`** | Non-null only for **`mutate`** successes (includes **`dry_run`** accepted mutations per §8). |
| **`error`** | **`null`** or **`{ "code": "...", "message": "..." }`**. |
| **`elapsed_ms`** | Integer wall time for the op (connect + request + normalize). |

---

## 6. Scope enforcement

The coordinator evaluates the **caller × op_kind** whitelist **before** any write and **before** delegating to mutate protocol paths.

**Narrative rules (normative):**

- **`agent-play-author`** — may **`set_property`** only on **preset-exposed** fields (no arbitrary object paths outside the preset contract). May run **probe** ops needed to validate targets.  
- **`agent-play-preview`** — may **`call_function`** only on **preset-exposed** functions (e.g. PIE launch helpers). May run **probes** before/after.  
- **`agent-asset-generate`** — **read-only** at the Unreal bridge layer: **probe** ops only; **mutations** are **`blocked`**.  
- **`agent-asset-place`** — may **`call_function`** for **reimport**-class operations **scoped** to the project’s **`Content/`** tree and manifest-declared destinations; may run **probes**.  
- **`user-direct-debug`** — when **`debug.agent_unreal: true`**, all **`op_kind`** values in the matrix below are allowed; harness MUST still attach **`scope`** and expect **`mutation_audit`** on writes.

**Scope violations** (`caller` not whitelisted, or **`op_kind`** not allowed): return **`status: "blocked"`**, **`error.code: "unreal.scope_rejected"`**, and emit a **`troubleshoot_commit`** memory entry (§13) with the denied tuple and envelope excerpt — **mandatory**.

### 6.1 Scope whitelist matrix (5 × 5, default-deny)

Rows are **`caller`**; columns are **`op_kind`**. **`true`** means the coordinator **may** dispatch the op to the appropriate subagent when other guards pass; **`false`** means **`blocked`** without network I/O for mutations, and **immediate rejection** for illegal mutate kinds.

| caller \ op_kind | `list_presets` | `describe_preset` | `ping_actor` | `set_property` | `call_function` |
|------------------|----------------|-------------------|--------------|----------------|-----------------|
| **`agent-play-author`** | true | true | true | true | false |
| **`agent-play-preview`** | true | true | true | false | true |
| **`agent-asset-generate`** | true | true | true | false | false |
| **`agent-asset-place`** | true | true | true | false | true |
| **`user-direct-debug`** | true | true | true | true | true |

**`user-direct-debug` precondition:** The row above applies **only** when the active harness plan sets **`debug.agent_unreal: true`**. If the flag is **false** or absent, treat **every** cell as **`false`** (all ops **`blocked`** at coordinator ingress).

**Default-deny semantics:** Any **`caller`** not listed above is **`blocked`**. Any **`op_kind`** not listed is **`blocked`**. **`mutate`** operations additionally require **`scope.allowed_mutations`** to explicitly list the mutation intent key (see **`unreal-bridge-contract.md`**).

---

## 7. Dry-run semantics

**Inherited from `unreal-bridge`:**

- **`CUEBERT_UNREAL_MODE=dry_run`** → coordinator and toolkit stay in **`dry_run`**; probes return **synthetic fixtures**; mutates are **accepted** per §8 without real HTTP **PUT** (**M5-P4** implements PUT).  
- **`CUEBERT_UNREAL_MODE=live`** → **live** only; unreachable editor → **`unreal.unreachable`** (or timeout taxonomy) — **no silent fallback**.  
- **Default unset (`auto` request field)** → toolkit **`auto`** behavior: attempt **live** when configured; if unreachable, **`dry_run`** fallback with a **`warn`** finding attached to the envelope (`mode: dry_run`, `status: dry_run` or `pass` per harness policy — see **`unreal-bridge-contract.md`** §5).

**When `mode` is `dry_run`:**

- **Probes** return synthetic fixtures from **`unreal-bridge`** (preset counts, example properties/functions, ping **`found: true`** shapes).  
- **Mutates** (**M5-P4+**) record **`mutation_audit`** with **`mode: dry_run`** and **do not** send HTTP **PUT**.

---

## 8. Mutation audit

Every **successful** mutation path (**live** or **`dry_run`**) produces one **`mutation_audit`** object attached to the envelope and appended as one JSON line to:

```text
.cuebert/traces/unreal/<timestamp>/mutations.jsonl
```

**Shape (conceptual):**

```json
{
  "timestamp": "2026-04-20T12:00:00Z",
  "caller": "agent-play-author",
  "op_kind": "set_property",
  "preset": "ExamplePreset",
  "object_path": "/Game/.../Actor_0",
  "property": "Brightness",
  "from": 0.5,
  "to": 0.7,
  "mode": "live",
  "editor_version": "5.4.0",
  "reversal_hint": "set Brightness=0.5 on same path"
}
```

**Memory:** **`troubleshoot_commit`** with the audit row text (or structured summary) is **mandatory** for successful **`mutate`** completions and for **`blocked`** scope violations — **not** **`milestone_commit`** (mutations are **operational**, not milestone markers). Harness-level success still uses **`milestone_commit`** per **`agent-asset.md`** / future **`/play`** memory policy.

---

## 9. Guard integration

`agent-unreal` is invoked **around** existing harness guards; it **does not** define new guard rows in **M5-P3**.

**Authoritative guard catalogs:**

- **`docs/_ai_system/standards/play-preview-guards.md`** — `/play` Preview Guards (**M2-P3** contract; evaluators **M5–M6**).  
- **`docs/_ai_system/standards/asset-pipeline-guards.md`** — `/asset` pipeline guards (**M4-P3** contract).

**Future guard ids (non-normative until evaluators ship):**

- **`guard.unreal.reachable`** — pre-mutation **probe** requirement.  
- **`guard.unreal.scope_violation`** — post-op audit consistency check.

---

## 10. Connection reuse

The bridge agent **does not** pool HTTP connections. Each invocation **opens and closes** the HTTP client inside the **`unreal-bridge`** tool implementation.

**Rationale:**

- Keeps **`dry_run`** and **`live`** semantics easy to reason about (no stale pooled sockets).  
- Remote Control is **single-threaded** on the editor side for many operations; parallelism wins are minimal.  
- Timeouts are **bounded** (≤ **30 s** per **M5-P1**).

**Future:** **M5-P4+** *may* add optional pooling; deferred.

---

## 11. Error taxonomy

Stable **`error.code`** values (string API):

| Code | Meaning |
|------|---------|
| **`unreal.unreachable`** | Connection refused, DNS failure, or connect timeout. |
| **`unreal.plugin_missing`** | **`/remote/info`** reachable but Remote Control metadata/plugins not as expected. |
| **`unreal.preset_not_found`** | Preset absent for describe/mutate. |
| **`unreal.scope_rejected`** | Caller not allowed for **`op_kind`**, or **`user-direct-debug`** without debug flag. |
| **`unreal.property_not_found`** | Mutation target property not exposed / not found (**M5-P4**). |
| **`unreal.validation_failed`** | UE rejected mutation (range, type, or Remote Control validation). |
| **`unreal.timeout`** | Operation exceeded configured cap (**≤ 30 s** hard ceiling). |
| **`unreal.unexpected`** | Catch-all for parser/internal failures. |

---

## 12. Outputs: envelope shape (full)

**`protocol_version`:** **`"1.0"`** for **M5-P3** — bump **major** on breaking field removals or type changes.

| Field | JSON type | Nullability | Notes |
|-------|-----------|-------------|-------|
| **`protocol_version`** | string | non-null | **`"1.0"`** |
| **`status`** | string | non-null | **`pass`**, **`dry_run`**, **`error`**, **`blocked`** |
| **`operation`** | string | non-null | **`probe`** \| **`mutate`** |
| **`op_kind`** | string | non-null | Mirrors request |
| **`result`** | object | non-null | May be empty object on some errors |
| **`mode`** | string | non-null | **`live`** \| **`dry_run`** |
| **`base_url`** | string | non-null | Resolved URL |
| **`editor_version`** | string | non-null | Includes **`-dry_run`** suffix when synthetic |
| **`mutation_audit`** | object | nullable | **`null`** unless **`mutate`** success path |
| **`error`** | object | nullable | **`null`** on success; else **`{ code, message }`** |
| **`elapsed_ms`** | number | non-null | Integer milliseconds |
| **`findings`** | array | nullable | Optional **`warn`** / **`info`** entries (e.g. non-localhost URL warning) |

---

## 13. Memory hooks

| Event | Memory action |
|-------|----------------|
| **Probe success/failure** | **No** **`troubleshoot_commit`** by default (too chatty). |
| **Mutate success** (**live** or **`dry_run`**) | **`troubleshoot_commit`** with **`mutation_audit`** — **mandatory**. |
| **Scope violation** | **`troubleshoot_commit`** with **`blocked`** tuple — **mandatory**. |
| **Session end** | Parent harness owns **`milestone_commit`** policy (`/asset` full success requires milestone per **`agent-asset.md`**). |

---

## 14. Engine support

**M5** targets **Unreal Engine 5.0+** for this bridge. **Unity** and **Godot** require **separate** bridge toolkits (**future M7** scope); **`agent-unreal`** MUST NOT pretend to drive them.

---

## 15. Non-goals

| Non-goal | Reason |
|----------|--------|
| **Multi-user CRDT-style editing** | Remote Control is not a collaborative editing protocol. |
| **Undo/redo orchestration** | UE’s editor undo stack exists, but cuebert does not drive it from here. |
| **Arbitrary Blueprint graph edits** | Only **preset-exposed** surfaces. |
| **PIE input injection / gameplay driving** | **M6 Gauntlet** territory. |

---

## 16. Rollback

Rollback is **per-mutation** and **manual** at the harness level: **`reversal_hint`** in **`mutation_audit`** is advisory text for a **follow-up** `agent-unreal` call. The bridge **does not** auto-reverse successful mutations.

---

## 17. Security notes

**Inherited from `unreal-bridge/SKILL.md`:**

- **Localhost-by-default**; non-loopback hosts emit **`warn`** findings, not automatic **`blocked`**.  
- **No auth** on stock Remote Control — LAN isolation assumption.  
- **Preset names**, **actor labels**, and **object paths** are validated with **M5-P1** regex allow-lists before HTTP.  
- **Response size** capped at **10 MB**; **timeout** capped at **30 s**.

**Agent-level rails:**

- **§6 whitelist** before writes.  
- **§8 audit** for every mutation envelope path.  
- **§13** memory commits for violations and mutations.

### 17.1 MCP tool mapping (M5-P1)

Probe operations map **1:1** onto existing **`unreal-bridge`** Python tools under **`.cursor/skills/unreal-bridge/tools/`**:

| `op_kind` | MCP tool | Implementation file (hub) |
|-----------|----------|----------------------------|
| *(reachability stamp)* | **`unreal_health_check`** | **`unreal_health_check.py`** |
| **`list_presets`** | **`unreal_list_presets`** | **`unreal_list_presets.py`** |
| **`describe_preset`** | **`unreal_describe_preset`** | **`unreal_describe_preset.py`** |
| **`ping_actor`** | **`unreal_ping_actor`** | **`unreal_ping_actor.py`** |

Shared HTTP client logic lives in **`_unreal_client.py`**. **`agent-unreal`** MUST NOT fork parallel one-off HTTP stacks — always call MCP tools so caps, sanitization, and envelopes stay centralized.

### 17.2 Coordinator responsibilities vs toolkit responsibilities

| Concern | Owner |
|---------|-------|
| Regex allow-lists for names/paths | **`unreal-bridge`** client (**M5-P1**) |
| **Caller × op_kind** policy | **`agent-unreal`** coordinator (**M5-P3**) |
| **`allowed_mutations`** string grammar | **`agent-unreal-mutate.md`** §11; enforcement in **`unreal-bridge-contract.md`** §2.2 |
| **Synthetic fixtures** in **`dry_run`** | **`unreal-bridge`** tools |
| **Trace append** **`mutations.jsonl`** | **`agent-unreal`** coordinator (**M5-P4** executor) |
| **`troubleshoot_commit` / `milestone_commit`** policy | Coordinator + parent harness (**§13**) |

### 17.3 Task envelope sketch (harness → coordinator)

```text
## Cuebert agent-unreal — single op
**First action:** Read docs/_ai_system/agents/agent-unreal.md

CALLER: [agent-play-author | agent-play-preview | agent-asset-generate | agent-asset-place | user-direct-debug]
OPERATION: [probe | mutate]
OP_KIND: [list_presets | describe_preset | ping_actor | set_property | call_function]
ARGS: [JSON object — minimal, no secrets]
SCOPE: { preset_name, allowed_mutations[] }
DRY_RUN: [auto | true | false]
DEBUG_AGENT_UNREAL: [true|false]  # required true when CALLER=user-direct-debug
```

### 17.4 Illustrative success envelope (probe, dry_run)

```json
{
  "protocol_version": "1.0",
  "status": "dry_run",
  "operation": "probe",
  "op_kind": "list_presets",
  "result": { "preset_count": 3, "presets": [{ "name": "ExamplePreset" }] },
  "mode": "dry_run",
  "base_url": "http://localhost:30010",
  "editor_version": "5.4.0-dry_run",
  "mutation_audit": null,
  "error": null,
  "elapsed_ms": 12,
  "findings": [{ "severity": "info", "message": "Synthetic preset list — no editor required." }]
}
```

### 17.5 Illustrative blocked envelope (scope)

```json
{
  "protocol_version": "1.0",
  "status": "blocked",
  "operation": "mutate",
  "op_kind": "set_property",
  "result": {},
  "mode": "live",
  "base_url": "http://localhost:30010",
  "editor_version": "5.4.0",
  "mutation_audit": null,
  "error": { "code": "unreal.scope_rejected", "message": "agent-asset-generate cannot set_property" },
  "elapsed_ms": 1,
  "findings": null
}
```

### 17.6 Negative examples (must REJECT)

- **`caller: agent-asset-generate`** with **`op_kind: set_property`** → **`blocked`** before any HTTP I/O.  
- **`caller: user-direct-debug`** when plan lacks **`debug.agent_unreal: true`** → **`blocked`**.  
- **`operation: mutate`** with empty **`scope.allowed_mutations`** → **`blocked`** (`unreal.scope_rejected`).  
- Parallel **`mutate`** Tasks against the same session **`base_url`** → harness policy violation; coordinator SHOULD return **`error`** / **`unreal.unexpected`** if it detects concurrent mutation tickets (**M5-P4** wire-up).

### 17.7 Relationship to `/asset` post-place reimport

`/asset` placement writes **PNG bytes** into **`Content/`**; Unreal may not hot-reload textures until a **reimport**-class function runs. **`agent-asset-place`** is whitelisted for **`call_function`** only for those **import-adjacent** functions, never arbitrary gameplay calls. Exact **function allow-list** strings land in **`unreal-bridge-contract.md`** and **M5-P4** toolkit docs.

### 17.8 Relationship to `/play` preview launch

`/play` Preview phase uses **`call_function`** for **preset-exposed** PIE helpers. Authoring phase uses **`set_property`** for **scalar** tuning on exposed properties. **Binary asset** writes remain **`agent-play-author`** disk operations — **`agent-unreal`** never writes **`.uasset`** bytes.

---

## 18. Cross-references

| Doc | Relationship |
|-----|----------------|
| `.cursor/skills/unreal-bridge/SKILL.md` | Toolkit entry, tool table, dry-run + security |
| `.cursor/skills/unreal-bridge/reference.md` | Per-tool envelopes and fields |
| `docs/_ai_system/agents/agent-unreal-probe.md` | Probe subagent protocol |
| `docs/_ai_system/agents/agent-unreal-mutate.md` | Mutate subagent (**SPEC ONLY** **M5-P3**) |
| `docs/_ai_system/standards/unreal-bridge-contract.md` | Protocol contract + matrix duplicate |
| `docs/_ai_system/agents/agent-play.md` | `/play` harness coordinator |
| `docs/_ai_system/agents/agent-asset.md` | `/asset` harness coordinator |
| `docs/_ai_system/standards/play-preview-guards.md` | `/play` guard catalog |
| `docs/_ai_system/standards/asset-pipeline-guards.md` | `/asset` guard catalog |

---

## 19. Footer

Status: **M5-P3** (coordinator + **`agent-unreal-probe`** spec + **`agent-unreal-mutate`** **SPEC ONLY**). **Live writes:** **M5-P4**. **Multi-engine bridge:** future.
