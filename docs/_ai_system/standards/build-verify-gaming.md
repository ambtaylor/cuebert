# build_verify — gaming-aware verification (M6-P4)

## 1. Purpose

The `build_verify` core MCP tool answers whether a workspace root looks buildable
under Cuebert’s expectations. For **gaming** repositories it is the first-line
compile/readiness gate that complements `/play`, `/ship`, and `/asset` flows:
it does not drive the editor or ship binaries, but it surfaces whether Unreal
tooling can resolve an engine, whether a dry-run UBT invocation is coherent, and
whether the vision-qa toolkit is reachable for screenshot-style QA. For
**web/server** stacks it remains the legacy typecheck / lint / test / build
runner when no gaming markers are present.

## 2. Supported stacks

| Stack  | Behavior |
|--------|----------|
| Unreal | Live check chain via `unreal-build` + advisory `vision-qa` |
| Unity  | `skip_with_reason` — Unity build toolkit not yet ported (M7) |
| Godot  | `skip_with_reason` — Godot build toolkit not yet ported (M7) |

If no Unreal, Unity, or Godot markers are found, classification falls through to
the web/server detector; when that also yields no runnable stack, the tool
returns `not_applicable` with the standard gaming-oriented explanation.

## 3. Unreal check chain

Checks run in order. **Check 1** errors stop the chain (checks 2 and 3 are not
executed). **Check 1** failures (`not_configured`, `invalid`) still allow checks
2 and 3 to run.

1. **`unreal.status`** — `unreal_build_status()`  
   Maps tool `status`: `ok` → pass; `dry_run` → dry_run; `not_configured` /
   `invalid` → fail; timeout or exception → error (chain stops).

2. **`unreal.build_dry_run`** — `unreal_build_target()` with
   `CUEBERT_UNREAL_BUILD_MODE=dry_run` forced for the call (previous env value
   restored afterward). Runs only if check 1 was pass or dry_run; otherwise
   skip with `detail` noting the prerequisite. Maps tool `status`: `dry_run` or
   `pass` → pass; `error` or `timeout` → fail.

3. **`vision.status`** — `vision_qa_status()`  
   Maps `ok` / `dry_run` → pass; any other status, timeout, or exception → fail.
   **Advisory:** a fail here does **not** flip the top-level envelope to fail.

## 4. Envelope schema

Gaming and not-applicable outcomes share this JSON shape (values illustrative):

```json
{
  "status": "pass | fail | skip_with_reason | not_applicable | error",
  "mode": "live | dry_run",
  "stack": "unreal | unity | godot | null",
  "project_path": "absolute path to .uproject, project.godot, Unity root, or null",
  "checks": [
    {
      "name": "unreal.status | unreal.build_dry_run | vision.status",
      "status": "pass | fail | skip | dry_run | error",
      "duration_s": 0.0,
      "detail": "human-readable summary"
    }
  ],
  "reason": "string or null (e.g. skip_with_reason text)",
  "warnings": ["strings"],
  "errors": ["strings"],
  "version": "1.0.0"
}
```

`version` tracks the check set (`GAMING_BUILD_VERIFY_VERSION` in
`build_verify.py`). Bump it when checks are added, removed, or reordered.

## 5. Top-level status resolution

- **pass** — No non-advisory check has `fail` or `error`; each non-advisory
  check is `pass`, `dry_run`, or `skip` (e.g. `unreal.build_dry_run` skipped when
  `unreal.status` was neither pass nor dry_run).
- **fail** — At least one non-advisory check is `fail`.
- **error** — At least one non-advisory check is `error`, or multiple gaming
  stacks were detected.
- **skip_with_reason** — Unity or Godot placeholder (M7).
- **not_applicable** — No gaming markers and no runnable web/server stack (or
  unsupported language override surfaced as not_applicable).

## 6. Advisory checks

`vision.status` is **advisory**. Its `fail` or `skip` does not downgrade a
top-level `pass` driven by Unreal checks. The check’s `detail` field states this
explicitly so harnesses do not misread a vision failure as a broken compile.

## 7. Timeouts

Per-check thread caps using `ThreadPoolExecutor(1)` and `future.result(timeout)`:

| Check               | Timeout |
|---------------------|--------:|
| `unreal.status`     | 30 s    |
| `unreal.build_dry_run` | 120 s |
| `vision.status`     | 10 s    |

## 8. Environment variables

| Variable | Role |
|----------|------|
| `CUEBERT_BUILD_VERIFY_TARGET_NAME` | Overrides UBT target name (default `Editor`). |
| `CUEBERT_UNREAL_BUILD_MODE` | Temporarily forced to `dry_run` around `unreal_build_target`; unset vs set-empty is preserved distinctly when restoring. |

## 9. Detection logic

Scan **only** the project root and **one** directory level beneath it (no deep
crawl):

- **Unreal** — any `*.uproject` file.
- **Unity** — `ProjectSettings/ProjectVersion.txt` exists.
- **Godot** — `project.godot` exists.

`project_path` in the envelope is the realpath of the `.uproject`, the
`project.godot` file, or the Unity project root directory containing
`ProjectSettings/`. This aligns with the depth and marker intent described in
`docs/_ai_system/agents/agent-ops-onboard.md` (onboard additionally mentions
`.sln` pairing for Unity; `build_verify` keys off `ProjectVersion.txt` as the
portable marker for M6-P4).

If more than one **engine family** is detected (e.g. Unreal and Godot), the tool
returns `status: error` with `errors: ["Multiple gaming stacks detected; ambiguous"]`
and both paths listed in `warnings`.

## 10. Extension points (M7+)

Unity and Godot will gain real check chains alongside Unreal. When doing so,
bump `GAMING_BUILD_VERIFY_VERSION` so downstream agents can branch on `version`
for migration. Preserve envelope keys to avoid breaking `agent-play-qa` and
guard harnesses.

## 11. Failure modes

| Situation | Outcome |
|-----------|---------|
| Skill module missing on disk | Check `error` with `build_verify.skill_not_found` in `detail`; import failure on check 1 stops the chain and sets top-level `error`. |
| `unreal.status` timeout / exception | Top-level `error`. |
| Multiple gaming stacks | Top-level `error` plus path warnings. |

## 12. Non-goals

- No live compilation is required for a top-level **pass** when dry-run is
  forced for the build step.
- No CI orchestration, matrix builds, or artifact publishing (see M8 for cook
  / ship hardening).
- No pixel-level screenshot verification here — that remains `vision-qa` compare
  tools and play agents.

## 13. Cross-references

- Skills: `.cursor/skills/unreal-build/`, `.cursor/skills/vision-qa/`
- Agents: `docs/_ai_system/agents/agent-ops-onboard.md`,
  `docs/_ai_system/agents/agent-play-qa.md` (when present)
- Plan: `docs/projects/cue/plans/active/cuebert-gaming-system.md` — milestone M6-P4
