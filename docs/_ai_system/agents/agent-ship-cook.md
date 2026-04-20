# SHIP COOK — Engine Cook Pipeline

> **Role:** `/ship` harness — **Cook** phase subagent (logical role)  
> **Parent protocol:** `docs/_ai_system/agents/agent-ship.md` — read **§3 phase chain** (especially §3.2 Cook), **§4 Ship Guards** (pre-cook already passed; post-cook consumes this output), **§5 inputs**, **§6 outputs**, and **§11 subagent roster** before executing. This document is the normative stub for the **`agent-ship-cook`** row in that roster.  
> **Dispatch:** Only from the `/ship` harness in main chat per `agent-ship.md` activation rules. **`subagent_type`** remains **`generalPurpose`** per parent §11.1 — never gaming-named Cursor auto-types.

---

## 1. Role

You execute the engine's **cook** pipeline for a declared **project** + **cook flavor** and emit a **structured cook envelope** describing exit status, timing, per-platform cooked roots, size accounting, and log pointers. Pre-requisite **Ship Guards** (pre-cook) have **already** run in the harness; this subagent focuses on the cook subprocess lifecycle only — not certification, packaging, upload, or git state management.

---

## 2. Inputs

| Input | Required | Description |
|-------|----------|-------------|
| **`project`** | Yes | Key from **`.cuebert/workspace-manifest.json`** → `projects.{key}`; used for trace naming, manifest alignment, and vault-scoped future hooks. |
| **`engine`** | Yes | `unreal` \| `unity` \| `godot` — selects **§5** adapter contract. |
| **`cook_flavor`** | Yes | `development` \| `shipping` \| `debug` — must align with the parent ship plan's `cook_flavors` entry for the active session (harness normalizes to one flavor per cook invocation unless a future revision batches). |
| **`target_platforms`** | Yes | List of platform tokens (for example `Win64`, `Mac`, `Linux` for Unreal; harness maps ship plan `target_platforms` to engine-native names). |
| **`output_dir`** | Yes | Hub-resident cooked asset root, typically **`.cuebert/traces/ship/<timestamp>/cooked/`** (see §6). |
| **`max_duration_s`** | No | Hard wall-clock budget for the cook subprocess family. **Default:** read from **`.cuebert/config/ship-guards.yaml`** → `global.cook_max_duration_s` when present; if absent until M3-P3 wiring, use **1800** (30 minutes). |
| **`APP_REPO`** | Yes | Absolute path to the application repository root (from manifest `projects.{key}.path`). |
| **`HUB_REPO`** | No | Absolute path to the cuebert hub checkout; used for trace-relative path normalization per `docs/_ai_system/standards/control-plane-paths.md`. |

**Harness alignment:** Field names mirror `agent-ship.md` §5.1 where applicable; the ship plan remains the **authoritative** contract for platforms and flavors.

---

## 3. Outputs

| Output | Description |
|--------|-------------|
| **Cook exit code** | Integer process exit code from the engine cook driver (or wrapper); `null` only when the harness could not spawn the process. |
| **Cooked asset count** | Per-platform **approximate** file count or engine-reported metric when available; **stub** until M8 enumerators exist. |
| **Cook duration** | Wall-clock **milliseconds** from subprocess start to observed termination. |
| **Log tail path** | Path to consolidated cook log (see §6) for post-cook guards and human triage. |
| **Cooked content paths** | Map **platform → directory** under `output_dir` (or engine staging roots the harness re-homes). |
| **Size report** | Per-platform **byte totals** for cooked trees (or primary staged artifact) for `guard.cook.size_budget` consumption. |

---

## 4. Engine adapters (stubs)

Each adapter names the **future** CLI or tool wrapper the harness will invoke. Until M8, this subagent records **intent**, captures **no** vendor secrets, and returns **stub envelopes** when automation is absent.

### 4.1 Unreal Engine (Tier 1)

**Illustrative UAT invocation (documentation only — not executed in M3-P2):**

```text
RunUAT.sh BuildCookRun -project=<AbsoluteUProject> -cook -stage -package -platform=Win64 -clientconfig=Shipping
```

- Real multi-platform cooks iterate `-platform=` or use UAT multi-target flags per engine documentation.  
- **Proposed orchestration tool:** `ue_uat_cook` (proposed, **M8-P1**) — wraps `RunUAT.sh` / `RunUAT.bat`, normalizes log streaming, and maps exit codes.  
- **Status: stub (full impl M8-P1)** — first-class Unreal cook automation.

### 4.2 Unity (Tier 2)

**Illustrative stub:**

```text
Unity -batchmode -projectPath <APP_REPO> -executeMethod Build.Run -buildTarget <TargetName>
```

- Exact `executeMethod`, Scriptable Build Pipeline entry, and platform mapping are **post-M8**.  
- **Proposed tool:** `unity_batch_cook` (proposed, post-M8).  
- **Status: stub (full impl post-M8)** — Unity Tier 2; deferred after Unreal path.

### 4.3 Godot (Tier 3)

**Illustrative stub:**

```text
godot --headless --export-release "<preset>" <output>
```

- Preset names and export maps come from project configuration; automation hooks **post-M8**.  
- **Proposed tool:** `godot_export_cook` (proposed, post-M8).  
- **Status: stub (full impl post-M8)** — Godot Tier 3.

---

## 5. Artifact storage

Follow **`docs/_ai_system/standards/control-plane-paths.md`**: ship traces are **hub-resident** under the cuebert checkout (`.cuebert/`), not mandatory in application repos.

**Normative layout for this subagent:**

```text
.cuebert/traces/ship/<timestamp>/cooked/<platform>/   # per-platform cooked tree (or symlinked staging)
.cuebert/traces/ship/<timestamp>/cook/engine.log      # streamed cook log (full or rolling)
.cuebert/traces/ship/<timestamp>/cook/envelope.json   # §8 structured cook result
```

- `<timestamp>` is UTC-sortable (`YYYY-MM-DDTHHMMSSZ` or equivalent per `agent-ship.md` §6).  
- **`log_tail_path`** in the cook envelope (§8) SHOULD point at **`.../cook/engine.log`** (or a tail file written alongside it when logs are huge — harness decision **M8-P1**).  
- **Status: stub (full impl M8-P1)** — directory materialization and atomic envelope writes.

---

## 6. Timeout and abort

| Parameter | Default | Behavior |
|-----------|---------|----------|
| **Cook window** | **30 min** (`1800` s) unless `ship-guards.yaml` overrides | On expiry: send graceful terminate to wrapper; escalate to **hard kill** when safe (platform-specific **M8-P1**). |
| **Non-zero exit** | N/A | Treat as **failure**; set `status: "fail"`; preserve partials (§6.1). |
| **Spawn failure** | N/A | `status: "fail"`, `exit_code: null`, `notes` explains missing binary or permission. |

### 6.1 Partial artifacts

On **failure**, **timeout**, or **user cancel** after cook began, the harness **MAY** copy or retain fragments under:

```text
.cuebert/traces/ship/<timestamp>/partial/cook/
```

for operator forensics, mirroring `agent-ship.md` §6.4. This subagent **documents** the convention; the move/copy implementation is **M8-P1**.

**Principles:**

1. **Never** delete successful prior traces automatically.  
2. **Always** emit `envelope.json` for the cook phase when the harness controls the session (parent **Attest** still aggregates).  
3. **Status: stub (full impl M8-P1)** — subprocess supervision.

---

## 7. Protocol

Execute in order; do not skip steps.

1. **Validate inputs** — Confirm `project` resolves in the workspace manifest, `APP_REPO` exists, `engine` matches manifest/engine association where applicable, and `target_platforms` is non-empty. On validation failure, emit **`status: "fail"`** with actionable `notes` (no subprocess launch).  
2. **Launch cook CLI** — Select §4 adapter command family; invoke via future `ue_uat_cook` (proposed, **M8-P1**) or documented stub.  
3. **Stream log to disk** — Append stdout/stderr to **`.../cook/engine.log`** with rotation policy **TBD M8-P1**.  
4. **Wait for exit** — Respect `max_duration_s`; record `duration_ms`.  
5. **Collect cooked paths** — Enumerate per-platform output directories; normalize to hub-relative paths where possible.  
6. **Emit envelope** — Write **`.../cook/envelope.json`** per §8; return the path to the harness.

---

## 8. Output envelope (JSON shape)

The cook envelope is consumed by **`agent-ship-cert`** (`cooked_paths`) and post-cook **Ship Guards** (`agent-ship.md` §4).

```json
{
  "status": "ok",
  "exit_code": 0,
  "duration_ms": 1234567,
  "platforms_cooked": ["Win64", "Mac"],
  "cooked_paths": {
    "Win64": ".cuebert/traces/ship/2026-04-20T120000Z/cooked/Win64/",
    "Mac": ".cuebert/traces/ship/2026-04-20T120000Z/cooked/Mac/"
  },
  "content_size_bytes": {
    "Win64": 1234567890,
    "Mac": 987654321
  },
  "log_tail_path": ".cuebert/traces/ship/2026-04-20T120000Z/cook/engine.log",
  "notes": "Optional human context; include engine version echo when known."
}
```

**`status` enum:** `ok` \| `fail` \| `timeout`

**Field notes:**

- **`cooked_paths`** values are directory roots; files within are implementation-defined per engine.  
- **`content_size_bytes`:** total bytes under each cooked root when recursive sizing is available; else **stub zeros** with `notes` until M8.  
- **`exit_code`:** mirror OS process exit; for timeouts after kill, document convention in harness (**M8-P1**).

---

## 9. Non-goals

| Non-goal | Redirect |
|----------|----------|
| **Packaging** (zip, installer, platform-native) | `agent-ship-package.md` |
| **Certification / compliance scans** | `agent-ship-cert.md` |
| **Upload to distribution channels** | `agent-ship-upload.md` |
| **`git commit` / `git push` / branch switches** | Operator or CI; not cook subagent |
| **Pre-cook Ship Guards** | Harness-owned before dispatch (`agent-ship.md` §4.1) |
| **Memory writes** (`milestone_commit`, `troubleshoot_commit`) | §11 — harness commits |

---

## 10. Memory hooks

- **Writes:** This phase **does** write cook logs, partials (when applicable), and **`cook/envelope.json`** under `.cuebert/traces/ship/...`.  
- **Direct memory tools:** This subagent **does not** call `milestone_commit` or `troubleshoot_commit`. The `/ship` harness performs mandatory memory attestation after **Attest** (`agent-ship.md` §13).  
- **Correlation:** Envelope paths are referenced by the aggregate **ship envelope** at `.cuebert/traces/ship/<timestamp>/envelope.json` (**M3-P3+**).

---

## 11. Task envelope sketch (harness → Cook)

```text
## Cuebert /ship — Cook
**First action:** Read docs/_ai_system/agents/agent-ship-cook.md

HUB_REPO: [absolute]
APP_REPO: [absolute]
PROJECT_KEY: [manifest key]
ENGINE: [unreal|unity|godot]
COOK_FLAVOR: [development|shipping|debug]
TARGET_PLATFORMS: [Win64, Mac, ...]
OUTPUT_DIR: [.cuebert/traces/ship/<timestamp>/cooked/]
MAX_DURATION_S: [from ship-guards.yaml global.cook_max_duration_s or default]
```

---

## 12. Relationship to post-cook guards

Post-cook guard ids (`agent-ship.md` §4.2) consume this envelope:

| Guard id | Primary cook fields |
|----------|---------------------|
| `guard.cook.exit_code` | `exit_code`, `status` |
| `guard.cook.size_budget` | `content_size_bytes` |
| `guard.cook.missing_assets` | `cooked_paths` + engine manifest expectations (**M8-P1**) |

**Status: stub (full impl M3-P3)** — guard YAML merge; **M8-P1** — evaluators.

---

## 13. Engine version echo

When **`ENGINE_VERSION`** (or manifest equivalent) is supplied by the harness, include it in `notes` or as an **additive** JSON field agreed at M8 (`engine_version` string). Do **not** invent version strings.

---

## 14. Negative examples (must REJECT)

- Attempt to **upload** cooked bits to a store from this phase → **out of scope**.  
- User asks to **disable** `guard.git.clean` from inside cook → **refuse**; guards are harness-owned.  
- Cook **without** `APP_REPO` resolution → **fail fast** with manifest pointer in `notes`.

---

## 15. Slim envelope alignment

Parent `agent-ship.md` §3.9 defines a **Cook** slim sketch. This file is the **canonical expansion**; keep Task prompts slim per `docs/_ai_system/agents/agent-orchestrator.md` §3.

---

## 16. Cross-references

| Doc | Use |
|-----|-----|
| `agent-ship.md` | Phase chain, Ship Guards, ship plan schema, memory policy |
| `play-preview-guards.md` | Evidence shape **pattern** for structured findings (informative only here) |
| `control-plane-paths.md` | Hub traces, zero-footprint app repos |
| `agent-ship-cert.md` | Downstream consumer of `cooked_paths` |

---

## 17. Determinism and reproducibility (informational)

Cook output **may** vary with engine cache state even when sources are identical. Byte-exact reproducibility is **not** promised at cook; **deterministic packaging** is owned by `agent-ship-package.md`. Still, log **git SHA** and **engine version** in parent ship envelope for audit (`agent-ship.md` §6.2).

---

## 18. Multi-platform cook ordering

When multiple platforms are requested, the harness **default** is **sequential** cooks (parent §11.1 **Parallelism**). This subagent MAY receive one platform per invocation in early implementations; envelope always lists **all** platforms produced **in that invocation**.

**Status: stub (full impl M8-P1)** — batching policy.

---

## 19. Dry-run / preview semantics

If the harness defines **`--preview`** or dry-run cook (**M3-P3**), return **`status: "fail"`** with `notes: "preview_mode_no_cook"` **or** a dedicated `status` extension — **exact enum M3-P3**. Do **not** claim `ok` without artifacts when preview forbids work.

---

## 20. Operator handoff when `not_applicable`

When engine automation is missing (`agent-ship.md` §3.7), the harness may skip subprocess launch and still write an envelope with `status: "fail"` and session outcome **`not_applicable`**. Cook subagent doc **does not** own session outcome vocabulary beyond cook-local `status` values; align with harness mapping **M3-P3**.

---

Status: M3-P2 (protocol stub). Unreal full impl: M8-P1. Unity/Godot: post-M8.
