# cert-game Checklist Catalog

**Status**: spec (M8-P2).  
**Duality**: INFO / WARN only. This catalog never defines a blocking finding severity for cert-game.  
**Total checklists**: 12 across 8 categories.

Cert-game is an advisory scanner. It surfaces platform-certification gaps so developers can address them before official submission, but it NEVER halts the `/ship` pipeline on its own.

Authoritative agent contract: `docs/_ai_system/agents/agent-cert-game.md`. Default configuration: `.cuebert/config/cert-game.yaml`.

---

## Summary table (M8-P2)

| checklist_id | category | default severity | applies_to |
|--------------|----------|------------------|------------|
| `metadata.app_icon_present` | icons | warn | all |
| `metadata.store_icon_resolutions` | icons | warn | `target_store` in {steam, epic, gog} |
| `metadata.game_description_set` | metadata | info | all |
| `metadata.screenshots_included` | metadata | warn | `target_store` in {steam, epic, gog} |
| `content_rating.declared` | content_rating | warn | `target_store` in {steam, epic} |
| `save_game.cloud_save_configured` | save_game | info | `target_store` = steam |
| `networking.offline_first` | networking | info | all |
| `input.controller_support_declared` | input | info | all |
| `localization.supported_languages_listed` | localization | info | all |
| `legal.eula_present` | legal | warn | `target_store` in {steam, epic, gog, itchio} |
| `legal.privacy_policy_present` | legal | warn | all |
| `legal.third_party_licenses_bundled` | legal | warn | all |

---

## Checklist: `metadata.app_icon_present`

- **Category:** icons  
- **Default severity:** warn  
- **Applies to:** all  
- **Files inspected:** Staged player binary or app bundle under `build_path` (platform-specific); project `Build/<Platform>/Resources/Windows/Application.ico`, `Build/Mac/Resources/*.icns`, or engine-documented icon override paths.  
- **Trigger:** No embedded icon resource and no fallback icon file on disk for the active `target_platform`.  
- **Pattern / probe:** Existence of `.ico` / `.icns` / bundle `Resources/*.icns` or PE/ Mach-O resource section heuristics when implementations support shallow reads.  
- **Evidence:** `file_path` to expected icon location; `observed_value: missing`; `expected: icon resource or platform resource file`.  
- **Platform doc reference (prose):** Steamworks partner documentation on application icons and listing artwork; Epic Games Store documentation on executable and branding assets; GOG packaging guidelines for desktop icons.  
- **Remediation hints:** Add `Application.ico` / `Application.icns` under Build resources; set icons in Unreal **Project Settings → Platforms**; rebuild and re-stage.  
- **False positive guardrails:** Validates presence only — not dimensions, transparency, or platform-specific bit depth rules.

---

## Checklist: `metadata.store_icon_resolutions`

- **Category:** icons  
- **Default severity:** warn  
- **Applies to:** `target_store` in {steam, epic, gog}  
- **Files inspected:** Operator convention directories (for example `Build/Resources/Store/`, hub trace `store-assets/`), plus optional manifest YAML listing required assets.  
- **Trigger:** Missing expected capsule / header / small capsule files for the active store (implementations match basename patterns such as `capsule_main.png`, `Capsule616x353.png`, `library_capsule.png` per team convention).  
- **Pattern / probe:** Glob for PNG/WebP store art; count files against configured minimum set from hub YAML.  
- **Evidence:** `file_path` of staging root; `observed_value` lists found files; `expected` lists required slots.  
- **Platform doc reference (prose):** Steamworks **Icons and Artwork** size tables; EGS **Store Page Assets** media specifications; GOG Galaxy artwork checklist.  
- **Remediation hints:** Export art at partner-required resolutions; place files where ship plan `store_assets_root` points; re-run package staging.  
- **False positive guardrails:** Does not decode image headers — filename and presence only until **M8-P3** adds optional validators.

---

## Checklist: `metadata.game_description_set`

- **Category:** metadata  
- **Default severity:** info  
- **Applies to:** all  
- **Files inspected:** `Config/DefaultGame.ini` — `[/Script/EngineSettings.GeneralProjectSettings]` (`Description=` and related narrative fields).  
- **Trigger:** `Description` absent, empty after trim, or placeholder tokens (`TODO`, `TBD`, `Lorem`).  
- **Pattern:**

  ```
  ^\s*Description\s*=\s*(.+)\s*$
  ```

  Trim capture; run placeholder heuristic case-insensitively on the result.  
- **Evidence:** `config_key: Description`, `observed_value`, `expected: non-empty listing-ready text`.  
- **Platform doc reference (prose):** Store partner docs require short and long descriptions for discoverability; internal catalogs benefit from the same fields.  
- **Remediation hints:** Fill **Description** in project settings; keep in sync with public store listing copy.  
- **False positive guardrails:** Early prototypes may intentionally ship thin copy — severity stays **info** by default.

---

## Checklist: `metadata.screenshots_included`

- **Category:** metadata  
- **Default severity:** warn  
- **Applies to:** `target_store` in {steam, epic, gog}  
- **Files inspected:** Staging folder under project or trace (for example `Screenshots/`, `Store/Screenshots/`).  
- **Trigger:** Fewer than `min_screenshot_count` image files (default **1** from hub YAML).  
- **Pattern / probe:** `(?i)\.(png|jpg|jpeg|webp)$` against immediate children or one-level subfolders per config.  
- **Evidence:** `file_path` to staging dir; `observed_value: N files`; `expected: >= min_screenshot_count`.  
- **Platform doc reference (prose):** Steamworks screenshot requirements; EGS media gallery rules; GOG store capture guidance.  
- **Remediation hints:** Capture gameplay stills from **Shipping** build; avoid debug overlays; upload per partner aspect ratios.  
- **False positive guardrails:** Does not verify HUD-less captures or minimum resolution — advisory only.

---

## Checklist: `content_rating.declared`

- **Category:** content_rating  
- **Default severity:** warn  
- **Applies to:** `target_store` in {steam, epic}  
- **Files inspected:** `Config/DefaultGame.ini`; optional sidecar rating export; `steam_appid.txt` adjacent metadata when used as hook only.  
- **Trigger:** No declared rating field, questionnaire id, or IARC hook string when store policy expects one for public listing.  
- **Pattern / probe:** Engine-specific keys under `GeneralProjectSettings` or partner plugin sections; non-vacuous string required.  
- **Evidence:** `config_key` of the missing or empty field; `platform_doc_ref` points to public questionnaire names only (no reproduced forms).  
- **Platform doc reference (prose):** Steam content survey workflow; Epic questionnaire and metadata binding.  
- **Remediation hints:** Complete partner questionnaire; sync resulting tokens into project and store backend.  
- **False positive guardrails:** Cannot certify legal accuracy; teams must obtain legal / ratings counsel independently.

---

## Checklist: `save_game.cloud_save_configured`

- **Category:** save_game  
- **Default severity:** info  
- **Applies to:** `target_store` = steam  
- **Files inspected:** `Config/DefaultEngine.ini` OnlineSubsystem Steam settings; plugin list in `.uproject`; optional `steam_appid.txt` in staged root.  
- **Trigger:** Steam target declared but no Steam OnlineSubsystem block and no `steam_appid.txt` when project metadata asserts Steam distribution.  
- **Pattern / probe:** Section `[OnlineSubsystemSteam]` or subsystem switch `DefaultPlatformService=Steam` heuristics; presence of small app id file.  
- **Evidence:** `file_path` to inspected INI; `observed_value`; `expected: Steam cloud or explicit offline-save declaration in operator notes`.  
- **Platform doc reference (prose):** Steamworks Cloud API overview; Steam Remote Storage partner pages.  
- **Remediation hints:** Enable Steamworks cloud saves or document offline-only saves in ship plan so harness can silence this checklist.  
- **False positive guardrails:** Single-player offline titles may legitimately omit cloud — keep default **info**, not elevated severity.

---

## Checklist: `networking.offline_first`

- **Category:** networking  
- **Default severity:** info  
- **Applies to:** all  
- **Files inspected:** `Config/DefaultGame.ini`, `Config/DefaultEngine.ini` for always-online flags; staged `Saved/Config/Windows/*.ini` when copied for distribution.  
- **Trigger:** Heuristic signals that single-player entry requires continuous authentication without product justification flags in YAML.  
- **Pattern / probe:** Search for `RequiresOnlineSubsystem=True`-class keys or DRM hooks as documented in standards appendix (**M8-P3**).  
- **Evidence:** `config_key`, `observed_value`, `expected: offline-capable launch path or documented live-service exception`.  
- **Platform doc reference (prose):** General XR themes on offline play where applicable; Steam offline mode documentation for desktop players.  
- **Remediation hints:** Gate online-only features; provide offline boot path when design allows; document live-service requirement in ship plan.  
- **False positive guardrails:** GaaS titles may require online by design — operator `status: off` in project YAML.

---

## Checklist: `input.controller_support_declared`

- **Category:** input  
- **Default severity:** info  
- **Applies to:** all  
- **Files inspected:** `Config/DefaultInput.ini`; `DefaultGame.ini` default player input; optional `README` / `Docs/INPUT.md` if referenced by hub manifest.  
- **Trigger:** No gamepad / XInput mapping section and product category implies controller-capable platform (desktop / Android / iOS class).  
- **Pattern / probe:** Presence of `Gamepad` mappings or engine default gamepad profile activation lines.  
- **Evidence:** `file_path`; `observed_value: no gamepad bindings detected`; `expected: declared controller support or keyboard-only rationale`.  
- **Platform doc reference (prose):** Platform cert questionnaires commonly ask for controller support and remapping policy.  
- **Remediation hints:** Enable default gamepad mappings; document partial keyboard-only support in store metadata.  
- **False positive guardrails:** Typing-only or mouse-only games may disable this checklist via YAML.

---

## Checklist: `localization.supported_languages_listed`

- **Category:** localization  
- **Default severity:** info  
- **Applies to:** all  
- **Files inspected:** `Config/DefaultGame.ini` internationalization settings; `Content/Localization/` staged tree; `*.locmeta` / `*.archive` counts when present.  
- **Trigger:** Cultures list empty while localized asset folders exist (mismatch), or no cultures declared for a title advertising multi-language on store plan.  
- **Pattern / probe:** `CulturesToStage=` or UE5 `Internationalization` culture lists; directory listing under staged localization path.  
- **Evidence:** `observed_value` lists cultures found vs configured; `expected: aligned culture set`.  
- **Platform doc reference (prose):** Store listing language tags must match shipped audio/text; partner localization policy pages.  
- **Remediation hints:** Stage cultures in packaging settings; shrink advertised languages to match shipped assets.  
- **False positive guardrails:** English-only pilots remain **info** when listing matches reality.

---

## Checklist: `legal.eula_present`

- **Category:** legal  
- **Default severity:** warn  
- **Applies to:** `target_store` in {steam, epic, gog, itchio}  
- **Files inspected:** Staged `Legal/EULA.txt`, `Content/Legal/EULA.pdf`, or URL fields in `DefaultGame.ini` / partner metadata bridge files.  
- **Trigger:** No bundled EULA file and no configured URL pointer when store distribution is selected.  
- **Pattern / probe:** Case-insensitive basename match `(?i)eula(\.txt|\.md|\.pdf)?$` under staged `Legal/` roots; INI key scan for `EULA` or `LicenseURL`.  
- **Evidence:** `file_path` to expected legal root; `observed_value: absent`; `expected: bundled EULA or partner URL`.  
- **Platform doc reference (prose):** Steamworks legal attribution flows; EGS legal documentation hooks; GOG and itch.io publisher agreements summaries.  
- **Remediation hints:** Add EULA text to staging; wire click-through URL in store backend and reference in project metadata.  
- **False positive guardrails:** Not legal advice; teams must have counsel review final terms.

---

## Checklist: `legal.privacy_policy_present`

- **Category:** legal  
- **Default severity:** warn  
- **Applies to:** all  
- **Files inspected:** `Config/DefaultGame.ini` (`PrivacyPolicy=`, `PrivacyPolicyUrl=` class keys); staged `Legal/Privacy.txt`; analytics plugin sections in `DefaultEngine.ini`.  
- **Trigger:** Analytics / online subsystem active but privacy URL or file missing.  
- **Pattern / probe:** If `OnlineSubsystem` or analytics modules enabled, require non-empty privacy URL or file.  
- **Evidence:** `config_key`; `observed_value`; `expected: privacy URL or bundled policy`.  
- **Platform doc reference (prose):** Steam / Epic / mobile platform expectations for privacy disclosures; GDPR-oriented partner notes (high level only).  
- **Remediation hints:** Publish policy at stable URL; reference from game and store pages; bundle offline copy if required.  
- **False positive guardrails:** Strictly offline titles may still be flagged if analytics plugins appear enabled — review plugin list for false detection.

---

## Checklist: `legal.third_party_licenses_bundled`

- **Category:** legal  
- **Default severity:** warn  
- **Applies to:** all  
- **Files inspected:** Project root; `Build/`; staged root for `NOTICES`, `THIRD_PARTY_NOTICES`, `Credits.txt`, `LICENSE`, `Licenses/**`.  
- **Trigger:** No consolidated notices file found using configured basename allowlist.  
- **Pattern:**

  ```
  (?i)(?:^|[/\\])(?:NOTICES|THIRD_PARTY_NOTICES|Credits\.txt|LICENSE(?:\.txt|\.md)?)$
  ```

- **Evidence:** `file_path` search root; `observed_value: none matched`; `expected: one consolidated notices artifact`.  
- **Platform doc reference (prose):** OSS attribution expectations in Steamworks and general distribution guidance; engine third-party license tooling references.  
- **Remediation hints:** Generate notices via UAT license step or SBOM export; ship alongside player-visible root.  
- **False positive guardrails:** Alternate canonical path may be supplied in `<project>/.cuebert/cert.yaml` (**M8-P3** path resolver).

---

## Extension notes (M8-P3 hook points)

- **Rule engine:** Load merged YAML (hub + project), expand `applies_to` filters for `target_store` and `target_platform`, emit findings into the §3 envelope from `agent-cert-game.md`.  
- **Guard bridge:** `ship.cert_advisory` SHOULD consume `findings[]` for dashboards without mapping any cert severity to a blocking halt.  
- **Path resolver:** Centralize staging roots (`build_path`) vs trace-relative store asset dirs to reduce duplicate configuration.  
- **Optional validators:** Image dimension probes and INI normalization may elevate confidence but remain advisory.  
- **Telemetry:** Log `checklist_version` + hub config `version` for reproducibility across CI runs.

### Implementation sketch (non-normative)

1. Resolve `project_path` and `build_path` with `realpath`; refuse paths outside allowed roots.  
2. Load INI files as UTF-8 text; tolerate BOM per engine conventions.  
3. For each checklist row in the summary table, evaluate `applies_to`; if out of scope, increment `skipped_count` without emitting a finding.  
4. Sort findings by `category`, then `checklist_id`, for stable envelopes.  
5. Map top-level `status` per `agent-cert-game.md` §3.1; never emit `fail` from cert-game logic.  
6. Return envelope to `agent-ship-cert` for formatting into `cert/report.md` and ship aggregate JSON.

### Versioning

Bump `checklist_version` in the output envelope when adding checklist rows or changing default severities. Hub `cert-game.yaml` `version` tracks config schema only.
