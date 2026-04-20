# SHIP HARNESS — Gaming Distribution Build Protocol

> **Role:** Distribution-build harness coordinator for cook + certification + packaging  
> **Shortcut:** `/ship`  
> **Activation:** As of **M9**, the Cuebert Supervisor loads this protocol into the **main chat** on `/ship` — same architectural rule as `/o` and `/d`: the harness MUST NOT be spawned as a named `subagent_type` Task; it runs in the main chat so it can chain phase spawns reliably. See `.cursor/rules/cuebert-supervisor.mdc` §0 (Shortcut Scan) and the `subagent_type` prohibition.  
> **Execution context:** Main chat (NOT a nested orchestrator subagent).

> **M9 activation:** The `/ship` harness is **live** in the Supervisor routing table. Cook, cert, package, and upload automation depth remain milestone-gated where noted below; **`/ship --preview`** is the walk-only health check (§15): no Task spawns, no cook subprocesses, no file writes.

---

## 1. Purpose

`/ship` is Cuebert’s harness for producing a **distributable build** of a gaming project: a clean, guard-gated tree, an engine **cook** pipeline, **platform certification** checks against configurable profiles (severity-threshold driven; no vendor checklist text in this doc), **packaging** into a target artifact format, and **optional** upload to a distribution channel (for example itch.io, Steam, or a custom endpoint). The harness targets an outcome where **another human can run the build without Cuebert** — binaries or archives suitable for players or storefront technical review, not editor-only iteration. Strict **Ship Guards** (§4) enforce entry conditions per phase; failing a gate **halts** the pipeline (§8). **Upload is disabled by default** and requires explicit opt-in in the ship plan (§5). Every completed or failed run **attests** via a ship envelope and **always** commits to memory (§13), unlike `/play`.

---

## 2. Relationship to `/play`, `/ship`, `/o`, and `/cook`

| Dimension | `/play` (M2 harness) | `/ship` (this harness, M3+) | `/o` (Cue orchestrator, inherited) | `/cook` (future shortcut) |
|-----------|----------------------|----------------------------|-------------------------------------|---------------------------|
| **Primary outcome** | In-editor preview (PIE / Play Mode / run project) | Cooked + certified + **packaged** artifact for distribution | Spec → Code → Review → QA for **product/engineering** delivery | Lower-level “run cook only” without full ship chain |
| **Speed / stakes** | Fast, local, **non-destructive** | Slow, **enforced**, produces irreversible-from-harness perspective **distribution binaries** | Phased engineering; not gaming-cook-specific | Narrower than `/ship`; deferred past M8 for shortcut semantics |
| **Cook / package** | No | **Yes** (stubs M3-P2; UE implementation M8-P1) | Not its focus | **Yes** (intended future entry; **not** `/play`) |
| **Cert / compliance** | No | **Yes** — profile + severity floor; stub M3-P2; full M8-P2 | N/A for typical Cue web/service stacks | No (cook-only) |
| **Formal plan** | Lightweight change list; optional hub plan | **Ship plan** required — stricter schema (§5) | Cue plan in `⟨CueActivePlans⟩` per `docs/_ai_system/standards/control-plane-paths.md` | TBD when `/cook` exists |
| **Gaming specificity** | **Yes** — engine, assets, maps, gameplay modules | **Yes** — ship-time artifacts, platforms, store rules | **No** — generic language matrix | **Yes** — engine cook only |
| **Default upload** | N/A | **`none`** — explicit `upload_channel` opt-in only | N/A | N/A |
| **Memory on success** | Optional / relaxed (`agent-play.md` §10) | **`milestone_commit` always** on success (§13) | Per orchestrator / deploy conventions | TBD |

**Normative statements:**

- **`/play`** = iterate + preview (**M2**) — fast, local, non-destructive, **no packaging**. **`/play` output is editor-only** and is **not** a distributable binary for non-developers.  
- **`/ship`** = cook + cert + package (**M3** protocol; **M8** full UE) — slow, enforced, produces a **distribution artifact**. **`/ship` is the ONLY Cuebert harness that produces binaries intended for non-developer distribution** (subject to engine and plan configuration).  
- **`/o`** = generic orchestrate — **not** gaming-specialized. Cuebert’s **`/play`** and **`/ship`** MAY be invoked as **phases or steps inside** an `/o` plan when the operator bridges gaming work into the hub orchestration model; the supervisor still loads harness protocols in **main chat** for `/play` and `/ship`, not as forbidden named `subagent_type` values.  
- **`/cook`** = future lower-level shortcut for “just cook” — **deferred past M8** for shortcut semantics and supervisor registration; do not use `/play` as a cook entrypoint.

**Summary:** Use **`/play`** to **iterate and preview**. Use **`/ship`** when you need a **packaged build another person can run** without the Cuebert workspace. Use **`/o`** for **standard multi-repo engineering** on the Cue hub. Treat **`/cook`** as **roadmap-only** until explicitly documented.

---

## 3. Phase chain (M8-P3 canonical order)

**Canonical phase order** (enforced in M8-P3):

```text
Phases:
  1. pre_cook
     ├── ship.prod_readiness   (M7-P3 enforced; REJECT gate)
     └── ...existing pre-cook guards
  2. cook
     ├── delegated to agent-ship-cook → agent-cook-package-game
     └── ship.cook_package (M8-P3, NEW; enforced; fail halts ship)
  3. post_cook
     ├── ship.qa_resilience    (M7-P3 enforced; REJECT gate for critical/error)
     └── ...existing post-cook guards
  4. package
     ├── delegated to agent-ship-package → agent-cook-package-game
     └── ship.cook_package continues evaluation here (multi-phase guard)
  5. cert
     ├── delegated to agent-ship-cert → agent-cert-game
     └── ship.cert_advisory (M8-P3, NEW; advisory-only, never blocks)
  6. upload (optional, dry-run default)
```

Each phase declares entry gates per §4 and `ship-guards.md`. Failing a **blocking** gate **halts** the pipeline; the harness still runs **Attest** (§3.7) to write the ship envelope and perform memory hooks (§13). Phases are **logical steps** aligned with `agent-ship-*` dispatchers (§11).

### 3.1 Pre-cook

- **Goal:** Validate **tree cleanliness** and **manifest alignment**: no uncommitted changes in the declared ship scope, no disallowed untracked files under cookable directory roots, no **unreferenced** assets per policy (warn-class where deterministic), **engine version** matches project + workspace manifest.  
- **Gating:** **Pre-cook Ship Guards** (§4.1) MUST pass (per severities in §8) before any cook subprocess is invoked. **`ship.prod_readiness`** (below) runs in this bucket.  
- **Dispatch:** Harness-owned evaluation + optional **`generalPurpose`** read-only Task for git/manifest scanning — exact split **M3-P3**.  
- **`ship.prod_readiness` (M7-P2 spec, M7-P3 enforced):** Before cook begins, `/ship` dispatches `agent-prod-readiness-game` with `project_path`, `target_platform`, `target_store`, and `build_config` from the ship plan. If any **REJECT** finding is returned and the **`user-direct-debug`** override is not active (§7.1), `/ship` halts with an error envelope. **INFO** findings are logged but do not block. Default **enforced** (`spec_only_as_info: false` in `.cuebert/config/prod-readiness-game.yaml`); transitional advisory demotion per `ship-guards.md` §2.2. See [`agent-prod-readiness-game.md`](./agent-prod-readiness-game.md), [`prod-readiness-game-rules.md`](../standards/prod-readiness-game-rules.md).

### 3.2 Cook

- **Goal:** Invoke the engine **cook** pipeline (Unreal **UAT BuildCookRun** via **`unreal-build`** MCP tools per [`agent-cook-package-game.md`](./agent-cook-package-game.md)).  
- **Gating:** Pre-cook gates **PASS**; **`ship.cook_package`** evaluates the **`cook`** row in `agent-cook-package-game` `phases[]` (halt on `fail` / `error` unless `cook-package-game.yaml` advisory demotion).  
- **Dispatch:** **`agent-ship-cook`** — thin delegator to **`agent-cook-package-game`** with **`skip_package: true`** (cook-only invocation). See [`agent-ship-cook.md`](./agent-ship-cook.md).  
- **Non-goal:** No direct UAT subprocesses from the cook subagent; all automation routes through **`agent-cook-package-game`**.

### 3.3 Post-cook

- **Goal:** Validate cook outputs before staging/packaging: exit-shaped signals, size budgets, missing assets, and **`ship.qa_resilience`** scan of cook logs / staged artifacts.  
- **Gating:** **`ship.qa_resilience`** dispatches `agent-qa-resilience-game` with **`session_kind: build`**; **critical** / **error** findings **halt** `/ship` (same override policy as M7-P3). Legacy **`guard.cook.*`** rows in §4.2 consume cook telemetry as documented.  
- **Dispatch:** Harness-owned guard runner + prod-readiness-adjacent checks already complete; **no** cert dispatch in this bucket.

### 3.4 Package

- **Goal:** **Stage** and **package** cooked output into the distributable layout per ship plan (Unreal: **`agent-cook-package-game`** **`stage`** + **`package`** phases).  
- **Gating:** Post-cook gates **PASS**; **`ship.cook_package`** continues for **`stage`** and **`package`** phases (any internal phase `fail` / `error` halts unless advisory demotion). Post-package **`guard.package.*`** checks (§4.2) run after artifacts are emitted.  
- **Dispatch:** **`agent-ship-package`** — delegator to **`agent-cook-package-game`** with **`skip_cook: true`**, **`skip_package: false`**. See [`agent-ship-package.md`](./agent-ship-package.md).  
- **Non-goal:** No direct UAT calls from the package subagent.

### 3.5 Cert

- **Goal:** Run **advisory** cert-checklist scan (**`agent-cert-game`**, M8-P2) on the **staged / packaged** tree (`build_path` from cook-package artifacts). INFO/WARN findings only; **no** REJECT severity; **no** ship halt from cert findings.  
- **Gating:** **`ship.cert_advisory`** surfaces findings into the ship envelope as **`cert_advisory: [...]`**; WARN findings log to memory at **info** severity per M8-P2 contract. If `cert_profile: none`, the harness may **skip** dispatch; policy mirrors `agent-cert-game` §skip semantics. Legacy **`guard.cert.*`** catalog rows (§4.2) remain for harnesses that still emit `cert/report.md` alongside **`agent-ship-cert`**; they do not elevate cert-game WARN to **fail** when `advisory_always: true`.  
- **Dispatch:** **`agent-ship-cert`** — delegator to **`agent-cert-game`**. See [`agent-ship-cert.md`](./agent-ship-cert.md), [`agent-cert-game.md`](./agent-cert-game.md).

### 3.6 Upload (optional)

- **Goal:** Push packaged artifact to **`upload_channel`** when not `none`.  
- **Gating:** **Disabled by default** — requires **`upload_channel != none`** in ship plan **and** all prior **blocking** guards **PASS** including post-package guards. Any failure → **no upload**, **BLOCKED** state for upload phase.  
- **Dispatch:** **`agent-ship-upload`** — **stub M3-P2**, full implementation **post-M8**.  
- **Credentials:** Resolved only via vault per `docs/_ai_system/standards/vault-standard.md` — never from ship plan files (§14).

### 3.7 Attest (always)

- **Goal:** Write the **ship envelope** (`envelope.json`) with **all phase verdicts**, artifact paths, checksums, version metadata, git SHA, engine version, cert summary pointers, and optional upload status. Run **mandatory memory hooks** (§13).  
- **Gating:** None — **always executes** after halt or success so audits exist.  
- **Skippable:** **No** — not skippable even when `--skip-memory` appears on other harnesses in older docs; for `/ship`, memory attestation is **policy-locked** in M3-P1 (future flags may not suppress `troubleshoot_commit` on failure — **M3-P3** reconciles with supervisor).

### 3.8 Session outcomes (normative vocabulary)

| State | Meaning | Next action |
|-------|---------|-------------|
| **`running`** | A phase Task or harness step is in flight. | Wait; avoid duplicate cook/upload for the same session id. |
| **`blocked`** | A Ship Guard or phase tool returned **fail** severity, or cert/package/upload prerequisites not met. | Operator fixes tree or plan; inspect envelope + cert report; re-run `/ship`. |
| **`not_applicable`** | Engine automation or cook toolchain missing. | Human cook instructions in trace; envelope records reason; memory still commits (§13). |
| **`complete`** | All required phases through Package passed; Upload skipped or succeeded; Attest succeeded. | Distribute artifact from trace path; optional store-side steps outside Cuebert. |

### 3.9 Harness position in the cuebert chain

```text
/play  →  /ship  →  (optional) /cook  …
```

- **`/play`:** iteration + preview — **no** distribution binary.  
- **`/ship`:** cook + cert + package (+ optional upload) — **distribution artifact**.  
- **`/cook`:** deferred shortcut — **do not** assume `/ship` implies a separate `/cook` invocation in M3.

### 3.10 Slim Task envelopes (sketches — M3-P2)

Do **not** paste full canonical agent bodies into Task prompts. Follow `docs/_ai_system/agents/agent-orchestrator.md` §3: a **slim envelope** with repo/branch/project, engine, **ship plan pointer**, prior phase summary, artifact roots, and output contract. **`subagent_type`** is always **`generalPurpose`** per `.cursor/rules/cuebert-supervisor.mdc`.

**Cook phase (`agent-ship-cook` role):**

```text
## Cuebert /ship — Cook
**First action:** Read cook slim (M3-P2 path TBD). Do NOT start upload or signing.

## Task envelope
HUB_REPO: [absolute path to cuebert hub]
APP_REPO: [from workspace-manifest projects.{key}.path — absolute]
PROJECT_KEY: [manifest key]
ENGINE: [unreal | unity | godot]
COOK_FLAVORS: [from ship plan]
TARGET_PLATFORMS: [from ship plan]
ARTIFACT_ROOT: [.cuebert/traces/ship/<timestamp>/cook/]

## Expected output
Cook log paths, exit summary, list of cooked output roots; explicit alignment to guard ids in docs/_ai_system/agents/agent-ship.md §4.
```

**Cert phase (`agent-ship-cert` role):**

```text
## Cuebert /ship — Cert
**First action:** Read cert slim (M3-P2). Do not embed vendor-secret checklist text in chat logs.

## Task envelope
CERT_PROFILE: [none | indie-light | platform-strict]
COOK_OUTPUT_ROOT: [path]
REPORT_PATH: [.cuebert/traces/ship/<timestamp>/cert/report.md]

## Expected output
Structured findings {id, severity, checklist_id}; markdown report path; severity_floor comparison ready for post-cert guards.
```

**Package phase (`agent-ship-package` role):**

```text
## Cuebert /ship — Package
**First action:** Read package slim (M3-P2).

## Task envelope
PACKAGE_FORMAT: [zip | installer | platform-native]
INPUT_ROOT: [cook output]
OUTPUT_DIR: [.cuebert/traces/ship/<timestamp>/packaged/]

## Expected output
Primary artifact path, checksum algorithm + value, manifest path.
```

**Upload phase (`agent-ship-upload` role, opt-in only):**

```text
## Cuebert /ship — Upload
**First action:** Read upload slim (M3-P2). Abort if upload_channel is none.

## Task envelope
UPLOAD_CHANNEL: [itch.io | steam | custom]
VAULT_SERVICE_IDS: [resolved names only — no secrets]
ARTIFACT_PATH: [from Package]

## Expected output
Upload ticket id or channel-specific handle; final URL if applicable; partial_failure markers on stream interrupt.
```

### 3.11 Production Readiness bridge (INFO → REJECT)

The authoritative **Production Readiness Register** populated during `/o` runs may surface **INFO**-class findings during engineering. For `/ship`, the harness treats agreed **ship-blocking categories** as **REJECT-class** at Pre-cook or Post-cook gates — the **INFO → REJECT** bridge is part of **M3** stub work in the plan (`cuebert-gaming-system` M3 demo). Exact category mapping is **M3-P3**; this doc reserves the gate **before cook** for “no debug-only flags / no mock endpoints in shipping flavor” style checks without enumerating web-stack rules here.

---

## 4. Ship Guards

**Authoritative spec:** `docs/_ai_system/standards/ship-guards.md`. **Defaults:** `.cuebert/config/ship-guards.yaml`.

**Authoritative pattern:** Mirror **`docs/_ai_system/standards/play-preview-guards.md`** — stable **`id`** keys, **`class`** by pipeline position, **`severity`**, evidence contract, YAML config with **`version: 1`**, and **`global.spec_only_as_info`**-style behavior until evaluators exist.

**Config file (hub):** **`.cuebert/config/ship-guards.yaml`** — **written and wired in M3-P3**; **M3-P1** defines the **contract** only. **Project overrides** MAY ship in **`.cuebert/workspace-manifest.json`** under a future `shipGuards.overrides` map (same resolution idea as `playGuards.overrides` in `play-preview-guards.md` §4.3) — **schema prose updated in M3-P3**.

### 4.1 Guard classes (four)

| Class | When run | Purpose |
|-------|----------|---------|
| **Pre-cook** | Before cook subprocess | Git cleanliness, engine version, ship metadata, asset reference hygiene signals |
| **Post-cook** | After cook completes | Exit code, size budgets, missing cooked assets |
| **Post-cert** | After cert subagent (skipped when `cert_profile: none` per §7) | Severity floor, required checklists completed |
| **Post-package** | After package subagent | Artifact exists, checksum matches expected, content manifest generated |

### 4.2 Guard catalog (stable ids)

Each row is **`spec only (M3-P1)`** for evaluators; **implementation milestone** noted. Harnesses MUST NOT rename ids after this release — they are an **API surface** for M3-P3 config and M8 engines.

| `id` | `class` | `severity` | Description | Implementation status |
|------|---------|------------|-------------|-------------------------|
| `guard.git.clean` | pre-cook | fail | Working tree has **no uncommitted changes** within declared ship scope (branch + path roots from plan). | **spec only (M3-P1)**; impl **M3-P3** harness git snapshot |
| `guard.git.untracked_cook_paths` | pre-cook | fail | **No untracked files** under cookable directory roots (engine-specific roots such as `Content/` for UE — exact roots **M3-P3**). | **spec only (M3-P1)**; impl **M3-P3** + **M8-P1** |
| `guard.engine.version_match` | pre-cook | fail | Declared engine kind + version match **workspace manifest** and project engine association where applicable. | **spec only (M3-P1)**; impl **M8-P1** (UE) |
| `guard.project.ship_metadata` | pre-cook | fail | Project manifest (or ship plan projection) includes **ship metadata**: at minimum `target_platforms`, `cook_flavors`, `package_format` consistency. | **spec only (M3-P1)**; impl **M3-P3** |
| `guard.assets.referenced_in_cook` | pre-cook | warn | Heuristic scan for **unreferenced** or suspiciously orphaned assets that commonly break cook (deterministic rules only). | **spec only (M3-P1)**; impl **M4–M8** asset graph |
| `guard.cook.exit_code` | post-cook | fail | Cook subprocess **exit code 0**; structured “skip” only when harness explicitly runs dry-run preview (**M3-P3** `--preview` semantics). | **spec only (M3-P1)**; impl **M8-P1** |
| `guard.cook.size_budget` | post-cook | warn→fail | Cooked output size within configured **byte budget**; crosses **fail** threshold when exceeded. | **spec only (M3-P1)**; impl **M8-P1** |
| `guard.cook.missing_assets` | post-cook | fail | Required cooked assets / manifest entries absent after cook. | **spec only (M3-P1)**; impl **M8-P1** |
| `guard.cert.severity_floor` | post-cert | configurable | No cert finding above configured severity (for example **fail** if any `error` when floor is `warn` — exact enum **M8-P2**). | **spec only (M3-P1)**; impl **M8-P2** |
| `guard.cert.required_checklists` | post-cert | fail | All checklist ids required by **`cert_profile`** executed and produced **PASS** or allowed **waived** entries per policy. | **spec only (M3-P1)**; impl **M8-P2** |
| `guard.cert.report_emitted` | post-cert | fail | When `cert_profile != none`, **`cert/report.md`** exists and is non-empty summary. | **spec only (M3-P1)**; impl **M3-P2** stub writer |
| `guard.package.exists` | post-package | fail | Primary package artifact path exists on disk. | **spec only (M3-P1)**; impl **M8** |
| `guard.package.checksum` | post-package | fail | Recorded checksum matches recomputed hash for the artifact bytes. | **spec only (M3-P1)**; impl **M8** |
| `guard.package.manifest` | post-package | fail | **Manifest of contents** generated beside or inside package per format rules. | **spec only (M3-P1)**; impl **M8** |

**Count:** **14** stable guard ids (within requested 10–14 range inclusive).

### 4.3 Evidence and empty-evidence policy

Mirror **`play-preview-guards.md` §5** and **`agent-play.md` §4.2**: each **`fail`** or **`warn`** finding MUST carry **non-vacuous evidence** (paths, hashes, log excerpts). Content-free failures invalidate the guard report and the harness MUST treat that as a **blocked** ship session.

### 4.4 `ship_guards_overrides`

Ship plan field **`ship_guards_overrides`** (§5) MUST be a **structural subset** of the **`ship-guards.yaml`** schema: per-guard `enabled`, `default_severity`, optional `threshold` objects — **exact merge rules M3-P3**.

---

## 5. Inputs (ship plan schema)

A `/ship` run requires a **ship plan** — stricter than a casual `/play` intent: it is the **authoritative contract** for engines, platforms, flavors, versioning, cert profile, and guard tuning.

### 5.1 Required fields (normative)

```yaml
project: <key from .cuebert/workspace-manifest.json projects map>
engine: unreal | unity | godot
target_platforms: [windows, mac, linux, android, ios, nintendo-switch, ...]
cook_flavors: [development | shipping | debug]
package_format: zip | installer | platform-native
upload_channel: none | itch.io | steam | custom   # default: none
version:
  semver: X.Y.Z
  build_number: N
  internal_label: string
cert_profile: none | indie-light | platform-strict
ship_guards_overrides: { ... }   # optional; must match .cuebert/config/ship-guards.yaml guard keys
memory_commit: always            # /ship ALWAYS commits to memory on completion (success or failure)
```

**JSON equivalent** is acceptable on disk if the hub adopts JSON ship plans in M3-P3; the **field names** above are normative.

### 5.2 Explicitly disallowed inputs / tree states

- **Uncommitted edits** in ship scope at Pre-cook.  
- **Untracked files** in cookable directories (see `guard.git.untracked_cook_paths`).  
- **Mismatched engine versions** between ship plan, manifest, and project association.  
- **Secrets or raw credentials** in the ship plan — use vault only (§14).

### 5.3 Resolution order

1. Ship plan file (path from user, `--ship-plan`, or hub convention under `docs/projects/{project}/plans/active/` — **M3-P3**).  
2. **`.cuebert/workspace-manifest.json`** project entry.  
3. **`.cuebert/config/ship-guards.yaml`** defaults + **`ship_guards_overrides`**.

---

## 6. Outputs

### 6.1 Primary artifact

- **Packaged build** under **`.cuebert/traces/ship/<timestamp>/packaged/`** — format per `package_format`.  
- `<timestamp>` is UTC-sortable (same convention as `/play`: `YYYY-MM-DDTHHMMSSZ` or equivalent).

### 6.2 Ship envelope

- **`.cuebert/traces/ship/<timestamp>/envelope.json`** — phase verdicts, artifact paths, checksums, **semver + build_number + internal_label**, **git SHA**, **engine version**, **cert report summary** (structured pointers, not necessarily full findings duplication), **`upload_status`** when upload ran or attempted.

### 6.3 Cert report

- **`.cuebert/traces/ship/<timestamp>/cert/report.md`** — human-readable findings; may contain **platform-internal** notes — **local only** by default (§14).

### 6.4 Cook logs and partial artifacts

- Cook logs under **`.cuebert/traces/ship/<timestamp>/cook/`** (implementation detail **M8-P1**).  
- On failure or abort, **`.cuebert/traces/ship/<timestamp>/partial/`** MAY retain fragments for forensics (§12).

### 6.5 Memory commits

- **Success:** `milestone_commit` (full) with project, version, platform(s), envelope path (§13).  
- **Failure:** `troubleshoot_commit` with failed phase, findings, envelope pointer (§13).

### 6.6 Hub-only traces

Application repositories remain **zero-footprint** for cuebert control-plane trees per **`docs/_ai_system/standards/control-plane-paths.md`** — ship traces live in the **hub** checkout.

---

## 7. Guard decision tree

**Phase sequence (canonical order, M7-P3 + M8-P3 `ship.*` gates):** same tree as §3 opening diagram — **`pre_cook` → `cook` → `post_cook` → `package` → `cert` → `upload`**. Cert runs **after** package so `agent-cert-game` can scan **`build_path`** from **`agent-cook-package-game`** artifacts.

Pseudo-flow (compare **`play-preview-guards.md` §7**):

```text
1. PRE-COOK GUARDS + ship.prod_readiness (M7-P3)
   a. Load .cuebert/config/ship-guards.yaml + merge ship_guards_overrides + manifest overrides (M3-P3).
   b. Run enabled pre-cook guards in stable sorted order by guard_id.
   c. Dispatch agent-prod-readiness-game; halt on REJECT unless user-direct-debug override (§7.1).
   d. If any resolved severity == fail -> HALT before cook; go to ATTEST (failure).
   e. Else continue.

2. COOK + ship.cook_package (phase: cook)
   a. Dispatch agent-ship-cook -> agent-cook-package-game (skip_package: true).
   b. On agent top-level status fail/error for cook phase -> HALT unless advisory demotion
      (cook-package-game.yaml spec_only_as_info) or user-direct-debug override for cook_package (§7.1).
   c. Else continue.

3. POST-COOK GUARDS + ship.qa_resilience (M7-P3)
   a. If any fail -> HALT before package; ATTEST (failure).
   b. Else continue.

4. PACKAGE + ship.cook_package (phases: stage, package)
   a. Dispatch agent-ship-package -> agent-cook-package-game (skip_cook: true).
   b. On any cook-package-game phase fail/error -> HALT unless advisory demotion or override (§7.1).
   c. POST-PACKAGE GUARDS: if any fail -> session BLOCKED for upload; ATTEST (failure or blocked_upload).

5. CERT + ship.cert_advisory (M8-P3; never blocks)
   a. Dispatch agent-ship-cert -> agent-cert-game when in scope; surface cert_advisory findings.
   b. WARN/INFO findings do not halt; agent error envelope is diagnostic-only (no REJECT path).

6. UPLOAD (only if upload_channel != none AND all blocking gates passed; dry-run default)
   a. Dispatch agent-ship-upload; on mid-stream failure -> envelope upload_status: partial_failure (§12).

7. ATTEST (always)
   a. Write envelope.json with full phase story + checksums.
   b. Memory hooks per §13 (mandatory).
```

### 7.1 Override mechanism (user-direct-debug only)

When invoked as **`user-direct-debug`**, a caller may pass **`--override=accept-risk`**
(equivalent envelope intent: **`override_reject: true`** for production readiness)
to bypass **`ship.prod_readiness`**, **`ship.qa_resilience`**, or a **`ship.cook_package`**
pipeline failure (FAIL gate — audit still required). The override:

- Is honored **ONLY** for **`caller == "user-direct-debug"`**.
- Is **NOT** honored when **`caller`** is any other agent (`agent-ship`,
  `agent-ship-cook`, etc.). Attempted override by non-user callers is treated
  as a **scope violation** and logged to **`troubleshoot_commit`** with severity
  **`error`** and code **`ship.override_unauthorized`**.
- Triggers an **audit entry** on every bypass: **`troubleshoot_commit`** severity
  **`warn`**, body includes **all findings** that would have blocked.
- Does **NOT** auto-accept future runs; must be **re-specified** each time.
- Does **NOT** apply to **`ship.cert_advisory`** — cert-game is **`advisory_always: true`**
  and has no blocking behavior to bypass.

Post-cook, **`agent-qa-resilience-game`** MUST be invoked with
**`session_kind: build`** for the **`ship.qa_resilience`** gate (cook log and
staged artifact analysis). Advisory demotion for that agent follows
**`.cuebert/config/qa-resilience-game.yaml`** → **`spec_only_as_info`**
(transitional only; same warning contract as `ship-guards.md` §11).

---

## 8. Severity and halt semantics

| Severity | Harness behavior |
|----------|------------------|
| **`fail`** | **Hard stop** for the current gate point — no downstream phases except **Attest**. Envelope written; **`troubleshoot_commit`** on failure (§13). |
| **`warn`** | **Continue** with logged finding in envelope and cert/package logs where applicable. **`warn→fail`** guards escalate when thresholds crossed (`guard.cook.size_budget`). |
| **`info`** | **Record only** — default for **spec-only** guards until M8 when `global.spec_only_as_info` analog is true (mirror play guards doc). |

**No `force` flag in M3** — strict by design. Future **M8** MAY document **`--unsafe-ship`** for debug-only operator builds; absent that flag, overrides remain YAML-scoped and auditable.

---

## 9. Non-goals for `/ship`

| Non-goal | Redirect |
|----------|----------|
| **Gameplay balance analysis** | Human design / bespoke analytics — not the ship harness |
| **Asset generation** | `/play` or **M4** ComfyUI pipeline |
| **Playtest automation** | `/play` preview + **M6** Gauntlet / vision QA |
| **Marketing asset generation** | Creative / publishing workflows outside Cuebert |
| **Live-ops deployment** | Cuebert ships **standalone builds**, not **services** or server fleets |
| **Automatic code signing / notarization** | Explicit human or CI steps configured via **`cert_profile`** partner docs — Cuebert does **not** sign binaries by default (§14) |
| **Replacing Cue `/d` for web stacks** | Cue **`agent-deploy.md`** remains for non-gaming deploy |

---

## 10. Engine support matrix

| Engine | Tier | Trajectory in cuebert | First-class cook automation |
|--------|------|----------------------|----------------------------|
| **Unreal Engine 5** | **1** | First-class cook via **UAT BuildCookRun** (proposed orchestration: `ue_uat_cook`, **proposed, M8-P1**) | **M8-P1** |
| **Unity** | **2** | Documented cook contract; implementation **deferred post-M8** | Post-M8 |
| **Godot** | **3** | Documentation-only cook/export contract | Post-M8 |

**Neutrality rule:** Narrative sections stay **engine-abstract** where possible; examples may cite Unreal paths as the **default** Tier 1 surface.

---

## 11. Subagent roster (placeholders)

The `/ship` harness will dispatch **`Task(subagent_type: "generalPurpose")`** roles whose first action is to read a canonical slim — same global prohibition as `/play` against named `.cursor/agents` auto-types as `subagent_type`.

| Logical role | Milestone | Responsibility |
|------------------|-----------|------------------|
| **`agent-ship-cook`** | **M8-P3** | Delegates to **`agent-cook-package-game`** (cook only; `skip_package: true`). |
| **`agent-ship-package`** | **M8-P3** | Delegates to **`agent-cook-package-game`** (stage + package; `skip_cook: true`). |
| **`agent-ship-cert`** | **M8-P3** | Delegates to **`agent-cert-game`** (advisory checklist scan); formats ship envelope. |
| **`agent-ship-upload`** | **Stub M3-P2**; **full post-M8** | Optional channel upload; stream partial failure handling. |

**Backing agents (not ship-named subagent_types):** **`agent-cook-package-game`** (M8-P1), **`agent-cert-game`** (M8-P2), **`agent-prod-readiness-game`** / **`agent-qa-resilience-game`** (M7; **`ship.*`** gates).

A reusable **ship plan** template is at **`docs/projects/_templates/ship-plan-template.md`**. Worked dry-run example: **`docs/_ai_system/examples/ship-sample-run-hello-level.md`**.

**Explicit statement:** Dispatch remains **`Task(subagent_type: "generalPurpose")`** reading these protocol docs; no gaming-named Cursor auto-types.

### 11.1 Dispatch rules (M3-P2+)

| Rule | Detail |
|------|--------|
| **Task type** | Always `generalPurpose` unless a future milestone documents `shell` isolation for cook only — never gaming-named Cursor auto-types. |
| **Harness location** | `/ship` coordinator runs in **main chat** per `.cursor/rules/cuebert-supervisor.mdc` (same family as `/d`). |
| **Chaining** | Pre-cook → Cook → Post-cook → Package → Post-package → Cert (advisory) → Upload (opt-in) → Attest. |
| **Parallelism** | **No** parallel cook or upload for the same session unless explicitly spec’d later. |

---

## 12. Rollback and bailout

| Condition | Harness behavior |
|-----------|------------------|
| **Any phase fails** | **Halt** immediately; **Attest** writes envelope; **no partial upload** unless upload phase already started (see below). |
| **Upload in progress then fails** | Envelope records **`upload_status: partial_failure`**; **human intervention** required to reconcile store state. |
| **Previously uploaded build** | **No automatic rollback** — Cuebert is not a live-ops tool; operators retract builds via storefront consoles. |
| **User Ctrl-C / cancel** | Best-effort: terminate subprocesses where implemented; preserve **partial/** artifacts for forensics; **Attest** still runs when harness shutdown hook permits (**M3-P3**). |
| **Git or disk errors** | **Blocked** — no cook start if pre-cook git guard fails; no destructive tree repair inside harness. |

---

## 13. Memory hooks (MANDATORY — policy difference from `/play`)

Every `/ship` run writes to Cuebert memory. **`/play` relaxes memory by default** (`agent-play.md` §10); **`/ship` does not.**

| Event | Tool | Payload (minimum) |
|-------|------|-------------------|
| **Success** | `milestone_commit` | `project`, `version` (semver + build_number), `target_platforms`, **`envelope.json` path**, primary artifact path |
| **Failure** | `troubleshoot_commit` | Failed **phase name**, top **findings**, **`envelope.json` path**, optional cert report path |

**Rationale:** Ship produces **distributable binaries** — a **durable audit trail** is required regardless of operator **memory mode**. Even when **`CUEBERT_MEMORY_MODE=text`**, the **text-only** memory commit still occurs (same tool surface as **`.cursor/skills/memory-toolkit/SKILL.md`**).

Nested under `/o`: Orchestrator memory bridges MAY add fields, but they **must not** silence `/ship` memory writes — **M3-P3** documents any additive envelope keys only.

---

## 14. Security notes (brief)

- **Cook produces binaries** — treat machine and artifact paths as **sensitive** from a supply-chain perspective; operators control where traces are copied.  
- **Signing / notarization:** Cuebert **does not** automatically sign or notarize; when required, those steps are **explicit** human or CI actions referenced by **`cert_profile`** and external runbooks — not implied by cook success.  
- **Upload credentials:** itch.io API keys, Steamworks credentials, and custom channel tokens are resolved **only** via the vault system per **`docs/_ai_system/standards/vault-standard.md`** — **never hardcoded**, **never embedded in ship plans**.  
- **Cert reports** may contain **platform-internal** information; cuebert writes them **locally** under the hub trace path and **does not transmit** them to third parties **without** an explicit, guard-passed **`upload_channel`** step that intentionally includes such data (rare; default **none**).

---

## 15. Preview Mode (`/ship --preview`)

When the user passes `--preview` on `/ship`, the harness walks the ship phase chain **without spawning subagents, invoking cook or package tools, uploading artifacts, or modifying repository files**. This mirrors `agent-orchestrator.md` §8 and `agent-play.md` §11.2: validation and reporting only.

**Activation:** `--preview` is detected in the Supervisor's Global Modifiers (`.cursor/rules/cuebert-supervisor.mdc` §2) and passed in the envelope.

**Phase chain for `/ship --preview`:**

1. **Pre-cook guards** — **`ship.prod_readiness`** via **`agent-prod-readiness-game`** (REJECT gate at full run; preview reports status only).
2. **Cook** — **`agent-ship-cook`** → **`agent-cook-package-game`** (cook phase only at full run; preview lists delegation and prerequisites).
3. **Post-cook guards** — **`ship.qa_resilience`** via **`agent-qa-resilience-game`**.
4. **Package** — **`agent-ship-package`** → **`agent-cook-package-game`** (stage + package phases).
5. **Cert** — **`agent-ship-cert`** → **`agent-cert-game`** (advisory only at full run).
6. **Upload** — **disabled by default**; preview reports channel only when the ship plan would enable it.

**Additional checks:**

- **Ship Guards availability:** Read **`.cuebert/config/ship-guards.yaml`**. For each top-level guard key under `guards:` (including **`ship.prod_readiness`**, **`ship.cook_package`**, **`ship.qa_resilience`**, **`ship.cert_advisory`**, and catalog rows such as **`guard.git.clean`**), report **`status` / `enabled`**, **`phase_boundary`** (or implied class for catalog rows), and **`default_severity`**.
- **Platform matrix:** From the ship plan (or defaults), resolve **`target_platform`** / **`target_platforms`**. For each target, cross-check **`.cuebert/config/cook-package-game.yaml`** → **`platform_matrix`** and report **`on`** as **supported**, **`skeleton`** as **skeleton**, absent keys as **unsupported** (normalize names to the matrix spelling, e.g. `Win64`, `Mac`, `Linux`, `IOS`, `Android`).

**Behavior (aligned with `/play --preview`):** Resolve workspace manifest and active project; probe **`sequentialthinking`** and **`cuebert-*`** MCP groups; spot-check gaming vault paths; verify **`.cuebert/registry/skills.yaml`** `skill_path` entries on disk; run **`cuebert_system_check`** with `scope="all"` and summarize. **Do NOT** spawn Tasks, run UAT, write envelopes to trace dirs, or mutate git.

**Output format:**

```
=== /ship PREVIEW ===
Command: /ship --preview [project]
Project: [name | NOT_FOUND]
Engine: [engine]
Target Platform: [from plan or default]
Target Store: [from plan or default]
Build Config: [from plan or default]

MCP Health:
  sequentialthinking: [PASS | FAIL]
  cuebert-core: [PASS | FAIL]
  cuebert-engine: [PASS | FAIL]
  cuebert-qa: [PASS | FAIL]

Vault (gaming spot-check): [PASS | FAIL | details]
Registry (skills on disk): [PASS | FAIL | missing paths]
Hub integrity (cuebert_system_check): [PASS | WARN | FAIL | summary]

Ship Guards:
  ship.prod_readiness: [on | off] pre_cook [REJECT gate]
  ship.cook_package: [on | off] cook_through_package [FAIL gate]
  ship.qa_resilience: [on | off] post_cook [REJECT gate]
  ship.cert_advisory: [on | off] cert [ADVISORY]
  [... other guards from ship-guards.yaml ...]

Phase Chain:
  1. Pre-cook -> ship.prod_readiness [prerequisites met: yes/no]
  2. Cook -> agent-ship-cook -> agent-cook-package-game [prerequisites met: yes/no]
  3. Post-cook -> ship.qa_resilience [prerequisites met: yes/no]
  4. Package -> agent-ship-package -> agent-cook-package-game [prerequisites met: yes/no]
  5. Cert -> agent-ship-cert -> agent-cert-game [prerequisites met: yes/no]
  6. Upload -> [disabled by default | enabled: channel]

Platform Support (cook-package-game):
  [platform]: [supported | skeleton | unsupported]

Estimated Subagent Spawns: [count]
Modifiers Active: [list]

Issues:
  - [any problems]
=============================
```

For `--preview` runs, **Estimated Subagent Spawns** MUST be **0**. **Modifiers Active** MUST include `--preview` when set.

---

## 16. Cross-references

| Doc | Relationship |
|-----|--------------|
| `docs/_ai_system/agents/agent-play.md` | Peer harness — iteration vs ship; phase vocabulary; trace philosophy |
| `docs/_ai_system/standards/play-preview-guards.md` | Guard taxonomy, YAML, evidence, decision-tree pattern mirrored here |
| `docs/_ai_system/standards/control-plane-paths.md` | Hub traces, `{active-project}`, plan path notation |
| `docs/_ai_system/standards/vault-standard.md` | Credential resolution for upload phase |
| `docs/_ai_system/agents/agent-ops-onboard.md` | **`workspace-manifest.json`** schema and project registration |
| `.cursor/skills/memory-toolkit/SKILL.md` | `milestone_commit`, `troubleshoot_commit` tool semantics |
| `docs/_ai_system/agents/agent-orchestrator.md` | Main-chat harness + `--preview` walk-only pattern reference |
| `.cursor/rules/cuebert-supervisor.mdc` | `/ship` harness routing (M9+); forbidden `subagent_type` values |
| `docs/projects/cue/plans/active/cuebert-gaming-system.md` | Authoritative milestone plan — M3/M8 ship scope |
| `docs/_ai_system/standards/ship-guards.md` §2.2, §4.5, §11 | **`ship.prod_readiness`**, **`ship.qa_resilience`**, **`ship.cook_package`**, **`ship.cert_advisory`** contracts and enforcement status |

---

## 17. Footer

Status: **M9** — Supervisor routes `/ship` and **`/ship --preview`** per §15. M8-P3 integrates cook-package + cert-game dispatch and **`ship.cook_package`** / **`ship.cert_advisory`** guards for full runs; automation depth follows §3 and the gaming-system plan.
