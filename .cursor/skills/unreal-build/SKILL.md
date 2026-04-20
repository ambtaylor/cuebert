---
name: unreal-build
description: Invoke Unreal Engine's command-line build pipeline (UBT, UAT, headless editor commandlets) from cuebert harnesses. Use when users ask to compile a UE project, run a commandlet, produce a cook without packaging, or script a CI-style build. Complements unreal-bridge which targets a RUNNING editor.
version: 0.1.0
status: alpha
---

## 0. Purpose

Command-line Unreal builds for cuebert harnesses. Covers compilation (UBT),
higher-level orchestration (UAT, deferred in later milestones), and headless
editor commandlets. Primary consumers:

- `/ship` M8 cook subagent.
- M6-P4 `build_verify` hook (this milestone).
- Future CI / automation agents.

Unlike **unreal-bridge**, which targets a **live** editor over HTTP Remote
Control, **unreal-build** shells to Epic’s **RunUBT** / **RunUAT** scripts and
**UnrealEditor-Cmd** on disk. No running editor session is required for compile
and commandlet flows.

### UBT vs UAT (orientation)

- **UnrealBuildTool (UBT)** — compiles C++ modules; `RunUBT.sh` / `RunUBT.bat`
  is the supported entry point used by `unreal_build_target`.
- **UnrealAutomationTool (UAT)** — wraps UBT for higher-level graphs (cook,
  stage, archive). **M6-P1** does not expose UAT MCP tools yet; they are
  foreshadowed in `reference.md` for M8 `/ship` work.
- **UnrealEditor-Cmd** — headless editor used by `unreal_run_commandlet` with
  `-run=<Commandlet>`.

## 1. Prerequisites

- Unreal Engine 5.0+ installed locally (Epic Launcher or source build) for
  **live** runs.
- Target project has a `.uproject` file.
- Optional: `CUEBERT_UNREAL_ENGINE_PATH` env or vault `unreal.engine_path`
  (logical tier: `shared/unreal/engine_path` in hub vault docs): absolute path
  to engine root, for example `/Users/Shared/Epic Games/UE_5.4`.
- Optional: `CUEBERT_UNREAL_BUILD_MODE` = `live` | `dry_run`. When unset, the
  toolkit uses **live** only if the engine path resolves and validation finds
  RunUBT, RunUAT, and `UnrealEditor-Cmd` under that root; otherwise it falls back
  to **dry_run** so MCP and agents start without a local UE install.

## 2. Operations (MCP tool catalog)

| Tool | Purpose | Dry-run behavior |
| --- | --- | --- |
| `unreal_build_status` | Resolve engine path, detect UE version, check UBT/UAT availability | Synthetic `dry_run` envelope with version `5.4.0-dry_run` |
| `unreal_build_target` | Compile a target (Editor/Game/Server) via UBT | Synthetic build log + `exit_code: 0` |
| `unreal_run_commandlet` | Invoke a headless editor commandlet | Synthetic commandlet exit status |
| `unreal_tail_log` | Tail the latest Unreal log file (read-only) | Return synthetic 20-line log excerpt |

All tools return a structured envelope. Live mode uses `subprocess.run` with
timeout and encoded stdout/stderr capture via `_build_runner._run_subprocess`.

## 3. Dry-run mode

Toolkit behaves as **dry_run** when any of the following holds:

- `CUEBERT_UNREAL_BUILD_MODE=dry_run` is set explicitly (or vault
  `unreal.build_mode`).
- Engine path (from env or vault) does not resolve to an existing directory.
- Engine path is set but RunUBT / RunUAT / editor-cmd are missing under it
  (implicit via mode resolution: unresolved layout keeps **dry_run** as the
  effective default when mode is unset).

Synthetic envelopes include `"mode": "dry_run"` so downstream agents (M6-P4
`build_verify`, M8 cook) can proceed without a real UE install.

## 4. Security

- Subprocess invocation is the riskiest vector. Controls:
  - Engine path must be absolute and must exist before **live** subprocesses.
  - Target project path must be absolute, exist, and end with `.uproject`.
  - Arguments to UBT and commandlet extras are constrained via allowlists per
    tool.
  - **No** `shell=True`. Argument vectors only.
  - Environment is scrubbed: inherit only minimal `PATH`, `HOME`, `TEMP` /
    `TMPDIR`, and Windows `PROGRAMFILES` / `PROGRAMFILES(X86)` / `USERPROFILE`
    as applicable.
  - Timeout hard cap at **3600s** (1 hour); per-call overrides are clamped.
  - Output captured with a **50MB** cap per stream; larger streams are truncated
    with a `<truncated>` marker.
- No file writes from this toolkit except under
  `.cuebert/traces/build/<timestamp>/` when trace capture is enabled.
- Log discovery for `unreal_tail_log` uses read-only `os.scandir`; it never
  executes files it finds.

## 5. Workflow / commandlet registry

Directory `.cursor/skills/unreal-build/commandlets/` holds the commandlet
allowlist (JSON descriptors). **M6-P1** seeds it empty; commandlets land with
M8 cook (for example `CookCommandlet`, `ResavePackages`). See `commandlets/README.md`.

## 6. Memory hooks

- `unreal_build_status`: no memory commit (query-only).
- `unreal_build_target`: on success, `troubleshoot_commit` with build metadata.
  On failure, `troubleshoot_commit` with error + last 100 lines of stderr.
- `unreal_run_commandlet`: same pattern; **blocked** allowlist violations also
  emit a warning-level `troubleshoot_commit`.
- `unreal_tail_log`: no memory commit.

## 7. Examples (pseudocode)

```python
# unreal_build_status() — typical laptop without UE installed
{"status": "dry_run", "mode": "dry_run", "version": "5.4.0-dry_run", ...}
```

```python
# unreal_build_target(
#   "/Games/Hello/Hello.uproject", "HelloEditor",
#   platform="Mac", config="Development",
# )
# With engine root "/Users/Shared/Epic Games/UE_5.4" and mode live: RunUBT.sh ...
```

```python
# unreal_run_commandlet("/Games/Hello/Hello.uproject", "ResavePackages")
# M6-P1: blocked unless CUEBERT_UNREAL_BUILD_ALLOW_UNLISTED_COMMANDLETS=1
```

```python
# unreal_tail_log("/Games/Hello/Hello.uproject", n_lines=50)
```

## 8. Non-goals

- Asset generation (see comfyui-toolkit + agent-asset).
- Live editor mutations (see unreal-bridge + agent-unreal).
- Cook / stage / archive orchestration details (see agent-ship-cook in M8).
- Package format creation (see agent-ship-package in M8).
- Platform SDK install / validation (see agent-ship-cert in M8).
- Build cache backends (shared DDC, Incredibuild, FASTBuild): future milestone.
- CI job scheduling / triggers: cuebert is interactive-first.

## 9. Cross-references

- `reference.md` — contracts and environment matrix.
- `docs/_ai_system/agents/agent-ship-cook.md` (M3).
- `docs/_ai_system/agents/agent-ship-package.md` (M3).
- `.cursor/mcp-server/core/build_verify.py` (extended M6-P4 for Unreal).
- `unreal-bridge/SKILL.md` — complementary live-editor toolkit.

## 10. Footer

Status: **alpha (M6-P1)**. Four tool stubs shipped. Full integration with `/ship`
cook lands **M8**. `build_verify` hook lands **M6-P4**. Gauntlet test bridge
ships **M6-P2**.

## Appendix A — Trace layout

Each build or commandlet invocation that materializes traces writes under:

`.cuebert/traces/build/<YYYY-mm-ddTHH-MM-SSZ>/`

Files:

| File | Contents |
| --- | --- |
| `cmd.txt` | JSON-encoded argv vector (no shell) |
| `meta.json` | Inputs: tool name, caller, timeouts, engine hint |
| `stdout.log` | Captured or synthetic stdout |
| `stderr.log` | Captured or synthetic stderr |

Downstream harnesses may treat this directory as the canonical artifact pointer
for CI repro and supervisor attestation.
