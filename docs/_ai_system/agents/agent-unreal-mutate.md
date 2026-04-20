# UNREAL MUTATE — Scoped Remote Control Writes

> **Role:** `agent-unreal` subagent — **`mutate`** operations (**HTTP PUT** to Remote Control via **`unreal_set_property`** and **`unreal_call_function`**).  
> **Status:** Live via **M5-P4** MCP tools. Scope whitelist is enforced at the **MCP tool layer** (caller constants) and mirrored in **`agent-unreal.md`** §6.1 for harness coordinators.  
> **Parent protocol:** `docs/_ai_system/agents/agent-unreal.md` — read **§6 (Scope enforcement)**, **§8 (Mutation audit)**, **§13 (Memory hooks)** before executing.  
> **Dispatch:** Only from the **`agent-unreal`** coordinator invoked under **`/play`** or **`/asset`** harness plans.

---

## 1. Role and scope

You perform **scoped writes** to a running Unreal Editor through Remote Control: **`set_property`** and **`call_function`**. Every mutation is a **single HTTP PUT** in live mode (no batching).

**Whitelist-only:** Writes proceed only when:

- **`caller` + `op_kind`** is allowed per **`agent-unreal.md`** §6.1, **and**  
- **`scope.allowed_mutations`** explicitly lists the mutation intent (e.g. **`set_property:Brightness`**, **`call_function:ReimportAsset`** — exact string grammar **`unreal-bridge-contract.md`** §3).

---

## 2. Inputs

| Field | Required | Description |
|-------|----------|-------------|
| **`caller`** | Yes | One of the five identities in the coordinator matrix. |
| **`op_kind`** | Yes | **`set_property`** or **`call_function`**. |
| **`args`** | Yes | Includes **`preset_name`**, target **`object_path`** (for property sets) or **`function_name`** / args payload (for calls). |
| **`scope`** | Yes | **`preset_name`** + **`allowed_mutations`** explicit list. |
| **`dry_run`** | No | **`auto`**, **`true`**, **`false`** per parent §7. |

### 2.1 `args` keys (normative names; validators **M5-P4**)

| `op_kind` | Required keys | Optional keys |
|-----------|---------------|----------------|
| **`set_property`** | **`preset_name`**, **`object_path`**, **`property`**, **`value`** | **`value_type`** hint string |
| **`call_function`** | **`preset_name`**, **`function_name`** | **`arguments`** array (ordered) |

MCP tool schemas (**`unreal_set_property`**, **`unreal_call_function`**) are the wire-level source of truth for field names (`property_name` vs coordinator prose `property`).

---

## 3. Outputs

| Output | Description |
|--------|-------------|
| **`agent-unreal` envelope** | **`operation: "mutate"`** plus §12 fields in **`agent-unreal.md`**. |
| **`mutation_audit`** | **Mandatory** on success paths (**live** and **`dry_run`**). |
| **`error`** | Populated on failure paths per §11. |

---

## 4. Scope guardrails (caller × op_kind)

Replicated from **`agent-unreal.md`** §6.1 for mutate columns only:

| `caller` | `set_property` | `call_function` |
|----------|----------------|-----------------|
| **`agent-play-author`** | **Allowed** (preset-exposed properties only) | **Denied** |
| **`agent-play-preview`** | **Denied** | **Allowed** (preset-exposed functions only) |
| **`agent-asset-generate`** | **Denied** | **Denied** |
| **`agent-asset-place`** | **Denied** | **Allowed** (reimport-by-path class only; **`Content/`** scope) |
| **`user-direct-debug`** | **Allowed** when **`debug.agent_unreal: true`** | **Allowed** when flag true |

**Additional rails:**

- **`allowed_mutations`** must include the concrete intent key or the coordinator returns **`blocked`** even if the coarse **`op_kind`** is allowed.  
- **`object_path`** must remain within the **preset exposure** contract for **`set_property`**; arbitrary engine paths are **`unreal.scope_rejected`**.

---

## 5. Atomicity

Each **`mutate`** invocation maps to **exactly one** Remote Control **PUT** in live mode. No multi-PUT transactions: if a harness needs two writes, it issues **two** coordinator calls **serialized**.

---

## 6. Rollback policy

The bridge **never auto-rolls back**. **`mutation_audit.reversal_hint`** documents a best-effort manual undo string for the **`set_property`** path; it is **`null`** for **`call_function`** (caller decides; bridge does not guess).

---

## 7. Protocol (ordered)

1. **Validate caller + `op_kind`** against §4 matrix; verify **`allowed_mutations`** covers this op.  
2. **Pre-mutation read** — for **`set_property`**, perform a **GET** on **`/remote/object/property`** to capture **`from`** values for audit. If pre-read fails, return **`error`**, **no write** (abort).  
3. **Emit HTTP PUT** — **`unreal_set_property`** / **`unreal_call_function`** delegate to **`_unreal_client`**.  
4. **Post-mutation read** — for **`set_property`**, confirm new state; populate **`to`** fields.  
5. **Write `mutation_audit` entry** — append JSON line to **`.cuebert/traces/unreal/<timestamp>/mutations.jsonl`**.  
6. **`troubleshoot_commit`** — **mandatory** for successful mutate path (including **`dry_run`** acceptance).  
7. **Emit envelope** — return to harness.

### 7.1 Preconditions (normative)

| Check | Failure |
|-------|---------|
| **`operation`** is **`mutate`** | Reject at coordinator — wrong subagent routing. |
| **`scope.preset_name`** required | If **absent** for **`mutate`**, **`unreal.scope_rejected`**. |
| **`allowed_mutations`** non-empty array | Empty → **`blocked`**. |
| **`args`** keys match **`op_kind`** schema | **`unreal.validation_failed`** before network. |

### 7.2 Postconditions

| Guarantee | Meaning |
|-----------|---------|
| **At most one PUT** | No batch APIs in **M5-P4**. |
| **Audit or explicit error** | No “silent success” without **`mutation_audit`** on success path. |
| **Memory** | **`troubleshoot_commit`** executed before returning success envelope to harness. |

### 7.3 Concurrency

Mutate ops **MUST NOT** run concurrently for the same **`base_url`** session unless **M5-P4+** explicitly documents safe function pairs. Harness coordinators serialize calls.

---

## 8. Output envelope (JSON shape)

Same top-level envelope as **`agent-unreal.md`** §12, with:

- **`operation`:** **`"mutate"`**  
- **`mutation_audit`:** non-null object on success paths

**`mutation_audit` extensions for partial post-read failure** (`PUT` ok, post-read fails):

- **`audit_status`:** **`partial_success`**  
- **`reversal_hint`:** best-effort string from pre-read snapshot  
- **`warnings`:** array explaining missing post-state (optional)

Canonical tool envelope (**M5-P4**): **`unreal_set_property`** / **`unreal_call_function`** return **`status`**, **`op_kind`**, **`mutation_audit`**, **`error`**, **`elapsed_ms`**, and op-specific fields (`value_from` / `value_to` / `return_value`).

---

## 9. Failure modes

| Case | Behavior |
|------|----------|
| **Scope rejected** | **`blocked`**, **`unreal.scope_rejected`**, **`troubleshoot_commit`** mandatory. |
| **Pre-mutation read fails** | **`error`**, **no PUT**, no completed **`mutation_audit`** (explain in **`error.message`**). |
| **PUT succeeds, post-read fails** | **`status: error`**, **`error.code: unreal.readback_failed`**, **`mutation_audit.audit_status: partial_success`**, **`reversal_hint`** populated. |
| **PUT fails or UE `errors` array** | **`error`**, **`unreal.put_rejected`**, no successful audit completion. |

### 9.1 Ordering guarantees

Failures **before** step 3 (**PUT**) never emit completed **`mutation_audit`** rows — partial pre-read data may still log to trace sidecars.

### 9.2 Negative examples (mutate)

| Scenario | Result |
|----------|--------|
| **`agent-asset-generate`** attempts **`set_property`** | **`blocked`** — matrix deny. |
| **`allowed_mutations`** lists **`call_function:Foo`** but op is **`set_property`** | **`blocked`** — token mismatch. |

---

## 10. Examples (dry_run)

### 10.1 `set_property` (synthetic acceptance)

**Request:** **`caller: agent-play-author`**, **`op_kind: set_property`**, **`dry_run: true`**, **`scope.allowed_mutations: ["set_property:Brightness"]`**.

**Outcome:** No HTTP **PUT**; envelope returns **`mode: dry_run`**, **`mutation_audit`** shows **`from`/`to`**, **`troubleshoot_commit`** fired.

### 10.2 `call_function` (synthetic acceptance)

**Request:** **`caller: agent-play-preview`**, **`op_kind: call_function`**, **`dry_run: true`**, **`scope.allowed_mutations: ["call_function:StartPIE"]`**.

**Outcome:** **`mutation_audit`** records function name; synthetic **`return_value`**; no live editor **PUT**.

---

## 11. `allowed_mutations` string grammar

Strings are **case-sensitive** unless a later milestone defines normalization:

| Pattern | Meaning |
|---------|---------|
| **`set_property:<PropertyName>`** | Author may set **`PropertyName`** on an exposed object path validated against preset metadata. |
| **`call_function:<FunctionName>`** | Preview/Place may invoke **`FunctionName`** exposed on the preset. |

Harness MAY prefix with namespace **`ue:`** later — **undecided** until harness JSON wiring hardens; do not rely on prefixes in parsers today.

---

## 12. Relationship to disk writes

**`agent-unreal-mutate`** never writes **`.uasset`** / **`.umap`** files from cuebert. **`set_property`** adjusts **live editor state**; **`call_function`** may trigger engine-side imports/reimports that **then** write binaries as a side effect of Unreal — still **not** cuebert file tools.

### 12.1 Interaction with **`agent-asset-place`**

Place writes **PNG** bytes; **`call_function`** reimport path informs Unreal to refresh **texture** assets. The two steps are **ordered** by **`agent-asset.md`** — mutate must not run before validated bytes exist on disk.

---

## 13. Operator visibility

Recommended trace layout (**M5-P4**):

```text
.cuebert/traces/unreal/<timestamp>/
  mutations.jsonl
  envelope.json
  pre_get.json
  post_get.json
```

Filenames are **recommendations**; committed worked examples may add **`scope_check/`**, **`memory/`**, and **`guards/`** subtrees (see **`unreal-bridge-sample-run-hello-level.md`**).

---

## 14. Cross-references

| Doc | Use |
|-----|-----|
| `agent-unreal.md` | Coordinator + full matrix |
| `unreal-bridge-contract.md` | Law for scopes, envelopes, errors |
| `agent-play-preview.md` | Preview consumer of **`call_function`** |
| `agent-asset-place.md` | Place consumer of reimport **`call_function`** |

---

## 15. Troubleshooting (documentation)

| Symptom | Likely cause | Next step |
|---------|--------------|-----------|
| **`blocked`** immediately | Caller/token mismatch | Fix harness envelope per **`unreal-bridge-contract.md`** §2.2 |
| **`unreal.unreachable`** | Editor down / wrong port | Start UE; confirm **`base_url`** |
| **`dry_run` always** | Mode env unset + toolkit unconfigured | Set **`CUEBERT_UNREAL_MODE=live`** explicitly for dev |
| **Audit missing on “success”** | Coordinator bug / skipped steps | Treat as **`unreal.unexpected`** — do not merge |

---

## 16. Alignment with **`agent-unreal.md`** memory split

| Event | `troubleshoot_commit` | `milestone_commit` |
|-------|----------------------|-------------------|
| **Mutate success** | **yes** | **no** |
| **Scope violation** | **yes** | **no** |
| **`/asset` batch complete** | harness optional notes | **yes** (per **`agent-asset.md`**) |

---

## 17. Revision note

**M5-P4** ships live **`unreal_set_property`** and **`unreal_call_function`** MCP tools, **`_unreal_client`** **PUT** helpers, worked dry-run sample run, and trace fixtures under **`.cuebert/traces/unreal/example-*/`**.

---

## 18. Footer

**M5-P4:** **`agent-unreal-mutate`** protocol is **live** with MCP tool backing. Harnesses **must** still pass **`caller`**, **`scope.allowed_mutations`**, and respect **`debug.agent_unreal`** for **`user-direct-debug`** at coordinator ingress per **`agent-unreal.md`**.
