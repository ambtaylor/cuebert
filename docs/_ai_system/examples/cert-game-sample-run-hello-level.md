# cert-game sample run — Hello Level (synthetic)

**Status:** illustrative only (M8-P2). Envelopes are synthetic and valid JSON. Cert-game is **advisory**: even `status: warn` does **not** halt `/ship` by itself.

---

## Scenario 1 — Steam target, mixed results (top-level `warn`)

**Narrative:** `metadata.app_icon_present` passes (no finding). `metadata.store_icon_resolutions`, `legal.eula_present`, and `legal.privacy_policy_present` produce **warn** findings. All other checklists pass. The envelope reports **three** findings; top-level `status` is **`warn`**. Downstream `/ship` may still proceed; the ship harness records `cert_advisory` for operator review.

```json
{
  "status": "warn",
  "mode": "live",
  "project_path": "/abs/HelloLevel/HelloLevel.uproject",
  "build_path": "/abs/HelloLevel/Saved/StagedBuilds/Windows",
  "target_platform": "Win64",
  "target_store": "steam",
  "build_config": "Shipping",
  "findings": [
    {
      "checklist_id": "metadata.store_icon_resolutions",
      "category": "icons",
      "severity": "warn",
      "detail": "Store capsule set incomplete: missing 460x215 class capsule asset in staging.",
      "evidence": {
        "file_path": "/abs/HelloLevel/Build/Resources/Store",
        "config_key": null,
        "observed_value": "capsule_460x215.png missing",
        "expected": "Steam capsule main + small capsule per partner artwork table",
        "platform_doc_ref": "Steamworks documentation: Icons and Artwork (size table)"
      },
      "remediation_hint": "Add required PNGs under the store staging root and re-run package staging."
    },
    {
      "checklist_id": "legal.eula_present",
      "category": "legal",
      "severity": "warn",
      "detail": "No EULA file found under staged Legal/ directory.",
      "evidence": {
        "file_path": "/abs/HelloLevel/Saved/StagedBuilds/Windows/HelloLevel/Legal/EULA.txt",
        "config_key": null,
        "observed_value": "missing",
        "expected": "Legal/EULA.txt or equivalent in staged build",
        "platform_doc_ref": "Steamworks: legal attribution and EULA presentation"
      },
      "remediation_hint": "Bundle EULA.txt in staged Legal/ or wire store-side click-through URL in partner console."
    },
    {
      "checklist_id": "legal.privacy_policy_present",
      "category": "legal",
      "severity": "warn",
      "detail": "Privacy policy URL not set in DefaultGame.ini while online subsystem is enabled.",
      "evidence": {
        "file_path": "/abs/HelloLevel/Config/DefaultGame.ini",
        "config_key": "PrivacyPolicy",
        "observed_value": "empty",
        "expected": "non-empty URL or bundled privacy policy file",
        "platform_doc_ref": "Steamworks: privacy disclosure expectations (summary)"
      },
      "remediation_hint": "Set privacy policy URL in project settings and mirror on public site."
    }
  ],
  "summary": {
    "total_checklists_evaluated": 12,
    "warn_count": 3,
    "info_count": 0,
    "skipped_count": 0
  },
  "checklist_version": "1.0.0",
  "memory_id": null
}
```

**Non-blocking note:** No severity in `findings[]` exceeds `warn`; cert-game never emits a blocking code. The `/ship` coordinator treats this as advisory input unless a separate non-cert guard fails.

---

## Scenario 2 — Internal target, info-only (top-level `info`)

**Narrative:** Zero **warn** findings. Two **info** findings: thin game description and localization matrix advisory. Top-level `status` is **`info`**.

```json
{
  "status": "info",
  "mode": "live",
  "project_path": "/abs/HelloLevel/HelloLevel.uproject",
  "build_path": "/abs/HelloLevel/Saved/StagedBuilds/Windows",
  "target_platform": "Win64",
  "target_store": "internal",
  "build_config": "Shipping",
  "findings": [
    {
      "checklist_id": "metadata.game_description_set",
      "category": "metadata",
      "severity": "info",
      "detail": "Description field is placeholder text; internal registry may still want listing copy.",
      "evidence": {
        "file_path": "/abs/HelloLevel/Config/DefaultGame.ini",
        "config_key": "Description",
        "observed_value": "TODO: add description",
        "expected": "non-placeholder description",
        "platform_doc_ref": null
      },
      "remediation_hint": "Replace placeholder in Project Settings → Description."
    },
    {
      "checklist_id": "localization.supported_languages_listed",
      "category": "localization",
      "severity": "info",
      "detail": "Only en culture staged; ship plan advertises multi-language later.",
      "evidence": {
        "file_path": "/abs/HelloLevel/Config/DefaultGame.ini",
        "config_key": "CulturesToStage",
        "observed_value": "en",
        "expected": "align staged cultures with advertised languages when going public",
        "platform_doc_ref": null
      },
      "remediation_hint": "Stage additional cultures before store targets; update listing tags to match."
    }
  ],
  "summary": {
    "total_checklists_evaluated": 12,
    "warn_count": 0,
    "info_count": 2,
    "skipped_count": 0
  },
  "checklist_version": "1.0.0",
  "memory_id": null
}
```

---

## Scenario 3 — Dry-run (`skip`, no findings)

**Narrative:** `CUEBERT_CERT_MODE=dry_run` is set. The scanner returns a synthetic envelope: `status: skip`, `findings: []`.

```json
{
  "status": "skip",
  "mode": "dry_run",
  "project_path": "/abs/HelloLevel/HelloLevel.uproject",
  "build_path": "",
  "target_platform": "Win64",
  "target_store": "steam",
  "build_config": "Shipping",
  "findings": [],
  "summary": {
    "total_checklists_evaluated": 0,
    "warn_count": 0,
    "info_count": 0,
    "skipped_count": 12
  },
  "checklist_version": "1.0.0",
  "memory_id": null
}
```
