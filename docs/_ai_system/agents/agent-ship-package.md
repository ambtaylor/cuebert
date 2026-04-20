# SHIP PACKAGE — Distribution Artifact Bundling

> **Role:** `/ship` harness — **Package** phase subagent (logical role)  
> **Parent protocol:** `docs/_ai_system/agents/agent-ship.md` — read **§3.4 Package**, **§4 Ship Guards** (post-package), **§5 inputs** (`package_format`, `version`), **§6 outputs**, and **§11 subagent roster**. This file defines **`agent-ship-package`**.  
> **Dispatch:** Only from the `/ship` harness in main chat. **`subagent_type`** remains **`generalPurpose`** per parent §11.1.

---

## 1. Role

Within `/ship`, **`agent-ship-package`** is a **thin delegator** to **`agent-cook-package-game`** with **`skip_cook: true`** and **`skip_package: false`**, so only the **`stage`** and **`package`** internal phases run. **Cook** MUST have completed in an earlier `/ship` step (via **`agent-ship-cook`**). Pre-requisite **post-cook** gates (**`ship.qa_resilience`**, legacy **`guard.cook.*`**) have **already** passed.

The delegator **returns** the child envelope with **`phases[]` filtered** to **`stage`** + **`package`** when the harness requests a package-phase summary, or the **full** child envelope otherwise. **`ship.cook_package`** evaluates all three internal phases across the split dispatches; this call satisfies **phases 2–3**.

**Non-goal:** No direct **UAT** / subprocess invocation — all automation routes through **`agent-cook-package-game`**. **`agent-cert-game`** runs **after** package per `agent-ship.md` §3.5; this role does **not** invoke cert.

---

## 2. Inputs

Pass-through to **`agent-cook-package-game`** §2 with:

| Field | Required | Description |
|-------|----------|-------------|
| **`project_path`** | Yes | Absolute `.uproject` path. |
| **`target_platform`** | Yes | Platform token (for example `Win64`). |
| **`target_store`** | Yes | Store token per child rules. |
| **`build_config`** | Yes | Maps from ship plan flavor. |
| **`skip_cook`** | Yes | **`true`** — stage/package only. |
| **`skip_package`** | Yes | **`false`**. |
| **`caller`** | Yes | **`agent-ship-package`**. |

**Optional:** `maps`, `cultures`, `compression`, `output_dir`, `extra_uat_args`, `timeout_s` per child spec.

**Legacy envelope fields** (`cooked_paths`, `package_format`, `version`, `cert_verdict`) MAY still appear in ship plans for documentation; the harness **maps** them into the child JSON and trace naming — they are **not** parallel packaging paths when **`agent-cook-package-game`** is active.

---

## 3. Outputs

| Output | Description |
|--------|-------------|
| **Child envelope** | Full **`agent-cook-package-game`** §3 object. |
| **Filtered view** | `phases[]` containing **`stage`** and **`package`** rows only when returning a package-phase summary. |
| **`artifacts`** | **`staged_build`**, **`package_size_mb`**, **`manifest_path`** populated per child rules; feeds post-package guards and **`agent-cert-game`** `build_path`. |
| **Failure propagation** | Any **`fail`** / **`error`** in **stage** or **package** MUST surface to **`ship.cook_package`** (halt unless advisory demotion or user-direct-debug override). |

---

## 4. Format adapters (stubs)

### 4.1 `zip` (Tier 1)

- **Approach:** Create **`.zip`** or **`.tar`** archives with **deterministic member ordering** (for example `zip` with sorted paths, or `tar --sort=name`) and normalized metadata where the format permits.  
- **Implementation sketch:** `python -m zipfile` with sorted `namelist` inputs, or `tar` with fixed **mtime** at epoch for reproducible builds when policy requires — exact tool choice **M8**.  
- **Proposed tool:** `ship_zip_bundle` (proposed, **M8**).  
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

1. **Confirm upstream cook** — Verify cook-phase success is recorded in the session trace (or re-read **`agent-cook-package-game`** artifacts) before dispatching stage/package.  
2. **Build child request** — **`skip_cook: true`**, **`skip_package: false`**, **`caller: "agent-ship-package"`**, plus `project_path` / platform / store / config tuple.  
3. **Dispatch** `agent-cook-package-game` — Child runs **stage** then **package** per §4.  
4. **On failure** — Return child **`fail`** / **`error`** to `/ship`; attach log tail per **`ship.cook_package`**.  
5. **On success** — Return envelope; post-package **`guard.package.*`** evaluators consume **`artifacts`** as implemented in M8 harness work.  
6. **Cert handoff** — Pass **`artifacts.staged_build`** (or packaged root per plan) to **`agent-ship-cert`** as **`build_path`** for **`agent-cert-game`** (next `/ship` phase).

---

## 8. Output envelope (JSON shape)

**Normative:** **`agent-cook-package-game.md`** §3. Illustrative **stage + package** summary:

```json
{
  "status": "pass",
  "mode": "dry_run",
  "project_path": "/path/to/HelloLevel.uproject",
  "phases": [
    {"name": "stage", "status": "pass", "duration_s": 15.2, "exit_code": 0},
    {"name": "package", "status": "pass", "duration_s": 8.7, "exit_code": 0}
  ],
  "artifacts": {
    "cooked_content": "/path/to/HelloLevel/Saved/Cooked/Win64/",
    "staged_build": "/path/to/HelloLevel/Saved/StagedBuilds/Win64-Shipping/",
    "package_size_mb": 1843.5,
    "manifest_path": null
  }
}
```

**Legacy §8 zip manifest** (`packages[]`, `verdict`) MAY still be produced by a future harness adapter for **`agent-ship-upload.md`**; until then, upload phase consumes paths from **`artifacts`** and ship rollup.

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
| `agent-cook-package-game.md` | Child agent |
| `agent-ship-cert.md` | Downstream; cert runs **after** package |
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

Status: M8-P3 (delegator to **`agent-cook-package-game`**). Legacy zip-only adapter narrative retained in §4 for non-UE futures.
