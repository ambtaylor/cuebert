# `/ship` Ship Guards — Contract & Configuration

> **SYSTEM ROLE:** Authoritative specification for **Ship Guards** that gate the `/ship` harness from **Pre-cook** through **Post-package** (and optional **Upload** preconditions), and for the **evidence contract** consumed by **Attest** and memory hooks.  
> **Scope:** Contract, taxonomy, severity semantics, configuration schema, evidence and envelope shape, artifact paths, evaluation ordering, and **workspace-manifest `ship` metadata** required by `guard.project.ship_metadata`. **No executable evaluator** is defined here — cook evaluators land in **M8-P1**, cert in **M8-P2**, package in **M8**, upload post-**M8**.

---

## 0. Purpose & scope

**Ship Guards** are **deterministic gates** that answer: “Is it safe and coherent to spend **cook time** and produce **distribution artifacts** from this tree right now?” They **gate the `/ship` pipeline**. Guards prevent **wasted cook time** and **block unsafe distributions** by halting before irreversible-from-harness steps when policy says **fail**.

Guards are **not** full **platform certification** (vendor checklists live outside cuebert docs). They are **not** **gameplay QA**, **not** `/play` preview probes, and **not** a substitute for **human release sign-off**. This document owns the **guard ids**, **classes**, **severity ladder**, **YAML configuration**, and **envelope contract** so later milestones plug **evaluators** into stable APIs without renaming concepts.

---

## 1. Guard taxonomy

Guards fall into **four classes** by **when** they run relative to **Cook**, **Cert**, **Package**, and **Upload**. The harness runs them in a **fixed order** within each class (see §7).

### 1.1 Pre-cook guards

Run **before any cook subprocess** is dispatched. Typical checks:

- **Git state:** clean working tree in declared ship scope; no disallowed **untracked** files under cookable directory roots.
- **Engine alignment:** declared **engine version** matches **workspace manifest** and project association where applicable.
- **Ship metadata:** `projects.<key>.ship` block in **`.cuebert/workspace-manifest.json`** satisfies §8 schema (`guard.project.ship_metadata`).
- **Asset reference hygiene:** deterministic heuristics for **unreferenced** or orphaned assets that commonly break cook (`warn` class).

**Intent:** Fail fast on **misconfiguration**, **dirty trees**, or **manifest drift** before expensive cook.

### 1.2 Post-cook guards

Run **after** the cook subagent completes and **before** cert (when cert is in scope). Typical checks:

- **Process outcome:** cook **exit code** is success-shaped.
- **Size budgets:** cooked output **byte totals** per platform stay within configured thresholds (`warn→fail` guard).
- **Inventory:** required cooked assets / manifest entries are **present**.

**Intent:** Avoid cert and packaging work when cook output is **structurally unusable**.

### 1.3 Post-cert guards

Run **after** the cert subagent when `cert_profile != none`. When `cert_profile: none`, the harness **skips** cert dispatch; post-cert severity floor checks are **N/A** and SHOULD emit **`info`** findings only (see `docs/_ai_system/agents/agent-ship.md` §7). Typical checks:

- **Severity floor:** no cert finding above configured tolerance (`guard.cert.severity_floor`).
- **Required checklists:** profile-required checklist ids executed with **PASS** or policy-allowed **waived** (`guard.cert.required_checklists`).
- **Report emission:** `cert/report.md` exists and contains a non-empty summary when profile requires work (`guard.cert.report_emitted`).

**Intent:** Block packaging when **cert policy** is breached.

### 1.4 Post-package guards

Run **after** the package subagent completes and **before** optional upload. Typical checks:

- **Artifact existence:** primary package paths exist on disk.
- **Checksum integrity:** recorded digest matches recomputed bytes.
- **Manifest:** aggregate **manifest of contents** exists per format rules.

**Intent:** Guarantee **auditable artifacts** before any upload phase.

### 1.5 Disambiguation vs `/play` Preview Guards

| Concern | Ship Guards (this doc) | `/play` Preview Guards (`play-preview-guards.md`) |
|--------|-------------------------|---------------------------------------------------|
| **Role** | Gate **cook → cert → package → upload** for **distribution builds**. | Gate **author → preview** for **editor iteration**. |
| **Primary risk** | Irreversible **binary distribution** mistakes, oversized trees, failed cert floors. | Wasted **editor startup** on broken compile / scope bleed. |
| **Timing** | Pre-cook; post-cook; post-cert; post-package. | Pre-author; post-author; post-preview. |
| **Overlap** | None normative — both use the **same finding JSON shape** (§5.1) for tooling reuse. | Same evidence contract pattern. |

---

## 2. Guard catalog

Each guard has a **stable `id`** (lowercase, dot-separated). **`class`** is one of: `pre-cook`, `post-cook`, `post-cert`, `post-package`. **`severity`** is the **default** effective severity when the guard is **fully implemented**; **`warn→fail`** means the guard **starts as warn** and **escalates to fail** when a **threshold** is crossed (see §4). **`evidence type`** names the **primary** attachment kind for findings. **`implementation status`** names the milestone that owns the **evaluator**.

Harness callers **MUST** treat guards whose status is **spec only (M3-P3)** as **non-blocking `info`** until the cited milestone ships, **unless** a project manifest explicitly promotes severity (discouraged before evaluators exist). The global flag **`spec_only_as_info`** (see `.cuebert/config/ship-guards.yaml` → `global`) defaults to **`true`** so unfinished evaluators never accidentally **block** `/ship`.

| `id` | `class` | `severity` | Description | Evidence type | Implementation status |
|------|---------|------------|-------------|----------------|-------------------------|
| `guard.git.clean` | pre-cook | fail | Working tree has **no uncommitted changes** within declared ship scope (branch + path roots from plan). | file | **spec only (M3-P3)**; impl **M8-P1** |
| `guard.git.untracked_cook_paths` | pre-cook | fail | **No untracked files** under cookable directory roots (engine-specific roots such as `Content/` for UE — exact roots **M3-P3** prose + M8 mapping). | file | **spec only (M3-P3)**; impl **M8-P1** |
| `guard.engine.version_match` | pre-cook | fail | Declared engine kind + version match **workspace manifest** and project engine association where applicable. | manifest | **spec only (M3-P3)**; impl **M8-P1** (UE) |
| `guard.project.ship_metadata` | pre-cook | fail | `projects.<key>.ship` in **`.cuebert/workspace-manifest.json`** satisfies §8 schema (engine path/version, platforms, flavors, formats, cert profile, budgets, optional overrides). | manifest | **spec only (M3-P3)**; schema **lands M3-P3**; evaluator **M3-P3** harness |
| `guard.assets.referenced_in_cook` | pre-cook | warn | Heuristic scan for **unreferenced** or suspiciously orphaned assets that commonly break cook (deterministic rules only). | file | **spec only (M3-P3)**; impl **M8-P1** asset graph milestones |
| `guard.cook.exit_code` | post-cook | fail | Cook subprocess **exit code 0**; structured “skip” only when harness explicitly runs dry-run preview (`--preview` semantics **M3-P3+**). | log | **spec only (M3-P3)**; impl **M8-P1** |
| `guard.cook.size_budget` | post-cook | warn→fail | Cooked output size within configured **byte budget**; crosses **fail** when `actual > warn_bytes * fail_multiplier` (YAML thresholds). | file | **spec only (M3-P3)**; impl **M8-P1** |
| `guard.cook.missing_assets` | post-cook | fail | Required cooked assets / manifest entries absent after cook. | manifest | **spec only (M3-P3)**; impl **M8-P1** |
| `guard.cert.severity_floor` | post-cert | fail (configurable) | Cert findings respect configured **max_fail_findings** and **max_warn_findings** thresholds (see YAML). | text | **spec only (M3-P3)**; impl **M8-P2** |
| `guard.cert.required_checklists` | post-cert | fail | All checklist ids required by **`cert_profile`** executed and produced **PASS** or allowed **waived** entries per policy. | manifest | **spec only (M3-P3)**; impl **M8-P2** |
| `guard.cert.report_emitted` | post-cert | fail | When `cert_profile != none`, **`cert/report.md`** exists and is non-empty summary. | file | **spec only (M3-P3)**; impl **M8-P2** |
| `guard.package.exists` | post-package | fail | Primary package artifact path exists on disk. | file | **spec only (M3-P3)**; impl **M8** |
| `guard.package.checksum` | post-package | fail | Recorded checksum matches recomputed hash for the artifact bytes. | file | **spec only (M3-P3)**; impl **M8** |
| `guard.package.manifest` | post-package | fail | **Manifest of contents** generated beside or inside package per format rules. | manifest | **spec only (M3-P3)**; impl **M8** |

**Count:** **14** stable `guard.*` ids — **API surface** frozen for **M3-P3** config and **M8** engines.

### 2.1 Legacy mapping (informational)

`agent-ship.md` §4.1 lists **four classes**. This catalog is the **stable id** expansion of that section; **do not rename** ids after **M3-P3**.

### 2.2 M7-P3 strict gates (`ship.*`)

These gates extend the `/ship` harness with **agent-dispatched** checks keyed under **`ship.*`** in `.cuebert/config/ship-guards.yaml`. **Evaluators** (log parsers, INI scanners) remain **future work**; this milestone defines **contract, ordering, severities, override policy, and advisory demotion** only.

#### Guard: `ship.prod_readiness`

- **Phase boundary:** pre-cook (before `agent-ship-cook` is dispatched).
- **Severity:** reject-eligible.
- **Trigger:** `agent-prod-readiness-game` returns any **REJECT** finding.
- **Envelope field consulted:** `findings[*].severity == "reject"`.
- **Default action on trigger:** halt `/ship` with a structured error envelope; surface `findings[]`.
- **Override:** only `caller == "user-direct-debug"` with `--override=accept-risk` (equivalent intent: `override_reject: true` per `agent-prod-readiness-game.md` §2) bypasses the block. **Override audit:** `troubleshoot_commit` with severity **`warn`**, body containing the **full** finding set that would have blocked.
- **Advisory mode (transitional):** when `.cuebert/config/prod-readiness-game.yaml` has **`spec_only_as_info: true`**, all **REJECT** findings **demote to warning** and **do not** block `/ship`. This mode is **for migration only**; the harness SHOULD emit a run-level warning (see **M7-P3 enforcement status** below).
- **Cross-refs:** `docs/_ai_system/agents/agent-prod-readiness-game.md`, `docs/_ai_system/standards/prod-readiness-game-rules.md`.

#### Guard: `ship.qa_resilience`

- **Phase boundary:** post-cook, pre-package (after cook completes and before cert/package when the harness runs post-cook gates; **normative ordering** matches `agent-ship.md` §7 with this gate evaluated in the **post_cook** bucket alongside existing post-cook guards).
- **Severity:** reject-eligible for **`critical`** or **`error`** findings; advisory for **`warn`** and **`info`**.
- **Trigger:** `agent-qa-resilience-game` returns any finding with `severity` **`critical`** or **`error`** when invoked with **`session_kind: build`** (analyzing the cook log and related build artifacts).
- **Envelope field consulted:** `findings[*].severity in {"critical", "error"}`.
- **Default action on trigger:** halt `/ship` with a structured error envelope; include the **metrics** snapshot from the agent envelope.
- **Override:** same **`--override=accept-risk`** mechanism as `ship.prod_readiness` (**`user-direct-debug`** only; symmetric audit trail).
- **Advisory mode (transitional):** when `.cuebert/config/qa-resilience-game.yaml` has **`spec_only_as_info: true`**, all findings **demote to `info`** and **do not** block `/ship`. **Transitional only**; run-level warning as below.
- **Cross-refs:** `docs/_ai_system/agents/agent-qa-resilience-game.md`, `docs/_ai_system/standards/qa-resilience-game-rules.md`.

---

## 3. Severity semantics

### 3.1 `fail`

- **Effect:** **Hard stop** for the current gate point.  
- **Pre-cook:** Harness **does not dispatch** cook. Writes **guard phase JSON** + rolls up to session **blocked** / **failure** per parent §3.7.  
- **Post-cook / post-cert / post-package:** Harness **does not dispatch** the next downstream phase (cert, package, or upload respectively). **Attest** still runs (`agent-ship.md` §3.6).  
- **Safety:** Guards perform **no destructive rollback** of source trees; they only **decide** and **record**.

### 3.2 `warn`

- **Effect:** **Continue** the chain **unless** harness policy elevates warnings at thresholds (`guard.cook.size_budget`, `guard.cert.severity_floor`).  
- **Recording:** Every warn **MUST** appear as a **finding** in the phase envelope.

### 3.3 `info`

- **Effect:** **Record only** — does not halt when `spec_only_as_info` maps spec-only evaluators to informational outcomes. Used for **diagnostics**, **skipped** evaluators, and **`cert_profile: none`** N/A rows.

### 3.4 `spec_only_as_info` default

Until an evaluator ships, the guard’s **contract** (id, class, evidence shape) is **stable**, but the harness **MUST NOT** treat unimplemented checks as failing **`fail`** accidentally. **Default:** when `global.spec_only_as_info` is **`true`**, unimplemented guards contribute **`severity: info`** findings (or explicit **skip/info** messages) per harness policy — **never** a silent **`pass`** with missing evidence for policy-critical claims.

Operators may set the flag to **`false`** only when **all** enabled guards in the session have **real evaluators** (typical **post-M8** hub).

### 3.5 `warn→fail` escalation

Guards marked **`warn→fail`** begin contributing **`warn`** until numeric thresholds are exceeded, then resolve **`fail`**. **`guard.cook.size_budget`** uses **`warn_bytes`** and **`fail_multiplier`** from YAML (per-guard or global defaults). **`guard.cert.severity_floor`** uses **`max_fail_findings`** and **`max_warn_findings`** counts.

---

## 4. Config file

### 4.1 Location & version

- **Path (hub):** `.cuebert/config/ship-guards.yaml`  
- **Version:** Top-level `version: 1` (**integer**). Tooling **MUST** reject unknown versions with a **loud, actionable error**. Additive keys within a version are allowed; **breaking** layout changes bump the integer.

### 4.2 Top-level shape (normative fields)

```yaml
version: 1
guards:
  <guard_id>:
    enabled: <bool>
    default_severity: fail | warn | info
    threshold: <object | null>   # optional; guard-specific
global:
  cook_max_duration_s: <int>
  cook_default_budget_bytes: <int>
  cert_max_duration_s: <int>
  package_max_duration_s: <int>
  upload_default_dry_run: <bool>
  spec_only_as_info: <bool>
```

- **`guards`:** Map keyed by **exact** guard `id`.  
- **`enabled`:** When `false`, the harness **skips** the guard (emits **`info`** “skipped” finding at harness discretion).  
- **`default_severity`:** Hub default **before** project overrides.  
- **`threshold`:** Optional per-guard parameters; **must** be documented per guard in the YAML comments and in §2.

### 4.3 Project overrides (manifest + ship plan)

Projects **MAY** override per-guard effective severity (and selected thresholds where supported) in:

1. **Ship plan** — `ship_guards_overrides` map (`agent-ship.md` §4.4).  
2. **`.cuebert/workspace-manifest.json`** — optional `projects.<key>.ship.guardOverrides` keyed by guard id (§8).

**Resolution order (highest wins):**

1. **Ship plan** `ship_guards_overrides.<guard_id>`  
2. **`projects.<key>.ship.guardOverrides.<guard_id>`** (manifest)  
3. **Hub file** `.cuebert/config/ship-guards.yaml` entry (`default_severity`, `threshold`, `enabled`)  
4. **Catalog default** in §2 (YAML should be complete for shipped hubs)

### 4.4 Engine-specific cook roots and checklist packs

**Per-engine cook root lists**, **asset graph rules**, and **cert checklist catalogs** do not live in this milestone. They ship as **adapter packs** (**M8**) referenced by evaluator implementations. This document **only** reserves **guard ids** and **evidence types**.

### 4.5 M7-P3 `ship.*` guard configuration (hub YAML)

The hub file **`.cuebert/config/ship-guards.yaml`** MAY list **`ship.prod_readiness`** and **`ship.qa_resilience`** alongside legacy **`guard.*`** keys (see committed example). **Severity mapping** for harness merge:

| Guard id | `phase_boundary` | Default blocking severities | Advisory when |
|----------|------------------|----------------------------|---------------|
| `ship.prod_readiness` | `pre_cook` | any `findings[].severity == reject` | `prod-readiness-game.yaml` → `spec_only_as_info: true` (REJECT → warn, non-blocking) |
| `ship.qa_resilience` | `post_cook` | any `findings[].severity in {critical, error}` | `qa-resilience-game.yaml` → `spec_only_as_info: true` (all findings → info, non-blocking) |

**Override:** documented in `docs/_ai_system/agents/agent-ship.md` (M7-P3). **`caller != user-direct-debug`** MUST NOT honor `--override=accept-risk`; attempted misuse is a **scope violation** logged to `troubleshoot_commit` (**`ship.override_unauthorized`**).

---

## 5. Evidence & envelope contract

### 5.1 Finding entry (single guard result)

When a guard produces **`warn`** or **`fail`**, or an **`info`** diagnostic is recorded, the harness emits a **finding** object:

```json
{
  "guard_id": "guard.git.clean",
  "class": "pre-cook",
  "severity": "fail",
  "evidence": {
    "type": "file",
    "path": "Content/Maps/TestMap.umap",
    "detail": "modified in working tree"
  },
  "message": "Short human-readable reason."
}
```

**`evidence.type`** is one of: `text`, `log`, `file`, `manifest` (extensible in future versions with version bump). **`path`** is repo- or hub-relative as appropriate; **`detail`** is optional structured context.

**Empty evidence policy:** For **`fail`** / **`warn`**, **`evidence`** **MUST** be non-vacuous — mirror `agent-ship.md` §4.3: content-free failures invalidate the guard report and the harness MUST treat that as a **blocked** ship session.

### 5.2 Harness envelope (aggregated)

All findings roll up into guard phase objects. Per-phase files (for example `guards/pre_cook.json`) use:

```json
{
  "guards": {
    "pre_cook": [],
    "post_cook": [],
    "post_cert": [],
    "post_package": []
  },
  "verdict": "pass|warn|fail",
  "phase": "pre_cook|post_cook|post_cert|post_package|complete"
}
```

**Phase files** typically populate **only** the bucket matching their filename (for example `pre_cook.json` contains the `pre_cook` array). The **aggregate** ship `envelope.json` at the trace root **MAY** embed the same `guards` object with all buckets filled for Attest.

**`verdict` composition (normative intent):**

- **`fail`** if any collected finding has **`severity: fail`** after resolution.  
- Else **`warn`** if any finding is **`warn`**.  
- Else **`pass`**.

The harness **MAY** include auxiliary keys (`timestamp`, `project_key`, `engine`, `guard_config_version`) — **additive** only.

---

## 6. Artifacts

Guard envelopes and machine-readable findings **MUST** be written under the session trace root:

```text
.cuebert/traces/ship/<timestamp>/guards/pre_cook.json
.cuebert/traces/ship/<timestamp>/guards/post_cook.json
.cuebert/traces/ship/<timestamp>/guards/post_cert.json
.cuebert/traces/ship/<timestamp>/guards/post_package.json
.cuebert/traces/ship/<timestamp>/envelope.json
```

Where `<timestamp>` is UTC-sortable (see `docs/_ai_system/standards/control-plane-paths.md` and `agent-ship.md` §6).

**Dispatch rules:**

- **Pre-cook fail:** **Cook never runs**; session moves to **Attest** (failure).  
- **Post-cook fail:** **Cert never runs** (and **Package** never runs).  
- **Post-cert fail:** **Package never runs**.  
- **Post-package fail:** **Upload never runs**; session **BLOCKED** for upload per parent §3.7.

**Hub-only traces:** Application repositories remain **zero-footprint** for cuebert control-plane trees per `control-plane-paths.md` — ship traces live in the **hub** checkout.

---

## 7. Decision tree (evaluation order)

Pseudo-flow for harness ordering (compare `agent-ship.md` §7 — this section aligns numbering for guard-centric readers):

```text
1. PRE-COOK GUARDS
   a. Load .cuebert/config/ship-guards.yaml + merge ship_guards_overrides + manifest overrides (M3-P3).
   b. Run enabled pre-cook guards in stable sorted order by guard_id.
   c. If any resolved severity == fail -> HALT; no cook dispatch; go to ATTEST (failure).
   d. Else continue.

2. DISPATCH agent-ship-cook
   a. Cook subagent writes cook/envelope.json + cook logs under the trace tree.

3. POST-COOK GUARDS
   a. If any fail -> HALT; no cert dispatch; ATTEST (failure).
   b. Else continue.

4. DISPATCH agent-ship-cert (skip when cert_profile:none; still emit post-cert info policy per parent §7)
   a. When skipped, severity_floor checks are N/A (info findings only).

5. POST-CERT GUARDS
   a. If any fail -> HALT; no package dispatch; ATTEST (failure).

6. DISPATCH agent-ship-package

7. POST-PACKAGE GUARDS
   a. If any fail -> HALT; no upload; envelope marks upload as BLOCKED; ATTEST (failure).

8. OPTIONAL agent-ship-upload
   a. Only if all guards pass AND upload_channel != none AND dry_run explicitly false (or harness-equivalent explicit opt-in per agent-ship-upload.md §6 defaults).
   b. Otherwise skip upload; upload/envelope.json SHOULD record skip/dry_run.

9. ATTEST (always)
   a. Write envelope.json with full phase story + checksums + version metadata.
   b. Memory: milestone_commit on pass; troubleshoot_commit on fail (CUEBERT_MEMORY_MODE=text compatible per memory-toolkit).
```

**Parallelism:** **No** parallel cook or upload for the same session unless a future version documents safe parallelism.

---

## 8. Project manifest schema (ship-specific)

The guard **`guard.project.ship_metadata`** validates a **`ship`** object under each onboarded project entry in **`.cuebert/workspace-manifest.json`**:

```yaml
ship:
  enginePath: <path or vault ref>       # required
  engineVersion: <semver>                 # e.g., 5.3.2
  targetPlatforms: [Win64, Mac]           # required
  defaultCookFlavor: shipping             # required
  defaultPackageFormat: zip               # required
  certProfile: none | indie-light | platform-strict
  contentBudgetBytes:                    # per platform
    Win64: 5368709120                    # 5GB example
  guardOverrides: {}                     # optional, keyed by guard id
```

**Field notes (normative intent):**

- **`enginePath`:** Absolute or workspace-relative engine root **or** a **vault reference token** resolvable per `vault-standard.md` — **never** raw secrets.  
- **`targetPlatforms`:** Engine-native tokens (for example UE `Win64`, `Mac`) — the harness maps ship plan `target_platforms` to these names (**M8**).  
- **`defaultCookFlavor` / `defaultPackageFormat`:** Defaults when the ship plan omits explicit fields; ship plan still wins when present (see `agent-ship.md` §5.3).  
- **`certProfile`:** Mirrors ship plan `cert_profile` vocabulary.  
- **`contentBudgetBytes`:** Per-platform byte ceilings feeding **`guard.cook.size_budget`** when thresholds are not overridden in YAML.  
- **`guardOverrides`:** Structural subset of per-guard keys (`enabled`, `default_severity`, optional `threshold`) — exact merge with `ship_guards_overrides` follows **M8** harness merge rules; **M3-P3** defines presence and shape only.

**JSON equivalent** uses camelCase keys as shown; YAML fragments in docs are illustrative.

---

## 9. Non-goals

- **Not full first-party console certification:** No vendor checklist reproduction — see **`agent-ship-cert.md`** §4.3.  
- **Not `/play`:** No PIE / preview guards — see **`play-preview-guards.md`**.  
- **Not signing / notarization automation:** Operator or CI per **`agent-ship.md` §14**.  
- **Not secrets in plans:** Upload credentials **vault-only** (`vault-standard.md`).  
- **Not git rollback:** Guards never revert working trees.  
- **Not live-ops deploy:** `/ship` produces **standalone builds**, not fleet rollouts (`agent-ship.md` §9).

---

## 10. Cross-references

| Document | Relevance |
|----------|-----------|
| `.cuebert/config/ship-guards.yaml` | Default thresholds, per-guard enables, **`global`** timers and **`spec_only_as_info`**. |
| `docs/_ai_system/agents/agent-ship.md` | Parent protocol — phase chain, severity table, memory hooks. |
| `docs/_ai_system/agents/agent-ship-cook.md` §8 | Cook envelope shape consumed by post-cook guards. |
| `docs/_ai_system/agents/agent-ship-cert.md` §6–§7 | Cert finding + envelope shapes consumed by post-cert guards. |
| `docs/_ai_system/agents/agent-ship-package.md` §8 | Package envelope consumed by post-package guards + upload. |
| `docs/_ai_system/agents/agent-ship-upload.md` §6–§8 | **Dry-run default true**; upload verdict mapping. |
| `docs/_ai_system/standards/control-plane-paths.md` | Hub trace roots, `{active-project}` resolution. |
| `docs/_ai_system/standards/vault-standard.md` | Engine path + upload credential resolution. |
| `.cuebert/workspace-manifest.json` | Project registration + **`ship`** metadata block (§8). |
| `docs/_ai_system/agents/agent-prod-readiness-game.md` | **`ship.prod_readiness`** dispatch contract. |
| `docs/_ai_system/agents/agent-qa-resilience-game.md` | **`ship.qa_resilience`** dispatch contract (`session_kind: build`). |
| `docs/_ai_system/standards/prod-readiness-game-rules.md` | Production readiness **rule_id** catalog. |
| `docs/_ai_system/standards/qa-resilience-game-rules.md` | QA resilience **rule_id** catalog. |

---

## 11. Footer

**Status:** **M3-P3** — **contract + default config**. **Evaluators:** **M8-P1** (cook), **M8-P2** (cert), **M8** (package). **Schema** for **`ship`** metadata in **`workspace-manifest.json`** lands in **M3-P3** (this document, §8). **`ship.*` gates:** **M7-P3** contract; **rule engines** TBD post-M7.

### M7-P3 enforcement status

Both gates default to **ENFORCED** as of M7-P3. Projects migrating from earlier milestones can opt into advisory mode by setting `spec_only_as_info: true` in the relevant config file. Advisory mode is intended for **transitional use only** and emits a warning at each `/ship` run:

```text
WARN: ship.<guard_name> is in advisory mode. Findings will not block cook.
Set spec_only_as_info: false in .cuebert/config/<config>.yaml to enforce.
```

Replace `<guard_name>` with `ship.prod_readiness` or `ship.qa_resilience`, and `<config>.yaml` with `prod-readiness-game.yaml` or `qa-resilience-game.yaml` respectively.

---

## Appendix A — Pre-cook failure (dirty tree)

**Situation:** Operator runs `/ship` with local modifications under declared ship scope.

**Expected:**

- `guard.git.clean` → **`fail`** with `evidence.type: file` listing an example path.  
- **Cook not dispatched.**  
- Attest records **`troubleshoot_commit`** per **`agent-ship.md` §13**.

---

## Appendix B — Post-cook failure (non-zero exit)

**Situation:** Cook subprocess returns exit code **1**; `guard.cook.exit_code` enforced.

**Expected:**

- Post-cook envelope **`verdict: fail`**.  
- **Cert not dispatched**; `cook/envelope.json` retains `exit_code` and log tail pointer.

---

## Appendix C — Cert floor breach

**Situation:** Cert emits a **`fail`** severity finding for profile `indie-light`.

**Expected:**

- `guard.cert.severity_floor` resolves **`fail`** (`max_fail_findings: 0`).  
- **Package not dispatched.**

---

## Appendix D — Package checksum mismatch

**Situation:** On-disk bytes differ from recorded SHA-256 (hypothetical corruption).

**Expected:**

- `guard.package.checksum` → **`fail`**.  
- **Upload never runs**; aggregate envelope marks **BLOCKED** for upload.

---

## Appendix E — Harness responsibilities (checklist)

The executable harness (future milestones) **SHOULD**:

1. **Materialize directories** under `.cuebert/traces/ship/<timestamp>/guards/` before writing JSON.  
2. **Atomically write** JSON where the platform permits (temp → rename).  
3. **Stamp** `project_key`, `engine`, `engine_version`, and `guard_config_version` (from YAML `version`) into envelopes.  
4. **Normalize paths** to forward slashes in findings.  
5. **Never embed** secrets from logs — redact per preview/QA guidance patterns.  
6. **Short-circuit** strictly per §7 — no post-cook guards if pre-cook failed unless entering an explicit **diagnostic** mode (future; document in `agent-ship.md` if added).  
7. **Surface** envelope paths in Supervisor-facing summaries.

---

## Appendix F — Operator diagnostics (dry-run / preview)

Future harness flags may allow **`--preview`** walks without cook dispatch (`agent-orchestrator.md` pattern). **Normative safety:** skipped guards **MUST** produce **`info`** findings with explicit operator attribution — never a silent **`pass`**.

---

## Appendix G — Id stability & API surface

Guard ids are **public contracts** for:

- MCP / CLI harness switches (`--guard-off guard.x` patterns — **future**).  
- Manifest overrides (`ship.guardOverrides` / plan `ship_guards_overrides`).  
- CI fixtures naming (`tests/fixtures/ship-guards/...` — **future**).

**Renaming policy:** Do **not** rename ids after **M3-P3**; add **new** ids for semantically distinct checks and **deprecate** across a **version bump**.

---

## Appendix H — Upload gating recap

Upload runs **only** when:

1. **All guards** passed at their gate points, **and**  
2. **`upload_channel != none`**, **and**  
3. **`dry_run: false`** explicitly set (harness-equivalent **M3-P3**), overriding **`global.upload_default_dry_run: true`** safety rail.

Otherwise **`upload/envelope.json`** records **`skip`** / **`dry_run`**.

---

## Appendix I — Relationship to `agent-ship.md` §7

This document’s §7 numbering aligns with parent pseudo-flow while naming **dispatch** steps explicitly. On conflict during early wiring, **`agent-ship.md` §7** remains the **parent** source; this file provides **guard-file** and **config** detail.

---

## Appendix J — Glossary

| Term | Meaning |
|------|---------|
| **Ship envelope** | Aggregate JSON at `.cuebert/traces/ship/<ts>/envelope.json`. |
| **Finding** | Single guard outcome row. |
| **Spec only** | Contract frozen in **M3-P3**; evaluator code ships in **M8** milestones. |
| **Cookable roots** | Engine-specific directories whose untracked files violate `guard.git.untracked_cook_paths`. |

---

## Appendix K — Revision history (documentation)

| Milestone | Change |
|-----------|--------|
| **M3-P3** | Initial ship taxonomy, catalog (**14 ids**), YAML schema v1, manifest **`ship`** block, artifact paths, decision tree. |
| **M8-P1** | Wire cook evaluators + size/missing asset probes. |
| **M8-P2** | Wire cert evaluators + checklist coverage. |
| **M8** | Wire package checksum/manifest validators. |
| **M7-P3** | Add **`ship.prod_readiness`** and **`ship.qa_resilience`** strict gate contracts, YAML entries, override and advisory semantics (`spec_only_as_info`); **evaluators** still pending. |

