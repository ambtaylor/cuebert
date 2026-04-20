# Sample run: cook-package-game (synthetic)

Worked example for **`agent-cook-package-game`** (**M8-P1** spec). All timestamps, paths, and metrics are **synthetic** for documentation. No UAT processes are executed here.

**Project:** `hello-level.uproject`  
**Invocation:** **Win64**, **`Shipping`**, **`target_store: internal`**, caller **`agent-ship-cook`**.

---

## Scenario 1: Success (three phases)

**Narrative**

1. **Phase 1 (cook):** Synthetic **`trace_dir`**, duration **120.5** s, exit **0**, **`Saved/Cooked/Win64/`** populated.  
2. **Phase 2 (stage):** Duration **15.2** s, exit **0**, staged tree under **`Saved/StagedBuilds/Win64-Shipping/`**.  
3. **Phase 3 (package):** Duration **8.7** s, exit **0**, **`.zip`** created alongside manifest.  
4. **Artifacts:** Staged build **~2.1 GB**; packaged archive **~1.8 GB**.  
5. **Memory:** **`milestone_commit`** records phase durations and sizes (illustrative payload below).

**Envelope (JSON)**

```json
{
  "status": "pass",
  "mode": "live",
  "project_path": "/abs/game/hello-level/hello-level.uproject",
  "target_platform": "Win64",
  "target_store": "internal",
  "build_config": "Shipping",
  "phases": [
    {
      "name": "cook",
      "status": "pass",
      "started_at": "2026-04-20T12:00:00.000Z",
      "duration_s": 120.5,
      "exit_code": 0,
      "trace_dir": "/abs/hub/.cuebert/traces/cook-package/20260420T120000Z/cook",
      "detail": "Saved/Cooked/Win64/ populated"
    },
    {
      "name": "stage",
      "status": "pass",
      "started_at": "2026-04-20T12:02:00.500Z",
      "duration_s": 15.2,
      "exit_code": 0,
      "trace_dir": "/abs/hub/.cuebert/traces/cook-package/20260420T120000Z/stage",
      "detail": "archive directory populated"
    },
    {
      "name": "package",
      "status": "pass",
      "started_at": "2026-04-20T12:02:15.700Z",
      "duration_s": 8.7,
      "exit_code": 0,
      "trace_dir": "/abs/hub/.cuebert/traces/cook-package/20260420T120000Z/package",
      "detail": "zip created"
    }
  ],
  "artifacts": {
    "cooked_content": "/abs/game/hello-level/Saved/Cooked/Win64/",
    "staged_build": "/abs/game/hello-level/Saved/StagedBuilds/Win64-Shipping/",
    "package_size_mb": 1843.2,
    "manifest_path": "/abs/game/hello-level/Saved/StagedBuilds/Win64-Shipping/Manifest_NonUFSFiles_Win64.txt"
  },
  "error": null,
  "memory_id": "mem_milestone_hello_level_cook_001"
}
```

**Synthetic `milestone_commit` payload (illustrative)**

```json
{
  "kind": "milestone_commit",
  "title": "hello-level Win64 Shipping cook+package",
  "body": "phases: cook 120.5s, stage 15.2s, package 8.7s; staged ~2.1GB; package ~1.8GB",
  "tags": ["ship", "cook-package", "Win64", "Shipping"]
}
```

---

## Scenario 2: Cook failure (short-circuit)

**Narrative**

- **Phase 1 (cook)** exits **1**. Log contains **`LogCook: Error: Could not find content for map /Game/Missing/Map`**.  
- **`unreal_tail_log`** returns the **last 20 lines** (synthetic excerpt referenced in **`detail`**).  
- **Top-level `status`:** **`fail`**.  
- **Phases 2 and 3:** **`skipped`** (not started).

**Envelope (JSON)**

```json
{
  "status": "fail",
  "mode": "live",
  "project_path": "/abs/game/hello-level/hello-level.uproject",
  "target_platform": "Win64",
  "target_store": "internal",
  "build_config": "Shipping",
  "phases": [
    {
      "name": "cook",
      "status": "fail",
      "started_at": "2026-04-20T14:00:00.000Z",
      "duration_s": 45.0,
      "exit_code": 1,
      "trace_dir": "/abs/hub/.cuebert/traces/cook-package/20260420T140000Z/cook",
      "detail": "LogCook: Error: Could not find content for map /Game/Missing/Map; tail last 20 lines via unreal_tail_log"
    },
    {
      "name": "stage",
      "status": "skipped",
      "started_at": "2026-04-20T14:00:45.000Z",
      "duration_s": 0.0,
      "exit_code": null,
      "trace_dir": null,
      "detail": "short-circuit after cook fail"
    },
    {
      "name": "package",
      "status": "skipped",
      "started_at": "2026-04-20T14:00:45.000Z",
      "duration_s": 0.0,
      "exit_code": null,
      "trace_dir": null,
      "detail": "short-circuit after cook fail"
    }
  ],
  "artifacts": {
    "cooked_content": null,
    "staged_build": null,
    "package_size_mb": null,
    "manifest_path": null
  },
  "error": {
    "code": "cook_failed",
    "message": "UAT cook exited 1; see LogCook errors in Saved/Logs"
  },
  "memory_id": "mem_troubleshoot_hello_level_cook_fail_002"
}
```

---

## Scenario 3: Dry-run mode

**Narrative**

- Environment: **`CUEBERT_COOK_PACKAGE_MODE=dry_run`**.  
- All phases return **`dry_run`** with **`.synthesized`** artifact paths.  
- **No** MCP tool dispatches for cook/package (per **`agent-cook-package-game`** §8).  
- **Top-level `status`:** **`dry_run`**.

**Envelope (JSON)**

```json
{
  "status": "dry_run",
  "mode": "dry_run",
  "project_path": "/abs/game/hello-level/hello-level.uproject",
  "target_platform": "Win64",
  "target_store": "internal",
  "build_config": "Shipping",
  "phases": [
    {
      "name": "cook",
      "status": "dry_run",
      "started_at": "2026-04-20T16:00:00.000Z",
      "duration_s": 0.0,
      "exit_code": null,
      "trace_dir": "/abs/hub/.cuebert/traces/cook-package/dry_run/cook.synthesized",
      "detail": "synthetic cook phase"
    },
    {
      "name": "stage",
      "status": "dry_run",
      "started_at": "2026-04-20T16:00:00.000Z",
      "duration_s": 0.0,
      "exit_code": null,
      "trace_dir": "/abs/hub/.cuebert/traces/cook-package/dry_run/stage.synthesized",
      "detail": "synthetic stage phase"
    },
    {
      "name": "package",
      "status": "dry_run",
      "started_at": "2026-04-20T16:00:00.000Z",
      "duration_s": 0.0,
      "exit_code": null,
      "trace_dir": "/abs/hub/.cuebert/traces/cook-package/dry_run/package.synthesized",
      "detail": "synthetic package phase"
    }
  ],
  "artifacts": {
    "cooked_content": "/abs/game/hello-level/Saved/Cooked/Win64/.synthesized",
    "staged_build": "/abs/game/hello-level/Saved/StagedBuilds/Win64-Shipping/.synthesized",
    "package_size_mb": null,
    "manifest_path": "/abs/game/hello-level/Saved/StagedBuilds/Win64-Shipping/manifest.synthesized.txt"
  },
  "error": null,
  "memory_id": null
}
```

---

## Cross-references

- `docs/_ai_system/agents/agent-cook-package-game.md`  
- `docs/_ai_system/standards/cook-package-commands.md`  
- `.cursor/skills/unreal-build/SKILL.md`
