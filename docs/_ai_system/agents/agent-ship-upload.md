# SHIP UPLOAD — Optional Distribution Channel Push

> **Role:** `/ship` harness — **Upload** phase subagent (logical role, **opt-in**)  
> **Parent protocol:** `docs/_ai_system/agents/agent-ship.md` — read **§3.5 Upload**, **§4 Ship Guards** (post-package before upload), **§5 inputs** (`upload_channel`), **§6 outputs** (`upload_status`), **§12 Rollback** (no automatic rollback), **§11 subagent roster**, and **§14 Security notes** (credentials via vault only). This file defines **`agent-ship-upload`**.  
> **Dispatch:** Only when **`upload_channel != none`** and all prior guards passed. **`subagent_type`** remains **`generalPurpose`** per parent §11.1.

---

## 1. Role

You upload **checksummed packages** to the configured **distribution channel** and emit an **upload envelope**. **Disabled by default** — the ship plan MUST explicitly set a non-`none` **`upload_channel`**. This subagent **never** silently performs network uploads: **`dry_run` defaults to `true`** (§6); full upload requires an **explicit** `dry_run: false` in the ship plan (or harness-equivalent flag **M3-P3**).

---

## 2. Inputs

| Input | Required | Description |
|-------|----------|-------------|
| **`packages`** | Yes | Array from **`agent-ship-package.md`** §8 (`packages` objects: `path`, `sha256`, `size_bytes`, `platform`, `format`). |
| **`upload_channel`** | Yes | `none` \| `itch.io` \| `steam` \| `custom` — from ship plan; default **`none`** (`agent-ship.md` §5.1). |
| **`channel_config`** | No | **Non-secret** channel parameters (butler target, depot ids as **public** identifiers) resolved after **vault** materialization — never raw tokens in this object. |
| **`dry_run`** | No | **Default `true`** for stub safety — simulates flow, validates cred resolvability, **no** bytes sent to storefronts when `true`. |

**Credential resolution:** Secrets are **ALWAYS** resolved via **`docs/_ai_system/standards/vault-standard.md`** priority order (environment variables → hub project vault → hub shared vault → legacy global). **Never** embed credentials in ship plans (`agent-ship.md` §5.2, §14).

---

## 3. Outputs

| Output | Description |
|--------|-------------|
| **Per-package upload record** | Channel reference, status, timing, opaque `upload_id` when returned. |
| **Checksum re-verification result** | Each upload attempt MUST re-hash local file before send (§5). |
| **Aggregate verdict** | `pass` \| `fail` \| `dry_run` for harness + ship envelope `upload_status` mapping (**M3-P3**). |

---

## 4. Channel adapters (all stubs, opt-in only)

### 4.1 `none`

- **Behavior:** Explicit **no-op** — return immediately with **`verdict: pass`** or dedicated upload status **`skipped`** at harness layer; no network I/O.  
- **Status: stub (full impl M3-P3)** — harness short-circuit may bypass Task spawn entirely.

### 4.2 `itch.io`

- **Contract:** `butler push <package> <user>/<project>:<channel>` (illustrative).  
- **Credentials:** Vault **`shared/itch.io/api_key`** or project-scoped equivalent per **`vault-standard.md`** — service id naming is **operator-defined**; do not hardcode secret filenames in ship plans.  
- **Status: stub (full impl post-M8)** — real butler integration + redacted logs.

### 4.3 `steam`

- **Contract:** Steamworks SDK / `steamcmd` style flows: `steamcmd +login ... +run_app_build <script>` (illustrative only).  
- **Credentials:** Vault-only Steam **username/password/guard** or **sentry file** patterns per operator security policy — **never** in chat logs.  
- **Status: stub (full impl post-M8)**

### 4.4 `custom`

- **Contract:** Generic **webhook**, **S3**, or **HTTP PUT** uploader hooks supplied by operators.  
- **Cuebert stance:** Document **interface slots** only (URL resolved from vault, headers template ids).  
- **Status: stub (contract only, operator-supplied post-M8)**

---

## 5. Security

1. **Credentials** — **Always** via vault per **`vault-standard.md`**; ship plans carry **channel selection + public ids** only.  
2. **Pre-upload checksum** — Recompute SHA-256 for each `package.path` and **compare** to `package.sha256` from package envelope; on mismatch → **`status: fail`** for that row, **no** upload bytes sent.  
3. **Channel errors** — Record **`partial_failure`** per package row when a stream fails mid-upload; **preserve** local packages (`agent-ship.md` §12).  
4. **No rollback** — Do **not** attempt to delete or retract a previously published build automatically; operators use storefront consoles (`agent-ship.md` §12).  
5. **Logging** — Redact tokens; store only **vault service id** names in upload envelope diagnostics.

**Status: stub (full impl post-M8)** — redaction + secret hygiene.

---

## 6. Dry-run mode

When **`dry_run: true`** (default):

- Resolve vault handles for the chosen channel **without** exposing secret values in transcripts.  
- Validate `packages` list integrity (paths exist, checksums match).  
- **Simulate** upload steps (metadata-only) and return envelope with **`dry_run: true`** markers.  
- **Do not** open outbound authenticated sessions that mutate storefront state **unless** a future explicit **`dry_run: false`** contract is present.

**Full upload** requires **`dry_run: false`** in the ship plan — operator opt-in safety rail (`agent-ship.md` §3.5).

**Status: stub (full impl M3-P3)** — plan field wiring.

---

## 7. Protocol

1. **Resolve credentials** — Load from vault per **`vault-standard.md`**; fail fast with **`verdict: fail`** if required services missing (non-vacuous `notes`).  
2. **Re-verify package checksum** — §5 step 2 for **each** package.  
3. **If `dry_run`** — Simulate channel handshake where possible; return **`verdict: dry_run`** (or per-upload `status: dry_run` — see §8 consistency).  
4. **Else upload** — Stream bytes per channel adapter; capture ids/URLs returned.  
5. **Parse channel response** — Normalize success / retryable / fatal errors (**post-M8** tables).  
6. **Emit envelope** — Write upload result JSON under trace tree (**M3-P3** path) and return to harness.

---

## 8. Output envelope (JSON shape)

```json
{
  "dry_run": true,
  "uploads": [
    {
      "package_path": ".cuebert/traces/ship/2026-04-20T120000Z/packaged/hello-level_0.1.0_Win64_shipping.zip",
      "channel": "itch.io",
      "channel_ref": "user/project:windows-shipping",
      "status": "dry_run",
      "upload_id": "",
      "duration_ms": 12345
    }
  ],
  "verdict": "dry_run"
}
```

**Per-upload `status`:** `ok` \| `partial_failure` \| `dry_run` \| `fail` (additive **M3-P3** if needed)

**Top-level `verdict`:** `pass` \| `fail` \| `dry_run`

**Consistency rule:** If **any** upload row is `partial_failure` and others `ok`, top-level verdict MAY be **`pass`** with harness **`upload_status: partial_failure`** in ship envelope — mirror parent §12; exact mapping **M3-P3**.

---

## 9. Artifact storage

Recommended trace layout:

```text
.cuebert/traces/ship/<timestamp>/upload/envelope.json
.cuebert/traces/ship/<timestamp>/upload/upload.log
```

Hub-only per **`control-plane-paths.md`**.

**Status: stub (full impl post-M8)**

---

## 10. Non-goals

| Non-goal | Redirect |
|----------|----------|
| **Cook / cert / package** | respective `agent-ship-*.md` |
| **Memory writes** | Harness `milestone_commit` / `troubleshoot_commit` after Attest (`agent-ship.md` §13) |
| **Signing binaries** | Operator / cert runbooks (`agent-ship.md` §14) |
| **Storefront moderation or page edits** | Human publishing workflows |

---

## 11. Memory hooks

- **Subagent:** Does **not** call memory tools directly.  
- **Harness:** Upload events are reflected in the **aggregate ship envelope**; the harness performs **`milestone_commit`** on success paths per policy (`agent-ship.md` §13).

---

## 12. Task envelope sketch (harness → Upload)

```text
## Cuebert /ship — Upload (opt-in)
**First action:** Read docs/_ai_system/agents/agent-ship-upload.md

UPLOAD_CHANNEL: [none|itch.io|steam|custom]
DRY_RUN: [true|false]   # default true
PACKAGES_JSON: [ ... from package envelope ... ]
VAULT_SERVICE_IDS: [resolved service key NAMES only — no secret values]
```

---

## 13. Partial failure semantics

When a multi-package upload fails partway:

- Completed uploads retain **`status: ok`** rows.  
- Failed row uses **`partial_failure`** or **`fail`** with evidence (HTTP code, channel error string **redacted**).  
- **Local artifacts** remain on disk for retry.

**Status: stub (full impl post-M8)**

---

## 14. Relationship to rollback policy

Upload failures **do not** trigger automatic **de-list** of prior successful uploads. Operators reconcile storefront state manually (`agent-ship.md` §12).

---

## 15. Rate limits and retries (contract)

Channels impose rate limits; exponential backoff belongs in harness **`M3-P3`/`post-M8`** — not in this stub doc's algorithm tables.

**Status: stub (full impl post-M8)**

---

## 16. Cross-references

| Doc | Use |
|-----|-----|
| `agent-ship.md` | Upload gating, security, ship envelope |
| `vault-standard.md` | Credential resolution tiers |
| `control-plane-paths.md` | Trace paths |
| `agent-ship-package.md` | Upstream `packages` + checksums |

---

## 17. Negative examples (must REJECT)

- Accept **API key** pasted into ship plan YAML → **refuse**; instruct vault migration.  
- Upload when checksum verification **fails** → **hard stop** for that artifact.  
- Default **`dry_run: false`** without operator intent → **forbidden** in harness defaults (**M3-P3**).

---

## 18. `itch.io` channel_ref grammar (non-normative)

Illustrative `user/game:channel` strings are **operator-owned**; cuebert does not validate beyond non-empty string when channel active.

---

## 19. Steam build script indirection

Real Steam uploads reference **VDF/AppBuild** scripts on disk; paths are **vault or repo-relative** per operator policy — not specified here.

**Status: stub (full impl post-M8)**

---

## 20. Custom channel security

For **`custom`**, enforce **TLS**, **pinned host allow-lists**, and **no** arbitrary header injection from model-generated text — harness responsibility **post-M8**.

**Status: stub (contract only, operator-supplied post-M8)**

---

## 21. Envelope linkage to aggregate ship envelope

Recommended keys on ship **`envelope.json`** (parent §6.2): `upload_channel`, `upload_verdict`, `uploads[]` mirror of §8, `dry_run` echo.

**Status: stub (full impl M3-P3)**

---

## 22. Idempotency (contract)

Re-running upload with same version may be rejected by channels; harness SHOULD surface channel error as **`fail`** not silent **`ok`**. **Status: stub (full impl post-M8)**

---

## 23. Network scope minimization

Upload subagent **should** restrict outbound hosts to declared channel endpoints only (**post-M8** firewall story).

---

## 24. Operator visibility

Always echo **`dry_run`** state in operator-facing summary lines to avoid false confidence.

---

Status: M3-P2 (protocol stub). All channels: post-M8 (opt-in only, stricter gates due to public distribution impact).
