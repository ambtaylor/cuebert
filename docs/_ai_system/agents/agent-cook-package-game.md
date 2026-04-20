# COOK + PACKAGE — Gaming (`agent-cook-package-game`)

> **Name:** `agent-cook-package-game`  
> **Status:** Spec (**M8-P1**). Dispatches **`unreal-build`** MCP tools when live execution is available; the agent itself remains **prompt-driven** and returns the §3 envelope.  
> **Consumers (dispatchers):** `docs/_ai_system/agents/agent-ship-cook.md` (**M8-P3** wiring), `docs/_ai_system/agents/agent-ship-package.md` (**M8-P3** wiring), `user-direct-debug`.  
> **Audience:** Not user-facing. Always dispatched by another agent or harness.

---

## 0. Identity

| Field | Value |
|-------|--------|
| **Agent id** | `agent-cook-package-game` |
| **Kind** | Unreal Engine **cook**, **stage**, and **package** orchestration via **UAT `BuildCookRun`** (argv catalog + envelopes) |
| **MCP tools** | **`unreal-build`** family: `unreal_build_status`, `unreal_build_target`, `unreal_run_commandlet`, `unreal_tail_log` (see §6 for how `BuildCookRun` maps today vs **M8-P3**) |
| **Canonical commands** | `docs/_ai_system/standards/cook-package-commands.md` |
| **Default config** | `.cuebert/config/cook-package-game.yaml` |

---

## 1. Purpose

Orchestrate **cook** + **package** phases for Unreal game projects using **UAT** via the **`unreal-build`** skill, producing a **staged build** ready for platform-specific distribution.

**Scope:** **Unreal Engine 5** first. **Unity** and **Godot** cook/package flows are **explicitly out of scope** (tracked for future milestones).

**Explicit non-purpose:** Does **not** deploy; does **not** upload to stores; does **not** sign binaries (signing is an external CI concern outside **M8**). Does **not** exercise Gauntlet (**M6-P2**). Does **not** apply production-readiness rules (**M7-P2** `agent-prod-readiness-game`); the harness runs that gate separately (`ship.prod_readiness`).

---

## 2. Inputs

The caller supplies a **cook/package manifest** (JSON object):

```json
{
  "project_path": "abs path to .uproject",
  "target_platform": "Win64" | "Mac" | "Linux" | "IOS" | "Android",
  "target_store": "steam" | "epic" | "gog" | "itchio" | "internal" | null,
  "build_config": "Shipping" | "Test" | "Development",
  "maps": ["str"],
  "cultures": ["en"],
  "compression": "zlib" | "oodle" | "none",
  "output_dir": "abs path to cook+staging root",
  "skip_cook": false,
  "skip_package": false,
  "extra_uat_args": ["str"],
  "timeout_s": null,
  "caller": "agent-ship-cook" | "agent-ship-package" | "user-direct-debug"
}
```

**Rules:**

- `project_path` MUST be an absolute path ending in `.uproject` for **live** runs (after `realpath` normalization).  
- `maps` — explicit map list; **`null`** means *project default* (packaging settings / engine defaults).  
- `cultures` — locales to cook; default **`["en"]`** when omitted (merge from YAML).  
- `compression` — default **`zlib`** for **M8-P1** when omitted.  
- `output_dir` — default **`<project_dir>/Saved/StagedBuilds/`** (or expanded from `output_dir_template` in YAML) when omitted.  
- `extra_uat_args` — each token MUST match the allowlist regex in `cook-package-commands.md` (max **16** entries).  
- `timeout_s` — per-phase wall clock; merges from YAML `defaults.timeout_s` when **`null`**.  
- **`caller`** is **required** for §7 scope and memory hooks. **`agent-play-qa`** is **not** a legal `caller` (denied).

---

## 3. Output envelope

```json
{
  "status": "pass" | "fail" | "dry_run" | "skip" | "error",
  "mode": "live" | "dry_run",
  "project_path": "str",
  "target_platform": "str",
  "target_store": "str | null",
  "build_config": "str",
  "phases": [
    {
      "name": "cook" | "stage" | "package",
      "status": "pass" | "fail" | "skipped" | "dry_run" | "error",
      "started_at": "iso timestamp",
      "duration_s": 0.0,
      "exit_code": null,
      "trace_dir": "str | null",
      "detail": "str"
    }
  ],
  "artifacts": {
    "cooked_content": "str | null",
    "staged_build": "str | null",
    "package_size_mb": null,
    "manifest_path": "str | null"
  },
  "error": null,
  "memory_id": "str | null"
}
```

### 3.1 Status resolution

| Condition | Top-level `status` |
|-----------|---------------------|
| All phases `pass` | `pass` |
| Any phase `fail` | `fail` (remaining phases **not** started — short-circuit) |
| Any phase `error` | `error` |
| All phases `skipped` | `skip` |
| Mixed `dry_run` across phases | top-level `dry_run` allowed; `mode: dry_run` |

`mode` is **`dry_run`** when §8 applies or when global unreal-build mode forces synthetic execution.

### 3.2 Worked status rollup (examples)

| Phase outcomes | Top-level `status` |
|----------------|-------------------|
| `pass`, `pass`, `pass` | `pass` |
| `fail`, `skipped`, `skipped` | `fail` |
| `error`, … | `error` |
| `skipped`, `skipped`, `skipped` | `skip` |
| `dry_run`, `dry_run`, `dry_run` | `dry_run` |

Mixed **`pass`** + **`dry_run`** is **not** expected in **M8-P1**; harnesses SHOULD normalize to a single mode per run.

---

## 4. Phase chain

Three phases, each **gated** on the previous **unless** `skip_*` flags skip work.

| Phase | Commands (UAT) | Success condition |
|-------|----------------|-------------------|
| **`cook`** | `RunUAT BuildCookRun -project=<uproject> -noP4 -platform=<platform> -clientconfig=<config> -cook -pak -compress=<compression>` (+ optional `-map=` / interned map list per project policy) | Exit **0** AND `Saved/Cooked/<Platform>/` populated |
| **`stage`** | `RunUAT BuildCookRun -project=<uproject> -noP4 -platform=<platform> -clientconfig=<config> -stage -archive -archivedirectory=<output_dir>` (+ `-skipcook` when cook already satisfied) | Exit **0** AND staged tree present under `archivedirectory` |
| **`package`** | `RunUAT BuildCookRun -project=<uproject> -noP4 -platform=<platform> -clientconfig=<config> -package -skipcook -skipstage` | Exit **0** AND packaged installer/zip present per platform layout |

**Gating (normative):**

- **Cook precondition:** `agent-prod-readiness-game` returned **`pass`** for the same `project_path` / platform / store / config tuple (**M7-P3** `ship.prod_readiness` guard — not re-run inside this agent).  
- **Package precondition:** **`cook`** phase `pass` AND **`stage`** phase `pass` (or legitimately **`skipped`** only when harness documents idempotent cache reuse — **M8-P3** policy).

**Operational note:** A **single** `BuildCookRun` combining `-cook -stage -package` is valid for CI (see `cook-package-commands.md` Win64 reference). The **phased** argv split above supports partial re-runs, `skip_package`, and clearer per-phase envelopes.

**Platform flags:** Normalized per §5. **M8-P1** ships a **Win64 Shipping** reference path; **Mac**, **Linux**, **IOS**, **Android** rows include **`todo_m8_p2`** where store, signing, or SDK stories are still skeletal.

---

## 5. Platform matrix

| Platform | `clientconfig` (default) | Compression (default) | Notes |
|----------|--------------------------|------------------------|-------|
| **Win64** | Shipping | zlib | **Reference path** for **M8-P1**; Steam-ready focus |
| **Mac** | Shipping | zlib | Codesign **out of scope** here (**M8-P2** cert checklist will flag missing signature) — `todo_m8_p2` for notarization story |
| **Linux** | Shipping | zlib | No store integration; **`internal`** only for **M8-P1** — `todo_m8_p2` for distro formats |
| **IOS** | Shipping | zlib | **Skeleton** — requires macOS host, Xcode, provisioning — `todo_m8_p2` |
| **Android** | Shipping | zlib | **Skeleton** — NDK + Gradle + keystore — `todo_m8_p2` |

Each platform has a matching §6 row in **`cook-package-commands.md`**.

### 5.1 Win64 + Steam-oriented flags (reference)

For **`target_store: steam`** with **`build_config: Shipping`**, argv **SHOULD** include **`-noP4`**, **`-platform=Win64`**, **`-clientconfig=Shipping`**, **`-cook`**, **`-pak`**, and **`-compress=zlib`** on the cook phase. Optional store-specific toggles (Steam SDK redist copy, depot layout) stay **out of M8-P1** — document only in ship plan notes until **M8-P2+**.

### 5.2 Mac / Linux skeleton notes

- **Mac:** expect **`.app`** bundle under the staged archive; **codesign / notarization** are **not** evaluated here.  
- **Linux:** expect an **unsigned** player binary plus **`.pak`** files; treat **`target_store`** other than **`internal`** as **`error`** in **M8-P1** unless project YAML explicitly opts in (**`todo_m8_p2`**).

### 5.3 IOS / Android (`todo_m8_p2`)

- **IOS:** Host **must** be macOS; provisioning profiles and bundle identifiers must match engine settings — packaging argv is **documented-only** in **M8-P1**.  
- **Android:** Keystore, package name, and NDK alignment are **documented-only** — no Gradle invocation contract in this milestone.

### 5.4 `maps` and `cultures` merge

When `maps` is non-null, append **`-cookallmaps=false`** and explicit map iterables only if the harness normalizes to supported UAT map switches (see **`cook-package-commands.md`**). When `cultures` is provided, merge **`-cultures=`** / staged i18n argv per engine version table in the standards doc. **M8-P1** does not mandate a single argv spelling across all UE5 minors — the standards doc carries the **canonical** Win64 example.

---

## 6. Execution model

Prompt-driven. The agent:

1. **Resolves inputs** — merge YAML defaults; normalize `project_path` with **`realpath`**; validate §2 rules and §7 caller.  
2. **For each phase** (`cook`, `stage`, `package`) — compose **`RunUAT BuildCookRun`** argv per §4 and `cook-package-commands.md`; honor `skip_cook` / `skip_package` by emitting **`skipped`** phases with zero duration and continuing per policy.  
3. **Dispatch** — all external I/O goes through **`unreal-build`** MCP tools only (no ad-hoc `subprocess` from the agent).  
   - **`unreal_build_target`:** optional **UBT** precompile when the ship plan splits **compile** from **UAT** (maps to `-build` / target-only work).  
   - **`unreal_run_commandlet`:** **supplemental** headless commandlets only (for example maintenance steps); **not** a substitute for full **`BuildCookRun`**.  
   - **Primary `BuildCookRun`:** **M8-P1** documents argv and trace expectations. **Concrete UAT dispatch** on the MCP server is **M8-P3** (`ship.cook_package` guard + unreal-build UAT adapter). Until then, live runs that require UAT **MUST** either use harness-local dispatch with identical audit/trace semantics **or** return **`dry_run`** / `error` with `detail` explaining the missing adapter.  
4. **Captures `trace_dir`** from each tool envelope that provides it.  
5. **On any phase `fail`:** call **`unreal_tail_log`** with **`n_lines=50`** (clamp per tool) on **`Saved/Logs/`**.  
6. **Returns** the consolidated §3 envelope.

---

## 7. Scope matrix

| Caller | `dry_run` | `live` |
|--------|-----------|--------|
| `agent-ship-cook` | ALLOWED (**M8-P3** default may be either; harness chooses) | REQUIRED (default for real ship) |
| `agent-ship-package` | ALLOWED | ALLOWED |
| `user-direct-debug` | ALLOWED | ALLOWED |
| `agent-play-qa` | **DENIED** | **DENIED** |

**M8-P1** is spec-only; enforcement lands **M8-P3** via new **`ship.cook_package`** guard (config mirrors `.cuebert/config/cook-package-game.yaml` → `scope`).

---

## 8. Dry-run semantics

If **`CUEBERT_COOK_PACKAGE_MODE=dry_run`**, **or** (`skip_cook=true` **AND** `skip_package=true`), **or** `project_path` missing / unreadable:

- Return a **synthetic** envelope: all phases **`dry_run`**, **`artifacts`** populated with **synthetic** paths ending in **`.synthesized`**, **`status`: `dry_run`**, **`mode`: `dry_run`**.  
- **No** subprocess / MCP side effects except what the unreal-build toolkit already performs in global **`dry_run`** mode (still allowed to probe **`unreal_build_status`** if the harness wants — optional; default **no tool dispatches** for pure synthetic path).

---

## 9. Memory hooks

| Top-level `status` | Memory action |
|--------------------|----------------|
| `pass` | `milestone_commit` — include phase durations + artifact sizes |
| `fail` | `troubleshoot_commit` severity **`error`** — failing phase + last **20** log lines (from `unreal_tail_log` or captured stderr) |
| `dry_run` | **no** commit (developer flow) |
| `skip`, `error` | `troubleshoot_commit` severity **`warn`** |

See `.cursor/skills/memory-toolkit/SKILL.md`.

---

## 10. Cross-references

| Doc / artifact | Role |
|----------------|------|
| `.cursor/skills/unreal-build/SKILL.md` | Implementation surface (UBT, commandlets, logs) |
| `.cursor/skills/unreal-build/reference.md` | Tool contracts, trace dirs, dry-run |
| `docs/_ai_system/agents/agent-ship.md` | Primary `/ship` consumer |
| `docs/_ai_system/agents/agent-ship-cook.md` | Cook dispatcher (**M8-P3** wiring) |
| `docs/_ai_system/agents/agent-ship-package.md` | Package dispatcher (**M8-P3** wiring) |
| `docs/_ai_system/agents/agent-prod-readiness-game.md` | Pre-flight gate (**M7-P2** / **M7-P3** `ship.prod_readiness`) |
| `docs/_ai_system/agents/agent-qa-resilience-game.md` | Post-cook gate sibling (**M7-P1** / `ship.qa_resilience`) |
| `docs/_ai_system/standards/cook-package-commands.md` | UAT argv catalog |
| `docs/_ai_system/standards/ship-guards.md` | Guard wiring (`ship.prod_readiness`, `ship.qa_resilience`; **`ship.cook_package`** in **M8-P3**) |
| `docs/_ai_system/agents/agent-ship-cert.md` | Current cert / checklist stub; **M8-P2** introduces advisory **`agent-cert-game`** sibling |
| `docs/projects/cue/plans/active/cuebert-gaming-system.md` | Plan **M8** |

---

## 11. Non-goals

- Code signing (external CI).  
- Store upload (**M8** does not ship an upload agent).  
- Platform SDK installation (operator-managed).  
- Cross-compilation pre-checks (operator-managed).  
- Iterative / incremental cook (**M8-P1** = **full** cook contract only).  
- Unity / Godot cook or export.

---

## 12. Deferred items

- Real agent implementation (prompt-driven execution beyond this spec).  
- **`ship.cook_package`** guard wiring (**M8-P3**).  
- Cert checklist integration (**M8-P2** `agent-cert-game`).  
- Iterative cook and build graph support.  
- Unity / Godot parallel pipelines.  
- Dedicated **`unreal_run_uat`** / argv dispatcher naming and allowlists on the MCP server (**M8-P3**).

---

## 13. Footer

Status: **spec only (M8-P1)**. UAT command catalog + envelope contract + **Win64 Shipping** reference path published. Execution wiring lands **M8-P3**.
