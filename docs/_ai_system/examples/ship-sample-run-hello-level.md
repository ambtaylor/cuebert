# `/ship` sample dry run — `hello-level` (documentation only)

## 1. Purpose

This document is a **documentation-only dry run** that walks the **M3 `/ship` harness** from **pre-cook guards** through **Attest**, using a **hypothetical** Unreal project named **`hello-level`**. **No UAT cook runs.** **No Cursor Tasks run.** All JSON envelopes and trace paths are **illustrative** but aligned with:

- `docs/_ai_system/agents/agent-ship.md` (parent protocol)
- `docs/_ai_system/standards/ship-guards.md` (guard ids, evidence contract, §7 decision tree)
- `.cuebert/config/ship-guards.yaml` (default severities, thresholds, `spec_only_as_info`)
- `docs/_ai_system/agents/agent-ship-cook.md` §8, `agent-ship-cert.md` §7, `agent-ship-package.md` §8, `agent-ship-upload.md` §8 (output envelopes)

Use this file as the **M3 integration narrative**: it ties **Ship plan intent**, **guard phases**, **subagent envelopes**, and **on-disk traces** together before **M8-P1** (UE cook), **M8-P2** (cert engines), and **M8** (package validators) exist.

---

## 2. Scenario setup

### 2.1 Project

| Field | Value |
|-------|-------|
| **Project key** | `hello-level` |
| **Engine** | Unreal Engine **5.3.2** (hypothetical) |
| **Manifest note** | The committed hub `.cuebert/workspace-manifest.json` may still use `projects: {}`. This dry run assumes a **future** valid `projects.hello-level.ship` block per `ship-guards.md` §8 so `guard.project.ship_metadata` can show a real **`pass`** in M3-P3 wiring narratives. |

### 2.2 Ship intent

Produce **offline zips** for **Win64** and **Mac**, **shipping** flavor, **version 0.1.0**, **build 42**, suitable for handoff to a publisher QA drop **without** store upload.

### 2.3 Declared ship parameters (plan-equivalent)

| Field | Value |
|-------|-------|
| **semver** | `0.1.0` |
| **build_number** | `42` |
| **internal_label** | `publisher-qa-drop-1` |
| **target_platforms** | `Win64`, `Mac` |
| **cook_flavor** | `shipping` |
| **package_format** | `zip` |
| **cert_profile** | `indie-light` |
| **upload_channel** | `none` (offline bundle) |
| **dry_run** | `true` (belt-and-suspenders with upload default) |

### 2.4 Success criteria (ship)

- Pre-cook **`verdict: pass`** with `guard.project.ship_metadata` **passing** against §8 schema.  
- Cook envelope shows **`exit_code: 0`**, both platforms cooked, **durations within** `global.cook_max_duration_s`.  
- Post-cook size guard within **warn** threshold (no escalation to fail).  
- Cert envelope shows **`verdict: warn`** with **zero** `fail` findings; post-cert **`guard.cert.severity_floor`** allows up to **10** warns.  
- Package envelope lists **two** zips with **SHA-256** digests and **`deterministic: true`**.  
- Post-package guards **pass**.  
- Upload phase **skipped** with explicit **`skip`** in `upload/envelope.json`.  
- Attest rollup **`verdict: pass`** at trace root; memory **`milestone_commit`** simulated.

### 2.5 Guard catalog reference (all 14 ids)

From `.cuebert/config/ship-guards.yaml` / `ship-guards.md` §2:

1. `guard.git.clean` — pre-cook  
2. `guard.git.untracked_cook_paths` — pre-cook  
3. `guard.engine.version_match` — pre-cook  
4. `guard.project.ship_metadata` — pre-cook  
5. `guard.assets.referenced_in_cook` — pre-cook  
6. `guard.cook.exit_code` — post-cook  
7. `guard.cook.size_budget` — post-cook  
8. `guard.cook.missing_assets` — post-cook  
9. `guard.cert.severity_floor` — post-cert  
10. `guard.cert.required_checklists` — post-cert  
11. `guard.cert.report_emitted` — post-cert  
12. `guard.package.exists` — post-package  
13. `guard.package.checksum` — post-package  
14. `guard.package.manifest` — post-package  

**Verdict vocabulary** for findings: `pass`, `warn`, `fail`, `info` (per `ship-guards.md` §5 and `spec_only_as_info` policy).

---

## 3. Harness timeline (happy path)

The ordered traversal matches **`ship-guards.md` §7** (and `agent-ship.md` §7):

1. **PRE-COOK GUARDS** — load YAML + overrides; stable sort by `guard_id`; on **`fail`**, halt before cook. Includes **`ship.prod_readiness`** (`agent-prod-readiness-game`) per **M7-P3**.  
2. **COOK** — dispatch `agent-ship-cook`.  
3. **POST-COOK GUARDS** — consume cook envelope + disk; halt before cert on **`fail`**. Includes **`ship.qa_resilience`** (`agent-qa-resilience-game`, `session_kind: build`) per **M7-P3**.  
4. **CERT** — dispatch `agent-ship-cert` when `cert_profile != none`.  
5. **POST-CERT GUARDS** — severity floor + checklist + report emission.  
6. **PACKAGE** — dispatch `agent-ship-package`.  
7. **POST-PACKAGE GUARDS** — exists / checksum / manifest.  
8. **UPLOAD** — optional; skipped here (`upload_channel: none`).  
9. **ATTEST** — always; rollup `envelope.json` + memory hooks (**`milestone_commit`** on this happy path).

Each subsection lists **step**, **actor**, **conceptual inputs**, **representative JSON**, and **verdict / next**.

---

### 3.1 Step — Pre-cook guards

**Actor:** harness guard runner (pre-cook class).  
**Sample input (conceptual):**

```text
PROJECT_KEY=hello-level
ENGINE=unreal
ENGINE_VERSION=5.3.2
GUARD_CONFIG=.cuebert/config/ship-guards.yaml
SPEC_ONLY_AS_INFO=true
SHIP_METADATA_PRESENT=true
```

**Evaluated guards (five):** `guard.git.clean`, `guard.git.untracked_cook_paths`, `guard.engine.version_match`, `guard.project.ship_metadata`, `guard.assets.referenced_in_cook`.

**Outcomes for this clean example:**

- First **four** guards report **`info`** where evaluators remain **spec-only**, **except** `guard.project.ship_metadata` which is **`pass`** in this M3-P3 narrative because the **`ship`** schema is now documented and treated as **checkable** by the harness bootstrap for manifest presence.  
- `guard.assets.referenced_in_cook` → **`info`** (graph evaluator **M8**).  

**Stable sort note:** `guard.assets.referenced_in_cook`, `guard.engine.version_match`, `guard.git.clean`, `guard.git.untracked_cook_paths`, `guard.project.ship_metadata` (lexicographic by `guard_id`).

**Representative `guards/pre_cook.json`:** see the committed fixture at `.cuebert/traces/ship/example-2026-04-20T12-30-00Z/guards/pre_cook.json` (five `pre_cook` rows: four `info` spec-only stubs plus one `pass` for `guard.project.ship_metadata`).

**Phase verdict:** `pass`.  
**Next:** **`ship.prod_readiness`** (M7-P3), then dispatch **`agent-ship-cook`**.

---

### 3.1a Phase: pre_cook (M7-P3 enforcement) — `ship.prod_readiness`

**Dispatch:** `agent-prod-readiness-game`

**Sample request:**

```json
{
  "project_path": "/path/to/HelloLevel.uproject",
  "target_platform": "Mac",
  "target_store": "internal",
  "build_config": "Shipping",
  "caller": "agent-ship"
}
```

**Sample response (pass):**

```json
{
  "status": "pass",
  "mode": "live",
  "findings": [],
  "summary": {
    "total_rules_evaluated": 14,
    "reject_count": 0,
    "info_count": 0,
    "skipped_count": 0
  },
  "rule_version": "1.0.0"
}
```

**Alternate response (reject variant):**

```json
{
  "status": "fail",
  "findings": [
    {
      "rule_id": "security.remote_control_disabled_shipping",
      "category": "security",
      "severity": "reject",
      "detail": "bEnable=True in [RemoteControl] section of Config/DefaultEngine.ini",
      "remediation_hint": "Set bEnable=False or remove the plugin."
    }
  ],
  "summary": {
    "reject_count": 1,
    "info_count": 0
  }
}
```

**/ship** halts with an error envelope surfacing the finding.

---

### 3.2 Step — `agent-ship-cook`

**Actor:** `agent-ship-cook` (future `generalPurpose` Task).  
**Sample input (conceptual):**

```text
APP_REPO=/abs/path/hello-level
COOK_FLAVOR=shipping
TARGET_PLATFORMS=Win64,Mac
OUTPUT_DIR=.cuebert/traces/ship/example-2026-04-20T12-30-00Z/cooked/
```

**Sample output (`cook/envelope.json`)** — shape per **`agent-ship-cook.md` §8**:

```json
{
  "status": "ok",
  "exit_code": 0,
  "duration_ms": 900000,
  "platforms_cooked": ["Win64", "Mac"],
  "cooked_paths": {
    "Win64": ".cuebert/traces/ship/example-2026-04-20T12-30-00Z/cooked/Win64/",
    "Mac": ".cuebert/traces/ship/example-2026-04-20T12-30-00Z/cooked/Mac/"
  },
  "content_size_bytes": {
    "Win64": 3221225472,
    "Mac": 3000000000
  },
  "log_tail_path": ".cuebert/traces/ship/example-2026-04-20T12-30-00Z/cook/engine.log",
  "notes": "Hypothetical UAT cook success for hello-level 0.1.0 build 42; both platforms within 5GB warn budget."
}
```

**Interpretation:** **15 minutes** wall time (`900000` ms), **`exit_code: 0`**, sizes **under** `cook_default_budget_bytes` (`5368709120`).  
**Phase verdict:** `pass`.  
**Next:** **post-cook guards**.

---

### 3.3 Step — Post-cook guards

**Actor:** harness guard runner (post-cook class).  
**Sample highlights:**

- `guard.cook.exit_code` → **`info`** (spec-only wiring) **or** **`pass`** when harness maps `exit_code==0` — this example uses **`info`** for the stub with a note that M8-P1 will promote to strict pass/fail. For narrative simplicity below, treat **effective halt decision** as **continue** because **`exit_code`** is **0** in the cook envelope.  
- `guard.cook.size_budget` → **`pass`** / **`info`** — sizes under **`warn_bytes`**.  
- `guard.cook.missing_assets` → **`info`**.

**Representative `guards/post_cook.json`:** see `.cuebert/traces/ship/example-2026-04-20T12-30-00Z/guards/post_cook.json` (three post-cook rows; all `info` in this doc-only pass, with cook log pointer evidence).

**Phase verdict:** `pass`.  
**Next:** **`ship.qa_resilience`** (M7-P3), then **`agent-ship-cert`**.

---

### 3.3a Phase: post_cook (M7-P3 enforcement) — `ship.qa_resilience`

**Dispatch:** `agent-qa-resilience-game` with **`session_kind: build`** (cook log scan).

**Sample request:**

```json
{
  "project_path": "/path/to/HelloLevel.uproject",
  "session_kind": "build",
  "artifacts": {
    "gauntlet_log_dir": null,
    "pie_log_path": null,
    "build_log_path": ".cuebert/traces/ship/example-2026-04-20T12-30-00Z/cook/engine.log",
    "screenshots_dir": null
  },
  "caller": "agent-ship"
}
```

**Sample response (pass):**

```json
{
  "status": "pass",
  "mode": "live",
  "session_kind": "build",
  "findings": [],
  "metrics": {
    "runtime_seconds": 900.0,
    "hitch_count": 0,
    "hitches_per_minute": 0.0,
    "peak_memory_mb": 2048.0,
    "memory_growth_mb_per_minute": 2.5,
    "ensure_count": 0,
    "crash_count": 0,
    "streaming_stall_count": 0
  },
  "rule_version": "1.0.0"
}
```

**Alternate response (fail variant — `crash.fatal_signal`):**

```json
{
  "status": "fail",
  "mode": "live",
  "session_kind": "build",
  "findings": [
    {
      "category": "crash",
      "severity": "critical",
      "detail": "Fatal signal SIGSEGV in cook log tail",
      "evidence": {
        "log_path": ".cuebert/traces/ship/example-2026-04-20T12-30-00Z/cook/engine.log",
        "line_number": 18440,
        "screenshot_path": null,
        "metric_value": null,
        "threshold": null
      },
      "rule_id": "crash.fatal_signal"
    }
  ],
  "metrics": {
    "runtime_seconds": 120.0,
    "hitch_count": 0,
    "hitches_per_minute": 0.0,
    "peak_memory_mb": 1800.0,
    "memory_growth_mb_per_minute": 5.0,
    "ensure_count": 0,
    "crash_count": 1,
    "streaming_stall_count": 0
  },
  "rule_version": "1.0.0"
}
```

**/ship** halts with a structured error envelope including the **metrics** snapshot.

Fixture envelopes (committed): `.cuebert/traces/ship/example-2026-04-20T15-00-00Z/prod_readiness/` and `qa_resilience/`.

---

### 3.4 Step — `agent-ship-cert`

**Actor:** `agent-ship-cert`.  
**Sample input:**

```text
CERT_PROFILE=indie-light
COOKED_PATHS_JSON={"Win64":".../cooked/Win64/","Mac":".../cooked/Mac/"}
REPORT_PATH=.cuebert/traces/ship/example-2026-04-20T12-30-00Z/cert/report.md
```

**Sample output (`cert/envelope.json`)** — per **`agent-ship-cert.md` §7`; full JSON on disk at `.cuebert/traces/ship/example-2026-04-20T12-30-00Z/cert/envelope.json` (`verdict: warn`, two warn-level findings, zero fail).

**Human report:** see committed **`cert/report.md`** in the trace fixture (two warns, **no** fails).  
**Phase verdict:** `warn` (allowed).  
**Next:** **post-cert guards**.

---

### 3.5 Step — Post-cert guards

**Actor:** harness guard runner (post-cert class).  
**Highlights:**

- `guard.cert.severity_floor` → **`pass`** — `max_fail_findings: 0` satisfied; `warn` count **2** **<=** `max_warn_findings: 10`.  
- `guard.cert.report_emitted` → **`pass`** — `report.md` exists and is non-empty.  
- `guard.cert.required_checklists` remains **spec-only** in this fixture (evaluator **M8-P2**); harness MAY fold it into post-cert once checklist coverage exists.

**Phase verdict:** `pass`.  
**Next:** **`agent-ship-package`**.

---

### 3.6 Step — `agent-ship-package`

**Actor:** `agent-ship-package`.  
**Sample output (`package/envelope.json`)** — shape per **`agent-ship-package.md` §8** (fixture path uses **`package/`** directory per M3-P3 example tree; artifact **paths** remain hub-relative):

```json
{
  "packages": [
    {
      "platform": "Win64",
      "format": "zip",
      "path": ".cuebert/traces/ship/example-2026-04-20T12-30-00Z/package/hello-level_0.1.0_Win64_shipping.zip",
      "size_bytes": 2800000000,
      "sha256": "a1b2c3d4e5f6789012345678901234567890abcd1234567890abcdef12345678",
      "deterministic": true
    },
    {
      "platform": "Mac",
      "format": "zip",
      "path": ".cuebert/traces/ship/example-2026-04-20T12-30-00Z/package/hello-level_0.1.0_Mac_shipping.zip",
      "size_bytes": 2650000000,
      "sha256": "b2c3d4e5f6789012345678901234567890abcde234567890abcdef1234567890a1",
      "deterministic": true
    }
  ],
  "manifest_path": ".cuebert/traces/ship/example-2026-04-20T12-30-00Z/package/manifest.json",
  "verdict": "pass"
}
```

**Note:** The **ASCII tree** in §5 lists **`package/envelope.json`** only for brevity; a real M8 run may also materialize **`manifest.json`** beside archives. This example names **`manifest_path`** for **`guard.package.manifest`** consumption.

**Phase verdict:** `pass`.  
**Next:** **post-package guards**.

---

### 3.7 Step — Post-package guards

**Highlights:**

- `guard.package.exists` → **`pass`**.  
- `guard.package.checksum` → **`pass`** (recompute matches envelope).  
- `guard.package.manifest` → **`pass`**.

**Phase verdict:** `pass`.  
**Next:** **Upload** evaluation.

---

### 3.8 Step — Upload (skipped)

**Actor:** harness short-circuit (no `agent-ship-upload` Task).  
**Sample `upload/envelope.json`:**

```json
{
  "dry_run": true,
  "upload_channel": "none",
  "verdict": "skip",
  "uploads": [],
  "notes": "Upload phase skipped: upload_channel=none per ship plan."
}
```

**Phase verdict:** `skip`.  
**Next:** **Attest**.

---

### 3.9 Step — Attest + memory

**Actor:** main-chat harness.  
**Rollup `envelope.json` (truncated):**

```json
{
  "schema_version": 1,
  "ship_run_id": "example-2026-04-20T12-30-00Z",
  "project": "hello-level",
  "engine": "unreal",
  "engine_version": "5.3.2",
  "git_sha": "deadbeefcafe0000",
  "started_at": "2026-04-20T12:30:00Z",
  "ended_at": "2026-04-20T12:55:00Z",
  "duration_ms": 1500000,
  "verdict": "pass",
  "phase_verdicts": {
    "pre_cook": "pass",
    "cook": "pass",
    "post_cook": "pass",
    "cert": "warn",
    "post_cert": "pass",
    "package": "pass",
    "post_package": "pass",
    "upload": "skip"
  },
  "artifacts": {
    "trace_root": ".cuebert/traces/ship/example-2026-04-20T12-30-00Z/"
  },
  "findings": []
}
```

**Memory (simulated):** `milestone_commit` with `project`, `version` (`semver`, `build_number`), `target_platforms`, **`envelope.json` path**, primary artifact paths per **`agent-ship.md` §13**. **Text mode** (`CUEBERT_MEMORY_MODE=text`) remains sufficient — no embedding requirement.

---

## 4. Failure variants (envelopes that change)

Each variant assumes the same Plan intent as §2 until the failure point.

---

### 4.A Uncommitted changes (`guard.git.clean`)

**Trigger:** Modified `Content/Maps/TestMap.umap` not committed; **`guard.git.clean`** evaluator enforced (post-**M8-P1**), or bootstrap fail in strict mode.

**Harness path:** Step **1.c** — **halt** before cook.

**`guards/pre_cook.json` (illustrative finding only):**

```json
{
  "schema_version": 1,
  "phase": "pre_cook",
  "verdict": "fail",
  "guards": {
    "pre_cook": [
      {
        "guard_id": "guard.git.clean",
        "class": "pre-cook",
        "severity": "fail",
        "message": "Working tree not clean for declared ship scope.",
        "evidence": {
          "type": "file",
          "path": "Content/Maps/TestMap.umap",
          "detail": "modified: working tree diff present"
        }
      }
    ],
    "post_cook": [],
    "post_cert": [],
    "post_package": []
  }
}
```

**Final rollup differs:** `verdict: fail`, `phase_verdicts.pre_cook: fail`, cook **not** dispatched, **`troubleshoot_commit`** with envelope pointer.

---

### 4.B Cook fails (`guard.cook.exit_code`)

**Trigger:** Cook subprocess exits **1**; `LogInit: Error:` tail captured.

**Harness path:** Post-cook step — **`guard.cook.exit_code`** **`fail`** → **no cert**.

**`guards/post_cook.json` (illustrative):**

```json
{
  "schema_version": 1,
  "phase": "post_cook",
  "verdict": "fail",
  "guards": {
    "pre_cook": [],
    "post_cook": [
      {
        "guard_id": "guard.cook.exit_code",
        "class": "post-cook",
        "severity": "fail",
        "message": "Cook returned non-zero exit code.",
        "evidence": {
          "type": "log",
          "path": ".cuebert/traces/ship/example-2026-04-20T12-30-00Z/cook/engine.log",
          "detail": "exit_code=1; tail contains LogCook: Error: staged failure (example)"
        }
      }
    ],
    "post_cert": [],
    "post_package": []
  }
}
```

**Cook envelope excerpt:**

```json
{
  "status": "fail",
  "exit_code": 1,
  "duration_ms": 120000,
  "platforms_cooked": ["Win64"],
  "notes": "Cook aborted before Mac slice completed."
}
```

**Memory:** `troubleshoot_commit` citing **post_cook** phase.

---

### 4.C Cert severity floor breached (`guard.cert.severity_floor`)

**Trigger:** Cert emits **`fail`** finding — example: **missing exe icon** for `indie-light` policy in this hypothetical catalog.

**`cert/envelope.json` excerpt:**

```json
{
  "profile": "indie-light",
  "verdict": "fail",
  "findings": [
    {
      "check_id": "cert.indie-light.icon-required",
      "profile": "indie-light",
      "severity": "fail",
      "evidence": {
        "type": "file",
        "path": ".cuebert/traces/ship/example-2026-04-20T12-30-00Z/cooked/Win64/HelloLevel-Win64-Shipping.exe",
        "detail": "Icon resource missing for Windows executable"
      },
      "message": "Shipping executable missing required icon metadata for indie-light profile."
    }
  ],
  "platform_summaries": {
    "Win64": { "checks_run": 5, "fail": 1, "warn": 0, "info": 0 },
    "Mac": { "checks_run": 0, "fail": 0, "warn": 0, "info": 0 }
  },
  "report_path": ".cuebert/traces/ship/example-2026-04-20T12-30-00Z/cert/report.md"
}
```

**Post-cert guard:** `guard.cert.severity_floor` → **`fail`** (`max_fail_findings: 0`). **Package not dispatched.**

---

### 4.D Package checksum mismatch (`guard.package.checksum`)

**Trigger:** Disk corruption or tampering — recomputed SHA-256 **does not** match `package/envelope.json` value.

**`guards/post_package.json` (illustrative):**

```json
{
  "schema_version": 1,
  "phase": "post_package",
  "verdict": "fail",
  "guards": {
    "pre_cook": [],
    "post_cook": [],
    "post_cert": [],
    "post_package": [
      {
        "guard_id": "guard.package.checksum",
        "class": "post-package",
        "severity": "fail",
        "message": "Checksum mismatch for Win64 zip.",
        "evidence": {
          "type": "file",
          "path": ".cuebert/traces/ship/example-2026-04-20T12-30-00Z/package/hello-level_0.1.0_Win64_shipping.zip",
          "detail": "expected a1b2...5678 recomputed c0ffee...beef"
        }
      }
    ]
  }
}
```

**Upload:** **not run**; aggregate envelope marks **`upload_status: BLOCKED`** (terminology per parent §3.7 **`blocked`** vocabulary). **`troubleshoot_commit`** with **post_package** phase.

---

## 5. Trace artifacts on disk (ASCII tree)

Committed example (text only; **no** binary zips checked in):

```text
example-2026-04-20T12-30-00Z/
├── README.md
├── envelope.json
├── guards/
│   ├── pre_cook.json
│   ├── post_cook.json
│   ├── post_cert.json
│   └── post_package.json
├── cook/
│   ├── envelope.json
│   └── engine.log  (illustrative 200 lines)
├── cert/
│   ├── envelope.json
│   └── report.md
├── package/
│   └── envelope.json
└── upload/
    └── envelope.json
```

Hub path prefix: `.cuebert/traces/ship/`. Aligns with **`control-plane-paths.md`** hub-local traces.

---

## 6. How to use this example

- **When M8-P1 lands UE cook**, promote this scenario to an automated **smoke `/ship`** against a template repo: same platforms, same guard chain, real **UAT** logs.  
- **Subagent prompt authors** mirror JSON shapes in `cook/`, `cert/`, `package/`, `upload/`, and `guards/` when writing slim Task envelopes.  
- **Humans authoring `/ship` plans** start from `docs/projects/_templates/ship-plan-template.md` and cross-check expectations against **`ship-guards.md` §7** and §2.

---

## 7. Footer

**Status:** M3-P3 (doc-only example). **Real executable run:** M8-P1 (cook) + M8-P2 (cert) + M8-P3 (package/upload wiring).  
**Fixture commit path:** `.cuebert/traces/ship/example-2026-04-20T12-30-00Z/` (curated exception under `.gitignore`).

---

## 8. Override walk-through (user-direct-debug)

**Caller:** `user-direct-debug`  
**Flag:** `--override=accept-risk`  
**Finding:** `ship.prod_readiness` returns a **REJECT** finding for **`content.no_placeholder_assets`**.

**Expected behavior:**

- `/ship` proceeds past pre-cook.
- **`troubleshoot_commit`** is called with severity **`warn`**, body containing the bypassed finding(s).
- Final **`/ship`** envelope includes **`"override_applied": true`** and **`"overridden_findings": [...]`**.
