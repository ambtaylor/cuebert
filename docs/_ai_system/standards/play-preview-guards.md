# `/play` Preview Guards — Contract & Configuration

> **SYSTEM ROLE:** Authoritative specification for **Preview Guards** that gate the `/play` harness transition from **Author** (changes made) to **Preview** (editor/runtime launch), and for the **first post-preview probes** whose thresholds are owned alongside guard configuration.  
> **Scope:** Contract, taxonomy, severity semantics, configuration schema, evidence/envelope shape, artifact paths, and evaluation ordering. **No executable evaluator** is defined here — runtime wiring lands in **M5-P1** (engine adapters), **M6-P1** (compile / build-verify gaming branch), **M6-P2** (log pattern evaluators), and **M2-P4** (scope guards in the sample plan).

---

## 0. Purpose & scope

**Preview Guards** are **cheap, deterministic checks** that answer: “Is it worth spending editor time (for example a multi-minute Unreal PIE cold start) on this tree right now?” They exist so the harness does **not** spin up preview automation when it **already knows** the session will fail — for example when **`.cpp` will not compile**, the **active project key is missing** from the workspace manifest, or the **author subagent edited outside declared scope**. Guards are **gates and signals** for the control-plane harness: they **decide whether to proceed**, record **structured evidence**, and **never replace** human judgment for creative QA.

Guards are **not** full **QA** (no visual diff baselines, no multimodal screenshot analysis, no gameplay balance review). They are **not** the **Gauntlet** / headless UAT suite. They are **not** visual regression or art-direction sign-off. They are **not** `/ship` cook, package, or certification. This document owns the **guard ids**, **classes**, **severity ladder**, and **envelope contract** so later milestones plug **evaluators** into stable APIs without renaming concepts.

---

## 1. Guard taxonomy

Guards fall into **three classes** by **when** they run relative to Author and Preview. The harness runs them in a **fixed order** within each class (see §7).

### 1.1 Pre-author guards

Run **before any Author edits** (and before expensive Plan work if the harness chooses to short-circuit early). Typical checks:

- Validate that the **declared change scope** is within the **hub allow-list** (no edits targeting `.cuebert/`, `.cursor/rules/`, `docs/_ai_system/` via scope declaration).
- Confirm the **`PROJECT_KEY`** exists in **`.cuebert/workspace-manifest.json`**.
- Confirm the **engine binary** is **reachable** and **executable** for the active engine profile (Unreal first; Unity/Godot may remain deferred per engine tier).

**Intent:** Fail fast on **misconfiguration** or **forbidden intent** before mutating the application repository.

### 1.2 Post-author / pre-preview guards

Run **after Author completes** and **before** the harness dispatches **`agent-play-preview`** (or local automation equivalent). Typical checks:

- **Compile / build sanity** for gaming modules when a build hook exists (stub today; real compile in **M6-P1**).
- **Asset reference validity** where deterministic (stub **M5-P3**; no deep linker graph here in M2-P3).
- **Scope bleed:** every **changed file** on disk matches **declared scope globs** — defense against author subagent **overreach** even when the model “felt” a fix was justified.

**Intent:** Avoid **PIE / Play Mode** when the tree is **structurally broken** or **policy-violating** relative to the session contract.

### 1.3 Post-preview quick checks

Run **during or immediately after** preview against the **live capture bundle** (log tail, screenshot listing, preview `envelope.json`). These are the **first automated probes** on preview output; thresholds and pattern ownership **overlap conceptually** with early rows in `docs/_ai_system/agents/agent-play-qa.md` §4.

**Disambiguation (normative):**

| Concern | Preview Guards (this doc) | QA phase (`agent-play-qa.md` §4) |
|--------|---------------------------|-----------------------------------|
| **Role** | **Gate** continuation, **block preview dispatch** (pre-preview), or mark the run **BLOCKED** / non-mergeable when policy says so (post-preview). | **Post-preview verdict** for Merge policy, richer **findings** list, optional **warn** tolerance. |
| **Timing** | Pre-author; post-author **before** preview Task; post-preview **immediately** on artifacts. | After Preview; may assume guards already ran. |
| **Overlap** | **ERROR floor**, **fatal line** detection, **screenshot existence**, **ready marker** timeout — **thresholds live in** `.cuebert/config/play-guards.yaml` **and are referenced here**. | Same heuristics may appear as **QA checks**; **duplicate findings are acceptable** until harness deduplication lands (**M2-P3** note in QA doc §14). |
| **Depth** | **Minimal** — enough to avoid **false confidence** and obvious **hard failures**. | **Lightweight** but may add ordering, engine hooks, and **Merge** recommendation text. |

**Rule:** If a post-preview guard **fails** at **`fail`** severity, the harness treats the session as **`blocked`** for Merge unless an operator explicitly opts into a **diagnostic** path documented in `agent-play.md` §9. QA may still emit a longer narrative for humans.

---

## 2. Guard catalog

Each guard has a **stable `id`** (lowercase, dot-separated, `verb.noun` style). **`class`** is one of: `pre-author`, `post-author`, `post-preview`. **`severity`** is the **default** effective severity when the guard is **fully implemented**; **`warn→fail`** means the guard **starts as warn** and **escalates to fail** when a **threshold** is crossed (see config §4). **`evidence type`** names the **primary** attachment kind for findings. **`implementation status`** names the milestone that owns the **evaluator**.

Harness callers **MUST** treat guards whose status is **spec only** as **non-blocking `info`** until the cited milestone ships, **unless** a project manifest explicitly promotes severity (discouraged before evaluators exist). The global flag **`spec_only_as_info`** (see `.cuebert/config/play-guards.yaml` → `global`) defaults to **`true`** so unfinished evaluators never accidentally **block** `/play`.

| `id` | `class` | `severity` | Description | Evidence type | Implementation status |
|------|---------|-------------|-------------|----------------|-------------------------|
| `guard.project.exists` | pre-author | fail | `PROJECT_KEY` resolves to an entry under `projects` in `.cuebert/workspace-manifest.json` (path field present and usable). | manifest | **spec only** (M2-P3); impl **M5-P1** |
| `guard.engine.reachable` | pre-author | fail | Engine **binary path** exists and is **executable** for the active `ENGINE` profile (per engine adapter table). | file | **spec only**; impl **M5-P1** (UE); **deferred** Unity/Godot until tier milestones |
| `guard.scope.allowlist` | pre-author | fail | Declared change-scope globs are **within allowed paths**; harness rejects scopes targeting **hub meta** trees (for example `.cuebert/`, `.cursor/rules/`, `docs/_ai_system/`) at **declaration** time. | file | **spec only**; impl **M2-P4** (sample plan + harness) |
| `guard.compile.status` | post-author | fail | Build / compile step for **gaming modules** returns **exit code 0** for the active configuration. Stub today: `build_verify.py` gaming branch may return **`skip`** until real compile wiring lands. | text | **spec**; impl **M6-P1** |
| `guard.scope.bleed` | post-author | fail | **Files changed** match **declared scope globs** (defense against author overreach vs `agent-play-author.md` §4). | file | **spec only**; impl **M2-P4** |
| `guard.asset.refs_valid` | post-author | warn→fail | Declared **asset references** resolve **on disk** (for example UE `.uasset` soft paths where deterministic). | file | **spec**; impl **M5-P3** |
| `guard.preview.ready_marker` | post-preview | fail | Engine emits a **recognizable ready marker** in the log within the **readiness window** (`agent-play-preview.md` §5). | log | **spec**; impl **M5-P1** |
| `guard.log.fatal` | post-preview | fail | **Zero** lines matching configured **fatal** families (for example `Fatal:`, `SCRIPT ERROR:`, `Exception:`) during the preview window. | log | **spec**; impl **M6-P2** |
| `guard.log.error_floor` | post-preview | warn→fail | **ERROR**-classified line count: **warn** at lower bound, **fail** at upper bound (defaults in YAML `global` / per-guard `threshold`). | log | **spec**; impl **M6-P2** |
| `guard.screenshot.exists` | post-preview | warn | At least **one** screenshot file captured when `CAPTURE_MODE` implies screenshots (`agent-play-preview.md`). | file | **spec**; impl **M5-P1** |

### 2.1 Legacy mapping (informational)

`agent-play.md` §4 lists **G-1 … G-5** at a high level. Approximate mapping to stable ids:

| Legacy row | Primary guard id(s) |
|-----------|---------------------|
| G-1 Engine reachability | `guard.engine.reachable` |
| G-2 Compile sanity | `guard.compile.status` |
| G-3 Critical log patterns | `guard.log.fatal`, `guard.log.error_floor` |
| G-4 Asset reference integrity | `guard.asset.refs_valid` |
| G-5 Scope containment | `guard.scope.allowlist`, `guard.scope.bleed` |

---

## 3. Severity semantics

### 3.1 `fail`

- **Effect:** **Hard stop** for the current gate point.  
- **Pre-author / post-author:** Harness **does not dispatch** the next phase (no Author, or no Preview). Writes a **guard envelope** and stops with session outcome analogous to **`blocked`** / **`not_applicable`** per parent protocol.  
- **Post-preview:** Harness marks the run **BLOCKED** for Merge (per `agent-play.md` §3.7) when Merge is in scope.  
- **Safety:** Guards perform **no destructive rollback** of source trees; they only **decide** and **record**.

### 3.2 `warn`

- **Effect:** **Continue** the chain **unless** harness policy elevates specific warnings to Merge blockers (parent `agent-play.md` §4.1 defers per-engine **WARN-blocking** policy to **M5–M6**).  
- **Recording:** Every warn **MUST** appear as a **finding** in the envelope.

### 3.3 `info`

- **Effect:** **Record only** — does not block Merge by itself. Used for **diagnostics**, **spec-only** placeholders, and **skipped** evaluators.

### 3.4 `spec only` status and default `info` behavior

Until an evaluator ships, the guard’s **contract** (id, class, evidence shape) is **stable**, but the harness **MUST NOT** treat unimplemented checks as failing **`fail`** accidentally. **Default:** when `global.spec_only_as_info` is **`true`**, unimplemented guards contribute **`severity: info`** findings (or no finding) per harness policy — **never** a silent pass with missing evidence. Operators may set the flag to **`false`** only when **all** enabled guards in the session have **real evaluators**.

---

## 4. Config file

### 4.1 Location & version

- **Path (hub):** `.cuebert/config/play-guards.yaml`  
- **Version:** Top-level `version: 1` (**integer**). Tooling **MUST** reject unknown versions with a **loud, actionable error**. New guards and optional keys are **additive** within a version; **breaking** layout changes bump the integer.

### 4.2 Top-level shape (normative fields)

```yaml
version: 1
guards:
  <guard_id>:
    enabled: <bool>
    default_severity: fail | warn | info
    threshold: <object | null>   # optional; guard-specific
    allow_list: []               # optional; path/glob fragments
global:
  preview_ready_timeout_s: <int>
  preview_max_duration_s: <int>
  spec_only_as_info: <bool>
```

- **`guards`:** Map keyed by **exact** guard `id`.  
- **`enabled`:** When `false`, the harness **skips** the guard (emits **`info`** “skipped” finding at harness discretion).  
- **`default_severity`:** Hub default **before** project overrides.  
- **`threshold` / `allow_list`:** Optional per-guard parameters; **must** be documented per guard in the YAML comments and in §2.

### 4.3 Project overrides (manifest)

Projects **MAY** override per-guard effective severity (and selected thresholds where supported) in **`.cuebert/workspace-manifest.json`** under:

```json
"projects": {
  "<projectKey>": {
    "playGuards": {
      "overrides": {
        "guard.log.error_floor": { "severity": "fail", "threshold": { "warn": 1, "fail": 3 } }
      }
    }
  }
}
```

**Resolution order (highest wins):**

1. **`projects.<key>.playGuards.overrides.<guard_id>`** (manifest)  
2. **Hub file** `.cuebert/config/play-guards.yaml` entry (`default_severity`, `threshold`, `enabled`)  
3. **Catalog default** in §2 (used only when YAML omits a field — YAML should be complete for shipped hubs)

### 4.4 Engine-specific regex packs (explicit non-content for M2-P3)

**Per-engine regex tables** for ready markers, ERROR classification, and fatal families **do not** live in this milestone. They will ship as **adapter packs** (**M5/M6**) referenced by evaluator implementations. This document **only** reserves **guard ids** and **evidence types**.

---

## 5. Evidence & envelope contract

### 5.1 Finding entry (single guard result)

When a guard produces **`warn`** or **`fail`**, or an **`info`** diagnostic is recorded, the harness emits a **finding** object:

```json
{
  "guard_id": "guard.scope.bleed",
  "class": "post-author",
  "severity": "fail",
  "evidence": {
    "type": "file",
    "path": ".cuebert/",
    "detail": "file outside declared scope"
  },
  "message": "Short human-readable reason."
}
```

**`evidence.type`** is one of: `text`, `log`, `file`, `manifest` (extensible in future versions with version bump). **`path`** is repo- or hub-relative as appropriate; **`detail`** is optional structured context.

**Empty evidence policy:** For **`fail`** / **`warn`**, **`evidence`** **MUST** be non-vacuous — mirror `agent-play.md` §4.2: content-free failures invalidate the guard report.

### 5.2 Harness envelope (aggregated)

All findings roll up into a single object (exact on-disk name may be `envelope.json`; see §6):

```json
{
  "guards": {
    "pre_author": [],
    "post_author": [],
    "post_preview": []
  },
  "verdict": "pass|warn|fail",
  "phase": "pre-author|post-author|post-preview|complete"
}
```

**`verdict` composition (normative intent):**

- **`fail`** if any collected finding has **`severity: fail`** after resolution.  
- Else **`warn`** if any finding is **`warn`**.  
- Else **`pass`**.

The harness **MAY** include auxiliary keys (`timestamp`, `project_key`, `engine`) — **additive** only.

---

## 6. Artifacts

Guard envelopes and machine-readable findings **MUST** be written under the session trace root:

```text
.cuebert/traces/play/<timestamp>/guards/envelope.json
```

Where `<timestamp>` is UTC-sortable (see `docs/_ai_system/standards/control-plane-paths.md` hub trace philosophy and `agent-play.md` §5.3).

**Preview dispatch rule:** If **post-author** guards yield **`verdict: fail`**, the harness **MUST NOT** dispatch **`agent-play-preview`** for that session (unless an explicit **diagnostic override** flag is added in a later revision and documented in `agent-play.md` §9).

**Hub-only traces:** Application repositories remain **zero-footprint** for cuebert control-plane trees per `control-plane-paths.md` — traces live in the **hub** checkout.

---

## 7. Decision tree (evaluation order)

Pseudo-flow for harness ordering:

```text
1. PRE-AUTHOR
   a. Load `.cuebert/config/play-guards.yaml` + resolve project overrides from `.cuebert/workspace-manifest.json`.
   b. Run all ENABLED pre-author guards in stable sorted order by guard_id.
   c. If any resolved severity == fail -> STOP; write envelope.json; verdict fail; phase pre-author.
   d. Else continue.

2. AUTHOR
   a. Dispatch agent-play-author (or equivalent automation).
   b. If Author aborts -> STOP with harness-specific abort envelope (out of scope for this doc's detail).

3. POST-AUTHOR / PRE-PREVIEW
   a. Re-load git/changed-files snapshot supplied by Author envelope.
   b. Run all ENABLED post-author guards.
   c. If any fail -> STOP; do NOT dispatch Preview; verdict fail; phase post-author.

4. PREVIEW
   a. Dispatch agent-play-preview OR run local preview driver.
   b. Capture logs, screenshots, preview envelope.json under `.cuebert/traces/play/<ts>/preview/`.

5. POST-PREVIEW
   a. Run post-preview guards against preview artifacts (log tail, screenshot dir, preview envelope).
   b. Merge findings into guards envelope; set verdict; phase post-preview or complete.
   c. If QA phase is enabled, pass artifacts + guard envelope pointers to agent-play-qa per parent §3.4.
```

**Parallelism:** **No** parallel guard evaluators within a **single class** for the same session unless a future version explicitly documents safe parallelism.

---

## 8. Non-goals

- **Not full QA:** No **visual diff**, no **multimodal** screenshot judging, no **Gauntlet** / UAT orchestration — see **`agent-play-qa.md`** and M6 milestones.  
- **Not `/ship`:** No **cook**, **package**, **cert**, or **store** gates.  
- **Not code rollback:** Guards **never** revert git state; **Merge** phase remains separate (`agent-play.md` §3.5).  
- **Not secrets management:** Redaction policy references vault standards when logs are persisted — operational detail remains in preview/QA docs.

---

## 9. Cross-references

| Document | Relevance |
|----------|-----------|
| `docs/_ai_system/agents/agent-play.md` §4 | Parent **Preview Guards** summary; phase chain and BLOCKED vocabulary. |
| `docs/_ai_system/agents/agent-play-preview.md` §5 | **Readiness marker** intent; consumed by `guard.preview.ready_marker`. |
| `docs/_ai_system/agents/agent-play-qa.md` §4 | **QA checks** that overlap; see §1.3 disambiguation. |
| `docs/_ai_system/agents/agent-play-author.md` §4 | **Scope guardrails** — author-side complement to `guard.scope.*`. |
| `docs/_ai_system/standards/control-plane-paths.md` | Hub trace roots, `{active-project}` resolution, plan path notation. |
| `.cuebert/config/play-guards.yaml` | **Default thresholds**, per-guard enables, **`global`** timing and **`spec_only_as_info`**. |

---

## 10. Footer

**Status:** **M2-P3** — **contract + default config** only. **Guard evaluators** ship in **M5-P1** (`guard.engine.reachable`, `guard.preview.ready_marker`, screenshot capture), **M6-P1** / **M6-P2** (`guard.compile.status`, log pattern guards), **M5-P3** (`guard.asset.refs_valid`), and **M2-P4** (scope guards in the **sample plan**). Unknown YAML **`version`** values are **errors** in future tooling.

---

## Appendix A — Worked examples (non-normative)

### A.1 Pre-author failure (unknown project)

**Situation:** User invokes `/play --project foo`, but `foo` is absent from `projects` in `.cuebert/workspace-manifest.json`.

**Expected:**

- Once `guard.project.exists` is **fully implemented** (`fail`), envelope shows `phase: pre-author`, `verdict: fail`, and Preview is **not** scheduled.  
- While the guard id is **spec only** and `global.spec_only_as_info` is **`true`**, the harness **still** SHOULD perform a **cheap manifest key lookup** as bootstrap (outside the formal evaluator table) so `/play` never targets a non-existent project silently — emit either a **`fail`** envelope from bootstrap or an **`info`** finding from the stub guard, but **never** a content-free success.

> **Note:** This split exists so **policy ids** stabilize in M2-P3 even before every evaluator binary ships. Operators should read the envelope **`phase`** field to see whether bootstrap or a named guard produced the stop.

### A.2 Post-author failure (scope bleed)

**Situation:** `DECLARED_SCOPE` was `Content/UI/**`, but Author touched `Source/MyGame/Private/Hud.cpp`.

**Expected:**

- `guard.scope.bleed` → **`fail`** with `evidence.type: file` listing the first out-of-scope path.  
- Preview **not** dispatched.  
- Operator widens scope in Plan or adjusts intent.

### A.3 Post-preview warn vs fail (ERROR floor)

**Situation:** Preview log contains **two** ERROR-class lines in a noisy project.

**Config:** `guard.log.error_floor.threshold.warn: 1`, `fail: 5`.

**Expected:**

- Count **> warn** threshold → at least **`warn`** finding.  
- Count **< fail** threshold → **`verdict: warn`** if no other failures.  
- Merge policy: parent **`agent-play.md` §4.1** default — **WARN may not block** until engine policy tightens (**M5–M6**).

### A.4 Post-preview fail (fatal line)

**Situation:** Log contains `Fatal: Assertion failed: ...`.

**Expected:**

- `guard.log.fatal` → **`fail`** regardless of ERROR count.  
- `verdict: fail`; Merge **blocked**.

---

## Appendix B — Harness responsibilities (checklist)

The executable harness (future milestones) **SHOULD**:

1. **Materialize directories** under `.cuebert/traces/play/<timestamp>/guards/` before writing `envelope.json`.  
2. **Atomically write** JSON where the platform permits (write temp → rename) to avoid partial reads by QA.  
3. **Stamp** `project_key`, `engine`, `engine_version`, and `guard_config_version` (from YAML `version`) into the envelope header.  
4. **Normalize paths** to forward slashes in findings for cross-platform diff stability.  
5. **Never embed** secrets from logs — follow redaction guidance in preview/QA docs.  
6. **Short-circuit** strictly per §7 — do not run post-author guards if pre-author already failed unless explicitly entering a **diagnostic** mode.  
7. **Surface** the envelope path in Supervisor-facing summaries for operators.

---

## Appendix C — `workspace-manifest.json` fragment (illustrative)

This fragment is **documentation only**; the authoritative manifest schema prose remains in `agent-ops-onboard.md` and manifest templates.

```json
{
  "projects": {
    "sample-ue-game": {
      "path": "../SampleUeGame",
      "engine": "unreal",
      "engine_version": "5.4",
      "playGuards": {
        "overrides": {
          "guard.log.error_floor": {
            "severity": "warn",
            "threshold": { "warn": 3, "fail": 20 }
          }
        }
      }
    }
  }
}
```

Unknown keys under `playGuards` **SHOULD** be ignored by tooling until documented in a **version bump**.

---

## Appendix D — QA overlap matrix (expanded)

| Symptom | Post-preview guard id | QA doc row (`agent-play-qa.md` §4) | Who owns threshold default |
|---------|------------------------|-------------------------------------|------------------------------|
| Compile errors in log tail | (often `guard.compile.status` **before** preview; log echoes in QA §4.1) | §4.1 Compile | YAML + build hook |
| Missing asset / linker | `guard.asset.refs_valid` | §4.2 Asset references | M5 regex packs |
| Assert / ensure / fatal | `guard.log.fatal` | §4.3 Asserts / ensures | M6-P2 packs |
| ERROR count | `guard.log.error_floor` | §4.4 Log ERROR floor | `.cuebert/config/play-guards.yaml` |
| Screenshot count | `guard.screenshot.exists` | §4.5 Screenshot existence | Preview + YAML |
| Scope | `guard.scope.bleed` (post-author) | §4.6 Scope bleed | Plan scope + git diff |

**Dedup strategy (future):** Harness may attach **`correlation_id`** per finding; **M2-P3** does not require deduplication.

---

## Appendix E — Operator diagnostics (dry-run)

Future harness flags may allow **`GUARDS_SKIPPED: true`** envelopes (see `agent-play-preview.md` §15). **Normative safety:** skipped guards **MUST** produce **`info`** findings with explicit operator attribution — never a silent **`pass`**.

---

## Appendix F — Id stability & API surface

Guard ids are **public contracts** for:

- MCP / CLI harness switches (`--guard-off guard.x` patterns — **future**).  
- Manifest overrides (`playGuards.overrides`).  
- CI fixtures naming (`tests/fixtures/guards/...` — **future**).

**Renaming policy:** Do **not** rename ids after M2-P3; add **new** ids for semantically distinct checks and **deprecate** old ids across a **version bump**.

---

## Appendix G — Relationship to `build_verify.py`

`guard.compile.status` references the **gaming branch** of hub `build_verify` tooling. Until **M6-P1**, the tool may return **`skip`**. The guard **still exists** so harnesses reserve envelope space; with `spec_only_as_info: true`, the stub should map to **`info`** (“compile check skipped”) rather than pretending **`pass`** without evidence.

---

## Appendix H — Readiness window vs preview duration

Two distinct timers:

- **`global.preview_ready_timeout_s`** — how long to wait for **`guard.preview.ready_marker`** after launch begins.  
- **`global.preview_max_duration_s`** — hard cap on preview process lifetime (aligns with `agent-play-preview.md` §7 defaults).

**Failure modes:**

- Ready marker **never** arrives → post-preview verdict **`fail`** for `guard.preview.ready_marker` when enforced; Preview envelope may still show `status: timeout`.

---

## Appendix I — Screenshot guard nuance

`guard.screenshot.exists` is **`warn`** by default because legitimate modes (`log-only`, crash before first frame) may yield **zero** PNGs. QA §4.5 defines **skip** semantics when mode is `log-only` — guards **MUST** align: when `CAPTURE_MODE` is `log-only`, screenshot guard should emit **`info`** (“not applicable”) not **`warn`**.

---

## Appendix J — Glossary

| Term | Meaning |
|------|---------|
| **Harness envelope** | Aggregated JSON object in `.cuebert/traces/play/<ts>/guards/envelope.json`. |
| **Finding** | Single guard outcome row inside the envelope lists. |
| **Spec only** | Contract frozen in M2-P3; evaluator code not yet shipped for that id. |
| **Scope bleed** | Changed files outside declared globs / roots. |
| **Ready marker** | Engine log line or IPC signal meaning “preview interactive” per engine adapter. |

---

## Appendix K — Revision history (documentation)

| Milestone | Change |
|-----------|--------|
| **M2-P3** | Initial taxonomy, catalog (10 ids), YAML schema v1, artifact path, decision tree. |
| **M5+** | Add engine packs; tighten `spec_only_as_info` defaults per engine tier. |
| **M6+** | Wire compile + log evaluators; optional dedup with QA. |

