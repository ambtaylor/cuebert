# `/play` sample dry run — `hello-level` (documentation only)

## 1. Purpose

This document is a **documentation-only dry run** that walks the **M2 `/play` harness** from **pre-author guards** through **Merge**, using a **hypothetical** Unreal project named `hello-level`. **No engine is launched.** **No Cursor Tasks run.** All JSON envelopes and trace paths are **illustrative** but aligned with:

- `docs/_ai_system/agents/agent-play.md` (parent protocol)
- `docs/_ai_system/standards/play-preview-guards.md` (guard ids, evidence contract, §7 decision tree)
- `.cuebert/config/play-guards.yaml` (default severities and `spec_only_as_info`)
- `docs/_ai_system/agents/agent-play-author.md` §7, `agent-play-preview.md` §9, `agent-play-qa.md` §7 (output envelopes)

Use this file as the **M2 integration narrative**: it ties **Plan intent**, **guard phases**, **subagent envelopes**, and **on-disk traces** together before **M5-P1** (UE bridge) and **M6-P2** (Gauntlet / log evaluators) exist.

---

## 2. Scenario setup

### 2.1 Project

| Field | Value |
|-------|-------|
| **Project key** | `hello-level` |
| **Engine** | Unreal Engine 5.3 (hypothetical) |
| **Manifest note** | Not registered in the committed `.cuebert/workspace-manifest.json` (`projects` is `{}` in the hub today). The dry run still labels envelopes with `hello-level` as the **intended** `PROJECT_KEY`. |

### 2.2 Change intent

Replace the **placeholder cube** in `TestMap.umap` with an **engine sphere**, adjust its **material color toward red**, and confirm that **preview evidence** (screenshot + log) shows a **red sphere near the world origin** after load.

### 2.3 Declared scope (globs)

```text
Content/Maps/TestMap.umap
Source/Game/Placeholder/**/*.cpp
Source/Game/Placeholder/**/*.h
```

Any Author edit outside these globs is **policy failure** for `guard.scope.bleed` (post-author).

### 2.4 Success criteria (QA)

- At least **one** screenshot artifact exists under `preview/screenshots/` when capture mode expects frames.
- **Zero** `Fatal:` lines in the preview log window for this session.
- **Zero** ERROR-class lines counted by `guard.log.error_floor` for this **clean** example (thresholds from YAML).
- Author `compile_status` is **`ok`** (or a documented `skip` with harness policy — here **`ok`**).
- Visual intent: screenshot shows a **red spherical** mesh at the origin (human QA; stubbed as placeholder file in M2-P4 fixtures).

### 2.5 Preview map

`/Game/Maps/TestMap.TestMap` (matches `TestMap.umap`).

### 2.6 Guard catalog reference (all 10 ids)

From `.cuebert/config/play-guards.yaml` / `play-preview-guards.md` §2:

1. `guard.project.exists` — pre-author  
2. `guard.engine.reachable` — pre-author  
3. `guard.scope.allowlist` — pre-author  
4. `guard.compile.status` — post-author  
5. `guard.scope.bleed` — post-author  
6. `guard.asset.refs_valid` — post-author  
7. `guard.preview.ready_marker` — post-preview  
8. `guard.log.fatal` — post-preview  
9. `guard.log.error_floor` — post-preview  
10. `guard.screenshot.exists` — post-preview  

**Verdict vocabulary** for findings in this example: `pass`, `warn`, `fail`, `info` only (per `play-preview-guards.md` and M2-P3 policy for spec-only evaluators surfaced as **`info`** when `global.spec_only_as_info` is **`true`**).

---

## 3. Harness timeline (happy path)

The ordered traversal matches **`play-preview-guards.md` §7**:

1. **PRE-AUTHOR** — load YAML + manifest overrides; run enabled pre-author guards in **stable sorted guard_id order**; on any resolved **`fail`**, STOP.  
2. **AUTHOR** — dispatch `agent-play-author`.  
3. **POST-AUTHOR** — diff vs declared scope; compile/asset gates; on **`fail`**, STOP (no Preview).  
4. **PREVIEW** — dispatch `agent-play-preview`; write `preview/envelope.json`, `engine.log`, screenshots.  
5. **POST-PREVIEW** — log + screenshot probes; failures mark session **blocked** for Merge per parent §3.7 / §9.  
6. **QA** — `agent-play-qa` reads preview artifacts; emits `qa/envelope.json`.  
7. **MERGE** — harness writes **final rollup** `envelope.json` at trace root; **no `git add` / commit** in this example (operator policy; parent §3.5).

Each subsection below lists **step name**, **actor**, **sample input**, **sample output envelope**, and **verdict / next**.

---

### 3.1 Step — Pre-author guards

**Actor:** harness guard runner (pre-author class).  
**Sample input (conceptual):**

```text
PROJECT_KEY=hello-level
ENGINE=unreal
DECLARED_SCOPE=Content/Maps/TestMap.umap;Source/Game/Placeholder/**/*.cpp;Source/Game/Placeholder/**/*.h
GUARD_CONFIG=.cuebert/config/play-guards.yaml
SPEC_ONLY_AS_INFO=true
```

**Sample output (`guards/pre_author.json` slice):** `guard.engine.reachable` and `guard.project.exists` report **`info`** (evaluators not shipped; stub honest about spec-only). `guard.scope.allowlist` reports **`pass`** because declared globs stay out of hub meta trees (no `.cuebert/` paths in scope).

**Stable sort note:** Evaluators run in guard_id order: `guard.engine.reachable`, `guard.project.exists`, `guard.scope.allowlist`.

**Representative envelope (abbreviated):**

```json
{
  "schema_version": 1,
  "phase": "pre_author",
  "verdict": "pass",
  "guards": {
    "pre_author": [
      {
        "guard_id": "guard.engine.reachable",
        "class": "pre-author",
        "severity": "info",
        "message": "Evaluator spec-only (M5-P1); harness recorded stub outcome while spec_only_as_info is true."
      },
      {
        "guard_id": "guard.project.exists",
        "class": "pre-author",
        "severity": "info",
        "message": "Evaluator spec-only (M5-P1); manifest lookup illustrative for hello-level dry run."
      },
      {
        "guard_id": "guard.scope.allowlist",
        "class": "pre-author",
        "severity": "pass",
        "message": "Declared globs do not target hub meta trees."
      }
    ]
  }
}
```

**Phase verdict:** `pass` (no **`fail`** severities after resolution).  
**Next:** dispatch **Author**.

---

### 3.2 Step — `agent-play-author`

**Actor:** `agent-play-author` (future `generalPurpose` Task).  
**Sample input (conceptual):**

```text
APP_REPO=/abs/path/hello-level
DECLARED_SCOPE=<as above>
CHANGE_LIST=swap cube mesh for engine sphere; tint material red
```

**Sample output (`author/envelope.json`):**

```json
{
  "files_changed": [
    "Content/Maps/TestMap.umap",
    "Source/Game/Placeholder/PlaceholderCube.cpp",
    "Source/Game/Placeholder/PlaceholderCube.h"
  ],
  "compile_status": "ok",
  "notes": "Replaced StaticMeshComponent cube reference with engine sphere. Adjusted material color."
}
```

**Note on schema drift:** The canonical author doc (`agent-play-author.md` §7) prefers `files_changed` as an array of objects with `{ "path", "action", "summary" }`. This **M2-P4** example uses a **string list** for readability; harness implementations SHOULD normalize to the §7 object form when parsing.

**Phase verdict:** `pass` (Author completed; no harness-level abort).  
**Next:** **post-author guards**.

---

### 3.3 Step — Post-author guards

**Actor:** harness guard runner (post-author class).  
**Sample input:** Author envelope + workspace diff snapshot (files touched).  
**Sample output highlights:**

- `guard.compile.status` → **`info`** (M6-P1 evaluator; spec-only; author already claimed `ok`).  
- `guard.scope.bleed` → **`pass`** (all touched paths under declared globs).  
- `guard.asset.refs_valid` → **`info`** (M5-P3 deep validation not run).

**Phase verdict:** `pass`.  
**Next:** dispatch **Preview** (would launch PIE in a real milestone).

---

### 3.4 Step — `agent-play-preview`

**Actor:** `agent-play-preview`.  
**Sample input:**

```text
ARTIFACT_DIR=.cuebert/traces/play/example-2026-04-20T12-00-00Z/preview/
CAPTURE_MODE=screenshots
PREVIEW_MAP=/Game/Maps/TestMap.TestMap
```

**Sample output (`preview/envelope.json`):**

```json
{
  "status": "ok",
  "screenshots": [
    ".cuebert/traces/play/example-2026-04-20T12-00-00Z/preview/screenshots/frame_0001.png.txt"
  ],
  "log_tail": "LogWorld: UWorld::CleanupWorld for TestMap, bSessionEnded=true, bCleanupResources=true\nLogWorld: BeginTearingDown for /Game/Maps/TestMap\nLogPlayLevel: Display: Shutting down PIE online subsystems\nLogSlate: Updating window title bar state: overlay mode, drag disabled, window buttons hidden, title bar hidden\nLogAudio: Display: Audio Device unregistered from world 0.\nLogUObjectHash: Compacting FUObjectHashTables data took   0.42ms\nLogPlayLevel: Display: Destroying online subsystem :Context_1\nLogExit: Preparing to exit.\nLogRenderer: Display: Waited for render fences 0.0 ms\nLogExit: Exiting.",
  "exit_code": 0,
  "duration_ms": 15000
}
```

**Illustrative log tail (10 lines as they might appear in a real `engine.log`):**

```text
LogWorld: UWorld::CleanupWorld for TestMap, bSessionEnded=true, bCleanupResources=true
LogWorld: BeginTearingDown for /Game/Maps/TestMap
LogPlayLevel: Display: Shutting down PIE online subsystems
LogSlate: Updating window title bar state: overlay mode, drag disabled, window buttons hidden, title bar hidden
LogAudio: Display: Audio Device unregistered from world 0.
LogUObjectHash: Compacting FUObjectHashTables data took   0.42ms
LogPlayLevel: Display: Destroying online subsystem :Context_1
LogExit: Preparing to exit.
LogRenderer: Display: Waited for render fences 0.0 ms
LogExit: Exiting.
```

The committed fixture `preview/engine.log` is **200 lines** of synthetic Unreal-style chatter ending in a clean shutdown; it includes `LogLoad: (1.12s) LoadMap: /Game/Maps/TestMap.TestMap` and `LogPlayLevel: Display: Game engine initialized.` as **readiness-adjacent** anchors for future `guard.preview.ready_marker` regex packs (**M5-P1**).

**Phase verdict:** `pass` (`status: ok`, `exit_code: 0`).  
**Next:** **post-preview guards**.

---

### 3.5 Step — Post-preview guards

**Actor:** harness guard runner (post-preview class).  
**Sample output highlights:**

- `guard.preview.ready_marker` → **`info`** (spec-only; log lines exist but evaluator not wired).  
- `guard.log.fatal` → **`pass`** (no `Fatal:` matches in this clean fixture).  
- `guard.log.error_floor` → **`pass`** (0 ERROR-class lines vs thresholds `warn: 1`, `fail: 5`).  
- `guard.screenshot.exists` → **`pass`** (placeholder capture file present for the example).

**Phase verdict:** `pass`.  
**Next:** **QA**.

---

### 3.6 Step — `agent-play-qa`

**Actor:** `agent-play-qa`.  
**Sample input:** paths to `preview/envelope.json`, `preview/engine.log`, `preview/screenshots/`, and guard JSON pointers.  
**Sample output (`qa/envelope.json`):**

```json
{
  "verdict": "pass",
  "findings": [],
  "summary": "1 screenshot captured; no Fatal entries; compile ok."
}
```

**Phase verdict:** `pass`.  
**Next:** **Merge** (rollup only in this doc).

---

### 3.7 Step — Merge (harness-owned)

**Actor:** main-chat harness (not a named forbidden `subagent_type`).  
**Behavior in this dry run:**

- Writes final **`envelope.json`** at `.cuebert/traces/play/example-2026-04-20T12-00-00Z/envelope.json` with `schema_version`, `play_run_id`, timestamps, `verdict: pass`, `phase_verdicts`, and an **`artifacts`** map pointing at per-phase JSON and logs.  
- **Does not** stage or commit the application repo; local branch commit remains **per-project policy** (parent `agent-play.md` §3.5).

**Sample final rollup (truncated `artifacts` for brevity in this doc — full file is on disk):**

```json
{
  "schema_version": 1,
  "play_run_id": "example-2026-04-20T12-00-00Z",
  "project": "hello-level",
  "engine": "unreal",
  "started_at": "2026-04-20T12:00:00Z",
  "ended_at": "2026-04-20T12:00:45Z",
  "duration_ms": 45000,
  "verdict": "pass",
  "phase_verdicts": {
    "pre_author": "pass",
    "post_author": "pass",
    "post_preview": "pass",
    "qa": "pass"
  },
  "artifacts": {
    "trace_root": ".cuebert/traces/play/example-2026-04-20T12-00-00Z/"
  },
  "findings": []
}
```

**Session outcome:** `complete` from the operator’s perspective (guards + QA passed); Merge **did not** mutate git.

---

## 4. Failure variants (envelopes that change)

Each variant assumes the same Plan intent as §2 until the failure point.

---

### 4.A Scope bleed (`guard.scope.bleed`)

**Trigger:** Author also edits `.cuebert/version.json` (hub file; outside declared gameplay globs).

**Harness path (§7):** POST-AUTHOR step **c** — **`fail`** → STOP; **Preview never runs**.

**`guards/post_author.json` (illustrative finding only):**

```json
{
  "schema_version": 1,
  "phase": "post_author",
  "verdict": "fail",
  "guards": {
    "post_author": [
      {
        "guard_id": "guard.scope.bleed",
        "class": "post-author",
        "severity": "fail",
        "message": "Changed file outside declared scope.",
        "evidence": {
          "type": "file",
          "path": ".cuebert/version.json",
          "detail": "not matched by DECLARED_SCOPE globs"
        }
      }
    ]
  }
}
```

**Final rollup `envelope.json` fields that differ:**

```json
{
  "verdict": "fail",
  "phase_verdicts": {
    "pre_author": "pass",
    "post_author": "fail",
    "post_preview": "info",
    "qa": "info"
  },
  "findings": [
    {
      "guard_id": "guard.scope.bleed",
      "severity": "fail",
      "phase": "post_author",
      "message": "Preview skipped due to scope bleed."
    }
  ]
}
```

**Operator next step:** shrink or correct Author output; widen scope **explicitly** in Plan if the hub edit was intentional (generally **not** appropriate inside `/play`).

---

### 4.B Engine missing (`guard.engine.reachable`)

**Trigger:** Editor binary path absent or not executable for the active `ENGINE=unreal` profile.

**Harness path (§7):** PRE-AUTHOR step **c** — when evaluator is real, **`fail`** stops before Author. In **`spec_only_as_info: true`** regimes, a **bootstrap** policy might still emit **`fail`** for true misconfiguration; this example shows a **hard fail** once M5-P1 wiring exists.

**`guards/pre_author.json` (illustrative):**

```json
{
  "schema_version": 1,
  "phase": "pre_author",
  "verdict": "fail",
  "guards": {
    "pre_author": [
      {
        "guard_id": "guard.engine.reachable",
        "class": "pre-author",
        "severity": "fail",
        "message": "UnrealEditor binary not found at configured path.",
        "evidence": {
          "type": "file",
          "path": "Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor",
          "detail": "stat errno=ENOENT (example)"
        }
      }
    ]
  }
}
```

**Final rollup excerpt:**

```json
{
  "verdict": "fail",
  "phase_verdicts": {
    "pre_author": "fail",
    "post_author": "info",
    "post_preview": "info",
    "qa": "info"
  },
  "findings": [
    {
      "guard_id": "guard.engine.reachable",
      "severity": "fail",
      "phase": "pre_author",
      "message": "Author not dispatched; install or configure engine path."
    }
  ]
}
```

**Operator next step:** follow parent `agent-play.md` §9 — structured **`not_applicable`** style guidance to run manual PIE until automation is configured.

---

### 4.C Fatal in preview log (`guard.log.fatal`)

**Trigger:** Post-preview scan finds `Fatal: Assertion failed: ...` in `preview/engine.log`.

**Harness path:** POST-PREVIEW yields **`fail`**; QA may be skipped or run **advisory only** per harness policy; Merge is **blocked**.

**`guards/post_preview.json` (illustrative):**

```json
{
  "schema_version": 1,
  "phase": "post_preview",
  "verdict": "fail",
  "guards": {
    "post_preview": [
      {
        "guard_id": "guard.log.fatal",
        "class": "post-preview",
        "severity": "fail",
        "message": "Fatal pattern matched in preview window.",
        "evidence": {
          "type": "log",
          "path": "preview/engine.log",
          "detail": "line=142 matched family fatal_assert"
        }
      }
    ]
  }
}
```

**Final rollup excerpt:**

```json
{
  "verdict": "fail",
  "phase_verdicts": {
    "pre_author": "pass",
    "post_author": "pass",
    "post_preview": "fail",
    "qa": "info"
  },
  "findings": [
    {
      "guard_id": "guard.log.fatal",
      "severity": "fail",
      "phase": "post_preview",
      "message": "Merge blocked; inspect engine.log near cited line."
    }
  ]
}
```

**Operator next step:** fix the assert source; re-run `/play` with the same scope after Author repair.

---

## 5. Trace artifacts on disk (ASCII tree)

Committed example (text only; **no** binary PNG):

```text
example-2026-04-20T12-00-00Z/
├── README.md
├── envelope.json
├── guards/
│   ├── pre_author.json
│   ├── post_author.json
│   └── post_preview.json
├── author/
│   └── envelope.json
├── preview/
│   ├── envelope.json
│   ├── engine.log (illustrative; 200 lines)
│   └── screenshots/
│       └── frame_0001.png.txt (text placeholder — not real PNG bytes)
└── qa/
    └── envelope.json
```

Hub path prefix: `.cuebert/traces/play/`. This matches the hub-local trace philosophy in `docs/_ai_system/standards/control-plane-paths.md` and `agent-play.md` §5.3.

---

## 6. How to use this example

- **When M5-P1 lands the Unreal bridge**, promote this scenario to an automated **smoke `/play`** against a real `hello-level` (or template) repo: same scope strings, same guard chain, real `UnrealEditor` binary checks, real PNG captures.  
- **Subagent prompt authors** can mirror the **JSON shapes** in `author/`, `preview/`, `qa/`, and `guards/` when writing slim Task envelopes.  
- **Humans authoring `/play` plans** should start from `docs/projects/_templates/play-plan-template.md` and **cross-check** guard expectations against §3 and §4 here.

---

## 7. Footer

**Status:** M2-P4 (documentation-only example). **Real executable run:** M5-P1 (UE bridge) + M6-P2 (Gauntlet / log evaluators).  
**Fixture commit path:** `.cuebert/traces/play/example-2026-04-20T12-00-00Z/` (curated exception under `.gitignore`).
