# Unreal bridge sample run: hello-level lighting and PIE preview

**Project**: `hello-level` (Unreal 5.4 sample project)  
**Mode**: `dry_run` (default when `CUEBERT_UNREAL_BASE_URL` is unset and vault has no `unreal.base_url`; or `CUEBERT_UNREAL_MODE=dry_run`)  
**Plan file**: *(hypothetical)* `/play` harness plan invoking `agent-unreal-mutate` twice  
**Trace dir**: `.cuebert/traces/unreal/example-2026-04-20T14-00-00Z/`  
**Commit**: M5-P4 worked example

Normative coordinator: [`docs/_ai_system/agents/agent-unreal.md`](../agents/agent-unreal.md). Mutate subagent: [`agent-unreal-mutate.md`](../agents/agent-unreal-mutate.md). Contract: [`unreal-bridge-contract.md`](../standards/unreal-bridge-contract.md). MCP skill: [`.cursor/skills/unreal-bridge/SKILL.md`](../../../.cursor/skills/unreal-bridge/SKILL.md). Preset fixture: [`.cursor/skills/unreal-bridge/presets/hello-level-example.json`](../../../.cursor/skills/unreal-bridge/presets/hello-level-example.json).

---

## 1. Purpose

This document is a **documentation-only dry run** that walks **`agent-unreal`** mutate operations end-to-end using the **`unreal-bridge`** MCP tools, with **no live Unreal Editor** HTTP when mode resolves to **`dry_run`**. **No Cursor Tasks run.** All JSON envelopes and trace paths are **illustrative** but aligned with:

- [`agent-unreal.md`](../agents/agent-unreal.md) (§6 scope matrix, §7 dry-run, §8 mutation audit, §12 envelope, §13 `troubleshoot_commit`)
- [`agent-unreal-mutate.md`](../agents/agent-unreal-mutate.md) (§4 scope table, §7 protocol, §9 failure modes)
- [`unreal-bridge-contract.md`](../standards/unreal-bridge-contract.md) (§2 matrix, §4 error catalog including `unreal.put_rejected` and `unreal.readback_failed`, §6 audit schema)

Use this file as the **M5 integration narrative**: scope enforcement at the MCP tool layer, **`mutation_audit`** rows, **`troubleshoot_commit`** hooks, and committed trace fixtures before **M6** build and Gauntlet work.

---

## 2. Scenario setup

### 2.1 Project

| Field | Value |
|-------|-------|
| **Project key** | `hello-level` |
| **Engine** | Unreal Engine **5.4** (hypothetical sample) |
| **Remote Control** | Preset **`hello_level_preset`** exposes five scalar properties and two functions (see preset JSON). |

### 2.2 Scenario

The team is iterating on **level lighting** for a hero shot. An author wants the key **point light intensity** at **75** before a preview. A separate preview step starts **PIE** via an exposed **`StartPIE`** function on a controller blueprint.

Two Cuebert operations are traced in one session:

1. **`agent-play-author`** calls **`unreal_set_property`** with **`preset_name=hello_level_preset`**, **`object_path`** for **`PointLight_0`**, **`property_name=Intensity`**, **`value=75.0`**.
2. **`agent-play-preview`** calls **`unreal_call_function`** with **`function_name=StartPIE`** on **`BP_PIEController_C`**.

Both run in **`dry_run`**: toolkit **`_get_mode()`** returns **`dry_run`** because Unreal is not explicitly configured for live HTTP in this narrative (mirrors default hub developer laptop).

### 2.3 Success criteria (Unreal mutate harness)

- **`unreal_set_property`**: **`status: dry_run`**, **`value_from: null`**, **`value_to: 75.0`**, non-null **`mutation_audit`**, **`troubleshoot_commit`** recorded (or skipped gracefully if memory MCP unavailable).  
- **`unreal_call_function`**: **`status: dry_run`**, synthetic **`return_value: true`**, **`mutation_audit.reversal_hint: null`**, memory hook same as above.  
- **`mutations.jsonl`**: exactly **two** lines, schema per contract §6.  
- **Scope**: first op whitelists **`agent-play-author`** for **`set_property`**; second op whitelists **`agent-play-preview`** for **`call_function`**.

### 2.4 Workspace manifest fragment

```json
{
  "projects": {
    "hello-level": {
      "path": "/abs/path/hello-level",
      "engine": "unreal",
      "engineVersion": "5.4.0"
    }
  }
}
```

### 2.5 Preset descriptor (excerpt)

Full file: **`.cursor/skills/unreal-bridge/presets/hello-level-example.json`**. Excerpt:

```json
{
  "Preset": {
    "Name": "hello_level_preset",
    "Path": "/Game/Presets/hello_level_preset.hello_level_preset"
  },
  "ExposedProperties": [
    {
      "ObjectPath": "/Game/Maps/HelloLevel.HelloLevel:PersistentLevel.PointLight_0",
      "PropertyName": "Intensity",
      "ExposedName": "hero_light_intensity",
      "Type": "float"
    }
  ],
  "ExposedFunctions": [
    {
      "ObjectPath": "/Game/Blueprints/BP_PIEController.BP_PIEController_C",
      "FunctionName": "StartPIE",
      "ExposedName": "start_pie",
      "ReturnType": "bool"
    }
  ]
}
```

### 2.6 Harness invocation (pseudo)

```text
/play --plan docs/projects/hello-level/plans/play/2026-04-20-lighting-preview.md
```

The **`/play`** coordinator dispatches **`agent-unreal`** twice with **`operation: mutate`**, passing **`caller`**, **`op_kind`**, **`args`**, and **`scope.allowed_mutations`** per **`agent-unreal-mutate.md`**. MCP tools receive the **`caller`** string as their **`caller`** parameter (default **`user-direct-debug`** only for direct Cursor debugging; harnesses pass explicit identities).

---

## 3. Harness timeline (happy path)

Ordered narrative matches **`agent-unreal.md`** §2 and **`agent-unreal-mutate.md`** §7.

1. **`/play`** dispatches **`agent-unreal-mutate`** with **`op_kind=set_property`**, **`caller=agent-play-author`**, **`scope.allowed_mutations`** containing **`set_property:Intensity`** (grammar per **`agent-unreal-mutate.md`** §11).  
2. **`agent-unreal.md`** §6.1 matrix: **`(agent-play-author, set_property) = true`** at coordinator ingress.  
3. **`unreal_set_property`** MCP tool re-checks caller against its whitelist (**`agent-play-author`**, **`user-direct-debug`** only for **`set_property`** — **`agent-play-preview`** remains **denied** for property writes per matrix).  
4. Mode resolution via **`_get_mode()`** yields **`dry_run`** (no explicit live URL in env or vault).  
5. Tool skips HTTP **GET**/**PUT**; synthesizes **`value_from=null`**, **`value_to=75.0`**.  
6. **`mutation_audit`** object is built with **`audit_status: ok`**, **`reversal_hint`** text for manual undo guidance.  
7. **`append_mutation_line`** writes one JSON line under **`.cuebert/traces/unreal/<timestamp>/mutations.jsonl`**.  
8. **`troubleshoot_commit_safe`** runs (inline **`try`** semantics inside helper: failures log to **stderr**, do not fail the tool).  
9. Tool envelope returns **`status: dry_run`**.  
10. Later, **`/play`** dispatches **`op_kind=call_function`**, **`caller=agent-play-preview`**, **`allowed_mutations`** includes **`call_function:StartPIE`**.  
11. Matrix: **`(agent-play-preview, call_function) = true`**.  
12. **`unreal_call_function`** whitelist accepts **`agent-play-preview`**, **`agent-asset-place`**, **`user-direct-debug`**.  
13. **`dry_run`**: synthetic **`return_value=true`**; audit line appended; **`troubleshoot_commit`** fires.  
14. Second envelope **`status: dry_run`**.  
15. Session rollup **`envelope.json`** records both ops (see committed trace).

Each subsection below references the **on-disk** fixtures where bytes matter.

---

### 3.0 Expanded chronology (operator transcript)

The following **numbered log** is what a harness transcript might show if it echoed coordinator decisions in order. It is **not** executable shell; it ties the same two MCP calls to guard semantics and disk artifacts.

1. Coordinator receives **`/play`** envelope **`protocol_version: 1.0`**, **`operation: mutate`**, **`op_kind: set_property`**.  
2. Validates **`scope.preset_name`** present; rejects at **`blocked`** if missing (**`unreal.scope_rejected`**).  
3. Validates **`scope.allowed_mutations`** non-empty; rejects if empty per **`agent-unreal-mutate.md`** §7.1.  
4. Confirms token **`set_property:Intensity`** (or property name token policy the harness chose) appears in the list.  
5. **`debug.agent_unreal`** gate: irrelevant for **`agent-play-author`** (only **`user-direct-debug`** row depends on the flag at coordinator ingress).  
6. Dispatches MCP **`unreal_set_property`** with **`caller=agent-play-author`**.  
7. Tool validates **`preset_name`** against **`^[A-Za-z0-9_.-]{1,128}$`**.  
8. Tool validates **`object_path`** against **`^[A-Za-z0-9_./-]{1,512}$`**.  
9. Tool validates **`property_name`** against **`^[A-Za-z][A-Za-z0-9_]{0,127}$`**.  
10. Tool validates **`value`** depth, list length, string length, JSON size caps via **`validate_mutation_value`**.  
11. **`_get_mode()`** returns **`dry_run`**; **`health_probe`** is **not** required for the mutate body path in **`dry_run`** (tool short-circuits before **`health_probe`** in current implementation).  
12. Tool builds **`mutation_audit`** with ISO **`timestamp`**, synthetic **`editor_version`**.  
13. Tool appends **`mutations.jsonl`** under a fresh **`mutation_trace_timestamp()`** directory stamp.  
14. Tool calls **`troubleshoot_commit_safe`**; fixture simulates success id **`11111111-...5501`**.  
15. Tool returns envelope; harness writes **`set_property/envelope.json`** snapshot for this worked example.  
16. Coordinator receives second envelope **`op_kind: call_function`**, **`caller: agent-play-preview`**.  
17. Matrix cell **`call_function`** is **true** for preview.  
18. MCP **`unreal_call_function`** validates **`function_name`** regex same as property identifier style.  
19. **`args`** defaults to **`{}`**; **`validate_parameters_dict`** treats empty dict as valid.  
20. **`dry_run`** branch sets synthetic **`return_value: true`** and audit **`to: true`** (return captured in audit for trace readability).  
21. Second **`mutations.jsonl`** line appended.  
22. Second **`troubleshoot_commit`** fixture id ends **`...5502`** in the paired **`memory/call_function_commit.json`**.  
23. **`guards/pre_op.json`** records both whitelist checks in one file for compact harness tests.  
24. **`guards/post_op.json`** records **`guard.audit.persisted`** for both ops.  
25. Root **`envelope.json`** sets **`mutation_count: 2`**, **`memory_commits: 2`**, **`completed_at`** after the second op.

---

### 3.1 Step — Scope guard (`set_property`)

**Actor:** harness guard + MCP tool ingress.  
**Fixture:** `.cuebert/traces/unreal/example-2026-04-20T14-00-00Z/scope_check/set_property.json` (caller, **`op_kind`**, matrix row, **`allow: true`**).  
**Also:** `.cuebert/traces/unreal/example-2026-04-20T14-00-00Z/guards/pre_op.json` aggregates **`guard.scope.whitelist`** rows for both ops; both **`verdict: pass`**.

---

### 3.2 Step — `unreal_set_property` (dry run)

**Actor:** `unreal_set_property` (FastMCP).  
**Representative output:** `.cuebert/traces/unreal/example-2026-04-20T14-00-00Z/set_property/envelope.json` (canonical on-disk bytes).  
**Next:** memory + **`mutations.jsonl`** line 1.

---

### 3.3 Step — `troubleshoot_commit` (`set_property`)

**Actor:** `memory-toolkit` via **`troubleshoot_commit_safe`** indirection.  
**Fixture:** `.cuebert/traces/unreal/example-2026-04-20T14-00-00Z/memory/set_property_commit.json` — simulated return envelope (**`status: ok`**, synthetic **`id`**).

---

### 3.4 Step — `unreal_call_function` (dry run)

**Actor:** `unreal_call_function`.  
**Fixture:** `.cuebert/traces/unreal/example-2026-04-20T14-00-00Z/call_function/envelope.json`.

---

### 3.5 Step — `troubleshoot_commit` (`call_function`)

**Fixture:** `.cuebert/traces/unreal/example-2026-04-20T14-00-00Z/memory/call_function_commit.json`.

---

### 3.6 Step — Post-op guards

**Fixture:** `.cuebert/traces/unreal/example-2026-04-20T14-00-00Z/guards/post_op.json` — **`guard.audit.persisted`** for both ops, **`verdict: pass`**.

---

### 3.7 Step — Session rollup

**Fixture:** `.cuebert/traces/unreal/example-2026-04-20T14-00-00Z/envelope.json` — protocol version, **`mutation_count: 2`**, **`memory_commits: 2`**, **`findings: []`**.

---

## 4. Envelopes (full reference shapes)

### 4.1 `unreal_set_property` (dry run)

Canonical: **`set_property/envelope.json`**. Inline copy:

```json
{
  "status": "dry_run",
  "operation": "mutate",
  "op_kind": "set_property",
  "caller": "agent-play-author",
  "preset_name": "hello_level_preset",
  "object_path": "/Game/Maps/HelloLevel.HelloLevel:PersistentLevel.PointLight_0",
  "property_name": "Intensity",
  "value_from": null,
  "value_to": 75.0,
  "base_url": "http://localhost:30010",
  "mode": "dry_run",
  "editor_version": "5.4.0-dry_run",
  "mutation_audit": {
    "timestamp": "2026-04-20T14:00:00Z",
    "caller": "agent-play-author",
    "op_kind": "set_property",
    "preset": "hello_level_preset",
    "object_path": "/Game/Maps/HelloLevel.HelloLevel:PersistentLevel.PointLight_0",
    "property": "Intensity",
    "from": null,
    "to": 75.0,
    "mode": "dry_run",
    "editor_version": "5.4.0-dry_run",
    "reversal_hint": "best-effort: set Intensity back to prior value on /Game/Maps/HelloLevel.HelloLevel:PersistentLevel.PointLight_0",
    "audit_status": "ok"
  },
  "error": null,
  "elapsed_ms": 4
}
```

### 4.2 `unreal_call_function` (dry run)

Canonical: **`call_function/envelope.json`**. Inline copy:

```json
{
  "status": "dry_run",
  "operation": "mutate",
  "op_kind": "call_function",
  "caller": "agent-play-preview",
  "preset_name": "hello_level_preset",
  "object_path": "/Game/Blueprints/BP_PIEController.BP_PIEController_C",
  "function_name": "StartPIE",
  "args": {},
  "return_value": true,
  "base_url": "http://localhost:30010",
  "mode": "dry_run",
  "editor_version": "5.4.0-dry_run",
  "mutation_audit": {
    "timestamp": "2026-04-20T14:00:05Z",
    "caller": "agent-play-preview",
    "op_kind": "call_function",
    "preset": "hello_level_preset",
    "object_path": "/Game/Blueprints/BP_PIEController.BP_PIEController_C",
    "function": "StartPIE",
    "from": null,
    "to": true,
    "mode": "dry_run",
    "editor_version": "5.4.0-dry_run",
    "reversal_hint": null,
    "audit_status": "ok"
  },
  "error": null,
  "elapsed_ms": 3
}
```

### 4.3 `mutations.jsonl` (two lines)

```json
{"timestamp":"2026-04-20T14:00:00Z","caller":"agent-play-author","op_kind":"set_property","preset":"hello_level_preset","object_path":"/Game/Maps/HelloLevel.HelloLevel:PersistentLevel.PointLight_0","property":"Intensity","from":null,"to":75.0,"mode":"dry_run","editor_version":"5.4.0-dry_run","reversal_hint":"best-effort: set Intensity back to prior value on /Game/Maps/HelloLevel.HelloLevel:PersistentLevel.PointLight_0","audit_status":"ok"}
```

```json
{"timestamp":"2026-04-20T14:00:05Z","caller":"agent-play-preview","op_kind":"call_function","preset":"hello_level_preset","object_path":"/Game/Blueprints/BP_PIEController.BP_PIEController_C","function":"StartPIE","from":null,"to":true,"mode":"dry_run","editor_version":"5.4.0-dry_run","reversal_hint":null,"audit_status":"ok"}
```

*(In the committed **`.jsonl`**, these appear as a single line each, no wrapping.)*

### 4.4 Preset snapshot

**`preset_snapshot.json`** duplicates **`hello-level-example.json`** at the time of the simulated run for diff-stable docs.

---

### 4.5 Fixture crosswalk (committed bytes)

The subsections below duplicate **small** committed JSON so readers can **`diff`** narrative drift. Canonical source remains the trace directory on disk.

#### 4.5.1 `scope_check/set_property.json`

```json
{
  "op_kind": "set_property",
  "caller": "agent-play-author",
  "matrix_reference": "docs/_ai_system/agents/agent-unreal.md §6.1",
  "cell": {"caller": "agent-play-author", "set_property": true},
  "allow": true,
  "reason": "Matrix row allows set_property for agent-play-author"
}
```

#### 4.5.2 `scope_check/call_function.json`

```json
{
  "op_kind": "call_function",
  "caller": "agent-play-preview",
  "matrix_reference": "docs/_ai_system/agents/agent-unreal.md §6.1",
  "cell": {"caller": "agent-play-preview", "call_function": true},
  "allow": true,
  "reason": "Matrix row allows call_function for agent-play-preview"
}
```

#### 4.5.3 `guards/pre_op.json`

```json
{
  "guard": {
    "scope": {
      "whitelist": [
        {
          "guard_id": "guard.scope.whitelist",
          "operation": "mutate",
          "op_kind": "set_property",
          "caller": "agent-play-author",
          "verdict": "pass"
        },
        {
          "guard_id": "guard.scope.whitelist",
          "operation": "mutate",
          "op_kind": "call_function",
          "caller": "agent-play-preview",
          "verdict": "pass"
        }
      ]
    }
  }
}
```

#### 4.5.4 `guards/post_op.json`

```json
{
  "guard": {
    "audit": {
      "persisted": [
        {
          "guard_id": "guard.audit.persisted",
          "op_kind": "set_property",
          "mutations_jsonl": true,
          "verdict": "pass"
        },
        {
          "guard_id": "guard.audit.persisted",
          "op_kind": "call_function",
          "mutations_jsonl": true,
          "verdict": "pass"
        }
      ]
    }
  }
}
```

#### 4.5.5 `memory/set_property_commit.json`

```json
{
  "status": "ok",
  "id": "11111111-2222-4333-8444-555555555501",
  "tool": "troubleshoot_commit",
  "problem": "unreal_set_property dry_run accepted",
  "tags": "unreal-bridge,set_property,dry_run",
  "agent": "unreal_set_property",
  "record_date": "2026-04-20"
}
```

#### 4.5.6 `memory/call_function_commit.json`

```json
{
  "status": "ok",
  "id": "11111111-2222-4333-8444-555555555502",
  "tool": "troubleshoot_commit",
  "problem": "unreal_call_function dry_run accepted",
  "tags": "unreal-bridge,call_function,dry_run",
  "agent": "unreal_call_function",
  "record_date": "2026-04-20"
}
```

#### 4.5.7 `findings.json`

```json
{
  "findings": []
}
```

---

## 5. Failure variants

Each variant assumes the same scenario as §2 until the failure point.

---

### 5.A Read-only caller attempts `set_property` (`agent-asset-generate`)

**Trigger:** **`caller=agent-asset-generate`** (probe-only row in §6.1 matrix) attempts **`unreal_set_property`**.

**Tool path:** MCP whitelist rejects before HTTP.

**Envelope excerpt:**

```json
{
  "status": "blocked",
  "operation": "mutate",
  "op_kind": "set_property",
  "caller": "agent-asset-generate",
  "error": {
    "code": "unreal.scope_rejected",
    "message": "caller 'agent-asset-generate' is not allowed for set_property"
  },
  "mutation_audit": null
}
```

**Memory:** **`troubleshoot_commit_safe`** still runs with a **scope violation** payload per **`agent-unreal.md`** §6 narrative.

---

### 5.B Live mode, Remote Control unavailable (pre-read)

**Trigger:** **`CUEBERT_UNREAL_MODE=live`**, editor up but **`/remote/object/property`** **GET** fails (for example **404** or connection error) **before** **PUT**.

**Tool path:** **`unreal_set_property`** returns **`status: error`**, **`no PUT`** attempted. Typical code **`unreal.property_not_found`** or **`unreal.unreachable`** depending on transport vs HTTP body (contract §4). Variant narratives that cite **`unreal.plugin_missing`** apply when **`/remote/info`** shows Remote Control plugins absent; the important invariant is **no silent write**.

---

### 5.C Live mode, **PUT** ok, post-read fails

**Trigger:** **`set_exposed_property`** returns **`ok: true`**, then **`get_exposed_property`** post-read fails (for example HTTP **500**).

**Tool path:** **`mutation_audit.audit_status: partial_success`**, **`reversal_hint`** uses pre-read snapshot, envelope **`status: error`**, **`error.code: unreal.readback_failed`** per **`agent-unreal-mutate.md`** §9.

**Envelope excerpt:**

```json
{
  "status": "error",
  "op_kind": "set_property",
  "value_from": 42.0,
  "value_to": null,
  "mutation_audit": {
    "audit_status": "partial_success",
    "from": 42.0,
    "to": null,
    "reversal_hint": "best-effort: set Intensity back to 42.0 on /Game/Maps/HelloLevel.HelloLevel:PersistentLevel.PointLight_0"
  },
  "error": {
    "code": "unreal.readback_failed",
    "message": "post-read failed after successful PUT"
  }
}
```

---

### 5.D **PUT** rejected or UE **`errors`** array

**Trigger:** Remote Control returns **4xx**/**5xx**, or **200** with an **`errors`** array in the JSON body.

**Tool path:** **`error.code: unreal.put_rejected`**; no completed success audit (ordering per **`agent-unreal-mutate.md`** §9.1).

---

## 6. What the user sees

The **main chat** transcript stays anchored on **`/play`**: the coordinator prints **`preset_name`**, resolved **`base_url`**, and **`mode`** echoing toolkit policy. After each **`agent-unreal`** mutate call, a **single-line rollup** shows **`op_kind`**, **`status`** (**`dry_run`**, **`pass`**, **`blocked`**, **`error`**), and **`elapsed_ms`**.

On **`dry_run`**, there is **no** “connected to editor” noise beyond the explicit **`mode`** field. **`blocked`** scope rows print a **clear denial** without decorative symbols. The closing banner repeats **`trace_dir`**, **`mutation_count`**, and whether **`memory_commits`** succeeded, ending with **`UNREAL BRIDGE SESSION COMPLETE`** on the happy path.

---

## 7. Known drift / deferred

- **Connection pooling** — **`agent-unreal.md`** §10 notes urllib-per-call posture; reuse is **M6+**.  
- **Live writes** in this sample are **fixtures only**; real **PUT** requires a running editor and **`CUEBERT_UNREAL_MODE=live`**.  
- **Undo stack** — Cuebert emits **`reversal_hint`** only; it does **not** invoke Epic’s editor undo.  
- **Multi-editor coordination** — one **`base_url`** per invocation (**M5** limitation).  
- **`user-direct-debug`** — full matrix cells apply **only** when **`debug.agent_unreal: true`** on the harness plan at **coordinator** ingress; MCP tools cannot see that flag and keep a **narrow tool whitelist** aligned with the **mutate** columns of §6.1.

---

## 8. Trace tree (ASCII)

Committed example (JSON + JSONL + Markdown only):

```text
example-2026-04-20T14-00-00Z/
├── README.md
├── envelope.json
├── findings.json
├── mutations.jsonl
├── preset_snapshot.json
├── call_function/
│   └── envelope.json
├── set_property/
│   └── envelope.json
├── guards/
│   ├── pre_op.json
│   └── post_op.json
├── memory/
│   ├── set_property_commit.json
│   └── call_function_commit.json
└── scope_check/
    ├── set_property.json
    └── call_function.json
```

Hub path prefix: `.cuebert/traces/unreal/`. Matches [`control-plane-paths.md`](../standards/control-plane-paths.md) hub trace conventions; **`.gitignore`** un-ignores **`example-*/`** under **`unreal/`**.

---

## 9. How to use this example

- **Harness authors** should treat **`guards/`**, **`scope_check/`**, **`memory/`**, **`set_property/`**, **`call_function/`**, and **`mutations.jsonl`** as **fixture contracts** when wiring **`/play`** envelopes to MCP.  
- **Plan authors** should cross-check **`scope.allowed_mutations`** tokens against **`agent-unreal-mutate.md`** §11 before enabling live mode.  
- **M6+** promotion: replay the same scenario with **`CUEBERT_UNREAL_BASE_URL`** pointed at a dev machine running UE with Remote Control **HTTP** enabled; expect **`mode: live`** and real **`value_from`**/**`value_to`** readbacks for **`set_property`**.

---

## 10. Footer

**Status:** worked example, **M5-P4**. **Real editor HTTP:** optional follow-up when local UE Remote Control is configured. **Reference trace:** `.cuebert/traces/unreal/example-2026-04-20T14-00-00Z/`. **Style reference:** [`asset-sample-run-hello-level.md`](asset-sample-run-hello-level.md).
