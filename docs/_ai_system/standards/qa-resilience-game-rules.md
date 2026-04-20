# QA Resilience — Gaming rule catalogue

Authoritative patterns for **`agent-qa-resilience-game`**. The agent spec at `docs/_ai_system/agents/agent-qa-resilience-game.md` summarizes behavior; this document owns **regex**, **evidence**, **remediation**, and **false-positive guardrails**.

**Engine:** Unreal Engine log channels first. **M7-P1:** spec only — patterns are validated as Python regex but not executed in shipped automation until **M7-P3**.

---

## Rule: `hitch.frame_time_exceeded`

- **Category:** hitch  
- **Default severity:** warn  
- **Trigger:** Single frame exceeds `frame_hitch_ms` (default 50ms).  
- **Log pattern** (Unreal):

  ```
  LogStats: .*Frame [0-9]+.*took ([0-9]+\.[0-9]+) ms
  ```

  Capture group **1** is frame time in milliseconds.

- **Evidence:**  
  - `log_path`, `line_number`, `metric_value` (ms), `threshold` (from config).  
- **Remediation hints:**  
  - Profile with Unreal Insights (`-trace` / `-tracehost` per project policy).  
  - Check heavy tick actors and ticking groups.  
  - Check garbage collection frequency and `gc.TimeBetweenPurgingPendingKillObjects`.  
- **False positive guardrails:**  
  - Ignore first **2** seconds after PIE start (warmup).  
  - Ignore frames overlapping level load markers matching `LogLoad: Took .* to load`.  
  - Ignore known editor-only spikes when `session_kind` is `preview` and the harness sets `editor_noise: true` (future envelope field).

---

## Rule: `hitch.rate_exceeded`

- **Category:** hitch  
- **Default severity:** error  
- **Trigger:** Hitches per minute exceed `max_hitches_per_minute` (count of frames exceeding `frame_hitch_ms` within a sliding 60s wall window).  
- **Log pattern** (Unreal): same line family as `hitch.frame_time_exceeded`:

  ```
  LogStats: .*Frame [0-9]+.*took ([0-9]+\.[0-9]+) ms
  ```

  Implementations derive rate from repeated matches; group **1** is per-line frame time.

- **Evidence:** aggregate `metric_value` for `hitches_per_minute`, plus `threshold`.  
- **Remediation hints:** same as `hitch.frame_time_exceeded`; prioritize recurring offenders (same callstack / same object).  
- **False positive guardrails:** apply the same warmup and `LogLoad` exclusions as `hitch.frame_time_exceeded`; require minimum window duration (for example **60s** of log time) before evaluating rate.

---

## Rule: `memory.growth_rate`

- **Category:** memory  
- **Default severity:** warn  
- **Trigger:** Estimated memory growth in MB per minute of session time exceeds `memory_growth_mb_per_minute`.  
- **Log pattern** (Unreal) — sampled resident memory lines (harness derives slope across matches):

  ```
  Mem Used:\s*([0-9]+(?:\.[0-9]+)?)\s*MB
  ```

  Capture group **1** is the sampled value in MB when this line form appears in engine or platform memory dumps.

- **Evidence:** `metric_value` (MB/min), `threshold`, optional paired timestamps in `detail`.  
- **Remediation hints:**  
  - Capture `memreport -full` at session start and end.  
  - Audit texture streaming pools and UObject counts.  
- **False positive guardrails:**  
  - Ignore first **30s** after PIE start while pools ramp.  
  - Ignore samples during intentional heavy streaming bursts if harness marks `streaming_burst: true` (future field).

---

## Rule: `memory.leak_signature`

- **Category:** memory  
- **Default severity:** error  
- **Trigger:** Log contains engine leak warning signatures.  
- **Log pattern** (Unreal):

  ```
  LogMemory: Warning:.*[Ll]eaked
  ```

- **Evidence:** `log_path`, `line_number`, matched substring in `detail`.  
- **Remediation hints:** fix UObject / refcount site cited nearby in log; validate subsystems unregister on teardown.  
- **False positive guardrails:** editor-only `LogMemory: Warning:` noise — compare against known editor shutdown ordering; downgrade to `warn` only when `spec_only_as_info` is active in project config.

---

## Rule: `crash.fatal_signal`

- **Category:** crash  
- **Default severity:** critical  
- **Trigger:** Non-recoverable fatal signatures.  
- **Log pattern** (Unreal):

  ```
  (?:Fatal error:|LogWindows: Error: appError)
  ```

  Either substring on a line constitutes a match (no capture required for minimal detection).

- **Evidence:** `log_path`, `line_number`; include short excerpt in `detail`.  
- **Remediation hints:** inspect crash call site, native plugins, and GPU drivers; reproduce under `-log` with minimal map.  
- **False positive guardrails:** treat `LogWindows: Error: appError` only when not part of a known benign automation teardown string (project allowlist in **M7-P3**).

---

## Rule: `crash.ensure_fired`

- **Category:** ensure  
- **Default severity:** warn  
- **Trigger:** Count of ensure lines exceeds `max_ensure_count`.  
- **Log pattern** (Unreal):

  ```
  Ensure condition failed:
  ```

- **Evidence:** `metric_value` (count), `threshold` (`max_ensure_count`).  
- **Remediation hints:** fix predicate; remove hot-loop Ensures; gate dev-only paths.  
- **False positive guardrails:** editor-only test maps may raise count — scope findings to declared `DECLARED_SCOPE` maps when harness provides it.

---

## Rule: `streaming.stall`

- **Category:** streaming  
- **Default severity:** warn  
- **Trigger:** Parsed flush duration exceeds `streaming_stall_ms` (default 500ms).  
- **Log pattern** (Unreal):

  ```
  LogStreaming: Warning: Flushing.*took ([0-9]+\.[0-9]+)\s*ms
  ```

  Capture group **1** is duration in milliseconds.

- **Evidence:** `metric_value`, `threshold`, `log_path`, `line_number`.  
- **Remediation hints:** reduce synchronous loads; fix oversized soft references; tune `s.AsyncLoadingTimeLimit`.  
- **False positive guardrails:** ignore stalls entirely contained within level load window matching `LogLoad: Took .* to load` within **±2** lines when correlation is available.

---

## Rule: `asset.missing`

- **Category:** asset  
- **Default severity:** error  
- **Trigger:** Failed asset load warnings.  
- **Log pattern** (Unreal):

  ```
  LogUObjectGlobals: Warning: Failed to load.*
  ```

- **Evidence:** `log_path`, `line_number`, asset path substring in `detail`.  
- **Remediation hints:** fix redirectors; restore missing packages; verify case-sensitive paths on Linux cook targets.  
- **False positive guardrails:** optional soft references may warn once — dedupe by normalized object path before counting toward fail.

---

## Rule: `network.latency_spike`

- **Category:** network  
- **Default severity:** warn  
- **Trigger:** Parsed round-trip time exceeds `latency_spike_ms` (**M7-P1:** doc-only; default config sets rule `status: off`).  
- **Log pattern** (Unreal):

  ```
  LogNetPing: Warning: Round-trip.*?([0-9]+\.[0-9]+)\s*ms
  ```

  Capture group **1** is RTT in milliseconds when the line encodes it in this shape.

- **Evidence:** `metric_value`, `threshold`.  
- **Remediation hints:** reduce RPC burst sizes; audit relevancy and replication priorities.  
- **False positive guardrails:** PIE without dedicated server may omit NetPing lines — absence MUST NOT auto-fail; treat as no signal.

---

## Rule: `resilience.deadlock_suspect`

- **Category:** hitch  
- **Default severity:** critical  
- **Trigger:** Single frame time exceeds **10000** ms **or** explicit hang signature lines.  
- **Log pattern** (Unreal) — combined **long frame** and **hang signature** matcher (implementations compare capture **1** to **10000** ms only when the first alternative matches):

  ```
  (?:LogStats: .*Frame [0-9]+.*took ([0-9]+\.[0-9]+) ms|LogWindows: Error: (?:Hang detected|Not responding))
  ```

- **Heartbeat absence:** when logs carry periodic heartbeat lines, implementations evaluate **absence longer than `heartbeat_absence_s`** (from `.cuebert/config/qa-resilience-game.yaml`) using time-window logic; this is intentionally **not** a single-line regex.

- **Evidence:** `metric_value` for long-frame case; `log_path` / `line_number` for hang signature.  
- **Remediation hints:** time-traces; inspect game-thread sync loads; review deadlocks around `FlushRenderingCommands`.  
- **False positive guardrails:** editor breakpoint pauses can exceed 10s — when debugger attached, harness SHOULD set `debugger_attached: true` (future envelope) to downgrade to `warn`.

---

## Cross-reference

- Agent: `docs/_ai_system/agents/agent-qa-resilience-game.md`  
- Config: `.cuebert/config/qa-resilience-game.yaml`  
- Gauntlet artifacts: `.cursor/skills/unreal-build/reference.md`  
- Screenshot advisory: `.cursor/skills/vision-qa/reference.md`
