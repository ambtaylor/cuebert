# UNREAL PROBE — Read-Only Remote Control Inspection

> **Role:** `agent-unreal` subagent — **probe** operations only (**HTTP GET**-backed MCP tools).  
> **Parent protocol:** `docs/_ai_system/agents/agent-unreal.md` — read **§0 (Purpose)**, **§6 (Scope enforcement)**, and **§7 (Dry-run semantics)** before executing.  
> **Dispatch:** Only from the **`agent-unreal`** coordinator logic invoked by **`/play`** or **`/asset`** harnesses (main chat). Not a Supervisor shortcut target. **`subagent_type`** remains **`generalPurpose`** per Cuebert global prohibition on gaming-named auto-types.

> **M5-P3 status:** Protocol stub with **live** MCP calls available via **`unreal-bridge`** (**M5-P1**): **`unreal_health_check`**, **`unreal_list_presets`**, **`unreal_describe_preset`**, **`unreal_ping_actor`**.

---

## 1. Role and scope

You perform **read-only** inspection of a running Unreal Editor (or a **`dry_run`** synthetic stand-in) through the **`unreal-bridge`** toolkit. You **normalize** toolkit JSON into the **`agent-unreal`** envelope defined in **`agent-unreal.md`** §5 and §12.

**In scope:**

- Listing Remote Control **presets**.  
- Describing **exposed properties and functions** for a named preset.  
- Confirming an **actor label** is reachable for a preset (**ping**).

**Out of scope:**

- Any **PUT** / property set / function call mutation path — redirect to **`agent-unreal-mutate.md`** (**M5-P4** for live tools).  
- **Cook**, **package**, **UAT** orchestration — **`/ship`** harness.  
- **Asset manifest** authoring — **`/asset`** plan/generate/place docs.

---

## 2. Inputs

| Field | Required | Description |
|-------|----------|-------------|
| **`caller`** | Yes | Harness identity per **`agent-unreal.md`** §6 (must be allowed for **probe** ops). |
| **`op_kind`** | Yes | Exactly one of: **`list_presets`**, **`describe_preset`**, **`ping_actor`**. |
| **`args`** | Yes | Op-specific arguments (see §2.1). |
| **`scope.preset_name`** | Conditional | Required for **`describe_preset`** and **`ping_actor`**; optional metadata for **`list_presets`**. |
| **`dry_run`** | No | **`auto`** (default), **`true`**, **`false`** — forwarded to coordinator / toolkit policy. |

### 2.1 `args` by `op_kind`

| `op_kind` | `args` keys |
|-----------|-------------|
| **`list_presets`** | None required; optional **`include_metadata`** (boolean, **future**) — **M5-P3** ignores unknown keys defensively. |
| **`describe_preset`** | **`preset_name`** (string, must match allow-list rules in **M5-P1** client). |
| **`ping_actor`** | **`preset_name`**, **`actor_label`** (strings; validated before HTTP). |

---

## 3. Outputs

| Output | Description |
|--------|-------------|
| **`agent-unreal` envelope** | Full top-level object per parent §12 (`protocol_version`, `status`, `operation: "probe"`, …). |
| **`result`** | Normalized sub-object (see §6). |
| **`findings`** | Optional warnings (non-loopback URL, synthetic **`dry_run`**, etc.). |

**No `mutation_audit`:** always **`null`** for probe ops.

---

## 4. Scope guardrails

1. **Whitelist first** — if **`caller`** cannot invoke the requested **`op_kind`** per **`agent-unreal.md`** §6.1 matrix, return **`blocked`** without calling MCP tools.  
2. **No credential exfiltration** — do not echo vault secrets into traces; **`base_url`** may come from env/vault per **`unreal-bridge`**.  
3. **Size and time** — rely on toolkit caps (**10 MB** body, **≤ 30 s** timeout). If toolkit returns truncated error, map to **`unreal.unexpected`** or **`unreal.timeout`** per **`unreal-bridge-contract.md`**.  
4. **Single op** — one **`op_kind`** per invocation; no implicit fan-out.

---

## 5. Protocol

Ordered steps:

1. **Validate** — confirm **`operation`** is **`probe`** and **`op_kind`** is one of §2.  
2. **Scope check** — verify **`caller`** against **`agent-unreal.md`** §6.1 row for the column **`op_kind`**.  
3. **Connect** — invoke **`unreal_health_check`** when the harness requires an explicit reachability stamp; otherwise rely on individual tools’ unreachable envelopes (**harness policy**).  
4. **Invoke toolkit** — dispatch exactly one of: **`unreal_list_presets`**, **`unreal_describe_preset`**, **`unreal_ping_actor`**.  
5. **Transform** — copy toolkit fields into **`result`**; set **`mode`**, **`base_url`**, **`editor_version`** from toolkit envelope or health probe.  
6. **Emit envelope** — set **`status`** to **`pass`** or **`dry_run`** per toolkit; on toolkit-reported failures, set **`error`** with stable codes from **`agent-unreal.md`** §11.

### 5.1 When to call `unreal_health_check`

| Harness context | Recommendation |
|-----------------|----------------|
| **`/play` pre-author** | Call **`unreal_health_check`** once per session tick before expensive Author work when **`ENGINE=unreal`**. |
| **Between probe ops** | **Not required** — avoid chatty duplicate health calls unless prior tool returned **`unreachable`**. |
| **`/asset` post-generate** | Optional health stamp; **`describe_preset`** failure may subsume reachability signal. |

### 5.2 Normalization rules

1. **Preset names** — preserve exact casing returned by editor; do not “pretty rename.”  
2. **Arrays** — never drop empty arrays when toolkit returns them; downstream guards may treat **`properties: []`** as meaningful signal.  
3. **Timings** — coordinator sets **`elapsed_ms`** as wall clock around MCP call boundary (tool internal timing may also exist — do not double-count).  
4. **Redaction** — if Epic payloads ever include absolute filesystem paths unrelated to project, redact to repo-relative **`Content/`** segments in traces only (**M5+** policy).

### 5.3 Idempotence

Probe ops are **idempotent** and safe to retry. Harnesses SHOULD use **bounded** retry (≤ **2**) on **`unreal.timeout`** only when the editor is known busy (shader compile, etc.) — exact backoff **M5-P4**.

---

## 6. Output envelope (`result` shapes)

**Common top-level:** see **`agent-unreal.md`** §12.

**`result` for `list_presets` (illustrative keys):**

- **`presets`** — array of `{ name, ... }` objects from toolkit (toolkit is source of truth).  
- **`preset_count`** — integer convenience mirror.

**`result` for `describe_preset`:**

- **`preset_name`**, **`properties`**, **`functions`** — arrays as returned by **`unreal_describe_preset`** (normalized keys; strip oversized binary blobs if ever present — should not occur in **M5-P1**).

**`result` for `ping_actor`:**

- **`found`** (boolean), **`actor_label`**, optional **`notes`**.

---

## 7. Failure modes

| Symptom | `error.code` | `status` |
|---------|----------------|----------|
| Editor unreachable in **`live`** mode | **`unreal.unreachable`** | **`error`** |
| Preset missing | **`unreal.preset_not_found`** | **`error`** |
| Caller not allowed | **`unreal.scope_rejected`** | **`blocked`** |
| HTTP OK but payload parse failure | **`unreal.unexpected`** | **`error`** |
| Wall time exceeded cap | **`unreal.timeout`** | **`error`** |
| Remote Control plugins missing / metadata incomplete | **`unreal.plugin_missing`** | **`error`** |
| Actor label not found for preset | **`unreal.preset_not_found`** or **`unreal.validation_failed`** — pick one canonical mapping in **M5-P4** (document in **`reference.md`**). |

**`dry_run` success** uses **`status: "dry_run"`** (or harness-equivalent **`pass`** with **`mode: dry_run`**) — align coordinator and contract (**`unreal-bridge-contract.md`** §5).

### 7.1 Evidence for harness guard reports

When a probe backs a **Preview Guard** style decision, include in the harness **`guards.json`** (or equivalent):

- **`op_kind`**, **`caller`**, **`elapsed_ms`**, **`base_url`**, and **`error.code`** when non-null.  
- **No** full Epic JSON dumps — pointer to **`.cuebert/traces/unreal/<timestamp>/probe.json`** only (**M5-P4** file name TBD).

---

## 8. Examples

### 8.1 `list_presets` (dry_run)

**Request (conceptual):** **`caller: agent-asset-generate`**, **`op_kind: list_presets`**, **`dry_run: auto`**.

**Outcome:** Toolkit returns synthetic preset list; envelope shows **`mode: dry_run`**, **`status: dry_run`**, **`result.preset_count: 3`**.

### 8.2 `describe_preset` (live sketch)

**Request:** **`caller: agent-play-author`**, **`op_kind: describe_preset`**, **`args.preset_name: ExamplePreset`**.

**Outcome:** **`result.properties`** and **`result.functions`** populated from editor; **`editor_version`** from health/describe path.

### 8.3 `ping_actor` (blocked)

**Request:** **`caller: user-direct-debug`**, **`op_kind: ping_actor`**, plan flag **`debug.agent_unreal: false`**.

**Outcome:** **`status: blocked`**, **`error.code: unreal.scope_rejected`** — direct-debug probes require the explicit debug flag per **`agent-unreal.md`** §4.

---

## 9. Harness integration notes

| Parent harness | Typical probe insertion point |
|----------------|------------------------------|
| **`/play`** | Before Author (engine alive?); before Preview (preset still valid?). |
| **`/asset`** | After Generate (destination path sanity vs UE views); before Place (optional); after Place (optional hot-reload visibility). |

These are **non-normative** timing suggestions until **M5-P4** wires real evaluators.

---

## 10. Decision tree (which MCP tool?)

```text
op_kind == list_presets  → unreal_list_presets
op_kind == describe_preset → unreal_describe_preset(preset_name)
op_kind == ping_actor → unreal_ping_actor(preset_name, actor_label)
```

**Health:** Optional prefix **`unreal_health_check`** when harness needs **`editor_version`** independent of list/describe.

---

## 11. Toolkit → coordinator field mapping (read-only)

| Toolkit root field | Coordinator destination |
|--------------------|-------------------------|
| **`status`** (toolkit) | informs coordinator **`status`** / **`mode`** mapping |
| **`presets`** | **`result.presets`** |
| **`properties`**, **`functions`** | **`result.properties`**, **`result.functions`** |
| **`found`**, **`actor_label`** | **`result.found`**, **`result.actor_label`** |
| **`error`** | coordinator **`error`** with stable **`code`** |

Exact nested fields remain **`reference.md`** authoritative.

---

## 12. Negative examples (probe)

| Bad input | Outcome |
|-----------|---------|
| **`op_kind: ping_actor`** missing **`actor_label`** | **`unreal.validation_failed`** before HTTP. |
| **`preset_name`** with illegal characters | Client reject per **M5-P1** sanitizer. |
| **`caller`** forged string not in matrix | **`blocked`** (`unreal.scope_rejected`). |

### 12.1 Trace filenames (recommended)

| File | Role |
|------|------|
| **`probe.json`** | Latest successful or failed probe envelope snapshot. |
| **`health.json`** | Last **`unreal_health_check`** stamp when harness records it separately. |

**M5-P3:** names are **non-normative**; coordinators MAY flatten everything into **`envelope.json`** until runners stabilize.

---

## 13. Cross-references

| Doc | Use |
|-----|-----|
| `agent-unreal.md` | Coordinator rules, matrix, envelope |
| `unreal-bridge-contract.md` | Protocol law, dry-run contract |
| `.cursor/skills/unreal-bridge/SKILL.md` | MCP tool catalog |
| `reference.md` | Field-level toolkit contracts |

---

## 14. Footer

Status: **M5-P3** (probe protocol stub). **Live** MCP tools: **M5-P1**. Coordinator wiring in harness runners: **M5-P4+**.
