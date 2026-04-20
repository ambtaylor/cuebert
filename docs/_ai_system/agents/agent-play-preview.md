# PLAY PREVIEW — Editor / Runtime Preview Capture

> **Role:** `/play` harness — **Preview** phase subagent (logical role)  
> **Parent protocol:** `docs/_ai_system/agents/agent-play.md` — read **§3.3 (Preview)**, **§4 (Preview Guards)** context, and **§6 (Subagent roster)**. This file defines **`agent-play-preview`**; guards enforcement timing is **M2-P3**; engine transport is **M5–M6**.  
> **Dispatch:** Only from the `/play` harness in main chat (`agent-play.md` activation block). Not a Supervisor shortcut target. **`subagent_type`** remains **`generalPurpose`** per parent §6.1.

---

## 1. Role

You launch the engine in **preview mode** (Unreal PIE, Unity Play Mode, Godot run-project) and produce **screenshots** plus **relevant log excerpts** for downstream QA. You terminate the session cleanly when capture completes or on timeout. You do **not** cook, package, submit to stores, or run certification checks. You do **not** perform source edits or QA verdict logic.

---

## 2. Inputs

| Input | Required | Description |
|-------|----------|-------------|
| **`PROJECT_KEY`** | Yes | Manifest key for trace naming and reporting. |
| **`APP_REPO`** | Yes | Absolute path to the game project. |
| **`ENGINE`** | Yes | `unreal \| unity \| godot` — selects preview mode §5. |
| **`PREVIEW_MAP`** | No | Explicit map / scene / level path for startup override (Unreal: `/Game/...` map asset or `.umap` stem; engine-specific resolution in M5). |
| **`CAPTURE_MODE`** | Yes | `screenshots` \| `video_stub` \| `log-only` — `video_stub` records intent only until M6 capture tooling exists. |
| **`ARTIFACT_DIR`** | Yes | Hub-resident directory root, typically `.cuebert/traces/play/<timestamp>/preview/` (see §6). |
| **`ENGINE_VERSION`** | No | From manifest; logged in `envelope.json` for reproducibility. |
| **`PREVIEW_TIMEOUT_MS`** | No | Override for §7; default **60000** ms total preview window. |
| **`READY_TIMEOUT_MS`** | No | Override for loaded-map / ready marker; default **30000** ms. |

---

## 3. Outputs

| Output | Description |
|--------|-------------|
| **Screenshot paths** | List of `.png` files under `ARTIFACT_DIR/screenshots/` (may be empty if `log-only` or crash before capture). |
| **Log tail path** | Path to `engine.log` (or merged stderr capture) containing the **tail** the harness configures (see proposed `engine_log_tail`, M5-P#). |
| **`envelope.json`** | Machine-readable summary co-located with artifacts (§8). |
| **`exit_code`** | Process exit code from the editor or wrapper; `null` if not captured. |
| **`duration_ms`** | Wall-clock duration from launch invocation to termination. |

---

## 4. Preview modes (stubs)

### 4.1 Unreal — PIE / editor-driven preview

**Illustrative launch line (not executed in M2):**

```text
Editor <Game>.uproject -Game -Windowed -ResX=1280 -ResY=720 -unattended -nopause -Map=<MapPathOrAsset>
```

- The exact editor binary name (`UnrealEditor` vs `Editor`), `-Game` vs alternate PIE automation APIs, and `-Map=` tokenization are **M5–M6** concerns.  
- **Proposed tools:** `ue_pie_launch` (proposed, M5-P1), `ue_editor_quit` (proposed, M5-P1).  
- **Status: stub (full impl M5-P1)** — Unreal editor bridge.

### 4.2 Unity — Play Mode (batch / automation)

**Illustrative stub:**

```text
Unity -batchmode -projectPath <APP_REPO> -executeMethod <HarnessEntryPoint> -logFile <ARTIFACT_DIR/engine.log>
```

- Entry point and play-mode capture pipeline are **deferred**.  
- **Status: stub (full impl M5-P4)** — Unity Tier 2.

### 4.3 Godot — F5 / run-project equivalent

**Illustrative stub:**

```text
godot --path <APP_REPO> --run --quit-after <N>
```

- Headless vs editor attach and screenshot hooks are **deferred** beyond the stub CLI shape.  
- **Status: stub (full impl M6-P1)** — Godot Tier 3.

---

## 5. Readiness marker (stub contract)

Before capture, the harness **will** wait for a **ready** signal (loaded map, first tick, or engine-specific log line). The readiness marker is evaluated by **`guard.preview.ready_marker`** (see `docs/_ai_system/standards/play-preview-guards.md` §2). Timeout defaults live in `.cuebert/config/play-guards.yaml` → `global.preview_ready_timeout_s`. The exact log regex patterns are **M5–M6** probes. This subagent doc records the **intent**:

| Engine | Example ready heuristic (documentation) |
|--------|-------------------------------------------|
| Unreal | Log line indicating map load completion or PIE start (regex catalog M5/M6). |
| Unity | Player loop entered / scene loaded message in editor or batch log. |
| Godot | Main scene ready or `--- GDScript language server started ---` style markers (TBD). |

**Status: stub (full impl M2-P3)** — “what constitutes ready” is normatively owned by Preview Guards; engine specifics land M5–M6.

---

## 6. Artifact storage

Follow `docs/_ai_system/standards/control-plane-paths.md`: traces are **hub-resident** under the cuebert checkout (`.cuebert/`), not mandatory in application repos.

**Normative layout for this subagent:**

```text
.cuebert/traces/play/<timestamp>/preview/
  screenshots/          # zero or more .png files
  engine.log            # rolling or tail-captured log
  envelope.json         # §8 structured result
```

- `<timestamp>` is UTC sortable (`YYYY-MM-DDTHHMMSSZ` or equivalent per parent `agent-play.md` §5.3).  
- Partial runs **preserve** whatever files were written before abort (§7).  
- **Status: stub (full impl M2-P3)** — harness shell that creates directories and copies logs may not exist until M2-P3.

---

## 7. Timeout and abort

| Parameter | Default | Behavior |
|-----------|---------|----------|
| **Total preview window** | **60 s** | After this, send graceful terminate; if ignored, **hard kill** the wrapper process (platform-specific M5). |
| **Ready wait** | **30 s** | If loaded-map / ready marker not observed, set `status: "timeout"`; still persist partial logs and any screenshots captured so far. |
| **User cancel** | N/A | Treat as harness abort — same as timeout for envelope purposes unless harness sends `status: "aborted"`. |

**Principles:**

1. Never leave orphan editor processes when automation is in control — **M5** implements signal handling.  
2. **Partial artifacts** are valid outputs; QA (`agent-play-qa.md`) must tolerate missing screenshots when `log-only` or crash.  
3. **Status: stub (full impl M5-P1)** — process supervision implementation.

---

## 8. Protocol

Ordered steps for the subagent (or the harness script it drives):

1. **Validate engine reachability** — Parent **G-1** (`agent-play.md` §4). If editor binary or license gate missing → `status: "engine_missing"`; skip launch.  
2. **Resolve preview map** — Use `PREVIEW_MAP` or project default from manifest / project file (M5 resolver).  
3. **Launch** — Invoke stub command family from §4 via future `ue_pie_launch` (proposed, M5-P1) or equivalent.  
4. **Wait for ready marker** — §5; respect **30 s** ready budget.  
5. **Capture** — Write screenshots to `screenshots/` when `CAPTURE_MODE` is `screenshots`; for `video_stub`, write a placeholder note in `envelope.json` only.  
6. **Terminate cleanly** — Close editor session or detach automation; flush logs.  
7. **Emit envelope** — Write `envelope.json` per §9; return paths to harness.

---

## 9. Output envelope (JSON shape)

```json
{
  "status": "ok",
  "screenshots": [
    ".cuebert/traces/play/2026-04-20T120000Z/preview/screenshots/frame_001.png"
  ],
  "log_tail": "... last N KB as UTF-8 text or path-only field variant per harness ...",
  "exit_code": 0,
  "duration_ms": 42000
}
```

**`status` enum:** `ok` | `timeout` | `crashed` | `engine_missing`

**Harness note:** `log_tail` MAY be either inline text (small) or a pointer `{ "path": ".../engine.log", "byte_range": [start, end] }` in a later revision — M2 keeps **documentation** permissive; pick one style when implementing.

---

## 10. Non-goals

| Non-goal | Reason |
|----------|--------|
| **Cooking / packaging** | `/ship` and M3/M8 |
| **Certification or compliance** | Out of preview scope |
| **Balance / gameplay QA analysis** | `agent-play-qa.md` lightweight checks only; deep analysis M6+ |
| **Network calls to Cisco / vendor APIs** | No telemetry exfiltration from Preview |
| **Uploading artifacts** to cloud or ticket systems | Local trace only unless harness adds explicit later phase |

---

## 11. Memory hooks

- **Writes:** This phase **does** write trace artifacts under `.cuebert/traces/play/...` (§6).  
- **`troubleshoot_commit`:** The Preview subagent **does not** call memory tools. The harness **may** commit troubleshooting notes after QA failure per parent §10.  
- **Redaction:** If logs may contain secrets, apply vault / redaction standards from hub docs before persisting (deferred operational detail M2-P3).

---

## 12. Relationship to `--preview` walk-only mode

Parent `agent-play.md` §11.2: `/play --preview` prints the phase chain **without** Task spawns. This subagent is irrelevant in that mode; no fake success should reference screenshots.

---

## 13. Task envelope sketch (harness → Preview)

```text
## Cuebert /play — Preview
**First action:** Read docs/_ai_system/agents/agent-play-preview.md

APP_REPO: [absolute]
ENGINE: [unreal|unity|godot]
ARTIFACT_DIR: [.cuebert/traces/play/<timestamp>/preview/]
CAPTURE_MODE: [screenshots|video_stub|log-only]
```

---

## 14. Engine log capture (stub)

| Concern | M2 stub guidance |
|---------|------------------|
| **Where logs go** | `ARTIFACT_DIR/engine.log` |
| **Tail extraction** | Future `engine_log_tail` (proposed, M5-P1) with byte limit |
| **Encoding** | UTF-8 preferred; binary segments flagged not for QA regex |

**Status: stub (full impl M5-P1)**

---

## 15. Gating before destructive actions

When M2-P3 lands, the harness runs **Preview Guards** before launches that mutate editor state. This subagent assumes **guards already evaluated** unless the envelope includes `GUARDS_SKIPPED: true` for dry-run diagnostics (future flag — do not use without explicit harness support).

---

## 16. Failure taxonomy (for QA consumption)

| `status` | Typical cause | Screenshots | Logs |
|----------|---------------|-------------|------|
| `engine_missing` | Binary not found / wrong `ENGINE_VERSION` | Empty / partial | Minimal |
| `timeout` | Ready marker not reached in 30 s | May exist | Yes |
| `crashed` | Non-zero exit or assert dialog | May exist | Yes |
| `ok` | Capture complete | Expected set | Yes |

---

## 17. Cross-references

| Doc | Use |
|-----|-----|
| `agent-play.md` | Phase chain, guard matrix, trace root |
| `docs/_ai_system/standards/play-preview-guards.md` | Guard ids, envelope contract, post-preview thresholds |
| `agent-play-qa.md` | Consumer of this phase’s artifacts |
| `control-plane-paths.md` | Hub vs app path philosophy |

---

## 18. Video capture deferral

`CAPTURE_MODE: video_stub` exists so envelopes remain **forward compatible**. Until M6 multimedia tooling ships, write:

```json
{ "video": { "status": "not_implemented", "milestone": "M6" } }
```

inside `envelope.json` or equivalent extension field agreed at harness implementation time.

**Status: stub (full impl M6-P3)** — extended capture when vision QA toolkit adds motion / clip support alongside screenshot baselines.

---

Status: M2-P2 (protocol stub). Engine bridge implementation: M5-P1 (Unreal). Preview guards contract (`play-preview-guards.md`, `play-guards.yaml`): M2-P3; ready-marker evaluator: M5-P1.
