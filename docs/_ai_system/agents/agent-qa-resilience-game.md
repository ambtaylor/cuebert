# QA RESILIENCE — Gaming (`agent-qa-resilience-game`)

> **Name:** `agent-qa-resilience-game`  
> **Status:** Spec (**M7-P1**). Implementation runs via prompt execution in later milestones; this agent owns **no** MCP tools.  
> **Consumers (dispatchers):** `docs/_ai_system/agents/agent-play-qa.md` (post-preview), `docs/_ai_system/agents/agent-ship.md` (via **M7-P3** strict gate).  
> **Audience:** Not user-facing. Always dispatched by another agent or harness.

---

## 0. Identity

| Field | Value |
|-------|--------|
| **Agent id** | `agent-qa-resilience-game` |
| **Kind** | Gaming-specific QA-resilience scan (PIE / Gauntlet / build artifacts) |
| **MCP tools** | None in **M7-P1**; contract + taxonomy + config only |
| **Canonical rules** | `docs/_ai_system/standards/qa-resilience-game-rules.md` |
| **Default config** | `.cuebert/config/qa-resilience-game.yaml` |

This agent is the gaming counterpart to Cue hub QA-resilience agents (`qa-resilience-react`, `qa-resilience-python` naming); it follows the same envelope-driven shape adapted for Unreal logs and Gauntlet traces.

---

## 1. Purpose

Scan gaming artifacts (Gauntlet logs, PIE traces, preview screenshots, build logs) for resilience-class defects that functional tests miss.

**In scope:** Frame hitches, memory growth or leak signatures, crash-free survivability signals, `Ensure` noise, asset-streaming stalls, missing-asset load failures, and (when wired) network latency sensitivity. **Engine focus:** Unreal first. Unity and Godot use the same manifest and envelope; parsers are deferred.

**Explicit non-purpose:**

- No performance benchmarking with regression CSV baselines (future **`bench-game`** agent).
- No security scanning (Cuebert `/sec` and project security workflows own that domain).
- No functional test execution (Gauntlet and harness-owned tests own that).
- No live network calls, no subprocess orchestration, and no write access to game source trees (read-only artifacts only).

---

## 2. Inputs

The caller supplies a **scan manifest** (JSON object, usually synthesized by the dispatching agent):

```json
{
  "project_path": "abs path to .uproject",
  "session_kind": "preview" | "gauntlet" | "build",
  "artifacts": {
    "gauntlet_log_dir": "str | null",
    "pie_log_path": "str | null",
    "build_log_path": "str | null",
    "screenshots_dir": "str | null"
  },
  "thresholds": {
    "frame_hitch_ms": 50,
    "max_hitches_per_minute": 6,
    "memory_growth_mb_per_minute": 20,
    "crash_count_tolerance": 0,
    "streaming_stall_ms": 500,
    "max_ensure_count": 3,
    "latency_spike_ms": 200,
    "heartbeat_absence_s": 30
  },
  "caller": "agent-play-qa" | "agent-ship" | "agent-ship-cook" | "user-direct-debug"
}
```

**Rules:**

- `project_path` MUST be an absolute path to a `.uproject` when `session_kind` is `preview` or `gauntlet` (Unreal). Build-only scans MAY relax this only when the harness documents an alternate project anchor.
- All `thresholds` are optional in the manifest; missing keys merge from `.cuebert/config/qa-resilience-game.yaml` (project copy overlays hub defaults per that file’s header comments).
- `caller` is **required** for memory hooks and for **§6** scope enforcement (when implemented in **M7-P3**).
- `latency_spike_ms` applies to `network.latency_spike` (**M7-P1:** doc-only; not wired).

Artifact paths MAY be null when a session produced only a subset (for example screenshots without a separate PIE log). The agent MUST NOT invent paths.

---

## 3. Output envelope

```json
{
  "status": "pass" | "fail" | "warn" | "skip" | "error",
  "mode": "live" | "dry_run",
  "session_kind": "str",
  "findings": [
    {
      "category": "hitch" | "memory" | "crash" | "ensure" | "streaming" | "asset" | "network",
      "severity": "info" | "warn" | "error" | "critical",
      "detail": "str",
      "evidence": {
        "log_path": "str | null",
        "line_number": "int | null",
        "screenshot_path": "str | null",
        "metric_value": "float | null",
        "threshold": "float | null"
      },
      "rule_id": "str"
    }
  ],
  "metrics": {
    "runtime_seconds": "float",
    "hitch_count": "int",
    "hitches_per_minute": "float",
    "peak_memory_mb": "float",
    "memory_growth_mb_per_minute": "float",
    "ensure_count": "int",
    "crash_count": "int",
    "streaming_stall_count": "int"
  },
  "rule_version": "1.0.0",
  "memory_id": "str | null"
}
```

### 3.1 Status resolution

| Condition | Top-level `status` |
|-----------|-------------------|
| Any finding with `severity: critical` | `fail` |
| `error` findings AND count exceeds the configured tolerance for that rule class | `fail` |
| At least one `warn` and no failing conditions above | `warn` |
| No findings after a successful scan | `pass` |
| No artifacts available to scan (all relevant paths null or missing) | `skip` (not `error`) |
| Manifest unreadable, IO failure, or internal inconsistency | `error` |

`mode` mirrors harness policy: `dry_run` when `CUEBERT_QA_RESILIENCE_MODE=dry_run` or when the harness forces synthetic envelopes.

---

## 4. Rule catalogue

Normative regex text and remediation detail live in **`docs/_ai_system/standards/qa-resilience-game-rules.md`**. This section summarizes the **M7-P1** rule set.

### 4.1 Summary table

| rule_id | category | severity | trigger |
|---------|----------|----------|---------|
| `hitch.frame_time_exceeded` | hitch | warn | Single frame exceeds `frame_hitch_ms` |
| `hitch.rate_exceeded` | hitch | error | Hitches per minute exceed `max_hitches_per_minute` |
| `memory.growth_rate` | memory | warn | MB/min exceeds `memory_growth_mb_per_minute` |
| `memory.leak_signature` | memory | error | Log matches canonical leak warning patterns |
| `crash.fatal_signal` | crash | critical | Fatal / appError signatures in log |
| `crash.ensure_fired` | ensure | warn | Count of `Ensure condition failed:` exceeds `max_ensure_count` |
| `streaming.stall` | streaming | warn | Streaming flush duration exceeds `streaming_stall_ms` |
| `asset.missing` | asset | error | Failed-to-load asset warnings |
| `network.latency_spike` | network | warn | NetPing round-trip exceeds `latency_spike_ms` (**doc-only M7-P1**) |
| `resilience.deadlock_suspect` | hitch | critical | Extreme frame time OR stall signatures per standards doc |

### 4.2 Rule entries (elaboration; normative regex in standards)

Each rule below lists **`rule_id`**, **category**, **severity**, **description**, **trigger**, **evidence**, and **remediation_hint** at a summary level. The **exact** regex, capture groups, and false-positive guardrails are defined only in **`docs/_ai_system/standards/qa-resilience-game-rules.md`** so the catalogue stays stable across harness iterations.

#### `hitch.frame_time_exceeded`

- **Description:** Detects isolated long frames (hitches) from stats-tagged frame timing lines.  
- **Trigger:** Parsed frame time in milliseconds exceeds `thresholds.frame_hitch_ms`.  
- **Evidence:** `log_path`, `line_number`, `metric_value` (ms), `threshold` (`frame_hitch_ms`).  
- **Remediation hint:** Profile with Unreal Insights; reduce work in tick; watch GC spikes.  
- **Pattern ownership:** Standards doc §Rule `hitch.frame_time_exceeded`.

#### `hitch.rate_exceeded`

- **Description:** Sustained hitch rate (hitches per minute) over a sliding window.  
- **Trigger:** Derived `hitches_per_minute` exceeds `max_hitches_per_minute`.  
- **Evidence:** Same as hitch rules; include aggregate in `detail`.  
- **Remediation hint:** Same as single-frame hitches; prioritize systemic causes (AI budget, streaming, sync loads).  
- **Pattern ownership:** Uses the same line family as `hitch.frame_time_exceeded` for counting.

#### `memory.growth_rate`

- **Description:** Rising resident memory over session wall time from sampled memory lines.  
- **Trigger:** Estimated MB/min exceeds `memory_growth_mb_per_minute`.  
- **Evidence:** `metric_value` (MB/min), `threshold`.  
- **Remediation hint:** Capture `memreport`; audit texture and UObject retention; check subsystems holding references.  
- **Pattern ownership:** Standards doc §Rule `memory.growth_rate`.

#### `memory.leak_signature`

- **Description:** Engine-reported leak warnings (canonical strings).  
- **Trigger:** Log line matches leak signature regex from standards.  
- **Evidence:** `log_path`, `line_number`, excerpt in `detail`.  
- **Remediation hint:** Fix reported refcount or UObject leak site; re-run long PIE.  
- **Pattern ownership:** Standards doc §Rule `memory.leak_signature`.

#### `crash.fatal_signal`

- **Description:** Fatal error or Windows appError path indicating non-recoverable failure.  
- **Trigger:** Any fatal signature match; `crash_count` increments; compare to `crash_count_tolerance` (default **0** implies fail on first).  
- **Evidence:** `log_path`, `line_number`.  
- **Remediation hint:** Open minidump / crash context; fix first fault; verify command-line and plugins.  
- **Pattern ownership:** Standards doc §Rule `crash.fatal_signal`.

#### `crash.ensure_fired`

- **Description:** Ensure failures below fatal threshold but above noise budget.  
- **Trigger:** Count of `Ensure condition failed:` lines exceeds `max_ensure_count`.  
- **Evidence:** Count in `metric_value`, threshold from config.  
- **Remediation hint:** Address failing predicate; downgrade hot-path Ensures in shipping paths where appropriate.  
- **Pattern ownership:** Standards doc §Rule `crash.ensure_fired`.

#### `streaming.stall`

- **Description:** Streaming flush or IO stall warnings beyond budget.  
- **Trigger:** Parsed stall duration exceeds `streaming_stall_ms`.  
- **Evidence:** `metric_value` (ms), `threshold`.  
- **Remediation hint:** Reduce synchronous loading in frame; fix oversized levels; tune async precache.  
- **Pattern ownership:** Standards doc §Rule `streaming.stall`.

#### `asset.missing`

- **Description:** Failed asset load warnings from UObjectGlobals.  
- **Trigger:** Any matching failed-load line at warning or error severity per standards.  
- **Evidence:** `log_path`, `line_number`, asset name in `detail`.  
- **Remediation hint:** Fix redirectors, mount roots, and cooker settings; restore missing content.  
- **Pattern ownership:** Standards doc §Rule `asset.missing`.

#### `network.latency_spike`

- **Description:** NetPing round-trip warnings (latency sensitivity).  
- **Trigger:** Parsed RTT exceeds `latency_spike_ms`.  
- **Evidence:** `metric_value`, `threshold`.  
- **Remediation hint:** Audit replication frequency, RPC bursts, and server tick budget.  
- **Pattern ownership:** Standards doc §Rule `network.latency_spike` (**not wired M7-P1**).

#### `resilience.deadlock_suspect`

- **Description:** Extreme single-frame time or explicit stall / hang signatures suggesting deadlock or unbounded main-thread block.  
- **Trigger:** Frame time above **10s** **or** hang signature lines per standards; optional heartbeat gap logic documented there.  
- **Evidence:** `metric_value`, `log_path`, `line_number`.  
- **Remediation hint:** Take time-traces; inspect sync primitives and game-thread waits.  
- **Pattern ownership:** Standards doc §Rule `resilience.deadlock_suspect`.

**M7-P1 is spec-only:** no parser code ships in this milestone. Harnesses and operators MAY still run prompt-driven scans that apply these rules manually against logs. Automated enforcement lands in **M7-P3** (`/ship` strict gates and optional `/play` guard wiring).

---

## 5. Execution model

1. **Input:** Scan manifest (§2), passed inside the caller’s task envelope.  
2. **Reads:** Log files, Gauntlet trace directories, and screenshot directories **read-only** (see `.cursor/skills/unreal-build/reference.md` for Gauntlet log layout and `unreal_run_gauntlet` outputs).  
3. **Output:** Structured envelope (§3).  
4. **Prohibited in this agent’s contract:** subprocesses, network I/O, MCP tool calls, and writes outside an optional harness-managed trace append (policy is harness-owned).

---

## 6. Scope matrix

Who may dispatch which `session_kind` (enforced in **M7-P3** wiring; documented here as normative):

| Caller | `preview` | `gauntlet` | `build` |
|--------|-----------|------------|---------|
| `agent-play-qa` | ALLOWED | ALLOWED (post-**M6-P2** Gauntlet capture) | DENIED |
| `agent-ship` | DENIED | DENIED | ALLOWED |
| `agent-ship-cook` | DENIED | DENIED | ALLOWED |
| `user-direct-debug` | ALLOWED | ALLOWED | ALLOWED |

Violations (when enforced) SHOULD yield `status: error` with a finding explaining the caller/session mismatch; until **M7-P3**, harnesses MAY still accept results for debugging.

---

## 7. Dry-run semantics

When **`CUEBERT_QA_RESILIENCE_MODE=dry_run`** OR when required artifacts are absent and the harness requests dry semantics:

- Emit **one** synthetic finding: `severity: info`, `detail: "dry-run: no artifacts scanned"`, `rule_id: "qa-resilience.dry_run"` (informational; not part of the ten production rules).
- Set top-level `status` to **`skip`** and `mode` to **`dry_run`**.

---

## 8. Memory hooks

| Top-level `status` | Memory action |
|--------------------|----------------|
| `pass` or `skip` | No `troubleshoot_commit` |
| `warn` | `troubleshoot_commit` at **`warn`**, summary of top **3** findings |
| `fail` | `troubleshoot_commit` at **`error`**, include **all** `error` and `critical` findings |
| `error` | `troubleshoot_commit` at **`error`**, include error code / message plus partial findings |

Memory toolkit entry points are described in `.cursor/skills/memory-toolkit/SKILL.md`; callers supply correlation IDs as today’s harnesses do for other QA phases.

---

## 9. Cross-references

| Doc / artifact | Role |
|----------------|------|
| `docs/_ai_system/agents/agent-play-qa.md` | Post-`/play` dispatcher |
| `docs/_ai_system/agents/agent-ship.md` | Future **`/ship`** strict gate consumer (**M7-P3**) |
| `docs/_ai_system/agents/agent-ship-cook.md` | Build-session dispatcher (same gate family) |
| `docs/_ai_system/standards/qa-resilience-game-rules.md` | Authoritative per-rule patterns |
| `.cuebert/config/qa-resilience-game.yaml` | Thresholds + per-rule toggles |
| `.cursor/skills/unreal-build/reference.md` | Gauntlet logs, `unreal_run_gauntlet`, trace dirs |
| `.cursor/skills/vision-qa/reference.md` | Screenshot checks; visual findings MAY attach as `evidence.screenshot_path` |
| `docs/_ai_system/agents/agent-play.md` | `/play` harness parent protocol |

**M7-P2** introduces the sibling **`prod-readiness-game`** ruleset (production-readiness gaming); this file does not duplicate that contract. Plan milestone tables for **M7** live in the Cue hub gaming-system plan (not duplicated here).

---

## 10. Non-goals

- Executing automated gameplay tests (Gauntlet owns functional coverage).
- Benchmarking with stored baselines or perf budgets (`bench-game`, future).
- Replacing `/sec` or dependency audit agents.
- Unity / Godot parsers in **M7-P1** (same envelope; engine-specific parsers later).

---

## 11. Deferred items (**M7-P1**)

- Log-parsing implementation inside harness or shared evaluators (**M7-P3**).
- CI integration and `/ship` strict gate wiring (**M7-P3**).
- Unity / Godot channel parsers.
- `network.latency_spike` wiring (requires NetPing log analyzer and stable thresholds).

---

## 12. Footer

Status: spec only (**M7-P1**). Rules, envelope, scope matrix, and default YAML are published. Automated enforcement lands in **M7-P3**.
