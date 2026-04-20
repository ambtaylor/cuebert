# PRODUCTION READINESS — Gaming (`agent-prod-readiness-game`)

> **Name:** `agent-prod-readiness-game`  
> **Status:** Spec (**M7-P2**). No MCP tools in this phase; runs as a **prompt-driven** `generalPurpose` subagent when dispatched.  
> **Dispatchers:** `docs/_ai_system/agents/agent-ship.md` (via **M7-P3** strict gate), `user-direct-debug`, optionally `docs/_ai_system/agents/agent-play-qa.md` for opt-in pre-ship smoke.  
> **Audience:** Not user-facing. Always dispatched by another agent or harness.

---

## 0. Identity

| Field | Value |
|-------|--------|
| **Agent id** | `agent-prod-readiness-game` |
| **Kind** | Gaming-specific **pre-ship** production-readiness scan (static config, build tree, metadata) |
| **MCP tools** | None in **M7-P2**; contract + taxonomy + YAML config only |
| **Canonical rules** | `docs/_ai_system/standards/prod-readiness-game-rules.md` |
| **Default config** | `.cuebert/config/prod-readiness-game.yaml` |

This agent is the gaming counterpart to Cue hub production-readiness scanning (see `agent-production-readiness.md` on the Cue hub for the INFO/REJECT register model); it preserves the same **INFO vs REJECT** duality for ship gating.

---

## 1. Purpose

Scan a gaming project prior to ship for production-readiness defects — misconfiguration, banned patterns, missing artifacts, inadequate metadata, insecure settings — and return **INFO** or **REJECT** findings.

**Severity semantics (normative):**

- **INFO:** Advisory. Logged to the envelope; does **not** fail `/ship` when strict gates are active.
- **REJECT:** Blocking. Halts `/ship` when any REJECT finding is present **unless** the caller is `user-direct-debug` **and** `override_reject: true` is set in the input envelope (equivalent intent: `--override=accept-risk` on the debug harness).

**Explicit non-purpose in this milestone:** no subprocess orchestration, no network I/O, no MCP tool calls, and no writes to the game source tree (read-only inspection under `project_path` only).

---

## 2. Inputs

The caller supplies a **readiness manifest** (JSON object):

```json
{
  "project_path": "abs path to .uproject",
  "target_platform": "Win64" | "Mac" | "Linux" | "IOS" | "Android",
  "target_store": "steam" | "epic" | "gog" | "itchio" | "internal" | null,
  "build_config": "Shipping" | "Test" | "Development",
  "build_path": "str | null",
  "skip_rules": ["str"],
  "override_reject": false,
  "caller": "agent-ship" | "agent-ship-cook" | "agent-play-qa" | "user-direct-debug"
}
```

**Rules:**

- `project_path` MUST be an absolute path ending in `.uproject` when the scan is `live` (see §7 for `skip` / `dry_run`).
- `skip_rules` lists **rule_id** strings only (not categories). Unknown ids SHOULD be ignored with an INFO-level note in `detail` when the harness supports it (**M7-P3**).
- `override_reject` is honored **only** when `caller` is `user-direct-debug`; other callers MUST treat `override_reject: true` as **invalid** and downgrade to `error` or strip the flag per harness policy (**M7-P3**).
- `build_path`, when non-null, points at cooked/staged output roots for binary and layout checks (PDB exclusion, signing evidence, dev-tool DLL probes).

---

## 3. Output envelope

```json
{
  "status": "pass" | "fail" | "warn" | "skip" | "error",
  "mode": "live" | "dry_run",
  "project_path": "str",
  "target_platform": "str",
  "target_store": "str | null",
  "build_config": "str",
  "findings": [
    {
      "rule_id": "str",
      "category": "metadata" | "packaging" | "security" | "perf" | "content" | "legal" | "crash" | "signing",
      "severity": "info" | "reject",
      "detail": "str",
      "evidence": {
        "file_path": "str | null",
        "line_number": "int | null",
        "config_key": "str | null",
        "observed_value": "str | null",
        "expected": "str | null"
      },
      "remediation_hint": "str"
    }
  ],
  "summary": {
    "total_rules_evaluated": "int",
    "reject_count": "int",
    "info_count": "int",
    "skipped_count": "int"
  },
  "rule_version": "1.0.0",
  "memory_id": "str | null"
}
```

### 3.1 Status resolution

| Condition | Top-level `status` |
|-----------|---------------------|
| Any finding with `severity: reject` AND `override_reject` is not `true` (per caller rules in §2) | `fail` |
| No `reject` findings; one or more `info` findings | `warn` |
| No findings after evaluation | `pass` |
| No project accessible / harness chooses not to scan (see §7) | `skip` |
| Rule engine or manifest inconsistency | `error` |

`mode` is `dry_run` when §7 applies; otherwise `live`.

---

## 4. Rule catalogue (M7-P2 — 14 rules)

Normative regex text, INI section scoping, and remediation detail live in **`docs/_ai_system/standards/prod-readiness-game-rules.md`**. This section summarizes ids and default severities; each rule below is **15–25 lines** of contract-level elaboration.

### 4.1 Summary table

| rule_id | category | default severity | applies_to |
|---------|----------|------------------|------------|
| `metadata.game_name_set` | metadata | reject | all |
| `metadata.company_name_set` | metadata | reject | all |
| `metadata.copyright_notice` | metadata | info | all |
| `metadata.game_version_parseable` | metadata | reject | all |
| `packaging.shipping_config_required` | packaging | reject | `target_store` in {steam, epic, gog} |
| `packaging.crash_reporter_included` | packaging | reject | all |
| `packaging.pdb_excluded_in_shipping` | packaging | reject | `build_config=Shipping` |
| `security.verbose_logging_disabled` | security | reject | `build_config=Shipping` |
| `security.remote_control_disabled_shipping` | security | reject | `build_config=Shipping` |
| `content.no_unused_editor_maps` | content | info | all |
| `content.no_placeholder_assets` | content | reject | all |
| `signing.code_signed` | signing | reject | `target_platform` in {Win64, Mac, IOS} |
| `legal.licenses_included` | legal | reject | all |
| `perf.no_shippable_dev_tools` | perf | info | `build_config=Shipping` |

### 4.2 Rule: `metadata.game_name_set`

- **Category:** metadata  
- **Default severity:** reject  
- **Applies to:** all  
- **Files inspected:** `Config/DefaultGame.ini`, optionally `<Project>.uproject` for drift checks.  
- **Check:** Under `[/Script/EngineSettings.GeneralProjectSettings]`, `ProjectName=` MUST be present and non-empty after trim.  
- **Pattern (INI value line):** `^\s*ProjectName\s*=\s*(.+)\s*$` — implementations trim capture **1**; empty or whitespace-only after `=` is a **REJECT**.  
- **Why REJECT:** Store submission and crash analytics require a stable human-readable product name; empty names break packaging metadata.  
- **Remediation:** Set `ProjectName` in **Project Settings → Description** (writes `DefaultGame.ini`).  
- **False positive guard:** None for ship; editor-only scratch projects may override severity to `info` in project YAML.

### 4.3 Rule: `metadata.company_name_set`

- **Category:** metadata  
- **Default severity:** reject  
- **Applies to:** all  
- **Files inspected:** `Config/DefaultGame.ini`.  
- **Check:** `CompanyName=` non-empty in `[/Script/EngineSettings.GeneralProjectSettings]`.  
- **Pattern:** `^\s*CompanyName\s*=\s*(.+)\s*$` — reject when capture **1** is empty after trim.  
- **Why REJECT:** Publisher and platform metadata require a legal publishing entity string.  
- **Remediation:** Fill **Company Name** in project description settings.  
- **False positive guard:** Internal `target_store: internal` MAY downgrade via project config only (explicit operator choice).

### 4.4 Rule: `metadata.copyright_notice`

- **Category:** metadata  
- **Default severity:** info  
- **Applies to:** all  
- **Files inspected:** `Config/DefaultGame.ini`.  
- **Check:** `CopyrightNotice=` present and longer than a minimal stub (implementations MAY require **N >= 8** visible chars).  
- **Pattern:** `^\s*CopyrightNotice\s*=\s*(.+)\s*$` — INFO when missing or clearly placeholder (`TODO`, `Your Name`).  
- **Why INFO:** Legal packaging often needs richer text than engine defaults; advisory until legal sign-off workflow runs.  
- **Remediation:** Replace with accurate copyright / rights line for ship year and rights holder.  
- **False positive guard:** Early prototypes legitimately short — keep as INFO, not REJECT, by default.

### 4.5 Rule: `metadata.game_version_parseable`

- **Category:** metadata  
- **Default severity:** reject  
- **Applies to:** all  
- **Files inspected:** `Config/DefaultGame.ini`.  
- **Check:** `ProjectVersion=` matches a dotted numeric tail suitable for store pipelines (at least `Major` or `Major.Minor`).  
- **Pattern:** `^\s*ProjectVersion\s*=\s*([0-9]+(?:\.[0-9]+){0,3})\s*$`  
- **Why REJECT:** Unparseable or missing versions break CI versioning, crash reports, and store binary association.  
- **Remediation:** Set **Project Version** under description; align with ship plan `version.semver`.  
- **False positive guard:** Pre-release labels MAY append non-numeric suffixes — if present outside capture, treat as INFO via project override (future **M7-P3** normalizer).

### 4.6 Rule: `packaging.shipping_config_required`

- **Category:** packaging  
- **Default severity:** reject  
- **Applies to:** `target_store` in {steam, epic, gog}  
- **Files inspected:** `Config/DefaultGame.ini` (`[/Script/UnrealEd.ProjectPackagingSettings]` block).  
- **Check:** `Build=BUILD_Shipping` (or engine-equivalent token) MUST be selected for distribution to those stores when `build_config` is Shipping.  
- **Pattern:** `^\s*Build\s*=\s*BUILD_Shipping\s*$` evaluated within the packaging settings section block.  
- **Why REJECT:** Shipping to public stores with Development/Test binaries is a release-class mistake.  
- **Remediation:** Set packaging build configuration to **Shipping** for store targets.  
- **False positive guard:** When `build_config` is `Test` or `Development`, this rule is **not evaluated** for REJECT (scope matrix §6).

### 4.7 Rule: `packaging.crash_reporter_included`

- **Category:** packaging  
- **Default severity:** reject  
- **Applies to:** all  
- **Files inspected:** `Config/DefaultGame.ini` / packaging-related sections per standards doc.  
- **Check:** Crash reporter client inclusion flag is **True** for distributable builds.  
- **Pattern:** `^\s*bIncludeCrashReporter\s*=\s*(?:[Tt][Rr][Uu][Ee])\s*$` (INI truth token).  
- **Why REJECT:** Without crash ingestion, post-launch stability is blind; platform policies often expect crash telemetry paths.  
- **Remediation:** Enable **Include Crash Reporter** in packaging settings.  
- **False positive guard:** `target_store: internal` MAY allow `False` only via explicit project YAML downgrade.

### 4.8 Rule: `packaging.pdb_excluded_in_shipping`

- **Category:** packaging  
- **Default severity:** reject  
- **Applies to:** `build_config=Shipping`  
- **Files inspected:** `build_path` tree (recursive), else `Binaries/<Platform>/` under the project.  
- **Check:** No `*.pdb` files ship alongside player binaries in staged output.  
- **Pattern (relative path / leaf name scan):** `(?i)\.pdb$`  
- **Why REJECT:** PDBs leak symbols, inflate download size, and complicate cert review.  
- **Remediation:** Strip debug symbols in packaging step; ensure staged directory excludes PDBs.  
- **False positive guard:** If `build_path` is null, implementations MAY `skip` this rule and increment `skipped_count` (document in `detail`).

### 4.9 Rule: `security.verbose_logging_disabled`

- **Category:** security  
- **Default severity:** reject  
- **Applies to:** `build_config=Shipping`  
- **Files inspected:** `Config/DefaultEngine.ini` (global log verbosity lines).  
- **Check:** No category sets log verbosity to `Verbose` or `VeryVerbose` for shipping scans.  
- **Pattern:** `^\s*Log(?:Global|Temp|Blueprint|UObjectGlobals)\s*=\s*(?:VeryVerbose|Verbose)\s*$`  
- **Why REJECT:** Verbose logs in shipping expose internals, paths, and player context at high volume — unacceptable data-exfil and perf risk.  
- **Remediation:** Remove or downgrade per-category overrides; rely on default shipping log tiers.  
- **False positive guard:** `Development` / `Test` configs do not trigger this rule.

### 4.10 Rule: `security.remote_control_disabled_shipping`

- **Category:** security  
- **Default severity:** reject  
- **Applies to:** `build_config=Shipping`  
- **Files inspected:** `Config/DefaultEngine.ini`  
- **Check:** `[RemoteControl]` `bEnable` must be `False` OR the section absent.  
- **Pattern:** `^\s*bEnable\s*=\s*(True|False)\s*$` applied within the `[RemoteControl]` section block.  
- **Why REJECT:** Remote Control exposes an HTTP/WS surface for property mutation; unacceptable in shipped builds.  
- **Remediation:** Set `bEnable=False` under `[RemoteControl]` in `DefaultEngine.ini` (or remove the plugin from `.uproject`).  
- **False positive guard:** Development/Test configs do not trigger this rule.

### 4.11 Rule: `content.no_unused_editor_maps`

- **Category:** content  
- **Default severity:** info  
- **Applies to:** all  
- **Files inspected:** `Content/` (recursive `*.umap` inventory).  
- **Check:** Flag maps living only under developer-only trees not intended for cook (see standards path regex).  
- **Pattern:** `(?i)[/\\]Content[/\\](?:Developer|Maps[/\\]Developer)[/\\].+\.umap$`  
- **Why INFO:** Clutters cook surface and confuses QA; not automatically ship-blocking.  
- **Remediation:** Move experiments out of cook roots or exclude from packaging.  
- **False positive guard:** Maps referenced by packaging settings as staged may be allow-listed in **M7-P3**.

### 4.12 Rule: `content.no_placeholder_assets`

- **Category:** content  
- **Default severity:** reject  
- **Applies to:** all  
- **Files inspected:** `Content/` asset paths (virtual paths and on-disk `.uasset` / `.umap` names).  
- **Check:** No asset path contains obvious placeholder tokens.  
- **Pattern:** `(?i)(?:PLACEHOLDER|[/\\]TEMP[/\\]|_WIP\.|TODO_ASSET)`  
- **Why REJECT:** Placeholder art/audio ships as production content — brand and cert risk.  
- **Remediation:** Rename/replace assets; purge `/Game/TEMP` staging dirs from default cook.  
- **False positive guard:** Deliberate internal codenames containing `TEMP` as substring MAY use project allowlist (**M7-P3**).

### 4.13 Rule: `signing.code_signed`

- **Category:** signing  
- **Default severity:** reject  
- **Applies to:** `target_platform` in {Win64, Mac, IOS}  
- **Files inspected:** `build_path` (staged `.app`, `.exe`, `.dylib`, codesign artifacts), optional CI log snippets under trace dirs.  
- **Check:** Evidence of successful code signature (platform-specific layout per standards).  
- **Pattern (macOS bundle artifact):** `(?i)[/\\][^/\\]+\.app[/\\]Contents[/\\]_CodeSign[/\\]CodeResources$`  
- **Why REJECT:** Unsigned macOS / iOS / Windows binaries fail notarization or SmartScreen expectations.  
- **Remediation:** Run platform signing pipeline; attach notarization stapling where required.  
- **False positive guard:** If `build_path` is null, treat as **skipped** with INFO explaining missing artifact root.

### 4.14 Rule: `legal.licenses_included`

- **Category:** legal  
- **Default severity:** reject  
- **Applies to:** all  
- **Files inspected:** Project root and `Content/` for common license file names; `Config/` optional.  
- **Check:** At least one consolidated third-party / license file exists for ship bundles.  
- **Pattern (acceptable filenames):** `(?i)(?:^|[/\\])(?:NOTICES|THIRD_PARTY_NOTICES|Credits\.txt|LICENSE(?:\.txt|\.md)?)$`  
- **Why REJECT:** Missing OSS attributions are a legal distribution defect.  
- **Remediation:** Add NOTICES / THIRD_PARTY_NOTICES generated from `RunUAT BuildGraph` license step or manual audit.  
- **False positive guard:** Some teams embed in `Settings` UI only — project YAML may point alternate canonical path (**M7-P3**).

### 4.15 Rule: `perf.no_shippable_dev_tools`

- **Category:** perf  
- **Default severity:** info  
- **Applies to:** `build_config=Shipping`  
- **Files inspected:** `build_path` / staged binaries.  
- **Check:** Editor binaries are not present in player staging (naming heuristic).  
- **Pattern:** `(?i)[/\\][^/\\]*UnrealEditor[^/\\]*\.(?:dll|dylib)$`  
- **Why INFO:** Shipping editor binaries is a severe size/perf mistake but sometimes caught late; advisory default.  
- **Remediation:** Fix staging rules; exclude editor targets from package.  
- **False positive guard:** Null `build_path` → skip with `skipped_count` increment.

---

## 5. Execution model

1. **Input:** Readiness manifest (§2).  
2. **Path safety:** Normalize with `realpath`; reject `..` traversal and paths outside the resolved project root (the directory containing the `.uproject`).  
3. **Reads:** INI/JSON text, directory listings, and shallow binary metadata checks only — **read-only**.  
4. **Merge order (highest precedence last):**  
   1. Hardcoded defaults in this spec + standards doc.  
   2. `.cuebert/config/prod-readiness-game.yaml` at the cuebert hub root (severities, `status: off`, `applies_to` filters).  
   3. `<project_dir>/.cuebert/prod-readiness.yaml` when present (project overrides).  
5. **Layer abilities:** each layer MAY flip severity between `info` and `reject`, MAY set `status: off` for known rule ids, and MUST NOT invent new `rule_id` keys in **M7-P2** (extension reserved for **M7-P3**).  
6. **Prohibited:** subprocesses, MCP tools, network calls, and writes to app repos.

---

## 6. Scope matrix

| Caller | `build_config=Shipping` | `build_config=Test` | `build_config=Development` |
|--------|-------------------------|---------------------|----------------------------|
| `agent-ship` | REQUIRED | ALLOWED | ALLOWED |
| `agent-ship-cook` | REQUIRED | ALLOWED | ALLOWED |
| `agent-play-qa` | ADVISORY ONLY | ADVISORY ONLY | ADVISORY ONLY |
| `user-direct-debug` | ALLOWED | ALLOWED | ALLOWED |

**REQUIRED** means **M7-P3** wiring makes this agent a **MUST-RUN** gate for that caller/config pair. **ADVISORY ONLY** means findings return but never block the caller’s flow.

---

## 7. Dry-run semantics

If `project_path` is missing/unreadable **or** `CUEBERT_PROD_READINESS_MODE=dry_run`:

- Emit **one** synthetic finding: `severity: info`, `rule_id: "dry-run.synthesized"`, `detail` explaining dry-run or missing project, `category: metadata` (or `packaging` when harness specifies).  
- Set top-level `status` to **`skip`** and `mode` to **`dry_run`**.

This mirrors **`agent-qa-resilience-game`** §7 shape (single synthetic finding + `skip` + `dry_run`) while using prod-readiness-specific ids and env var.

---

## 8. Memory hooks

| Top-level `status` | Memory action |
|--------------------|----------------|
| `pass` | No `troubleshoot_commit` |
| `warn` (INFO-only findings) | `troubleshoot_commit` at **`info`**, include **rule_id** list |
| `fail` | `troubleshoot_commit` at **`error`**, include **all** REJECT findings |
| `skip`, `error` | `troubleshoot_commit` at **`warn`** with envelope summary |

Memory toolkit entry points are described in `.cursor/skills/memory-toolkit/SKILL.md`.

---

## 9. Cross-references

| Doc / artifact | Role |
|----------------|------|
| `docs/_ai_system/agents/agent-qa-resilience-game.md` | Sibling runtime-resilience agent (**M7-P1**) |
| `docs/_ai_system/agents/agent-ship.md` | Primary `/ship` dispatcher (**M7-P3** gate consumer) |
| `docs/_ai_system/agents/agent-ship-cook.md` | Cook-time dispatcher (packaging checks) |
| `docs/_ai_system/standards/ship-guards.md` | Where REJECT gate wiring is documented alongside Ship Guards |
| `docs/_ai_system/agents/agent-ship-cert.md` | Downstream consumer of REJECT findings for cert checklist input |
| `docs/_ai_system/standards/prod-readiness-game-rules.md` | Authoritative per-rule patterns |
| `.cuebert/config/prod-readiness-game.yaml` | Default severities + scope metadata |
| `docs/projects/cue/plans/active/cuebert-gaming-system.md` | Plan **M7** tables |

---

## 10. Non-goals

- Runtime log behavior (**`agent-qa-resilience-game`** owns that).  
- Cert checklist authoring (**M8-P2**).  
- Performing actual code signing (external tooling; **M7-P3** wires invocation only).  
- Performance benchmarking (future **`bench-game`**).  
- Store-specific TRC/XR expansions (**M8**).

---

## 11. Deferred items

- Rule-engine implementation (**M7-P3**).  
- `/ship` strict gate wiring (**M7-P3**).  
- Custom per-project rule additions beyond YAML toggles (**M7-P3** extension point).  
- Additional engine families and export pipelines (**post-M7**; not part of this rule catalogue).

---

## 12. Footer

Status: spec only (**M7-P2**). **14** rules, **8** categories, **INFO/REJECT** duality. Rule engine + `/ship` gate wiring land in **M7-P3**.
