# build_verify gaming envelope — synthetic examples

These examples are **illustrative only** (no commands were executed to produce
them). They show how M6-P4 aggregates Unreal and vision checks into one
envelope.

## Scenario A — Unreal project, engine not configured (dry-run build still passes)

Context: `build_verify` runs in a directory that contains `Game.uproject`. No
Unreal engine is installed or `CUEBERT_UNREAL_ENGINE_PATH` is unset, so
`unreal_build_status` returns `not_configured`. Check 2 still runs under forced
`dry_run` and succeeds. `vision_qa_status` returns `ok`. Because `unreal.status`
is **non-advisory** and mapped to **fail**, the top-level status is **fail**
even though vision passed.

```json
{
  "status": "fail",
  "mode": "live",
  "stack": "unreal",
  "project_path": "/tmp/SampleGame/Game.uproject",
  "checks": [
    {
      "name": "unreal.status",
      "status": "fail",
      "duration_s": 0.04,
      "detail": "Unreal engine root not found. Set CUEBERT_UNREAL_ENGINE_PATH or vault unreal.engine_path (logical tier: shared/unreal/engine_path)."
    },
    {
      "name": "unreal.build_dry_run",
      "status": "pass",
      "duration_s": 0.12,
      "detail": "forced dry_run path; tool status=dry_run"
    },
    {
      "name": "vision.status",
      "status": "pass",
      "duration_s": 0.01,
      "detail": "Advisory only: failure does not fail build_verify top-level status. vision-qa readiness probe. status=ok."
    }
  ],
  "reason": null,
  "warnings": [],
  "errors": [],
  "version": "1.0.0"
}
```

## Scenario B — Unity project (placeholder)

A repo root contains `ProjectSettings/ProjectVersion.txt`. No Unreal chain runs.

```json
{
  "status": "skip_with_reason",
  "mode": "live",
  "stack": "unity",
  "project_path": "/tmp/UnitySample",
  "checks": [],
  "reason": "Unity build toolkit not yet ported (tracked for M7)",
  "warnings": [],
  "errors": [],
  "version": "1.0.0"
}
```

## Scenario C — Empty hub-style tree (not applicable)

No `.uproject`, `project.godot`, or Unity `ProjectVersion.txt`, and no
single-language web markers (e.g. a documentation-only repo).

```json
{
  "status": "not_applicable",
  "mode": "live",
  "stack": null,
  "project_path": null,
  "checks": [],
  "reason": "No gaming stack detected (no .uproject, project.godot, or Unity ProjectSettings/ProjectVersion.txt)",
  "warnings": [],
  "errors": [],
  "version": "1.0.0"
}
```

## Takeaways

- **Fail vs pass** is driven by Unreal checks; vision is diagnostic only.
- **Unity/Godot** intentionally short-circuit with `skip_with_reason` until M7
  adds engine-local toolchains.
- **`version`** must change when the ordered check list changes so automation
  can detect schema drift.
