# SHIP COOK — Engine Cook Pipeline

> **Role:** `/ship` harness — **Cook** phase subagent (logical role)  
> **Parent protocol:** `docs/_ai_system/agents/agent-ship.md` — read **§3 phase chain** (especially §3.2 Cook), **§4 Ship Guards** (pre-cook already passed; post-cook consumes this output), **§5 inputs**, **§6 outputs**, and **§11 subagent roster** before executing. This document is the normative stub for the **`agent-ship-cook`** row in that roster.  
> **Dispatch:** Only from the `/ship` harness in main chat per `agent-ship.md` activation rules. **`subagent_type`** remains **`generalPurpose`** per parent §11.1 — never gaming-named Cursor auto-types.

---

## 1. Role

Within `/ship`, **`agent-ship-cook`** is a **thin delegator**: it dispatches **`agent-cook-package-game`** with **`skip_package: true`** so only the **cook** internal phase runs. Pre-requisite **Ship Guards** (pre-cook, including **`ship.prod_readiness`**) have **already** passed; this role does **not** re-run production readiness.

The delegator **forwards** the child envelope to the harness, **filtered** to the **`cook`** row in `phases[]` (plus shared top-level fields: `status`, `mode`, `project_path`, `artifacts`, `error`, etc.). **`ship.cook_package`** (M8-P3) evaluates **`phases[*].status`** across cook, stage, and package; this dispatch satisfies **phase 1** of that multi-phase guard.

**Non-goal:** No direct **UAT** / subprocess invocation from this doc's role — all automation is owned by **`agent-cook-package-game`** (which uses **`unreal-build`** MCP tools only). See [`agent-cook-package-game.md`](./agent-cook-package-game.md).

---

## 2. Inputs

Pass-through to **`agent-cook-package-game`** §2 — **same JSON fields** as the child agent **except** do **not** set **`skip_cook`** (it stays **`false`** / omitted). The harness **MUST** set:

| Field | Required | Description |
|-------|----------|-------------|
| **`project_path`** | Yes | Absolute path to `.uproject` (from ship plan + manifest resolution). |
| **`target_platform`** | Yes | Single platform token for this invocation (for example `Win64`). |
| **`target_store`** | Yes | `steam` \| `epic` \| `gog` \| `itchio` \| `internal` (or null per child rules). |
| **`build_config`** | Yes | `Shipping` \| `Test` \| `Development` — maps from ship plan `cook_flavors`. |
| **`skip_package`** | Yes | **`true`** — cook-only dispatch. |
| **`caller`** | Yes | **`agent-ship-cook`** (scope matrix). |

**Optional** child fields (`maps`, `cultures`, `compression`, `output_dir`, `extra_uat_args`, `timeout_s`) follow **`agent-cook-package-game.md`** §2 when the harness supplies them.

**Legacy slim fields** (`PROJECT_KEY`, `APP_REPO`, `HUB_REPO`) MAY appear in Task envelopes for human context; the **normative** dispatch body is the child JSON above.

---

## 3. Outputs

| Output | Description |
|--------|-------------|
| **Child envelope** | Full **`agent-cook-package-game`** §3 object returned by the child call. |
| **Harness-facing view** | Same envelope **with `phases[]` filtered** to entries where **`name == "cook"`** (stage/package rows omitted from this subagent's return payload when the harness wants a cook-only summary; the trace tree may still retain the full child artifact). |
| **`status` propagation** | If the **cook** phase reports **`fail`** or **`error`**, or the child top-level `status` is **`fail`** / **`error`**, the delegator **MUST** surface that to `/ship` so **`ship.cook_package`** halts (unless advisory demotion or user-direct-debug override per `agent-ship.md` §7.1). |
| **`artifacts.cooked_content`** | From child envelope; feeds post-cook guards and downstream package dispatch. |

On success (`pass` / `dry_run` per child rules), **`phases[0].trace_dir`**, **`duration_s`**, and **`exit_code`** carry cook telemetry. On failure, the harness SHOULD attach **`unreal_tail_log`** output (last **20** lines per **`ship.cook_package`** contract in `ship-guards.md`).

---

## 4. Engine adapters (delegation)

**Unreal (Tier 1):** argv composition, MCP dispatch, and per-phase envelopes are defined in **`agent-cook-package-game.md`** §4–§6 and **`cook-package-commands.md`**. This file does **not** duplicate UAT spelling.

**Unity / Godot:** Out of scope for **`agent-cook-package-game`** until future milestones; `/ship` does not invoke this delegator for those engines until a child agent exists.

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

1. **Read parent context** — Confirm `agent-ship.md` §3.2 (cook phase) and active **`ship.cook_package`** policy in `.cuebert/config/cook-package-game.yaml` + `ship-guards.yaml`.  
2. **Build child request** — Construct **`agent-cook-package-game`** §2 JSON with **`skip_package: true`**, **`caller: "agent-ship-cook"`**, and ship-plan fields (`project_path`, `target_platform`, `target_store`, `build_config`, optional `maps` / `timeout_s`).  
3. **Dispatch child** — Invoke **`agent-cook-package-game`** (Task envelope points readers to **`agent-cook-package-game.md`**).  
4. **Evaluate cook outcome** — If the **cook** phase `status` is **`fail`** or **`error`**, or top-level child `status` is **`fail`** / **`error`**, return that failure to `/ship` **without** synthesizing a legacy §8 stub.  
5. **Filter and return** — Return the child envelope; if the harness requests a cook-only summary, **`phases`** contains **only** the **`cook`** entry.  
6. **Trace** — Persist under **`.cuebert/traces/ship/<timestamp>/cook/`** (`envelope.json`, logs) per §5; align paths with the child `trace_dir` when present.

---

## 8. Output envelope (JSON shape)

**Normative shape:** **`agent-cook-package-game.md`** §3. Illustrative **cook-only** return (filtered `phases`):

```json
{
  "status": "pass",
  "mode": "dry_run",
  "project_path": "/path/to/HelloLevel.uproject",
  "target_platform": "Win64",
  "target_store": "internal",
  "build_config": "Shipping",
  "phases": [
    {
      "name": "cook",
      "status": "pass",
      "duration_s": 120.5,
      "exit_code": 0,
      "trace_dir": ".cuebert/traces/build/example-cook-2026-04-20T15-30-00Z/",
      "detail": "Cooked 42 maps, 238 assets"
    }
  ],
  "artifacts": {
    "cooked_content": "/path/to/HelloLevel/Saved/Cooked/Win64/",
    "staged_build": null,
    "package_size_mb": null,
    "manifest_path": null
  },
  "error": null,
  "memory_id": null
}
```

**Legacy M3-P2 stub** (`status: ok`, `cooked_paths` map) is **deprecated** for Unreal once **`agent-cook-package-game`** dispatch is active; post-cook guards SHOULD read **`artifacts.cooked_content`** and **`phases[]`** from this envelope.

---

## 9. Non-goals

| Non-goal | Redirect |
|----------|----------|
| **Packaging** (zip, installer, platform-native) | `agent-ship-package.md` |
| **Certification / compliance scans** | `agent-ship-cert.md` (runs **after** package in `/ship`; not invoked from cook) |
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
| `agent-cook-package-game.md` | Child agent — argv, MCP dispatch, full envelope |
| `cook-package-commands.md` | UAT argv catalog |
| `agent-ship-package.md` | Sibling delegator for stage + package |

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

Status: M8-P3 (delegator to **`agent-cook-package-game`**). Unity/Godot: post-M8.
