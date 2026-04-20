# Production Readiness — Gaming rule catalogue

Authoritative patterns for **`agent-prod-readiness-game`**. The agent spec at `docs/_ai_system/agents/agent-prod-readiness-game.md` summarizes behavior; this document owns **INI/file probes**, **Python `re` patterns**, **evidence**, **remediation**, and **false-positive guardrails**.

**Engine:** Unreal Engine project layout first. **M7-P2:** spec only — patterns are validated as Python regex but not executed in shipped automation until **M7-P3**.

---

## Summary table (M7-P2)

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

---

## Rule: `metadata.game_name_set`

- **Category:** metadata  
- **Default severity:** reject  
- **Applies to:** all  
- **Files inspected:** `Config/DefaultGame.ini` — section `[/Script/EngineSettings.GeneralProjectSettings]`.  
- **Trigger:** `ProjectName` missing, or value empty after trim.  
- **Pattern:**

  ```
  ^\s*ProjectName\s*=\s*(.+)\s*$
  ```

  Capture **1**; trim whitespace; empty string ⇒ REJECT.

- **Evidence:** `file_path`, `line_number`, `config_key: ProjectName`, `observed_value`, `expected: non-empty display name`.  
- **Remediation hints:** Project Settings → Description → **Project Name**; keep aligned with store listing.  
- **False positive guardrails:** None for public ship; downgrade only via hub/project YAML for jam builds.

---

## Rule: `metadata.company_name_set`

- **Category:** metadata  
- **Default severity:** reject  
- **Applies to:** all  
- **Files inspected:** `Config/DefaultGame.ini` — same `GeneralProjectSettings` section.  
- **Trigger:** `CompanyName` empty.  
- **Pattern:**

  ```
  ^\s*CompanyName\s*=\s*(.+)\s*$
  ```

- **Evidence:** same shape as `metadata.game_name_set` with `config_key: CompanyName`.  
- **Remediation hints:** Fill **Company Name** in description settings.  
- **False positive guardrails:** `target_store: internal` may use YAML to downgrade to **INFO** if policy allows.

---

## Rule: `metadata.copyright_notice`

- **Category:** metadata  
- **Default severity:** info  
- **Applies to:** all  
- **Files inspected:** `Config/DefaultGame.ini` — `CopyrightNotice` in `GeneralProjectSettings`.  
- **Trigger:** Missing line, or capture matches placeholder substrings after trim.  
- **Pattern (line presence):**

  ```
  ^\s*CopyrightNotice\s*=\s*(.+)\s*$
  ```

- **Pattern (placeholder heuristic, run on trimmed capture):**

  ```
  (?i)^(TODO|YOUR\s+COMPANY|TBD|FIXME|\(c\)\s*20[0-9]{2}\s*$)
  ```

- **Evidence:** `observed_value` carries the trimmed string.  
- **Remediation hints:** Replace with accurate `(c) YEAR Rights Holder` text; coordinate with legal.  
- **False positive guardrails:** Short legitimate notices remain **INFO**, not REJECT, by default.

---

## Rule: `metadata.game_version_parseable`

- **Category:** metadata  
- **Default severity:** reject  
- **Applies to:** all  
- **Files inspected:** `Config/DefaultGame.ini` — `ProjectVersion`.  
- **Trigger:** Line missing or numeric tuple not parseable per capture.  
- **Pattern:**

  ```
  ^\s*ProjectVersion\s*=\s*([0-9]+(?:\.[0-9]+){0,3})\s*$
  ```

- **Evidence:** `observed_value` = capture **1**; compare to ship plan semver in harness (**M7-P3**).  
- **Remediation hints:** Align `ProjectVersion` with CI `BUILD_NUMBER` injection or manual bump.  
- **False positive guardrails:** Suffix labels (`-alpha`) require normalizer in **M7-P3** — until then, treat non-matching line as REJECT.

---

## Rule: `packaging.shipping_config_required`

- **Category:** packaging  
- **Default severity:** reject  
- **Applies to:** `target_store` in {steam, epic, gog} **and** `build_config=Shipping` (combined gate in engine).  
- **Files inspected:** `Config/DefaultGame.ini` — `[/Script/UnrealEd.ProjectPackagingSettings]`.  
- **Trigger:** Required `Build=BUILD_Shipping` line absent or wrong token inside the section block.  
- **Pattern:**

  ```
  ^\s*Build\s*=\s*BUILD_Shipping\s*$
  ```

- **Evidence:** `file_path`, `line_number`, `config_key: Build`, `expected: BUILD_Shipping`.  
- **Remediation hints:** Packaging settings → **Shipping** for store-bound builds.  
- **False positive guardrails:** Non-Shipping `build_config` skips evaluation entirely.

---

## Rule: `packaging.crash_reporter_included`

- **Category:** packaging  
- **Default severity:** reject  
- **Applies to:** all  
- **Files inspected:** `Config/DefaultGame.ini` — `[/Script/UnrealEd.ProjectPackagingSettings]` (or engine-documented equivalent for crash reporter inclusion).  
- **Trigger:** `bIncludeCrashReporter` not exactly `True` when distributable ship is implied.  
- **Pattern:**

  ```
  ^\s*bIncludeCrashReporter\s*=\s*(?:[Tt][Rr][Uu][Ee])\s*$
  ```

- **Evidence:** boolean observed vs expected `True`.  
- **Remediation hints:** Enable **Include Crash Reporter** in packaging; verify crash receiver endpoint policy separately.  
- **False positive guardrails:** Internal-only distribution may downgrade via project YAML with audit trail.

---

## Rule: `packaging.pdb_excluded_in_shipping`

- **Category:** packaging  
- **Default severity:** reject  
- **Applies to:** `build_config=Shipping`  
- **Files inspected:** `build_path` when set; else `Binaries/<TargetPlatform>/` under the project directory.  
- **Trigger:** Any file path ending in `.pdb` under the inspected roots.  
- **Pattern:**

  ```
  (?i)\.pdb$
  ```

  Match against each relative path string produced by the walker.

- **Evidence:** `file_path` of first PDB hit.  
- **Remediation hints:** Remove PDBs from staging; disable PDB copy in packaging options.  
- **False positive guardrails:** If no `build_path` and binaries not yet staged, mark rule **skipped** (not failed) with INFO in harness notes.

---

## Rule: `security.verbose_logging_disabled`

- **Category:** security  
- **Default severity:** reject  
- **Applies to:** `build_config=Shipping`  
- **Files inspected:** `Config/DefaultEngine.ini` — global log category overrides.  
- **Trigger:** Any shipping-relevant category forced to verbose tiers.  
- **Pattern:**

  ```
  ^\s*Log(?:Global|Temp|Blueprint|UObjectGlobals)\s*=\s*(?:VeryVerbose|Verbose)\s*$
  ```

- **Evidence:** `config_key` from line LHS; `observed_value` from RHS.  
- **Remediation hints:** Delete hot overrides; rely on shipping defaults; move diagnostics behind `#if !UE_BUILD_SHIPPING` in code paths (engine change — out of scope for this scanner).  
- **False positive guardrails:** `Development` / `Test` builds skip this rule.

---

## Rule: `security.remote_control_disabled_shipping`

- **Category:** security  
- **Default severity:** reject  
- **Applies to:** `build_config=Shipping`  
- **Files inspected:** `Config/DefaultEngine.ini`  
- **Check:** `[RemoteControl]` `bEnable` must be `False` OR the section absent.  
- **Pattern:**

  ```
  ^\s*bEnable\s*=\s*(True|False)\s*$
  ```

  Applied only inside the `[RemoteControl]` INI block; `True` ⇒ REJECT.

- **Evidence:** `observed_value` captures `True`/`False`; `expected: False or absent section`.  
- **Remediation hints:** Set `bEnable=False` under `[RemoteControl]` (or remove Remote Control plugin from `<Project>.uproject`).  
- **False positive guardrails:** `Development` / `Test` configs do not trigger this rule.

---

## Rule: `content.no_unused_editor_maps`

- **Category:** content  
- **Default severity:** info  
- **Applies to:** all  
- **Files inspected:** `Content/` — all `*.umap` paths.  
- **Trigger:** Map path matches developer-only subtree heuristic.  
- **Pattern:**

  ```
  (?i)[/\\]Content[/\\](?:Developer|Maps[/\\]Developer)[/\\].+\.umap$
  ```

- **Evidence:** `file_path` of each hit; dedupe in summary.  
- **Remediation hints:** Move maps to production tree or exclude from packaging cook.  
- **False positive guardrails:** If a developer map is intentionally shipped, add allowlist entries in **M7-P3** project config.

---

## Rule: `content.no_placeholder_assets`

- **Category:** content  
- **Default severity:** reject  
- **Applies to:** all  
- **Files inspected:** `Content/` — `.uasset`, `.umap`, virtual `/Game/...` mount strings when indexer supplies them.  
- **Trigger:** Path basename or virtual path matches placeholder tokens.  
- **Pattern:**

  ```
  (?i)(?:PLACEHOLDER|[/\\]TEMP[/\\]|_WIP\.|TODO_ASSET)
  ```

- **Evidence:** first matching `file_path`.  
- **Remediation hints:** Replace placeholders; delete scratch `/Game/TEMP` assets from default cook set.  
- **False positive guardrails:** Legitimate asset names containing `TEMP` as substring use project allowlist (**M7-P3**).

---

## Rule: `signing.code_signed`

- **Category:** signing  
- **Default severity:** reject  
- **Applies to:** `target_platform` in {Win64, Mac, IOS}  
- **Files inspected:** `build_path` staged tree; optional signing log text supplied by harness.  
- **Trigger:** Expected signing artifacts or log success markers absent when player binaries exist.  
- **Pattern (macOS bundle artifact — relative path probe):**

  ```
  (?i)[/\\][^/\\]+\.app[/\\]Contents[/\\]_CodeSign[/\\]CodeResources$
  ```

- **Pattern (Windows signing log success line):**

  ```
  (?i)Successfully\s+signed
  ```

  Implementations OR filesystem signals with log checks; absence of both when a staged `.exe` is present ⇒ REJECT.

- **Evidence:** `file_path` to bundle or EXE; attach log excerpt in `detail` when used.  
- **Remediation hints:** Run `signtool sign` / `codesign` / `xcrun notarytool` per platform runbooks.  
- **False positive guardrails:** If `build_path` is null, skip rule and increment `skipped_count`.

---

## Rule: `legal.licenses_included`

- **Category:** legal  
- **Default severity:** reject  
- **Applies to:** all  
- **Files inspected:** repository root, `Content/`, `Config/` — shallow filename scan (recursive optional **M7-P3**).  
- **Trigger:** No file whose full relative path basename matches the allow-list pattern.  
- **Pattern (acceptable license file paths):**

  ```
  (?i)(?:^|[/\\])(?:NOTICES|THIRD_PARTY_NOTICES|Credits\.txt|LICENSE(?:\.txt|\.md)?)$
  ```

  At least one directory entry MUST match for PASS.

- **Evidence:** missing ⇒ `expected: one of NOTICES|THIRD_PARTY_NOTICES|Credits.txt|LICENSE*`.  
- **Remediation hints:** Generate NOTICES from engine third-party tool; legal review before ship.  
- **False positive guardrails:** Alternate canonical path MAY be configured in **M7-P3** `legal.licenses_included.paths[]`.

---

## Rule: `perf.no_shippable_dev_tools`

- **Category:** perf  
- **Default severity:** info  
- **Applies to:** `build_config=Shipping`  
- **Files inspected:** `build_path` staged binaries.  
- **Trigger:** Editor-named shared libraries present in staged player tree.  
- **Pattern:**

  ```
  (?i)[/\\][^/\\]*UnrealEditor[^/\\]*\.(?:dll|dylib)$
  ```

- **Evidence:** first hit `file_path`.  
- **Remediation hints:** Fix staging filters; ensure package uses `UEGame` binaries only.  
- **False positive guardrails:** Null `build_path` ⇒ skip with documented reason.

---

## Cross-reference

- Agent: `docs/_ai_system/agents/agent-prod-readiness-game.md`  
- Config: `.cuebert/config/prod-readiness-game.yaml`  
- Ship harness: `docs/_ai_system/agents/agent-ship.md`  
- Guard taxonomy: `docs/_ai_system/standards/ship-guards.md`

---

## Extension notes (M7-P3)

1. **Rule engine placement:** A shared evaluator (hub Python module or MCP-adjacent tool, **TBD**) will read the merged YAML (hub defaults + `<project>/.cuebert/prod-readiness.yaml`), walk declared paths under `project_path`, apply each active rule’s patterns, and emit the §3 JSON envelope from `agent-prod-readiness-game.md`.  
2. **Custom project rules:** **M7-P2** intentionally forbids new `rule_id` keys in YAML. **M7-P3** will add an optional `custom_rules:` list with `{id, category, severity, pattern, paths_glob}` objects validated against a JSON Schema; ids MUST be prefixed `custom.` to avoid collision with hub catalogue ids.  
3. **Strict `/ship` gate:** When `spec_only_as_info` flips to `false` in hub config, REJECT findings from this engine become hard stops in the pre-cook gate unless `user-direct-debug` supplies `override_reject: true` per contract.  
4. **Evidence enrichment:** **M7-P3** may attach optional `evidence.sha256` for binary signing checks without changing top-level envelope fields reserved here.

---

Status: **M7-P2** — patterns are normative for documentation and regex validation; automation executes in **M7-P3**.
