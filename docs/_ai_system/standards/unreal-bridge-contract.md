# Unreal Bridge — Protocol Contract (`agent-unreal`)

> **SYSTEM ROLE:** Authoritative **protocol-layer** specification between Cuebert **`/play`** and **`/asset`** harnesses and the **Unreal Editor Remote Control HTTP API**, as enforced by **`docs/_ai_system/agents/agent-unreal.md`**.  
> **Scope:** Capability taxonomy, **default-deny** scope matrix, request/response envelope law, stable **error codes**, **dry-run** semantics, **mutation audit** schema, **scope violation** memory contract, transport caps, and **versioning**. **No** executable harness code — runners land **M5-P4+**.

---

## 0. Purpose & scope

This contract answers: **“Which Remote Control operations may run, under which harness identity, with what evidence, and what do callers do on failure?”**

**In scope:**

- **`agent-unreal`** coordinator inputs/outputs and **caller × op_kind** policy.  
- Relationship to **`.cursor/skills/unreal-bridge`** MCP tools (**M5-P1** read-only; **M5-P4** writes).  
- **Trace**, **audit**, and **memory** obligations for mutations and violations.

**Out of scope:**

- **ComfyUI** HTTP — **`comfyui-toolkit`** / **`agent-asset-generate.md`**.  
- **Cook / ship / cert** — **`ship-guards.md`**, **`agent-ship.md`**.  
- **Gameplay input automation** — **M6 Gauntlet**.

**Enforcement owner:** **`agent-unreal.md`** coordinator logic (future implementation); until then, this document is the **normative** checklist for manual harness simulation.

### 0.1 Relationship to gaming harness guard catalogs

| Guard catalog | How **`agent-unreal`** participates (**M5-P3**) |
|---------------|-----------------------------------------------|
| **`play-preview-guards.md`** | Supplies **evidence** for engine/preset reachability decisions; does **not** add new **`guard.*` ids** in **M5-P3**. |
| **`asset-pipeline-guards.md`** | Supplies optional **post-generate** / **post-place** evidence about UE visibility; **no** new guard rows here. |

Future **`guard.unreal.*`** ids (**§0** in **`agent-unreal.md`**) will reference **this contract** for thresholds when evaluators ship.

### 0.2 Memory split (normative)

| Activity | Memory tool |
|----------|-------------|
| **Per-mutation success**, **scope violations**, **novel op errors** | **`troubleshoot_commit`** |
| **Harness session success** (for example **`/asset`** full batch complete) | **`milestone_commit`** at **harness** level only |

**Rule:** **`agent-unreal`** MUST NOT call **`milestone_commit`** for routine engine tweaks.

### 0.3 Artifact paths (hub)

All **`agent-unreal`** traces live under:

```text
.cuebert/traces/unreal/<timestamp>/
```

The hub remains the **control plane** per **`docs/_ai_system/standards/control-plane-paths.md`** — application repos do not host cuebert trace roots by default.

---

## 1. Capability taxonomy

Capabilities split into **`probe`** (read-only) and **`mutate`** (write). **`probe`** ops MUST NOT append **`mutations.jsonl`** rows.

| `op_kind` | Capability | M5-P1 toolkit tool | Status |
|-----------|------------|-------------------|--------|
| *(connectivity / version stamp)* | **`probe`** | **`unreal_health_check`** | **live** (with **`dry_run`** fixtures) |
| **`list_presets`** | **`probe`** | **`unreal_list_presets`** | **live** |
| **`describe_preset`** | **`probe`** | **`unreal_describe_preset`** | **live** |
| **`ping_actor`** | **`probe`** | **`unreal_ping_actor`** | **live** |
| **`set_property`** | **`mutate`** | **`unreal_set_property`** (**planned name**) | **spec-only (M5-P4)** |
| **`call_function`** | **`mutate`** | **`unreal_call_function`** (**planned name**) | **spec-only (M5-P4)** |

**Rule:** **`mutate`** rows MUST NOT be executed against **live** HTTP until **M5-P4** ships the tools; **M5-P3** coordinators may still emit **`dry_run`** **`mutation_audit`** previews when documenting harness behavior.

### 1.1 Transport & client stack

All **M5-P1** tools use **stdlib** HTTP clients (see **`.cursor/skills/unreal-bridge/tools/_unreal_client.py`**) — no shell **`curl`**, no browser automation for Remote Control.

### 1.2 Capability boundaries

| Concern | **`probe`** | **`mutate`** |
|---------|-------------|--------------|
| **HTTP verbs** | **GET** family | **PUT** family (**M5-P4**) |
| **`mutations.jsonl`** | never writes | appends on success |
| **`troubleshoot_commit`** | optional / absent by default | **mandatory** on success + violations |

---

## 2. Scope whitelist matrix (caller × op_kind)

**Normative matrix** — reproduced from **`agent-unreal.md`** §6.1. Values are **booleans** interpreted by the coordinator **before** MCP calls.

| caller \ `op_kind` | `list_presets` | `describe_preset` | `ping_actor` | `set_property` | `call_function` |
|--------------------|----------------|-------------------|--------------|------------------|-------------------|
| **`agent-play-author`** | true | true | true | true | false |
| **`agent-play-preview`** | true | true | true | false | true |
| **`agent-asset-generate`** | true | true | true | false | false |
| **`agent-asset-place`** | true | true | true | false | true |
| **`user-direct-debug`** | true | true | true | true | true |

**`user-direct-debug` precondition:** The **`user-direct-debug`** row applies **only** when **`debug.agent_unreal: true`** is set on the active harness plan. If the flag is missing or **false**, treat **all** cells as **false** (default-deny).

**Default-deny:** Callers not listed → **all false**. **`op_kind`** not listed → **all false**. **`mutate`** additionally requires **`scope.allowed_mutations`** explicit entries (**§2.2**).

### 2.1 Worked interpretation rows

| Scenario | Matrix result |
|----------|----------------|
| **`agent-play-author`** calls **`call_function`** | **false** → **`blocked`** |
| **`agent-play-preview`** calls **`set_property`** | **false** → **`blocked`** |
| **`agent-asset-generate`** calls **`describe_preset`** | **true** → allow (subject to toolkit validation) |
| **`agent-asset-place`** calls **`call_function`** for reimport | **true** → allow when **`allowed_mutations`** includes the function token |

### 2.2 Explicit list requirement for **`mutate`**

Even when the matrix cell is **true**, the coordinator MUST reject the request when **`scope.allowed_mutations`** is missing, empty, or does not include the specific mutation token (**`agent-unreal-mutate.md`** §11 grammar).

---

## 3. Request / response envelope schema (prose)

**Future JSON Schema artifact** may ship beside **`asset-manifest`** schemas; **M5-P3** uses prose tables only.

### 3.1 Request (harness → coordinator)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| **`protocol_version`** | string | recommended | Should match coordinator (**`"1.0"`**). |
| **`caller`** | string | yes | One of five known callers. |
| **`operation`** | string | yes | **`probe`** \| **`mutate`**. |
| **`op_kind`** | string | yes | Must align with **`operation`**. |
| **`args`** | object | yes | Op-specific; must not embed secrets. |
| **`scope`** | object | yes | Includes **`preset_name`**; **`allowed_mutations`** string array for **`mutate`**. |
| **`dry_run`** | string | no | **`auto`**, **`true`**, **`false`**. |

### 3.2 Response (coordinator → harness)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| **`protocol_version`** | string | yes | **`"1.0"`** for **M5-P3**. |
| **`status`** | string | yes | **`pass`**, **`dry_run`**, **`error`**, **`blocked`**. |
| **`operation`** | string | yes | Echo. |
| **`op_kind`** | string | yes | Echo. |
| **`result`** | object | yes | May be `{}` on some errors. |
| **`mode`** | string | yes | **`live`** \| **`dry_run`**. |
| **`base_url`** | string | yes | Resolved Remote Control URL. |
| **`editor_version`** | string | yes | Editor or synthetic. |
| **`mutation_audit`** | object or null | yes | **`null`** unless **`mutate`** success path. |
| **`error`** | object or null | yes | **`{ code, message }`** or **`null`**. |
| **`elapsed_ms`** | number | yes | Integer ≥ 0. |
| **`findings`** | array or null | no | **`warn`** / **`info`** entries. |

### 3.3 `findings` entry shape (each element)

| Field | Type | Required |
|-------|------|----------|
| **`severity`** | string | yes — **`warn`** \| **`info`** |
| **`code`** | string | no — short machine token |
| **`message`** | string | yes — human readable |

### 3.4 Partial success (`mutate` extension)

When **`PUT`** succeeds but post-read fails, **`mutation_audit.audit_status`** MAY be **`partial_success`**; envelope **`status`** handling is **harness-defined** (**M5-P4** picks **`error`** vs **`pass`** with warnings).

---

## 4. Error code catalog

| Code | Severity | Description | Caller-recoverable? |
|------|----------|-------------|---------------------|
| **`unreal.unreachable`** | error | TCP/TLS connect failure, DNS, refused port. | yes — retry later / start editor |
| **`unreal.plugin_missing`** | error | HTTP reachable but Remote Control metadata/plugins incomplete. | sometimes — enable plugins |
| **`unreal.preset_not_found`** | error | Unknown preset or actor exposure. | yes — fix preset name |
| **`unreal.scope_rejected`** | blocked | Policy denial before write. | yes — adjust caller/op |
| **`unreal.property_not_found`** | error | Mutation property not exposed. | yes — fix manifest/preset |
| **`unreal.validation_failed`** | error | UE rejected values (range/type). | yes — adjust args |
| **`unreal.timeout`** | error | Exceeded **30 s** cap. | yes — reduce work / retry |
| **`unreal.unexpected`** | error | Parse failure / internal bug. | rarely — escalate |

### 4.1 Mapping from HTTP symptoms (informative)

| HTTP / transport symptom | Typical code |
|--------------------------|--------------|
| **connection refused** | **`unreal.unreachable`** |
| **read timeout** | **`unreal.timeout`** |
| **404 preset** | **`unreal.preset_not_found`** |
| **400 bad payload** | **`unreal.validation_failed`** |

Exact mapping table per tool lives in **`reference.md`** (**M5-P1**).

---

## 5. Dry-run contract

| Mode | Probes | Mutates (**M5-P4+**) | Caller interpretation |
|------|--------|----------------------|-------------------------|
| **`live`** | Real **GET** traffic | Real **PUT** traffic | Treat as authoritative editor state |
| **`dry_run`** | Synthetic fixtures from **`unreal-bridge`** | **No PUT**; **`mutation_audit`** still emitted when harness accepts synthetic mutation (**M5-P3** docs path) | Continue planning; do not assume pixels moved |
| **`auto`** | Try **live** per toolkit; fallback **`dry_run`** when unreachable | Same split as probes/mutates | Inspect **`findings`** for **`warn`** |

**Coordinator status mapping:**

- Successful **`dry_run`** probe → **`status: dry_run`** (or **`pass`** with **`mode: dry_run`** — pick one per harness wire-up; **M5-P4** MUST canonicalize).  
- **`live`** unreachable with **`auto`** → **`mode: dry_run`**, non-null **`findings`** warning, **`status`** typically **`dry_run`**.

---

## 6. Mutation audit schema

Each successful **`mutate`** (**live** or accepted **`dry_run`**) appends one JSON object as a **single line** in **`.cuebert/traces/unreal/<timestamp>/mutations.jsonl`** and mirrors summary into **`mutation_audit`** on the envelope.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| **`timestamp`** | string | yes | ISO-8601 UTC. |
| **`caller`** | string | yes | Harness identity. |
| **`op_kind`** | string | yes | **`set_property`** \| **`call_function`**. |
| **`preset`** | string | yes | Preset name. |
| **`object_path`** | string | conditional | Property targets; optional for some calls. |
| **`property`** | string | conditional | **`set_property`** only. |
| **`function`** | string | conditional | **`call_function`** only. |
| **`from`** | any | recommended | Pre-read value; **`null`** if unknown. |
| **`to`** | any | recommended | Post-read value; **`null`** if post-read failed. |
| **`mode`** | string | yes | **`live`** \| **`dry_run`**. |
| **`editor_version`** | string | yes | Echo stamp. |
| **`reversal_hint`** | string | yes | Best-effort undo guidance. |
| **`audit_status`** | string | no | **`ok`** \| **`partial_success`** extension |

**Retention:** Traces are **hub-local**; default **git-ignore** per control-plane policy. Operators MAY prune old **`unreal`** trace dirs manually.

**Memory:** **`troubleshoot_commit`** carries the same payload summary (**mandatory**).

### 6.1 Example audit line (**`mutations.jsonl`**)

```json
{"timestamp":"2026-04-20T12:00:00Z","caller":"agent-play-author","op_kind":"set_property","preset":"ExamplePreset","object_path":"/Game/Example/BP_Ship","property":"Brightness","from":0.5,"to":0.7,"mode":"dry_run","editor_version":"5.4.0-dry_run","reversal_hint":"set Brightness=0.5 on /Game/Example/BP_Ship"}
```

### 6.2 Forbidden audit contents

| Forbidden | Reason |
|-----------|--------|
| **Vault secrets** | Memory + traces must stay secret-free |
| **Full Epic JSON blobs** | Size + noise — store pointers only |

---

## 7. Scope violation contract

**When:** Coordinator rejects **`caller` + op_kind`**, rejects **`user-direct-debug`** without debug flag, or rejects missing **`allowed_mutations`** entries.

**Must emit:**

1. Envelope **`status: blocked`**, **`error.code: unreal.scope_rejected`**, concise **`message`**.  
2. **`troubleshoot_commit`** including: **`caller`**, attempted **`op_kind`**, **`preset_name`**, and redacted **`args`** summary (no secrets).  
3. Optional trace file **`scope_violation.json`** under the **`unreal`** trace root (**M5-P4** recommendation).

**Severity:** Always **policy** failure — not retried automatically unless the harness changes inputs.

---

## 8. Timeout & size rails

| Rail | Value | Source |
|------|-------|--------|
| **HTTP timeout hard cap** | **30 seconds** | **`unreal-bridge/SKILL.md`** (**M5-P1**) |
| **Max response body** | **10 MB** | **`unreal-bridge`** client (**M5-P1**) |
| **URL schemes** | **`http`**, **`https`** only | **`unreal-bridge`** sanitizer |
| **Userinfo URLs** | rejected | **`unreal-bridge`** sanitizer |

Callers MUST NOT raise caps from harness YAML without updating this contract’s **major** version.

### 8.1 Cross-check with **`unreal-bridge`** implementation

When **`CUEBERT_UNREAL_MODE`** or vault keys alter timeout defaults, the **effective** timeout is **`min(operator_value, 30s)`** — toolkit enforces the ceiling; this contract **normatively** depends on that behavior.

### 8.2 Large payload handling

If Epic returns oversized payloads (should not occur for describe/ping), tools MUST fail with **`unreal.unexpected`** rather than spilling multi-hundred-MB strings into MCP transcripts.

---

## 9. Versioning

- **`protocol_version: "1.0"`** — **M5-P3** initial frozen envelope.  
- **Breaking** removals/renames of fields or error codes → bump **major** (`"2.0"`).  
- **Additive** optional fields → **minor** bump policy (**M5-P4** defines semver alignment).

---

## 10. Non-goals

| Non-goal | Where instead |
|----------|----------------|
| **JSON Schema file on disk** | Deferred **M5-P4+** |
| **Websocket streaming** | Future **`unreal-bridge`** milestone |
| **Multi-editor selection UI** | Out of scope **M5** |
| **Perforce / P4 integration** | VCS docs / future |

### 10.1 Unity / Godot

This contract applies to **Unreal only**. Other engines require **separate** bridge contracts (**future M7**).

---

## 11. Cross-references

| Doc | Relationship |
|-----|----------------|
| `docs/_ai_system/agents/agent-unreal.md` | Coordinator |
| `docs/_ai_system/agents/agent-unreal-probe.md` | Probe subagent |
| `docs/_ai_system/agents/agent-unreal-mutate.md` | Mutate subagent (**SPEC ONLY** **M5-P3**) |
| `.cursor/skills/unreal-bridge/SKILL.md` | Toolkit overview |
| `.cursor/skills/unreal-bridge/reference.md` | MCP field contracts |
| `docs/_ai_system/agents/agent-play.md` | `/play` harness |
| `docs/_ai_system/agents/agent-asset.md` | `/asset` harness |
| `docs/_ai_system/standards/play-preview-guards.md` | `/play` guards |
| `docs/_ai_system/standards/asset-pipeline-guards.md` | `/asset` guards |

### 11.1 Harness sequencing (informative)

Typical **`/play`** Unreal session (**happy path** sketch):

```text
probe (health) → author (disk edits) → probe (describe preset) → mutate (PIE start) [M5-P4] → probe (log tail helpers) [future]
```

Typical **`/asset`** session touchpoint:

```text
generate (ComfyUI) → probe (describe / registry hints) → place (disk copy) → mutate (reimport) [M5-P4]
```

**Ordering** is owned by **`agent-play.md`** and **`agent-asset.md`** — this contract only constrains **what** `agent-unreal` may do **when** invoked.

### 11.2 Operator checklist (manual dry run)

1. Confirm **`.cursor/skills/unreal-bridge`** MCP server enabled.  
2. Set **`CUEBERT_UNREAL_MODE=dry_run`** for safe docs walk-through.  
3. Invoke **`unreal_list_presets`** — expect synthetic **`preset_count`**.  
4. Attempt **`mutate`** call — expect **SPEC ONLY** response from coordinator docs until **M5-P4**.

### 11.3 Glossary

| Term | Meaning |
|------|---------|
| **`Remote Control`** | Epic editor HTTP API family under configured **`base_url`**. |
| **`preset`** | Named exposure bundle of actors/properties/functions. |
| **`bridge agent`** | Logical coordinator **`agent-unreal`** — not a user shortcut. |

---

## 12. Footer

Status: **M5-P3**. **Live writes** and **canonical JSON Schema artifact:** **M5-P4+**.
