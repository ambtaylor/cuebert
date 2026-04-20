# /ship plan: {PLAN_TITLE}

Project: {PROJECT_KEY} (must exist in `.cuebert/workspace-manifest.json` under `projects.{PROJECT_KEY}` and include a valid `ship` block per `docs/_ai_system/standards/ship-guards.md` §8)
Engine: {unreal|unity|godot}
Target platforms: {Win64, Mac, Linux, ...} (engine-native tokens; map from plan vocabulary as needed)

---

## Ship intent

{One to three sentences: what distributable outcome should this `/ship` run produce? Describe platforms, flavor, and player-facing deliverable. Do not paste credentials or vendor-confidential checklist text.}

---

## Version

| Field | Value |
|-------|-------|
| **semver** | {X.Y.Z} |
| **build_number** | {N} |
| **internal_label** | {string — e.g., rc1, demo-steamfest} |

---

## Package format

Pick one: **`zip`** | **`installer`** | **`platform-native`**

{If installer or platform-native, describe operator-supplied templates or SDK steps at a high level — no secrets.}

---

## Cert profile

Pick one: **`none`** | **`indie-light`** | **`platform-strict`**

{Explain why this profile matches the release class. For `none`, note internal-only or cook-only intent.}

---

## Upload channel

Pick one: **`none`** | **`itch.io`** | **`steam`** | **`custom`** (default: **`none`**)

**Dry-run default: TRUE** — the harness and `agent-ship-upload.md` treat missing explicit opt-in as **no network mutation**. Set **`dry_run: false`** only when you intentionally authorize upload for this run.

{If not `none`, list public channel identifiers only — vault service names, no secret values.}

---

## Guards overrides (optional)

Per-run tuning uses **`.cuebert/workspace-manifest.json`** → `projects.<key>.ship.guardOverrides` and/or ship plan **`ship_guards_overrides`**. Both MUST be structural subsets of `.cuebert/config/ship-guards.yaml` per-guard keys (`enabled`, `default_severity`, optional `threshold`).

Example intent (shape only — not copy-paste truth):

```yaml
ship_guards_overrides:
  guard.cook.size_budget:
    default_severity: warn
    threshold:
      warn_bytes: 4294967296
      fail_multiplier: 1.25
```

Document **why** an override is needed (known large content slice, temporary waiver, and so on).

---

## Pre-flight checklist

- [ ] **Git clean** in declared ship scope (or intentional waiver documented outside this template — discouraged).
- [ ] **Engine installed** and `enginePath` / `engineVersion` resolvable for the active profile.
- [ ] **Credentials** for upload (if any) exist only in vault per `docs/_ai_system/standards/vault-standard.md`.
- [ ] **Cert profile** configured to match storefront or internal policy; external runbooks linked where required.
- [ ] **Workspace manifest** `ship` block reviewed for `targetPlatforms`, budgets, and `guardOverrides`.

---

## Success criteria

What does **pass** mean for this ship session?

- {Criterion 1 — e.g., post-cook guards pass; cook `exit_code` is 0; cooked roots exist for each `targetPlatforms` entry.}
- {Criterion 2 — e.g., cert verdict is `pass` or `warn` within configured floors; `cert/report.md` emitted when profile requires it.}
- {Criterion 3 — e.g., post-package guards pass; SHA-256 recorded for each zip; `manifest.json` present.}
- {Criterion 4 — optional — e.g., upload phase skipped or `dry_run` envelope recorded when `upload_channel: none`.}
- {Criterion 5 — optional — Attest wrote `.cuebert/traces/ship/<timestamp>/envelope.json` and memory hook succeeded in text mode.}

---

## Non-goals

Explicitly out of scope for this `/ship` run (pick what applies):

- No `/play` iteration or editor-only preview artifacts as the final deliverable.
- No automatic **code signing** or **notarization** unless a future approved harness flag documents it.
- No refactors unrelated to packaging readiness.
- {Add project-specific boundaries.}

---

## Footer (harness)

```text
Status: DRAFT
Author: {USER}
Harness expected phase chain: pre-cook guards → agent-ship-cook → post-cook guards → agent-ship-cert (skip if cert_profile:none) → post-cert guards → agent-ship-package → post-package guards → agent-ship-upload (opt-in) → Attest + memory commit
```

When promoting from draft, set `Status: APPROVED` and link the trace directory path after the run (under `.cuebert/traces/ship/<timestamp>/`).
