# PLAY HARNESS — Gaming Quick-Iteration Protocol

> **Role:** Fast-iteration harness coordinator for gameplay-visible changes  
> **Shortcut:** `/play`  
> **Activation:** When implemented (M2-P2+), the Cuebert Supervisor loads this protocol into the **main chat** on `/play` — same architectural rule as `/o` and `/d`: the harness MUST NOT be spawned as a named `subagent_type` Task; it runs in the main chat so it can chain phase spawns reliably. See `.cursor/rules/cuebert-supervisor.mdc` §0 (Shortcut Scan) and the `subagent_type` prohibition.  
> **Execution context:** Main chat (NOT a nested orchestrator subagent). Until M2-P2, the Supervisor responds that the harness is not yet wired; this document is the **normative spec** for that wiring.

> **⛔ M2-P1 scope:** This file is **documentation only**. No `.cursor/agents` slims, no Python/shell harness, and no executable preview automation exist for `/play` in M2-P1. Subagent names below are **placeholders** for later milestones.

---

## 1. Purpose

`/play` is Cuebert’s **fast-iteration harness** for changes that should show up in a **live editor preview** (Unreal PIE by default; Unity Play Mode; Godot F5) rather than in a shipped binary. It targets the class of work where the payoff is **seeing the game state move**: asset swaps, level tweaks, C++ gameplay module edits, Blueprint-adjacent source, UI/layout adjustments, and content wiring. The harness optimizes for a **tight loop** from intent to visible feedback: **under 60 seconds from edit to preview when the engine, project, and change scope are warm and automation is available** — this is a **design target**, not a hard SLA; cold starts, large recompiles, or first-time imports may exceed it. `/play` deliberately stays **low-stakes**: no cook, no package, no cert gate, no cloud deploy. For distribution readiness, use `/ship` (M3+). For generic multi-repo engineering lifecycles unrelated to in-editor gameplay preview, Cue’s `/o` remains the general orchestrator (see §2).

---

## 2. When to use `/play` vs `/ship` vs `/o`

| Dimension | `/play` (this harness) | `/ship` (M3+ harness) | `/o` (Cue orchestrator, inherited) |
|-----------|------------------------|----------------------|-------------------------------------|
| **Primary outcome** | In-editor preview (PIE / Play Mode / run project) | Cook + cert + package path toward distribution | Spec → Code → Review → QA chain for **product/engineering** delivery |
| **Packaging / cook** | No | Yes (stub then real in M3/M8) | Not its focus (web/service stacks) |
| **Cert / platform compliance** | No | Yes (advisory → strict per plan) | N/A for typical Cue stacks |
| **Deployment / cloud push** | No | May include release automation per `agent-deploy.md` analog | Deploy harness (`/d`) is separate in Cue |
| **Formal plan requirement** | Lightweight change list; full Cue plan optional for trivial edits | Plan and PR-style gates as ship doc will specify | Cue plan in `⟨CueActivePlans⟩` / hub project plans per `docs/_ai_system/standards/control-plane-paths.md` |
| **Gaming specificity** | **Yes** — engine, assets, maps, gameplay modules | **Yes** — ship-time game artifacts | **No** — generic language matrix (React/Python/Angular/CUE) |
| **Default git behavior** | Local branch commit in **Merge** phase when guards pass; **no push to remote by default** | TBD in M3 docs; expect stricter audit trail | Per Cue orchestrator and project policy |

**Summary:** Use **`/play`** to **iterate and preview**. Use **`/ship`** when you need **build artifacts suitable for distribution or certification**. Use **`/o`** when you are on the Cue hub doing **standard orchestrated engineering** that is not specialized for the gaming preview loop. Cuebert’s `/play` and `/ship` are **specializations** of the “harness in main chat + phased subagents” pattern described for `/o` and `/d` in `docs/_ai_system/agents/agent-orchestrator.md` and Cuebert’s supervisor — they are **not** replacements for `/o` on the Cue meta-repo.

---

## 3. Phase chain (stub — implementation M2-P2 through M2-P4)

The following phases are **logical steps** the harness will implement. Names align with future agent stubs; envelopes and spawn contracts land in M2-P2+.

### 3.1 Plan

- **Goal:** Produce a **lightweight spec** and a **change list** (files, assets, maps, rationale).  
- **Formality:** No mandatory full `/o` plan for **trivial** edits (single asset swap, one-line tweak) — the harness MAY still record a one-paragraph intent block for traceability under `.cuebert/traces/play/<timestamp>/` (see §5).  
- **Outputs:** Change list, risk notes (e.g. “touches `DefaultEngine.ini`”), optional link to an existing hub plan under `⟨CuebertActivePlans⟩` per `docs/_ai_system/standards/control-plane-paths.md`.  
- **Implementation:** Deferred to **M2-P2** (state machine + sample plan in **M2-P4**).

### 3.2 Author

- **Goal:** Apply edits to **gameplay-visible surfaces**: `.uasset` / `.umap` where applicable, `.cpp` / `.h`, generated Blueprint glue, level/world partition data, UI markup for supported engines, scripting assets.  
- **Dispatch:** A **gaming-author** subagent — **stub naming** in the plan references `code-ue-cpp` or a consolidated `code-gaming` slim; **final Task envelope and `.cursor/agents/*` file names are decided in M2-P2**. The canonical **placeholder protocol names** for this doc are listed in §6 (`agent-play-author`).  
- **Constraints:** Author phase MUST respect **declared scope** (paths/globs from Plan or user flag). Cross-cutting refactors without plan agreement are **out of scope** for `/play`.  
- **Implementation:** **M2-P2** (author stub), real UE tooling **M5+** per `cuebert-gaming-system` plan.

### 3.3 Preview

- **Goal:** Launch the engine in **PIE** (Unreal), **Play Mode** (Unity), or **run project** (Godot); capture **screenshots** and **log excerpts** for downstream QA.  
- **Default:** Unreal **PIE** is the Tier 1 path (see §8).  
- **Gating:** **Preview Guards** (§4) run before and after preview where applicable; failures set session state to **BLOCKED** (§9).  
- **Implementation:** **M2-P3** (preview automation + guards wiring); engine bridge specifics **M5–M6**.

### 3.4 QA

- **Goal:** **Lightweight** checks: visual diff against last-known-good or inline heuristics, **console log scan** for obvious failures.  
- **Not in scope for M2:** Full **Gauntlet**, headless UAT runs, multimodal vision QA — those are **M6** per the authoritative plan. **M2-P4** supplies a **sample plan** and harness copy that references a **stub** QA phase only.  
- **Dispatch placeholder:** `agent-play-qa` (§6).  
- **Implementation:** Stub in **M2-P4**; full toolkit integration **M6-P2/P3**.

### 3.5 Merge

- **Goal:** If all guards and QA gates pass, **commit** to the **current local branch** with a message derived from the change list.  
- **Remote:** `/play` **does not push** to `origin` by default. Operators may push manually or a later milestone may add an opt-in flag — **deferred beyond M2-P4** unless explicitly specified in a future plan revision.  
- **Implementation:** **M2-P4** documents `milestone_commit` / branch expectations; git automation may remain manual until tool support lands.

**Ordering:** `Plan → Author → Preview → QA → Merge` is the **happy path**. Remediation loops (Author re-run after QA failure) follow patterns analogous to Cue’s orchestrator remediation, but **exact circuit-breaker counts and memory injections** for `/play` are **deferred to M2-P2** — do not assume parity with `/o` §4A until documented there.

### 3.6 Harness position in the cuebert chain

Long-term ordering (authoritative plan alignment):

```text
/play  →  /ship  →  (optional) /cook  …
```

- **`/play`:** iteration + preview (this document).  
- **`/ship`:** cook + cert + package (M3+); **INFO → REJECT** bridge from Production Readiness registers is documented there, not here.  
- **`/cook`:** roadmap language for dedicated cook steps; **shortcut semantics deferred** — do not treat `/play` as a cook entrypoint.

### 3.7 Session outcomes (normative vocabulary)

| State | Meaning | Next action |
|-------|---------|-------------|
| **`running`** | A phase Task is in flight. | Wait; do not start duplicate spawns for the same phase. |
| **`blocked`** | A Preview Guard or QA gate failed; Merge skipped. | Operator fixes; re-run `/play` with narrowed or corrected scope. |
| **`not_applicable`** | Engine or automation prerequisites missing. | Manual preview instructions in the report; no git Merge. |
| **`complete`** | Guards passed; QA lightweight pass; Merge succeeded (when Merge is enabled for the run). | Optional `/ship` when distribution work begins. |

### 3.8 Slim Task envelopes (sketches — M2-P2)

Do **not** paste full canonical agent bodies into Task prompts. Follow `docs/_ai_system/agents/agent-orchestrator.md` §3: a **slim envelope** with repo/branch/project, engine, plan/change-list pointer, prior phase summary, and output contract.

**Plan phase (future spawn):**

```text
## Cuebert /play — Plan
**First action:** Read the active instructions for Plan phase (M2-P2 slim TBD). Follow harness ordering in docs/_ai_system/agents/agent-play.md §3.

## Task envelope (required)
HUB_REPO: [absolute path to cuebert hub]
APP_REPO: [from workspace-manifest projects.{name}.path — resolved absolute]
PROJECT_KEY: [manifest key]
ENGINE: [unreal | unity | godot]
ENGINE_VERSION: [semver or engine association string]
USER_PROMPT: [verbatim request]
DECLARED_SCOPE: [paths | none]

## Expected output
Change list (markdown table or bullet list), risks, explicit list of files that Author may touch. Stop with structured result — no user approval gate inside the subagent.
```

**Author phase (`agent-play-author` role):**

```text
## Cuebert /play — Author
**First action:** Read gaming author slim (M2-P2 path TBD). Observe DECLARED_SCOPE strictly.

## Task envelope
APP_REPO: [absolute]
BRANCH: [git branch]
CHANGE_LIST: [from Plan]
FORBIDDEN_PATHS: [computed inverse of scope]

## Output constraint
Edit only gameplay-visible surfaces per §3.2. Do NOT start PIE/Play Mode inside this Task unless explicitly allowed in a later revision.
```

**Preview phase (`agent-play-preview` role):**

```text
## Cuebert /play — Preview
**First action:** Read preview slim (M2-P3). Execute Preview Guards before destructive editor actions.

## Task envelope
APP_REPO: [absolute]
ENGINE: [unreal | unity | godot]
ARTIFACT_DIR: [.cuebert/traces/play/<timestamp>/preview/]

## Expected output
Paths to screenshots + log excerpts; PIE/Play session id if available; explicit PASS/FAIL per guard checklist §4.
```

**QA phase (`agent-play-qa` role, lightweight):**

```text
## Cuebert /play — QA (lightweight)
**First action:** Read QA stub slim (M2-P4). Do NOT claim Gauntlet or vision baseline results unless M6 toolkits are present.

## Task envelope
PREVIEW_ARTIFACTS: [paths]
GUARD_REPORT: [paths]

## Expected output
Log scan summary, visual diff summary (thresholds TBD), recommendation: merge | retry author | escalate to M6 QA.
```

**Merge phase (harness-owned or delegated):**

Merge may execute in **main chat** (preferred for small git operations) or a dedicated `generalPurpose` Task with **read-only** preview artifacts — decision **M2-P4**. In all cases, Merge MUST re-read the guard report before `git commit`.

---

## 4. Preview Guards (M2-P3)

Preview Guards are **hard prerequisites** before treating a `/play` session as successful. **M2-P3** implements the enforcement; **M5–M6** deepen engine-specific probes.

| Guard | Description | Notes / deferrals |
|-------|-------------|-------------------|
| **G-1 Engine reachability** | The harness MUST verify that the target **editor or runtime** is reachable via the supported automation channel (Unreal Editor running for PIE; Unity Editor; Godot head or editor — **exact transport deferred to M5**). | Failure → `not_applicable` or `BLOCKED` per §9. |
| **G-2 Compile sanity** | No **compile errors** in affected modules / scripts for the current configuration (e.g. UE **Development Editor**). | Partial project rebuild strategies — **M5–M6**. |
| **G-3 Critical log patterns** | Scan captured logs for **asserts**, **ensures**, **`Error:`** / **`ERROR`** lines, and other **engine-specific fatal patterns**. | **Regex catalogs per engine** — **M5/M6**; M2-P3 may ship conservative generic patterns only. |
| **G-4 Asset reference integrity** | No **missing** `.uasset` / textures / soft object paths introduced by the change list (where deterministically detectable). | Deep reference graph validation — **M4–M5** asset pipeline. |
| **G-5 Scope containment** | Changed paths MUST stay inside **declared scope** (repo-relative roots from Plan or `--scope` / manifest). Silent edits outside scope are a **guard failure** even if the build succeeds. | Manifest: `.cuebert/workspace-manifest.json` project `path` + optional user override. |

**Blocked behavior:** On any **REJECT-class** guard outcome, the harness **does not** perform Merge, **does not** force-push, and **does not** delete artifacts; it writes a **guard report** into the trace directory (§5) and stops.

### 4.1 Severity mapping (preview context)

| Severity | Typical cause | Harness action |
|----------|---------------|----------------|
| **REJECT** | G-2 compile failure, G-4 broken reference, G-5 scope violation | `blocked` — stop chain before Preview or before Merge depending on where detected. |
| **WARN** | Benign log noise, non-fatal editor warning | Record in guard report; **M2-P3** decides whether WARN blocks Merge for Tier 1 UE (default: **WARN does not block** unless tied to gameplay regression heuristics). |
| **INFO** | Performance note, unrelated third-party plugin spam | Attach to trace only. |

**Deferral:** WARN-blocking policy per engine — **M5–M6**.

### 4.2 Evidence requirements

Each guard failure row MUST cite **artifact paths** (log file, screenshot diff json, compile log tail). Empty evidence is treated as **REJECT** of the guard report itself — the harness must not emit content-free failures.

---

## 5. Inputs and outputs

### 5.1 Inputs

| Input | Source |
|-------|--------|
| **User prompt** | Chat message invoking `/play` (optional flags to be defined in M2-P2, e.g. `--preview`, `--project`, `--scope`). |
| **Active project** | Resolved per **Supervisor Step 0.7** in `.cursor/rules/cuebert-supervisor.mdc`: prefer `--project`, then handoff `REPO`/`project`, then `.cuebert/workspace-manifest.json` keys, then heuristics per `docs/_ai_system/standards/control-plane-paths.md` §5. |
| **Engine metadata** | From manifest entry: `engine`, `engine_version`, `language`, and disk `path` to the application repo. |
| **Optional change scope** | User-declared path(s) or globs limiting Author + scope guard (§4 G-5). |

### 5.2 Outputs

| Output | Description |
|--------|-------------|
| **Preview artifacts** | Screenshots, stdout/stderr **excerpts**, optional small video — paths recorded in the session trace `manifest.json` or `README.md` (format **M2-P3**). |
| **Change list** | Files touched, assets added/replaced, rationale from Plan. |
| **Guard report** | Pass/Fail per §4 with evidence pointers. |
| **Next-step suggestion** | e.g. “Fix compile error in `FooModule`”, “widen scope to include `Content/UI`”, or “run `/ship` when ready to package”. |

### 5.3 Artifact storage

All `/play` traces live under:

```text
.cuebert/traces/play/<timestamp>/
```

`<timestamp>` is UTC sortable (`YYYY-MM-DDTHHMMSSZ` or equivalent). Subdirectories (`preview/`, `logs/`, `screens/`) are **implementation details of M2-P3**. This layout follows the hub-local trace philosophy described in `docs/_ai_system/standards/control-plane-paths.md` (hub-resident control plane; zero-footprint in app repos). Do **not** require game repositories to host cuebert-only trees for tracing.

### 5.4 Trace directory layout (recommended)

| Path under `.cuebert/traces/play/<timestamp>/` | Contents |
|-------------------------------------------------|----------|
| `plan.md` | Intent, change list, scope declaration. |
| `author/` | Diff stat summary, optional `FILES.txt` manifest. |
| `preview/` | Screenshots, session metadata, engine build id if known. |
| `logs/` | Raw excerpts; redact secrets per vault standards when tool-assisted. |
| `guards.json` or `guards.md` | Machine- or human-readable guard matrix. |
| `qa.md` | Lightweight QA outcome; link to M6 baselines when present. |

Exact filenames are **non-normative** until M2-P3 chooses a schema; the **directory root** is normative.

### 5.5 `workspace-manifest.json` fields used by `/play`

From `.cuebert/workspace-manifest.json` (`projects` entries, see `docs/_ai_system/agents/agent-ops-onboard.md` §3–4):

| Field | Use in `/play` |
|-------|----------------|
| `path` | Resolve `APP_REPO` for Author/Preview shells. |
| `engine` | Select Preview defaults and guard sets (§8). |
| `engine_version` | Display + compatibility notes; automation uses it **M5+**. |
| `language` | Route author slim (`cpp` vs `blueprint_only` vs others). |
| `description` | Echo in reports; no behavioral effect. |

Hub-level `memory.mode` does **not** change Preview Guards; it only affects optional `troubleshoot_*` calls (§10).

---

## 6. Subagent roster (placeholders — not implemented in M2-P1)

The `/play` harness will dispatch **generalPurpose** Tasks (per Cuebert supervisor global rule: only `generalPurpose`, `explore`, `shell`, `browser-use`, `best-of-n-runner`) whose **first action** is to read a canonical doc or slim prompt — mirroring `docs/_ai_system/agents/agent-orchestrator.md` §3.

| Placeholder name | Milestone | Responsibility |
|------------------|-----------|------------------|
| **`agent-play-author`** | **M2-P2** | Author phase: apply scoped gameplay/content edits; report file list and build notes. |
| **`agent-play-preview`** | **M2-P3** | Preview phase: drive editor/runtime, capture screenshots and logs; emit preview bundle paths. |
| **`agent-play-qa`** | **M2-P4** stub; **M6-P2/P3** full | QA phase: lightweight log scan + visual diff; full Gauntlet/vision QA replaces stub per plan. |

**Explicit statement:** **`agent-play-author`**, **`agent-play-preview`**, and **`agent-play-qa`** do **not** exist as implemented agents or slims in **M2-P1**. No Task spawn should claim these names as `subagent_type` (forbidden anyway); they are **logical roles** for future prompts.

**Relationship to legacy naming:** Engineering plans may refer to `code-ue-cpp` / `code-gaming` as the **author skill**; treat those as **implementation aliases** for the **`agent-play-author`** role until consolidated.

### 6.1 Dispatch rules (M2-P2+)

| Rule | Detail |
|------|--------|
| **Task type** | Always `subagent_type: "generalPurpose"` unless a future milestone explicitly documents `shell`/`browser-use` for isolated capture — never `orchestrate` or gaming-named Cursor auto-types. |
| **Harness location** | `/play` coordinator logic runs in **main chat** per `.cursor/rules/cuebert-supervisor.mdc` (same family as `/o` / `/d` prohibition text). |
| **Chaining** | Default **auto-chain** Plan→Author→Preview→QA→Merge unless a future `--pause` modifier is added — **modifier parity deferred to M2-P3**. |
| **Parallelism** | No parallel author Tasks for the same session unless explicitly spec’d later; Preview and QA may run sequentially to simplify log attribution. |

### 6.2 Negative harness tests (plan cross-reference)

`docs/projects/cue/plans/active/cuebert-gaming-system.md` defines **N-2**: `/play --preview` must print the phase chain **without** spawning subagents. `/play` preview semantics intentionally mirror `agent-orchestrator.md` §8 **walk-only** behavior; MCP probes list for `/play` preview — **M2-P3**.

---

## 7. Non-goals for `/play`

| Non-goal | Redirect |
|----------|----------|
| **Cooking / packaging** | `/ship` (M3/M8) |
| **Certification / first-party compliance submission** | `/ship` + `cert-game` milestones |
| **Cloud deploy / Steam upload / console packaging** | `/ship` and later ship harness docs |
| **Gameplay balance analytics** (economy tuning, meta design) | Campaign-specific agents / human design — not the harness |
| **Full research swarm** | Optional for complex tasks; baseline `/play` stays lean — large swarms **deferred to M4+** per plan |
| **Replacing `/o` on the Cue hub** | Use **`/o`** for Cue meta-engineering |
| **Authoring net-new GDD / narrative bible** | `/spec` or human docs workflows — `/play` consumes a **short** intent, not franchise-scale design |
| **Licensing / legal clearance for third-party assets** | Legal review outside harness |

---

## 8. Engine support matrix

| Engine | Tier | M2–M4 expectation | First-class automation |
|--------|------|-------------------|------------------------|
| **Unreal Engine 5** | **1** | Fully supported path in documentation; stubs land M2; editor/PIE automation **M5–M6** | **M2–M6** per `cuebert-gaming-system` |
| **Unity** | **2** | **Stubs only** in M2–M4 (docs, placeholders, no mandatory tooling) | **M5+** first-class |
| **Godot** | **3** | **Stubs only** (detection exists in onboard doc; harness treats as optional) | **Post-M5** unless plan revises |

**Neutrality rule:** Author and Preview sections MUST remain **engine-abstract** where possible; examples may cite Unreal paths (`Content/`, `Source/`) as the **default** because Tier 1 is UE5.

### 8.1 Editor vs headless note

`/play` is **editor-preview-first**. Headless UAT / nullrhi runs belong to **M6** build and Gauntlet tooling, not the baseline `/play` loop. When M6 features are available, the harness MAY offer an optional branch — **deferred**.

---

## 9. Rollback and bailout

| Condition | Harness behavior |
|-----------|------------------|
| **Engine not found / automation unavailable** | Return a structured **`not_applicable`** result; include **manual instructions** (open editor, PIE, watch Output Log). No destructive git operations. |
| **Preview Guard failure** | Mark session **`BLOCKED`**, write **guard report** under `.cuebert/traces/play/<timestamp>/`, **stop before Merge**. |
| **Author or Preview crash** | Same as guard failure where safety is uncertain; preserve partial logs. |
| **User abort (Ctrl-C / cancel Task)** | Best-effort: **no Merge** if not reached; intermediate files may exist locally — operator cleans up like any aborted edit session. |
| **Git errors during Merge** | Do not force-merge; surface stderr; leave working tree for human inspection. |

**No silent fallbacks:** Missing engine or failed guard MUST NOT pretend success.

### 9.1 Partial author success

If Author completes **part** of the change list but reports a blocking compile error:

1. Do **not** run Preview on a broken tree unless the operator explicitly requests a **diagnostic preview** — default is **stop** at G-2.  
2. Write `blocked` state with author logs to trace.  
3. Suggested next step: fix compile, re-run `/play` with same scope.

### 9.2 Workspace manifest empty

If `.cuebert/workspace-manifest.json` has `"projects": {}`:

- Treat **`active-project`** as unknown.  
- Harness returns `not_applicable` with instructions to run `/onboard` per `docs/_ai_system/agents/agent-ops-onboard.md`.  
- Do not guess application roots from unrelated repos in the workspace.

---

## 10. Memory hooks

`/play` is optimized as a **tight loop**; it **does not** write to Cuebert memory by default.

| Tool | When MAY be called |
|------|--------------------|
| **`troubleshoot_commit`** | When Preview Guards or QA discover a **novel failure mode** worth persisting and the operator or harness policy enables it (similar spirit to Cue Orchestrator remediation memory in `agent-orchestrator.md` §4A, §5A). |
| **`milestone_lookup` / `milestone_commit`** | When `/play` is invoked **inside** a broader **M#-P#** orchestrated context (e.g. user explicitly bridges `/o` milestone tracking into a play session) — optional envelope fields to be defined in **M2-P4**. |

Default: **no memory writes** for routine successful previews.

### 10.1 Alignment with Cue orchestrator memory gates

Cue’s Orchestrator (`docs/_ai_system/agents/agent-orchestrator.md` §5A) mandates `milestone_commit` between phases for milestone-tracked work. `/play` **relaxes** that default: a standalone `/play` session is allowed to omit `milestone_commit` entirely. When `/play` is nested under `/o` with explicit bridge flags (future), treat Orchestrator rules as **superseding** this section for those fields only — **M2-P4** will document the bridge.

### 10.2 `troubleshoot_search` (optional)

The harness **MAY** call `troubleshoot_search` before re-attempting Author after a **repeatable** guard failure (second attempt policy — **M2-P2**). Nothing in M2-P1 requires MCP memory to be configured for `/play` docs to remain valid.

---

## 11. Cross-references, preview flag, and ownership boundaries

### 11.1 Related documentation

| Doc | Relationship |
|-----|----------------|
| `docs/_ai_system/standards/control-plane-paths.md` | Plan locations (`⟨CuebertActivePlans⟩`), `{active-project}` resolution, hub vs app paths. |
| `.cursor/rules/cuebert-supervisor.mdc` | Shortcut registration; `/play` stub response until M2-P2 wires harness; `subagent_type` prohibitions. |
| `docs/_ai_system/agents/agent-orchestrator.md` | Pattern reference for main-chat harness + phased Tasks (`/o`); remediation and `--preview` §8. |
| `docs/_ai_system/agents/agent-ops-onboard.md` | Gaming registration + `.cuebert/workspace-manifest.json` fields used as inputs. |
| `docs/_ai_system/standards/agent-shared-lifecycle.md` | Subagent structured results §12 — **M2-P2** aligns `/play` spawn outputs. |

### 11.2 `/play --preview` (future)

`/play --preview` walks **Plan → Author → Preview → QA → Merge** with **no Task spawns** and **no repo writes**, analogous to `agent-orchestrator.md` §8. Output schema, MCP health inclusion, and registry checks — **M2-P3** (plan **N-2**).

### 11.3 What `/play` does NOT own

- **Supervisor intent detection** — `.cursor/rules/cuebert-supervisor.mdc`.  
- **Vault credential materialization** — `docs/_ai_system/standards/vault-standard.md` (when present in cuebert).  
- **Production readiness REJECT scans** — `/ship` and M7 gaming readiness agents.  
- **MCP server implementation** — `.cursor/mcp-server` milestones.  
- **Jira / ticketing** — unless explicitly bridged in a later harness revision.

### 11.4 Footer

Status: M2-P1 (documentation only). Implementation phases: M2-P2 (agent stubs), M2-P3 (preview guards), M2-P4 (sample plan).
