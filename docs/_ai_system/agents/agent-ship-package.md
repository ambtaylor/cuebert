# SHIP PACKAGE — Distribution Artifact Bundling

> **Role:** `/ship` harness — **Package** phase subagent (logical role)  
> **Parent protocol:** `docs/_ai_system/agents/agent-ship.md` — read **§3.4 Package**, **§4 Ship Guards** (post-package), **§5 inputs** (`package_format`, `version`), **§6 outputs**, and **§11 subagent roster**. This file defines **`agent-ship-package`**.  
> **Dispatch:** Only from the `/ship` harness in main chat. **`subagent_type`** remains **`generalPurpose`** per parent §11.1.

---

## 1. Role

You bundle **cooked build output** into the configured **distribution format** and emit **checksummed package artifacts** plus an **aggregate package manifest** suitable for post-package Ship Guards and optional upload (`agent-ship-upload.md`). You assume **cook outputs exist** and **cert verdict is not `fail`** when cert was in scope.

---

## 2. Inputs

| Input | Required | Description |
|-------|----------|-------------|
| **`project`** | Yes | Manifest key; used in naming convention (§7). |
| **`version`** | Yes | Object with **`semver`**, **`build_number`**, optional **`internal_label`** — mirrors `agent-ship.md` §5.1 `version` block. |
| **`cooked_paths`** | Yes | Per-platform directories from **`agent-ship-cook.md`** §8. |
| **`target_platforms`** | Yes | Drives one package per platform (default) unless harness batches. |
| **`package_format`** | Yes | `zip` \| `installer` \| `platform-native` — from ship plan. |
| **`output_dir`** | Yes | Typically **`.cuebert/traces/ship/<timestamp>/packaged/`**. |
| **`cert_verdict`** | No | From **`agent-ship-cert.md`** §7; when absent and profile was `none`, harness supplies `skip`. |
| **`cook_flavor`** | No | `development` \| `shipping` \| `debug` — used in filename stem (§7). |
| **`git_sha`** | No | Short SHA for non-shipping filename suffix (§7); harness-supplied. |

---

## 3. Outputs

| Output | Description |
|--------|-------------|
| **Per-platform package files** | Archive or installer artifact path per platform under `output_dir`. |
| **SHA-256 checksums** | One digest per package file (hex lowercase **recommended**). |
| **Aggregate manifest** | JSON index of all packages, sizes, checksums, determinism flags (**§8**). |

---

## 4. Format adapters (stubs)

### 4.1 `zip` (Tier 1)

- **Approach:** Create **`.zip`** or **`.tar`** archives with **deterministic member ordering** (for example `zip` with sorted paths, or `tar --sort=name`) and normalized metadata where the format permits.  
- **Implementation sketch:** `python -m zipfile` with sorted `namelist` inputs, or `tar` with fixed **mtime** at epoch for reproducible builds when policy requires — exact tool choice **M8**.  
- **Proposed tool:** `cuebert_package_zip` (proposed, **M8**).  
- **Status: stub (full impl M8)** — first packaging automation for UE cooked trees.

### 4.2 `installer` (Tier 2)

- **Scope:** Windows NSIS/MSI, macOS `.pkg`/`.dmg`, Linux AppImage — **contract only**.  
- **Operator responsibility:** Supply **templates** and signing hooks **outside** this stub; Cuebert records paths only.  
- **Status: stub (contract only, operator-supplied post-M8)** — no embedded vendor wizards.

### 4.3 `platform-native` (Tier 3)

- **Scope:** First-party packaging layouts (store-specific bundles) requiring **platform SDKs**.  
- **Operator responsibility:** Provide SDK-backed steps; cuebert doc stays **interface-only**.  
- **Status: stub (contract only, operator-supplied post-M8)** — no proprietary layout specs in-repo.

---

## 5. Determinism requirement

**Goal:** Same **git SHA** + identical **cooked inputs** + same **packaging options** SHOULD yield the **same package checksum** for supply-chain auditability.

| Format adapter | Determinism expectation |
|----------------|-------------------------|
| **`zip` with sorted file list + fixed metadata** | **CAN** guarantee byte-stable archives when engine outputs are stable (**M8**). |
| **`tar` with `--sort=name` + clamped mtime** | **CAN** approach reproducibility; platform tool flags are harness-owned (**M8**). |
| **`installer`** | **Often non-deterministic** (timestamps, GUIDs, code signing) — operator MUST document acceptance criteria; Cuebert records actual checksums post-build. |
| **`platform-native`** | **Generally non-deterministic** without vendor-specific normalization — treat as **operator-supplied** determinism policy. |

**Externalities:** **Notarization retries**, **timestamp servers**, and **signing** (when added by operators per `agent-ship.md` §14) may change bytes — package envelope MUST record **`deterministic: false`** when those steps apply.

**Status: stub (full impl M8)** — determinism validators.

---

## 6. Version naming convention

**Pattern:**

```text
<project>_<version>_<platform>_<flavor>.<ext>
```

**Example:**

```text
hello-level_0.1.0_Win64_shipping.zip
```

**Non-shipping flavors:** append **`_<git_sha_short>`** before extension when `git_sha` is available:

```text
hello-level_0.1.0_Win64_development_abc1234.zip
```

**Characters:** Prefer `[a-z0-9-]+` for project slug normalization; exact slug rules **M3-P3**.

---

## 7. Protocol

1. **Validate cert verdict** — If `cert_verdict == "fail"`, **abort** with `verdict: "fail"` in package envelope and **no** packages written (or write **empty** manifest with failure notes — harness picks **M3-P3**).  
2. **For each platform** — Bundle `cooked_paths[platform]` according to `package_format` (§4).  
3. **Compute checksum** — SHA-256 over final artifact bytes.  
4. **Write manifest** — Append per-package record (§8) to **`manifest.json`** in `output_dir`.  
5. **Emit envelope** — Return §8 JSON + paths to harness.

---

## 8. Output envelope (JSON shape)

Consumed by **`agent-ship-upload.md`** (`packages` list).

```json
{
  "packages": [
    {
      "platform": "Win64",
      "format": "zip",
      "path": ".cuebert/traces/ship/2026-04-20T120000Z/packaged/hello-level_0.1.0_Win64_shipping.zip",
      "size_bytes": 1234567890,
      "sha256": "<hex>",
      "deterministic": true
    }
  ],
  "manifest_path": ".cuebert/traces/ship/2026-04-20T120000Z/packaged/manifest.json",
  "verdict": "pass"
}
```

**`verdict`:** `pass` \| `fail` — packaging-level only; does not override cert semantics.

---

## 9. Artifact storage

```text
.cuebert/traces/ship/<timestamp>/packaged/<files...>
.cuebert/traces/ship/<timestamp>/packaged/manifest.json
```

Hub-only per **`control-plane-paths.md`**.

**Status: stub (full impl M8)**

---

## 10. Non-goals

| Non-goal | Redirect |
|----------|----------|
| **Upload** | `agent-ship-upload.md` |
| **Cook** | `agent-ship-cook.md` |
| **Cert execution** | `agent-ship-cert.md` |
| **Signing / notarization** | No signing in Package — signing is operator-configured and referenced via **`cert_profile`** / external runbooks per `agent-ship.md` §14 (not implied by successful package) |
| **`git tag` / release promotion** | Operator workflow |

---

## 11. Memory hooks

- **Subagent:** Does **not** call memory tools directly.  
- **Harness:** `milestone_commit` on full ship success includes primary artifact paths (`agent-ship.md` §13).

---

## 12. Post-package guard alignment

| Guard id | Consumer fields |
|----------|------------------|
| `guard.package.exists` | `packages[].path` |
| `guard.package.checksum` | `packages[].sha256` + on-disk recompute |
| `guard.package.manifest` | `manifest_path` |

**Status: stub (full impl M8)**

---

## 13. Task envelope sketch (harness → Package)

```text
## Cuebert /ship — Package
**First action:** Read docs/_ai_system/agents/agent-ship-package.md

PROJECT_KEY: [manifest key]
VERSION_JSON: { "semver": "0.1.0", "build_number": 42, "internal_label": "rc1" }
PACKAGE_FORMAT: [zip|installer|platform-native]
COOKED_PATHS_JSON: [{ "Win64": "..." }]
OUTPUT_DIR: [.cuebert/traces/ship/<timestamp>/packaged/]
CERT_VERDICT: [pass|warn|fail|skip]
GIT_SHA: [optional short]
```

---

## 14. Integrity checks before upload handoff

Upload phase MUST re-verify checksums; package phase SHOULD store **relative** paths stable across machines when `HUB_REPO` is consistent.

---

## 15. Failure taxonomy

| Condition | `verdict` | Notes field |
|-----------|-----------|-------------|
| Missing cooked dir | `fail` | Which platform |
| IO error mid-archive | `fail` | Exception class |
| Unsupported format on stub harness | `fail` | `not_implemented` |

---

## 16. Cross-references

| Doc | Use |
|-----|-----|
| `agent-ship.md` | Package phase, ship envelope aggregation |
| `agent-ship-cook.md` | Upstream `cooked_paths` |
| `agent-ship-cert.md` | Upstream `cert_verdict` |
| `agent-ship-upload.md` | Downstream consumer of `packages` |

---

## 17. Manifest record shape (per package)

```json
{
  "platform": "Win64",
  "format": "zip",
  "path": "...",
  "size_bytes": 123,
  "sha256": "...",
  "deterministic": true,
  "semver": "0.1.0",
  "build_number": 42
}
```

**Additive keys** allowed with manifest `version: 1` bump policy (**M3-P3**).

---

## 18. Parallelism

Default: **one platform package at a time** to reduce IO thrash; future parallel policy **M8**.

**Status: stub (full impl M8)**

---

## 19. Negative examples (must REJECT)

- Package when **cert `fail`** for active profile → **stop** (§7 step 1).  
- Strip checksums to “save space” → **forbidden**; post-package guards require hashes.  
- Write packages into **application repo** roots → **forbidden**; hub traces only.

---

## 20. Relationship to primary artifact (`agent-ship.md` §6.1)

The **primary artifact** path in the ship envelope SHOULD reference the **per-platform** package the operator cares about first (Windows vs Mac policy **harness**). This subagent lists **all** built packages uniformly.

---

## 21. Size and disk preflight (stub)

Before archiving, verify free disk space ≥ **`sum(content_size_bytes) * margin`** when `content_size_bytes` is present from cook envelope — policy **M8**.

**Status: stub (full impl M8)**

---

## 22. Installer code signing note (informational)

Installers often embed signatures that change bytes. Set **`deterministic: false`** and record **signing identity** only if harness adds redaction-safe fields (**post-M8**).

---

## 23. `platform-native` handoff without SDK

When SDK is missing, return **`verdict: fail`** with `notes: not_applicable_missing_sdk` and session outcome mapping per parent §3.7 (**M3-P3** harness).

**Status: stub (full impl post-M8)**

---

## 24. Slim alignment

Parent `agent-ship.md` §3.9 **Package** slim references `INPUT_ROOT` / `OUTPUT_DIR` — this doc expands multi-platform **`cooked_paths`** explicitly.

---

Status: M3-P2 (protocol stub). zip adapter full impl: M8. installer/platform-native: operator-supplied post-M8.
