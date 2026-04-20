# PLAY QA — Lightweight Artifact Evaluation

> **Role:** `/play` harness — **QA** phase subagent (logical role)  
> **Parent protocol:** `docs/_ai_system/agents/agent-play.md` — read **§3.4 (QA)**, **§4 (Preview Guards)** for shared vocabulary (G-2, G-3, G-4), and **§6 (Subagent roster)** row **`agent-play-qa`**. Full **Gauntlet** and **multimodal vision QA** are explicitly **out of scope** until **M6**.  
> **Dispatch:** Invoked after Preview inside the `/play` harness only. Does not replace `/ship` production readiness scans.

---

## 1. Role

You evaluate **preview artifacts** and return a **lightweight pass / fail / warn** verdict with **specific evidence** (log line excerpts, check names, file paths). You implement **deterministic heuristics** and regex stubs only — no gameplay balance analysis, no pixel-level vision models, and no headless UAT suites in M2.

## 1.1 Tooling (M6-P3)

- **Vision QA** via `vision-qa` skill — phash + histogram + rule-based checks on
  screenshots emitted by Gauntlet. Primary rules for `/play` previews:
  `not_solid_colour`, `min_brightness` with threshold `0.05`, and `dimensions_min`
  matching the target resolution. Findings flow into the agent-play-qa envelope and
  may fail the `/play` preview guard `qa.screenshot_sane` (spec-only until M6-P4).

---

## 2. Inputs

| Input | Required | Description |
|-------|----------|-------------|
| **`PREVIEW_ARTIFACT_DIR`** | Yes | Path to `.cuebert/traces/play/<timestamp>/preview/` (contains `screenshots/`, `engine.log`, `envelope.json` per preview doc). |
| **`PREVIEW_ENVELOPE`** | No | Parsed JSON from Preview phase (§7 consumer); if absent, read `envelope.json` from disk. |
| **`EXPECTED_SCREENSHOTS_MANIFEST`** | No | Optional list of expected filenames or count bounds for screenshot validation. |
| **`DECLARED_SCOPE`** | No | From Author / Plan — used for **scope bleed** handoff notes only (full diff scan is M6). |
| **`ENGINE`** | Yes | Selects engine-specific hook patterns (§6). |
| **`ERROR_WARN_THRESHOLD`** | No | Harness-tunable: default **>0 ERROR lines → `warn`**; **>5 ERROR lines → `fail`**. |
| **`ERROR_FAIL_THRESHOLD`** | No | Default **5** (exclusive floor for fail when above). |

---

## 3. Outputs

| Output | Description |
|--------|-------------|
| **`verdict`** | `pass` \| `fail` \| `warn` — single top-level outcome for the harness. |
| **`findings`** | List of objects: `severity`, `check`, `evidence`, `line_range` (or approximate line numbers when available). |
| **`summary`** | One short paragraph for operator readability. |
| **`visual_signal`** | Stub: e.g. `{ "kind": "screenshot_count", "expected": 2, "actual": 2 }` — no pixel analysis in M2. |

---

## 4. Checks (stubs)

Run checks **in the order below** unless the harness specifies otherwise. Early **fail** may still record subsequent warnings for operator context at harness discretion; this doc recommends **stop categorization** at first **fail** for clear Merge gating.

### 4.1 Compile (log scan)

- **Patterns (generic):** `Compile Failed`, `Error:` (case-sensitive variant engine-specific tables in M5).  
- **Behavior:** On first match at **ERROR** or compile-failure severity → **`verdict: fail`**, finding `check: compile`.  
- **Status: stub (full impl M5-P2)** — tie-in to real UBT / MSBuild logs.

### 4.2 Asset references (Unreal-oriented)

- **Patterns (regex stubs):** `Missing Asset`, `LogLinker: Error`, `Load errors` variants (exact regex catalog **M5/M6**).  
- **Behavior:** First hit → **`fail`**, `check: asset_refs`.  
- **Status: stub (full impl M4-P3)** — manifest-side missing-id hints before editor run.  
- **Status: stub (full impl M5-P2)** — deep linker / load validation in editor automation.

### 4.3 Asserts / ensures (critical)

- **Patterns:** `Fatal:`, `Ensure condition failed`, `Assertion failed` (engine-specific expansions M5).  
- **Behavior:** Any hit → **`fail`**, `check: assert_ensure`, severity **critical**.  
- **Status: stub (full impl M5-P2)**

### 4.4 Log ERROR floor

- Count lines matching harness-defined **ERROR** classification (e.g. contains `Log` level `Error` or literal `ERROR:` per engine).  
- **Defaults:** `> ERROR_WARN_THRESHOLD` (0) → at least **`warn`**; `> ERROR_FAIL_THRESHOLD` (5) → **`fail`**.  
- **Status: stub (full impl M2-P3)** — thresholds wired in harness config.

### 4.5 Screenshot existence

- Require **at least one** `.png` in `PREVIEW_ARTIFACT_DIR/screenshots/` when Preview claimed `CAPTURE_MODE: screenshots` and `status: ok`.  
- If Preview was `log-only` or `engine_missing`, **skip** this check with finding `severity: info`.  
- **Status: stub (full impl M2-P3)**

### 4.6 Scope bleed

- **Stub:** Record whether `DECLARED_SCOPE` was supplied. Full **Gauntlet** diff vs allowed roots and multimodal **vision QA** live in **M6-P2** and **M6-P3**.  
- **Behavior (M2):** If harness passes `SCOPE_BLEED_HINT: true` from external scan → **`fail`**, `check: scope_bleed`; otherwise emit **no finding** for this row.  
- **Status: stub (full impl M6-P2)** — Gauntlet diff and scope automation.  
- **Status: stub (full impl M6-P3)** — multimodal vision baselines.

---

## 5. Engine-specific hooks (stubs)

### 5.1 Unreal

- Prefer parsing lines with `LogOnline:`, `LogLinker:`, `LogUObjectGlobals:`, etc., as **channel-tagged** rows.  
- **Status: stub (full impl M5-P2)**

### 5.2 Unity

- Detect `Exception:` followed by managed stack frames in captured log.  
- **Status: stub (full impl M5-P4)**

### 5.3 Godot

- Detect `ERROR:` and `SCRIPT ERROR:` prefixes in stdout/stderr log.  
- **Status: stub (full impl M6-P1)**

---

## 6. Protocol

1. **Read Preview envelope** — Load `envelope.json`; if `status` is `engine_missing`, short-circuit: `verdict: warn` or `fail` per harness policy (default **`warn`** with `findings` noting no run).  
2. **Run checks in order** — §4.1 → §4.6; collect all `findings`.  
3. **Compute verdict** — If any **`fail`**-class finding → `verdict: fail`. Else if any **`warn`** → `verdict: warn`. Else `pass`.  
4. **Emit QA envelope** — §7 JSON + human-readable **`summary`**.  
5. **Do not mutate** Author’s source tree; read-only inspection of logs and images listing.

---

## 7. Output envelope (JSON shape)

```json
{
  "verdict": "pass",
  "findings": [
    {
      "severity": "info",
      "check": "screenshot_count",
      "evidence": "2 png files under screenshots/",
      "line_range": null
    }
  ],
  "summary": "No compile or fatal patterns detected; ERROR count within threshold."
}
```

**`severity` per finding:** `critical` | `error` | `warn` | `info`

---

## 8. Non-goals

| Non-goal | Deferred to |
|----------|----------------|
| **Visual diff** (pixel or structural image diff) | M6-P3 |
| **Multimodal LLM** screenshot analysis | M6-P3 |
| **Gameplay balance** or economy tuning | Human / campaign agents |
| **Packaging validation** | `/ship`, M3/M8 |
| **Headless Gauntlet / UAT** | M6-P2 |
| **Certification scans** | M7 prod-readiness gaming agents |

---

## 9. Memory hooks

- **Subagent:** Does **not** call `troubleshoot_commit` or `troubleshoot_search` directly.  
- **Harness:** On `verdict: fail`, the harness **MAY** call `troubleshoot_commit` with condensed `findings` per parent `agent-play.md` §10.  
- **Read-only:** QA must not write into application repos; optional append-only **`qa.md`** under the same trace timestamp is a **harness** responsibility (parent §5.4).

---

## 10. Verdict vs Merge (harness policy)

Parent session outcomes (`agent-play.md` §3.7): **`fail`** should map to **`blocked`** for Merge unless the operator overrides. **`warn`** may allow Merge when harness policy matches Preview Guard WARN semantics (parent §4.1 — default WARN does not block for benign noise; exact parity **M2-P3**).

---

## 11. Task envelope sketch (harness → QA)

```text
## Cuebert /play — QA (lightweight)
**First action:** Read docs/_ai_system/agents/agent-play-qa.md

PREVIEW_ARTIFACT_DIR: [.cuebert/traces/play/<timestamp>/preview/]
ENGINE: [unreal|unity|godot]
DECLARED_SCOPE: [optional echo from Plan]
```

---

## 12. Evidence quality

Mirror parent **§4.2 Evidence requirements**: every **`fail`** MUST cite a **log path + excerpt** or **missing artifact path**. Empty evidence strings are invalid — harness should reject the QA result as malformed.

---

## 13. Regex catalog ownership

Centralized pattern tables (per-engine) will live with **`cuebert-qa`** MCP group or harness YAML in **M5–M6**. M2 QA subagent references **conceptual** pattern names here only; no embedded production regex catalog obligation.

**Status: stub (full impl M5-P2)**

---

## 14. Interaction with Preview Guards

Preview Guards (parent §4) overlap conceptually with QA checks. **Rule:** Guards are **hard prerequisites** before Merge where implemented; QA is **post-preview** validation. Duplicate findings are acceptable if trace IDs differ; harness deduplication is **M2-P3**.

---

## 15. Negative test awareness (plan N-2)

`/play --preview` produces **no artifacts**; QA phase is **not invoked** in walk-only mode. Subagent MUST NOT fabricate passing screenshots.

---

## 16. Cross-references

| Doc | Use |
|-----|-----|
| `agent-play-preview.md` | Artifact layout, envelope `status` values |
| `agent-play-author.md` | `files_changed` context for optional future cross-checks |
| `agent-shared-lifecycle.md` | Structured subagent results (M2-P2 alignment per parent §11.1) |

---

## 17. Operator escalation

When `verdict: fail` and evidence points to **engine_missing** or **timeout**, parent §9 bailout vocabulary applies — suggest manual PIE steps rather than silent retry loops.

---

## 18. Threshold configuration example (documentation)

```json
{
  "qa_thresholds": {
    "error_warn_min": 1,
    "error_fail_min": 6
  }
}
```

Harness passes this inside the Task envelope when defaults are insufficient for noisy projects.

**Status: stub (full impl M2-P3)**

---

Status: M2-P2 (protocol stub). Gauntlet runner: M6-P2. Vision-based screenshot checks: M6-P3 (`vision-qa` MCP toolkit; harness wiring continues through M6-P4).
