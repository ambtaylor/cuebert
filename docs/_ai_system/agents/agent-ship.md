# SHIP HARNESS — Gaming Distribution Build Protocol

> **Role:** Distribution-build harness coordinator for cook + certification + packaging  
> **Shortcut:** `/ship`  
> **Activation:** When implemented (M3-P3+), the Cuebert Supervisor loads this protocol into the **main chat** on `/ship` — same architectural rule as `/o` and `/d`: the harness MUST NOT be spawned as a named `subagent_type` Task; it runs in the main chat so it can chain phase spawns reliably. See `.cursor/rules/cuebert-supervisor.mdc` §0 (Shortcut Scan) and the `subagent_type` prohibition.  
> **Execution context:** Main chat (NOT a nested orchestrator subagent). Until M3-P3, the Supervisor responds that the harness is not yet wired; this document is the **normative spec** for that wiring.

> **CRITICAL — M3-P1 scope:** This file is **documentation only**. No `.cursor/agents` slims, no Python/shell harness, and no executable cook or cert automation exist for `/ship` in M3-P1. Subagent names in §11 are **placeholders** for M3-P2 stubs and M8 full implementations.

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

## 3. Phase chain (stub — implementation M3-P2 through M3-P3; full cook M8-P1, cert M8-P2)

Each phase declares a **strict entry gate**. Failing a gate **halts** the pipeline; the harness still runs **Attest** (§3.6) to write the ship envelope and perform memory hooks (§13). Phases are **logical steps** aligned with future subagent stubs (`agent-ship-*`, §11).

### 3.1 Pre-cook

- **Goal:** Validate **tree cleanliness** and **manifest alignment**: no uncommitted changes in the declared ship scope, no disallowed untracked files under cookable directory roots, no **unreferenced** assets per policy (warn-class where deterministic), **engine version** matches project + workspace manifest.  
- **Gating:** **Pre-cook Ship Guards** (§4.1) MUST pass (per severities in §8) before any cook subprocess is invoked.  
- **Dispatch:** Harness-owned evaluation + optional **`generalPurpose`** read-only Task for git/manifest scanning — exact split **M3-P3**.  
- **Implementation:** Guard contract **M3-P1** (this doc); default config path **`.cuebert/config/ship-guards.yaml`** — **M3-P3**; evaluators **M8** (UE Tier 1 first).

### Pre-ship readiness scan (`ship.prod_readiness`, M7-P2 spec, M7-P3 enforced)

Before cook begins, `/ship` dispatches `agent-prod-readiness-game` under guard
**`ship.prod_readiness`** with:

- `project_path` from the ship plan.
- `target_platform`, `target_store`, `build_config` from the ship plan.

If any **REJECT** finding is returned and the **`user-direct-debug`** override
is not active (see §7.1), `/ship` halts with an error envelope surfacing the
findings. **INFO** findings are logged but do not block.

**M7-P3** makes this a **strict gate** by default (`spec_only_as_info: false` in
`.cuebert/config/prod-readiness-game.yaml`). The earlier **advisory-only**
behavior is **deprecated** for new hub checkouts; projects still migrating MAY
set **`spec_only_as_info: true`** temporarily (transitional advisory demotion
per `ship-guards.md` §2.2 and §11).

See: [`agent-prod-readiness-game.md`](./agent-prod-readiness-game.md),
[`prod-readiness-game-rules.md`](../standards/prod-readiness-game-rules.md).

### 3.2 Cook

- **Goal:** Invoke the engine’s **cook** pipeline: Unreal **UAT BuildCookRun** (proposed tool name `ue_uat_cook`, **proposed, M8-P1**), Unity **Build Pipeline** entry (proposed, post-M8), Godot **export** CLI (proposed, post-M8).  
- **Gating:** Pre-cook guards **PASS**; cook subprocess contract satisfied before post-cook guards consume outputs.  
- **Dispatch:** **`agent-ship-cook`** — **stub M3-P2**, full UE implementation **M8-P1**.  
- **Implementation:** **M3-P2** stub envelope only; **M8-P1** minimum viable cooked output for documented platforms.

### 3.3 Cert

- **Goal:** Run **platform certification profile** checks: configurable **severity floor**, **required checklist ids** resolved from profile (`none` \| `indie-light` \| `platform-strict` in ship plan), aggregated into a **human-readable report** under the trace tree (§6). Cuebert supports a **cert profile system** with thresholds; **profile pack locations and checklist contents are out of scope for M3-P1** (vendor-confidential material is not reproduced here).  
- **Gating:** Post-cook guards **PASS**; if `cert_profile: none`, the harness **skips** cert subagent work but still runs **post-cert guard** policy documented in §7 (severity floor treated as N/A).  
- **Dispatch:** **`agent-ship-cert`** — **stub M3-P2**, full implementation **M8-P2**.  
- **Implementation:** Stubs **M3-P2**; checklist engines **M8-P2**.

### 3.4 Package

- **Goal:** Bundle cooked output into **`package_format`** (zip, installer stub, or platform-native layout per plan).  
- **Gating:** Post-cert guards **PASS** when cert is in scope; else gate after cook only per §7.  
- **Dispatch:** **`agent-ship-package`** — **stub M3-P2**, full **M8** packaging path for UE.  
- **Implementation:** **M3-P2** stub; **M8** UE-first.

### Cert phase advisory (M8-P2 spec)

After package succeeds, /ship dispatches `agent-cert-game` (spec M8-P2) which
returns advisory cert-checklist findings. These findings are:

- INFO/WARN severity only — cert-game NEVER halts /ship.
- Surfaced in the ship envelope as `cert_advisory: [...]`.
- Logged to memory on WARN findings (severity: info; NOT severity: warn, since
  cert findings are advisory).

Strict gate wiring lands M8-P3. Until then, the call is deferred and /ship
proceeds without cert evaluation.

See: [`agent-cert-game.md`](./agent-cert-game.md).

### 3.5 Upload (optional)

- **Goal:** Push packaged artifact to **`upload_channel`** when not `none`.  
- **Gating:** **Disabled by default** — requires **`upload_channel != none`** in ship plan **and** all prior guards **PASS** including post-package guards. Any failure → **no upload**, **BLOCKED** state for upload phase.  
- **Dispatch:** **`agent-ship-upload`** — **stub M3-P2**, full implementation **post-M8**.  
- **Credentials:** Resolved only via vault per `docs/_ai_system/standards/vault-standard.md` — never from ship plan files (§14).

### 3.6 Attest (always)

- **Goal:** Write the **ship envelope** (`envelope.json`) with **all phase verdicts**, artifact paths, checksums, version metadata, git SHA, engine version, cert summary pointers, and optional upload status. Run **mandatory memory hooks** (§13).  
- **Gating:** None — **always executes** after halt or success so audits exist.  
- **Skippable:** **No** — not skippable even when `--skip-memory` appears on other harnesses in older docs; for `/ship`, memory attestation is **policy-locked** in M3-P1 (future flags may not suppress `troubleshoot_commit` on failure — **M3-P3** reconciles with supervisor).

### 3.7 Session outcomes (normative vocabulary)

| State | Meaning | Next action |
|-------|---------|-------------|
| **`running`** | A phase Task or harness step is in flight. | Wait; avoid duplicate cook/upload for the same session id. |
| **`blocked`** | A Ship Guard or phase tool returned **fail** severity, or cert/package/upload prerequisites not met. | Operator fixes tree or plan; inspect envelope + cert report; re-run `/ship`. |
| **`not_applicable`** | Engine automation or cook toolchain missing. | Human cook instructions in trace; envelope records reason; memory still commits (§13). |
| **`complete`** | All required phases through Package passed; Upload skipped or succeeded; Attest succeeded. | Distribute artifact from trace path; optional store-side steps outside Cuebert. |

### 3.8 Harness position in the cuebert chain

```text
/play  →  /ship  →  (optional) /cook  …
```

- **`/play`:** iteration + preview — **no** distribution binary.  
- **`/ship`:** cook + cert + package (+ optional upload) — **distribution artifact**.  
- **`/cook`:** deferred shortcut — **do not** assume `/ship` implies a separate `/cook` invocation in M3.

### 3.9 Slim Task envelopes (sketches — M3-P2)

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

### 3.10 Production Readiness bridge (INFO → REJECT)

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

**Phase sequence (canonical order, including M7-P3 `ship.*` gates):**

```text
Phases:
  1. pre_cook
     ├── ship.prod_readiness   (M7-P3, enforced)
     └── [existing pre-cook guards]
  2. cook
  3. post_cook
     ├── ship.qa_resilience    (M7-P3, enforced)
     └── [existing post-cook guards]
  4. pre_package
  5. package
  6. upload (optional, dry-run default)
```

The numbered pseudo-flow below inserts **CERT** and **POST-CERT** between
**post-cook** and **package** when `cert_profile != none`. **`pre_package`** in
the shorthand list is the span from **post-cook guards** through **post-cert
guards** up to the **package** dispatch boundary.

Pseudo-flow (compare **`play-preview-guards.md` §7**):

```text
1. PRE-COOK GUARDS
   a. Load .cuebert/config/ship-guards.yaml + merge ship_guards_overrides + manifest overrides (M3-P3).
   b. Run enabled pre-cook guards in stable sorted order by guard_id.
   c. If any resolved severity == fail -> HALT before cook; go to ATTEST (failure).
   d. Else continue.

2. COOK
   a. Dispatch agent-ship-cook (stub M3-P2; real M8-P1).
   b. If cook aborts -> HALT; ATTEST (failure).

3. POST-COOK GUARDS
   a. If any fail -> HALT before cert; ATTEST (failure).
   b. Else continue.

4. CERT (skipped when cert_profile == none)
   a. Dispatch agent-ship-cert when profile requires work.
   b. If cert subagent errors -> HALT; ATTEST (failure).

5. POST-CERT GUARDS
   a. If cert_profile == none: treat severity_floor checks as N/A (emit info findings only).
   b. If any fail -> HALT before package; ATTEST (failure).

6. PACKAGE
   a. Dispatch agent-ship-package.
   b. If package errors -> HALT; ATTEST (failure).

7. POST-PACKAGE GUARDS
   a. If any fail -> session BLOCKED for upload; ATTEST (failure or blocked_upload).

8. UPLOAD (only if upload_channel != none AND all prior guards passed)
   a. Dispatch agent-ship-upload; on mid-stream failure -> envelope upload_status: partial_failure (§12).

9. ATTEST (always)
   a. Write envelope.json with full phase story + checksums.
   b. Memory hooks per §13 (mandatory).
```

### 7.1 Override mechanism (user-direct-debug only)

When invoked as **`user-direct-debug`**, a caller may pass **`--override=accept-risk`**
(equivalent envelope intent: **`override_reject: true`** for production readiness)
to bypass either **`ship.prod_readiness`** or **`ship.qa_resilience`**. The override:

- Is honored **ONLY** for **`caller == "user-direct-debug"`**.
- Is **NOT** honored when **`caller`** is any other agent (`agent-ship`,
  `agent-ship-cook`, etc.). Attempted override by non-user callers is treated
  as a **scope violation** and logged to **`troubleshoot_commit`** with severity
  **`error`** and code **`ship.override_unauthorized`**.
- Triggers an **audit entry** on every bypass: **`troubleshoot_commit`** severity
  **`warn`**, body includes **all findings** that would have blocked.
- Does **NOT** auto-accept future runs; must be **re-specified** each time.

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

| Placeholder name | Milestone | Responsibility |
|------------------|-----------|------------------|
| **`agent-ship-cook`** | **Stub M3-P2**; **full UE M8-P1** | Run engine cook; emit cook logs and output roots. |
| **`agent-ship-cert`** | **Stub M3-P2**; **full M8-P2** | Run cert profile checks; write `cert/report.md` findings structure. |
| **`agent-ship-package`** | **Stub M3-P2**; **full M8** | Produce packaged artifact + checksum + manifest. |
| **`agent-ship-upload`** | **Stub M3-P2**; **full post-M8** | Optional channel upload; stream partial failure handling. |

A reusable **ship plan** template is at **`docs/projects/_templates/ship-plan-template.md`**. Worked dry-run example: **`docs/_ai_system/examples/ship-sample-run-hello-level.md`**.

**Explicit statement:** These subagents **do not exist** as implemented slims in **M3-P1**. They are **logical roles** for future prompts.

### 11.1 Dispatch rules (M3-P2+)

| Rule | Detail |
|------|--------|
| **Task type** | Always `generalPurpose` unless a future milestone documents `shell` isolation for cook only — never gaming-named Cursor auto-types. |
| **Harness location** | `/ship` coordinator runs in **main chat** per `.cursor/rules/cuebert-supervisor.mdc` (same family as `/d`). |
| **Chaining** | Pre-cook → Cook → Post-cook → Cert (if any) → Post-cert → Package → Post-package → Upload (opt-in) → Attest. |
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

## 15. Cross-references

| Doc | Relationship |
|-----|--------------|
| `docs/_ai_system/agents/agent-play.md` | Peer harness — iteration vs ship; phase vocabulary; trace philosophy |
| `docs/_ai_system/standards/play-preview-guards.md` | Guard taxonomy, YAML, evidence, decision-tree pattern mirrored here |
| `docs/_ai_system/standards/control-plane-paths.md` | Hub traces, `{active-project}`, plan path notation |
| `docs/_ai_system/standards/vault-standard.md` | Credential resolution for upload phase |
| `docs/_ai_system/agents/agent-ops-onboard.md` | **`workspace-manifest.json`** schema and project registration |
| `.cursor/skills/memory-toolkit/SKILL.md` | `milestone_commit`, `troubleshoot_commit` tool semantics |
| `docs/_ai_system/agents/agent-orchestrator.md` | Main-chat harness + `--preview` pattern reference for future `/ship --preview` |
| `.cursor/rules/cuebert-supervisor.mdc` | `/ship` stub until wired; forbidden `subagent_type` values |
| `docs/projects/cue/plans/active/cuebert-gaming-system.md` | Authoritative milestone plan — M3/M8 ship scope |
| `docs/_ai_system/standards/ship-guards.md` §2.2, §4.5, §11 | **`ship.prod_readiness`**, **`ship.qa_resilience`** contracts and M7-P3 enforcement status |

---

## 16. Footer

Status: M3-P1 (protocol doc). Subagent stubs: M3-P2. Wiring + config: M3-P3. Full UE implementation: M8.
