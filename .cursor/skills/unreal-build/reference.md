# unreal-build — agent reference

Companion to `SKILL.md`. Covers MCP tool contracts, `_build_runner.py`
subprocess semantics, dry-run behavior, UBT target concepts, environment
variables, failure modes, vault integration, and proposed future tools.

## Tool catalog

### `unreal_build_status() -> dict`

**Purpose:** Resolve engine root, read `Engine/Build/Build.version` when present,
and probe RunUBT / RunUAT / `UnrealEditor-Cmd` on the **host** platform.

**Returns (stable keys):**

| Key | Type | Notes |
| --- | --- | --- |
| `status` | str | `ok`, `not_configured`, `invalid`, `dry_run`, or `error` |
| `mode` | str | Effective `live` or `dry_run` from `_get_mode()` |
| `engine_path` | str or null | Absolute resolved root when known |
| `platform` | str | Host OS bucket: `mac`, `win`, or `linux` |
| `version` | str or null | Parsed `Major.Minor.Patch` (+ changelist) or dry-run token |
| `ubt_available` | bool | True when RunUBT script exists (or synthetic in `dry_run` status) |
| `uat_available` | bool | True when RunUAT script exists (or synthetic in `dry_run`) |
| `editor_cmd_available` | bool | True when `UnrealEditor-Cmd` exists (or synthetic in `dry_run`) |
| `reason` | str or null | Populated for `not_configured` / `invalid` / `error` |
| `warnings` | list[str] or null | Reserved for future non-fatal notices |

**`dry_run` status:** When effective mode is `dry_run`, the envelope is synthetic
(`version` = `5.4.0-dry_run`) so harnesses can proceed without UE installed.

**`not_configured`:** Mode is `live` but no engine root could be resolved.

**`invalid`:** A root path was found but `Engine/Build/BatchFiles` is missing
RunUBT or RunUAT, or `Engine/Binaries/<Host>` is missing `UnrealEditor-Cmd`.

---

### `unreal_build_target(project_path, target_name, platform="Mac", config="Development", timeout_s=None, caller="user-direct-debug") -> dict`

**Purpose:** Invoke Epic **RunUBT** with `-project=` for a sanitized `.uproject`.

**Args:**

| Arg | Type | Requirement |
| --- | --- | --- |
| `project_path` | str | Absolute `.uproject` path that exists on disk |
| `target_name` | str | Regex `^[A-Za-z][A-Za-z0-9_]{0,63}$` |
| `platform` | str | One of `Win64`, `Mac`, `Linux`, `IOS`, `Android` |
| `config` | str | One of `Debug`, `DebugGame`, `Development`, `Shipping`, `Test` |
| `timeout_s` | int or null | Optional per-call timeout; clamped to **3600** |
| `caller` | str | Recorded in traces and memory rows (informational in M6-P1) |

**Returns:** Envelope with `status` in `pass`, `error`, `dry_run`, `timeout`,
`stdout_bytes`, `stderr_bytes`, `log_excerpt` (last 20 stdout lines),
`trace_dir`, structured `error` (`code`, `message`), and optional `memory_id`.

**Dry-run:** Writes synthetic `stdout.log` / `stderr.log` under
`.cuebert/traces/build/<utc>/` and returns `exit_code: 0` without subprocess.

**Live:** Writes real logs; on non-zero exit, `troubleshoot_commit` includes the
last **100** stderr lines.

---

### `unreal_run_commandlet(project_path, commandlet_name, args=None, timeout_s=None, caller="user-direct-debug") -> dict`

**Purpose:** Run `UnrealEditor-Cmd <project> -run=<Commandlet> [args...]`.

**Allowlist:** JSON files under `commandlets/` must list the commandlet `name`.
**M6-P1** ships an empty allowlist, so calls return `blocked` unless
`CUEBERT_UNREAL_BUILD_ALLOW_UNLISTED_COMMANDLETS=1` (dev only). With bypass,
`commandlet_name` must match `^[A-Za-z][A-Za-z0-9_]{0,127}$`.

**Extra args:** Each entry must match
`^[A-Za-z0-9=_.\-/+]{1,256}$` (no whitespace inside a token).

**Returns:** `status` in `pass`, `error`, `dry_run`, `timeout`, `blocked`; plus
`trace_dir`, `error`, `memory_id`.

---

### `unreal_tail_log(project_path, n_lines=100, filter_regex=None) -> dict`

**Purpose:** Read-only tail of newest `*.log` under `<project>/Saved/Logs/`.

**Args:** `n_lines` clamped to **1..10000**. Optional `filter_regex` compiled with
`re.MULTILINE`; invalid regex yields `status: error`.

**Returns:** `status` in `ok`, `not_found`, `dry_run`, `error`; `lines` list;
`log_path` when live and found.

---

## Build target primer (UBT)

- **Targets:** `*Editor` builds the editor module for a game project; `*Game` is
  the standalone game module; `*Server` / `*Client` are networking splits when
  the project defines them. The string passed to UBT is the **module target
  name**, not always the `.uproject` stem.
- **Platforms:** Common values include `Win64`, `Mac`, `Linux`, plus mobile
  `IOS` / `Android` when those SDKs are installed.
- **Configs:** `Debug`, `DebugGame`, `Development`, `Shipping`, `Test` map to
  UE’s standard optimization / symbol settings. `Development` is the usual
  iteration default; `Shipping` is for performance-close binaries.

RunUBT is the low-level compile entry point; UAT wraps UBT for higher-level
graphs (cook/stage/archive) and is referenced for future tools.

---

## Subprocess contract

- **Vector:** `subprocess.run(..., shell=False)` with a `list[str]` argv.
- **Environment:** `_minimal_subprocess_env` copies only safe inherited keys
  (see `SKILL.md` §4).
- **Timeout:** `subprocess.run(..., timeout=seconds)`; `TimeoutExpired` maps to
  toolkit `timeout` statuses.
- **Capture:** stdout/stderr read into memory with a **50MB** cap per stream;
  overflow is truncated with `<truncated>` before UTF-8 decode (`errors="replace"`).

---

## Dry-run semantics

When `_get_mode()` returns `dry_run`, compile and commandlet tools must not
spawn Unreal. They still emit **trace directories** with `cmd.txt`, `meta.json`,
and synthetic logs so `/ship` and `build_verify` fixtures see a stable layout.

`unreal_build_status` short-circuits to a synthetic envelope whenever mode is
`dry_run`, even if a valid engine exists on disk (operators can force dry-run
for planning).

---

## Engine path resolution

Order:

1. `CUEBERT_UNREAL_ENGINE_PATH` (absolute, expanded, strict `resolve()`).
2. Vault `unreal.engine_path` (documented logical path: `shared/unreal/engine_path`).
3. Heuristic scan of known Epic Launcher roots:
   - macOS: `/Users/Shared/Epic Games/UE_*`
   - Windows: `C:/Program Files/Epic Games/UE_*`
   - Linux: `~/Epic Games/UE_*`

The first directory whose `Engine/` child exists wins.

---

## Environment variables

| Variable | Role |
| --- | --- |
| `CUEBERT_UNREAL_ENGINE_PATH` | Absolute engine root override |
| `CUEBERT_UNREAL_BUILD_MODE` | `live` or `dry_run` (overrides auto default) |
| `CUEBERT_UNREAL_BUILD_TIMEOUT_S` | Default subprocess timeout (seconds, capped at 3600) |
| `CUEBERT_UNREAL_PROJECT_PATH` | Optional operator hint (tools take `project_path` arg; reserved for harness defaults) |
| `CUEBERT_UNREAL_BUILD_ALLOW_UNLISTED_COMMANDLETS` | Set to `1` to allow non-allowlisted commandlets in dev |

---

## Failure modes

| Mode | Typical codes / outcomes |
| --- | --- |
| Config | `build.engine_not_found`, `not_configured`, `invalid` status on status tool |
| Input | `build.invalid_project`, `build.invalid_target`, `build.invalid_platform`, `build.invalid_config`, `build.invalid_commandlet_args` |
| Policy | `build.commandlet_not_allowlisted` with `blocked` |
| Runtime | `build.timeout`, `build.subprocess_error`, `build.ubt_failed`, `build.commandlet_failed` |
| Resources | OOM from OS if a runaway child exceeds host RAM (outside toolkit control) |
| Output | Truncated stdout/stderr at 50MB per stream with `<truncated>` marker |

---

## Vault integration

| Vault key | Logical tier doc | Purpose |
| --- | --- | --- |
| `unreal.engine_path` | `shared/unreal/engine_path` | Engine root |
| `unreal.build_mode` | `shared/unreal/build_mode` | `live` / `dry_run` override |
| `unreal.build_timeout_s` | `shared/unreal/build_timeout_s` | Default timeout seconds |

Resolution uses the same `get_resolver().get_credential(...)` pattern as
`unreal-bridge` and `comfyui-toolkit`, guarded when `cuebert_vault` is absent.

---

## Proposed future tools

| Tool | Role | Milestone hint |
| --- | --- | --- |
| `unreal_cook_content` | UAT cook graphs without package | M8 |
| `unreal_package_project` | Stage / archive | M8 |
| `unreal_run_gauntlet` | Automated test pass via Gauntlet | M6-P2 |

These are **not** implemented in M6-P1; they are documented here so registry and
agents can align naming early.

---

## Example envelopes (illustrative)

### `unreal_build_status` — `dry_run`

```json
{
  "status": "dry_run",
  "mode": "dry_run",
  "engine_path": null,
  "platform": "mac",
  "version": "5.4.0-dry_run",
  "ubt_available": true,
  "uat_available": true,
  "editor_cmd_available": true,
  "reason": null,
  "warnings": null
}
```

### `unreal_build_target` — `dry_run`

```json
{
  "status": "dry_run",
  "mode": "dry_run",
  "engine_path": null,
  "project_path": "/Games/Hello/Hello.uproject",
  "target_name": "HelloEditor",
  "platform": "Mac",
  "config": "Development",
  "exit_code": 0,
  "duration_s": 0.0,
  "stdout_bytes": 2048,
  "stderr_bytes": 32,
  "log_excerpt": ["LogCook: Display: Cook time:", "LogOutputDevice: Display: Packaging succeeded"],
  "trace_dir": "/abs/cuebert/.cuebert/traces/build/2026-04-20T12-00-00Z",
  "error": null,
  "memory_id": "11111111-1111-1111-1111-111111111111"
}
```

### `unreal_run_commandlet` — `blocked`

```json
{
  "status": "blocked",
  "mode": "dry_run",
  "project_path": "/Games/Hello/Hello.uproject",
  "commandlet_name": "CookCommandlet",
  "exit_code": null,
  "duration_s": null,
  "trace_dir": null,
  "error": {
    "code": "build.commandlet_not_allowlisted",
    "message": "Commandlet not in .cursor/skills/unreal-build/commandlets/*.json allowlist. Set CUEBERT_UNREAL_BUILD_ALLOW_UNLISTED_COMMANDLETS=1 for local dev only."
  },
  "memory_id": "22222222-2222-2222-2222-222222222222"
}
```

### `unreal_tail_log` — `ok`

```json
{
  "status": "ok",
  "mode": "live",
  "project_path": "/Games/Hello/Hello.uproject",
  "log_path": "/Games/Hello/Saved/Logs/Hello.log",
  "line_count": 12,
  "lines": ["LogInit: Display: Hello", "..."],
  "error": null
}
```

---

## Memory payload hints

`troubleshoot_commit_safe` receives short JSON summaries (never raw secrets):

- **Success:** target or commandlet name, platform/config, `duration_s`, `trace`
  path string.
- **Failure:** same tuple plus `exit_code` and `stderr_tail` list (last 100
  lines for UBT; commandlet failures use stderr tail as well).
- **Blocked commandlet:** commandlet string, caller, `allowed_count`.
- **Gauntlet:** pass counts on success; failure list + stderr tail on `fail`;
  engine missing / parse errors on `error`.

The hub memory DB stores these as operational troubleshooting rows (`source`:
`agent`) consistent with **unreal-bridge** mutate tooling.

---

## JUnit / XML hardening (Gauntlet)

`_gauntlet_parser.parse_gauntlet_xml_fallback`:

1. **defusedxml** — When `defusedxml` is importable, the parser reads only the first
   **max_bytes** from disk into `io.BytesIO` and uses `defusedxml.ElementTree.parse`,
   which avoids XXE and hostile DTD behavior by design.
2. **stdlib fallback** — If `defusedxml` is absent: strip the first `<!DOCTYPE …>`
   declaration (internal-subset aware), then `xml.etree.ElementTree.fromstring` with
   `XMLParser(resolve_entities=False)` on Python **3.13+** (expat entity resolution off).
   Older interpreters fall back to a plain `XMLParser()` after DOCTYPE removal
   (reduced blast radius; installing **defusedxml** is recommended for untrusted XML).
