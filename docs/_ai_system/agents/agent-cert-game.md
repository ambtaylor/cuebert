# CERT CHECKLIST — Gaming (`agent-cert-game`)

> **Name:** `agent-cert-game`  
> **Status:** Spec (**M8-P2**). **Advisory-only** scanner. No MCP tools in this phase; runs as a **prompt-driven** `generalPurpose` subagent when dispatched.  
> **Consumers (dispatchers):** `docs/_ai_system/agents/agent-ship-cert.md` (**M8-P3** wiring replaces M3-P2 stub behavior for checklist evaluation), `docs/_ai_system/agents/agent-ship-package.md` (post-package advisory), `user-direct-debug`.  
> **Audience:** Not user-facing. Always dispatched by another agent or harness.

**CRITICAL:** This agent **never** emits a blocking ship severity. Every finding is **`info`** or **`warn`** only. The top-level envelope never uses a `fail` status driven by cert findings.

---

## 0. Identity

| Field | Value |
|-------|--------|
| **Agent id** | `agent-cert-game` |
| **Kind** | **Advisory** certification checklist scan (TRC/XR-style *themes*, without official platform SDKs) on a **staged / packaged build** plus project metadata |
| **MCP tools** | None in **M8-P2**; contract + taxonomy + YAML config only |
| **Canonical checklists** | `docs/_ai_system/standards/cert-game-checklists.md` |
| **Default config** | `.cuebert/config/cert-game.yaml` |

This agent is the **advisory** counterpart to **`agent-prod-readiness-game`** (**M7-P2**): prod-readiness may block `/ship` on severe defects; cert-game **never** blocks `/ship` on its own findings.

---

## 1. Purpose

Scan a cooked and packaged gaming build against platform certification requirements (TRC/XR-style themes) and return advisory findings without blocking ship.

**Scope:** Steam, Epic, GOG, itch.io, and **internal** builds (**M8-P2** reference). **Xbox, PlayStation, and Nintendo** checks are **deliberately omitted** — those require official SDKs under NDA and fall outside an open-source gaming harness.

**Explicit non-purpose:** Not a blocking gate; not a replacement for official cert submission; not a legal compliance review; not a platform SDK wrapper. No subprocess, no network, no writes. File access is bounded to `project_path` and `build_path` subtrees with `realpath` normalization.

---

## 2. Inputs

The caller supplies a **cert manifest** (JSON object):

```json
{
  "project_path": "abs path to .uproject",
  "build_path": "abs path to staged/packaged build root (from cook-package-game)",
  "target_platform": "Win64" | "Mac" | "Linux" | "IOS" | "Android",
  "target_store": "steam" | "epic" | "gog" | "itchio" | "internal",
  "build_config": "Shipping" | "Test" | "Development",
  "skip_checklists": ["str"],
  "caller": "agent-ship-cert" | "agent-ship-package" | "user-direct-debug"
}
```

**Rules:**

- `project_path` MUST be an absolute path ending in `.uproject` when the scan is `live` (see §7 for `skip` / `dry_run`).
- `build_path` SHOULD point at the **staged build root** produced upstream by **`agent-cook-package-game`** (`artifacts.staged_build` or equivalent).
- `skip_checklists` lists **checklist_id** strings only (not categories). Unknown ids SHOULD be ignored with an `info`-level note in harness logs when supported (**M8-P3**).
- **`caller`** is **required** for §6. **`agent-play-qa`** is **not** a legal `caller` (denied).

---

## 3. Output envelope

```json
{
  "status": "pass" | "warn" | "info" | "skip" | "error",
  "mode": "live" | "dry_run",
  "project_path": "str",
  "build_path": "str",
  "target_platform": "str",
  "target_store": "str",
  "build_config": "str",
  "findings": [
    {
      "checklist_id": "str",
      "category": "metadata" | "icons" | "content_rating" | "save_game" | "networking" | "input" | "localization" | "legal",
      "severity": "info" | "warn",
      "detail": "str",
      "evidence": {
        "file_path": "str | null",
        "config_key": "str | null",
        "observed_value": "str | null",
        "expected": "str | null",
        "platform_doc_ref": "str | null"
      },
      "remediation_hint": "str"
    }
  ],
  "summary": {
    "total_checklists_evaluated": "int",
    "warn_count": "int",
    "info_count": "int",
    "skipped_count": "int"
  },
  "checklist_version": "1.0.0",
  "memory_id": "str | null"
}
```

### 3.1 Status resolution

| Condition | Top-level `status` |
|-----------|---------------------|
| Any finding with `severity: warn` | `warn` (still **non-blocking** for `/ship`) |
| No `warn` findings; one or more `info` findings | `info` |
| No findings after evaluation | `pass` |
| No build accessible / harness chooses not to scan (see §7) | `skip` |
| Scanner or manifest inconsistency | `error` |

`mode` is `dry_run` when §7 applies; otherwise `live`.

---

## 4. Checklist catalogue (M8-P2 — 12 checklists)

Normative patterns, file probes, and remediation detail live in **`docs/_ai_system/standards/cert-game-checklists.md`**. This section summarizes ids and default severities; each checklist below includes contract-level elaboration.

### 4.1 Summary table

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

### 4.2 Checklist: `metadata.app_icon_present`

- **Category:** icons  
- **Default severity:** warn  
- **Applies to:** all  
- **Build path inspected:** `<build_path>/<Platform>/<ProjectName>.{exe,app}` resource section / bundle icon; fallback project `Build/<Platform>/Resources/` icons.  
- **Check:** Presence of an embedded icon resource or platform `Application.ico` / `Application.icns` / bundle `Resources` icon.  
- **Severity rationale:** warn — storefronts expect a recognizable application icon; absence yields placeholder listings.  
- **Platform doc:** Steamworks documentation on icons and artwork; EGS store page assets; GOG Galaxy packaging notes (prose references only in checklist catalog).  
- **Remediation:** Add platform icons under `Build/.../Resources/` and rebuild; align with Unreal project settings for platform targets.  
- **False positive guards:** Presence-only; does not validate pixel dimensions.

### 4.3 Checklist: `metadata.store_icon_resolutions`

- **Category:** icons  
- **Default severity:** warn  
- **Applies to:** `target_store` in {steam, epic, gog}  
- **Files inspected:** Hub or project store asset staging dirs (for example `Build/Windows/Resources/Steam/` or operator convention), plus `Config/DefaultGame.ini` hints when present.  
- **Check:** Required capsule / small capsule / header art files exist for the active store policy (heuristic file names and minimum counts).  
- **Severity rationale:** warn — incomplete artwork blocks or delays store submission.  
- **Platform doc:** Steam capsule sizes; EGS media specifications; GOG artwork checklist (catalog points to public docs conceptually).  
- **Remediation:** Generate and stage store-specific PNGs per storefront runbook.  
- **False positive guards:** Does not parse image headers; filename and presence heuristics only.

### 4.4 Checklist: `metadata.game_description_set`

- **Category:** metadata  
- **Default severity:** info  
- **Applies to:** all  
- **Files inspected:** `Config/DefaultGame.ini` — `[/Script/EngineSettings.GeneralProjectSettings]` (`Description`, `ProjectName` adjacent copy blocks when used as listing fallback).  
- **Check:** Non-empty description suitable for store listing or internal registry.  
- **Severity rationale:** info — impacts discoverability; not always blocking for internal builds.  
- **Platform doc:** Store partner docs emphasize short/long description fields.  
- **Remediation:** Fill description in project settings; mirror in store backend when required.  
- **False positive guards:** Internal `target_store` may downgrade to off via project YAML.

### 4.5 Checklist: `metadata.screenshots_included`

- **Category:** metadata  
- **Default severity:** warn  
- **Applies to:** `target_store` in {steam, epic, gog}  
- **Files inspected:** Operator staging folder under project or hub trace (`Screenshots/`, `Store/`, or manifest-driven paths).  
- **Check:** At least **N** screenshots present (default **N=1** in config merge).  
- **Severity rationale:** warn — storefronts require screenshot sets for review.  
- **Platform doc:** Steamworks screenshots; EGS media; GOG store assets.  
- **Remediation:** Export captures from build; add to staging per store guidelines.  
- **False positive guards:** Does not verify resolution or HUD cleanliness.

### 4.6 Checklist: `content_rating.declared`

- **Category:** content_rating  
- **Default severity:** warn  
- **Applies to:** `target_store` in {steam, epic}  
- **Files inspected:** `Config/DefaultGame.ini`, optional sidecar `ContentRating.ini` or IARC questionnaire export path if present.  
- **Check:** Declared age rating / questionnaire hook / `Rating` field non-empty per engine conventions.  
- **Severity rationale:** warn — storefront age gates depend on declared ratings.  
- **Platform doc:** Steam content survey; Epic Games Store rating flows.  
- **Remediation:** Complete partner questionnaire; sync fields into project metadata.  
- **False positive guards:** Cannot validate legal accuracy; advisory only.

### 4.7 Checklist: `save_game.cloud_save_configured`

- **Category:** save_game  
- **Default severity:** info  
- **Applies to:** `target_store` = steam  
- **Files inspected:** `Config/DefaultEngine.ini` / plugin sections for Steam subsystem; optional `steam_appid.txt` near staged root.  
- **Check:** Steam online subsystem or Steamworks integration markers present when project declares Steam target.  
- **Severity rationale:** info — cloud saves are expected for many Steam titles but not universal.  
- **Platform doc:** Steamworks Cloud documentation.  
- **Remediation:** Enable Steam Cloud APIs or document offline-only intent in operator notes (still INFO if ambiguous).  
- **False positive guards:** Single-player offline games may legitimately omit cloud; keep INFO default.

### 4.8 Checklist: `networking.offline_first`

- **Category:** networking  
- **Default severity:** info  
- **Applies to:** all  
- **Files inspected:** `Config/DefaultGame.ini` online subsystem defaults; packaged `*.ini` in staged `Saved/Config/` if present.  
- **Check:** No hard dependency on always-on auth for single-player entry (heuristic: mandatory online-only flags absent unless declared).  
- **Severity rationale:** info — cert narratives emphasize graceful offline behavior for applicable titles.  
- **Platform doc:** Steam offline mode notes; general platform XR themes on connectivity.  
- **Remediation:** Gate online features behind sign-in; provide offline path where product design allows.  
- **False positive guards:** Live-service titles may intentionally require connectivity — operator YAML may set checklist `off`.

### 4.9 Checklist: `input.controller_support_declared`

- **Category:** input  
- **Default severity:** info  
- **Applies to:** all  
- **Files inspected:** `Config/DefaultInput.ini`, project `DefaultGame.ini` input sections, README or `Input/` manifest if used.  
- **Check:** Gamepad / XInput / DualSense support declared when `target_platform` is desktop or console-class.  
- **Severity rationale:** info — cert questionnaires ask about controller support.  
- **Remediation:** Document supported controllers; enable default mappings.  
- **False positive guards:** Keyboard-only titles may silence via config.

### 4.10 Checklist: `localization.supported_languages_listed`

- **Category:** localization  
- **Default severity:** info  
- **Applies to:** all  
- **Files inspected:** `Config/DefaultGame.ini` cultures / `Internationalization` settings; staged `Content/Localization/` or manifest.  
- **Check:** Supported language list non-empty and matches packaged loc assets when present.  
- **Severity rationale:** info — store pages and cert forms expect language matrix alignment.  
- **Remediation:** Enable cultures in packaging; list supported locales in metadata.  
- **False positive guards:** English-only shippable pilots remain INFO by default.

### 4.11 Checklist: `legal.eula_present`

- **Category:** legal  
- **Default severity:** warn  
- **Applies to:** `target_store` in {steam, epic, gog, itchio}  
- **Files inspected:** Staged `Legal/EULA.txt`, `Content/Legal/`, or URL reference in `DefaultGame.ini` / store metadata bridge.  
- **Check:** EULA artifact or URL pointer present for players.  
- **Severity rationale:** warn — storefronts require click-through or bundled terms for distribution.  
- **Remediation:** Add EULA file to staged build or wire URL in settings and store backend.  
- **False positive guards:** Not a substitute for counsel review; advisory scan only.

### 4.12 Checklist: `legal.privacy_policy_present`

- **Category:** legal  
- **Default severity:** warn  
- **Applies to:** all  
- **Files inspected:** `Config/DefaultGame.ini` (`PrivacyPolicy`, partner URL fields), staged `Legal/Privacy.txt`, or hub operator manifest.  
- **Check:** Privacy policy URL or bundled policy file present when online features or analytics are declared (heuristic).  
- **Severity rationale:** warn — platform submissions expect privacy disclosures for networked titles.  
- **Remediation:** Add policy URL consistent with live service; bundle offline copy if required.  
- **False positive guards:** Offline-only titles may still INFO if URL missing — YAML may tune severity.

### 4.13 Checklist: `legal.third_party_licenses_bundled`

- **Category:** legal  
- **Default severity:** warn  
- **Applies to:** all  
- **Files inspected:** Project root / `Build/` / staged `NOTICES`, `THIRD_PARTY_NOTICES`, `Credits.txt`, `Licenses/`.  
- **Check:** Consolidated third-party attribution file present near player-facing root.  
- **Severity rationale:** warn — distribution requires OSS and middleware credits.  
- **Remediation:** Generate notices from build graph or manual audit; ship alongside binaries.  
- **False positive guards:** Alternate paths may be configured in project YAML (**M8-P3** resolver).

---

## 5. Execution model

1. **Input:** Cert manifest (§2).  
2. **Path safety:** Normalize with `realpath`; deny `..` traversal outside resolved `project_path` parent and resolved `build_path` root.  
3. **Reads:** INI/JSON text, directory listings, shallow resource presence checks — **read-only**.  
4. **Merge order (highest precedence last):**  
   1. Hardcoded defaults in this spec + checklist standards doc.  
   2. `.cuebert/config/cert-game.yaml` at the cuebert hub root.  
   3. `<project_path>/.cuebert/cert.yaml` when present.  
5. **Layer abilities:** each layer MAY flip severity between `info` and `warn`, MAY set `status: off` for known checklist ids, and MUST NOT add new `checklist_id` keys in **M8-P2** (extension reserved for **M8-P3**).  
6. **Prohibited:** subprocesses, MCP tools, network calls, writes to app repos.

---

## 6. Scope matrix

| Caller | Invocation |
|--------|------------|
| `agent-ship-cert` | REQUIRED (**M8-P3** default — must-run advisory step; never blocking) |
| `agent-ship-package` | ALLOWED |
| `agent-play-qa` | DENIED |
| `user-direct-debug` | ALLOWED |

**REQUIRED** means **M8-P3** wiring always invokes cert-game when the ship plan enables cert evaluation; outcomes remain **advisory** for `/ship` progression.

---

## 7. Dry-run semantics

If `CUEBERT_CERT_MODE=dry_run` **or** `build_path` is missing / unreadable:

- Return a **synthetic** envelope: top-level `status: skip`, `mode: dry_run`, `findings: []`, `summary` zeroed appropriately.

---

## 8. Memory hooks

| Top-level `status` | Memory action |
|--------------------|----------------|
| `pass` | No `troubleshoot_commit` |
| `warn` | `troubleshoot_commit` at **`info`** — include first **5** `warn` findings (cert remains advisory; memory severity stays `info`) |
| `info` | No `troubleshoot_commit` |
| `skip`, `error` | `troubleshoot_commit` at **`warn`** with envelope summary |

Memory toolkit entry points are described in `.cursor/skills/memory-toolkit/SKILL.md`.

---

## 9. Cross-references

| Doc / artifact | Role |
|----------------|------|
| `docs/_ai_system/agents/agent-prod-readiness-game.md` | Sibling **blocking** pre-ship gate (**M7-P2**) |
| `docs/_ai_system/agents/agent-cook-package-game.md` | Upstream producer of staged build (**M8-P1**) |
| `docs/_ai_system/agents/agent-ship-cert.md` | M3-P2 stub; **M8-P3** wires this agent as the checklist evaluator |
| `docs/_ai_system/standards/cert-game-checklists.md` | Detailed checklist catalog |
| `docs/_ai_system/standards/ship-guards.md` | Advisory guard wiring lands **M8-P3** (`ship.cert_advisory` and related) |
| `.cuebert/config/cert-game.yaml` | Default severities + scope metadata |
| `docs/projects/cue/plans/active/cuebert-gaming-system.md` | Plan **M8** |

---

## 10. Non-goals

- Blocking findings of any kind from cert-game.  
- Official cert submission tooling (use platform SDKs — out of scope here).  
- Xbox / PlayStation / Nintendo first-party checks (under NDA).  
- Legal compliance sign-off (see **`agent-security.md`** / organizational counsel workflows).  
- Runtime behavioral QA (see **`agent-qa-resilience-game`**).

---

## 11. Deferred items

- Rule-engine implementation (**M8-P3**).  
- `ship.cert_advisory` guard wiring (**M8-P3**).  
- Xbox / PlayStation / Nintendo checklist packs.  
- Store-specific expansions (full Steam TRC, EGS XR enumerations) beyond the **M8-P2** catalog.

---

## 12. Footer

Status: spec only (**M8-P2**). **12** advisory checklists, **8** categories, **INFO/WARN** duality. Rule engine + `/ship` advisory wiring land in **M8-P3**.
