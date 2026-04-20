# SHIP CERT — Certification Profile Evaluation

> **Role:** `/ship` harness — **Cert** phase subagent (logical role)  
> **Parent protocol:** `docs/_ai_system/agents/agent-ship.md` — read **§3.3 Cert**, **§4 Ship Guards** (post-cert gates), **§5 inputs** (`cert_profile`), **§6 outputs** (`cert/report.md`), **§11 subagent roster**, and **§14 Security notes** (no vendor checklist reproduction in cuebert docs). This file defines **`agent-ship-cert`**; checklist engines are **M8-P2**.  
> **Dispatch:** Only from the `/ship` harness in main chat. **`subagent_type`** remains **`generalPurpose`** per parent §11.1.

---

## Execution (M8-P2 spec, M8-P3 wiring)

Starting M8-P3, this agent delegates cert-checklist evaluation to
`agent-cert-game` (spec M8-P2). The cert-game agent returns advisory findings
(INFO/WARN only, never REJECT). This agent then formats the findings for the
ship envelope and, if all checklists are advisory-passing, marks the ship
phase as cert-clear.

Until M8-P3 wiring lands, the M3-P2 stub remains in place and no cert checks
run.

See: [`agent-cert-game.md`](./agent-cert-game.md),
[`cert-game-checklists.md`](../standards/cert-game-checklists.md).

---

## 1. Role

You evaluate a **cooked build** against the configured **cert profile** and emit a **human-readable cert report** plus a **structured findings envelope** suitable for post-cert Ship Guards and the aggregate ship envelope. You do **not** invoke cook, package, upload, or signing automation. You do **not** embed **vendor-confidential** checklist text for first-party console platforms — **`platform-strict`** remains a **contract** for operators to implement under their own NDAs (`agent-ship.md` §14).

---

## 2. Inputs

| Input | Required | Description |
|-------|----------|-------------|
| **`project`** | Yes | Manifest key for reporting and profile resolution. |
| **`cooked_paths`** | Yes | Map **platform → directory** from **`agent-ship-cook.md`** §8 `cooked_paths` (cook envelope). |
| **`target_platforms`** | Yes | List echoing the ship plan; used to iterate checks per platform. |
| **`cert_profile`** | Yes | `none` \| `indie-light` \| `platform-strict` — from ship plan (`agent-ship.md` §5.1). |
| **`cert_overrides`** | No | Optional per-project overrides (workspace manifest or harness-supplied) — schema **M3-P3**. |
| **`HUB_REPO`** | No | Hub root for trace-relative paths. |
| **`REPORT_PATH`** | No | Default **`.cuebert/traces/ship/<timestamp>/cert/report.md`** when harness omits. |

---

## 3. Outputs

| Output | Description |
|--------|-------------|
| **Cert report** | Markdown narrative with per-platform summaries, check outcomes, and evidence pointers on disk. |
| **Findings envelope** | JSON list of structured findings (§6) aggregated into the cert output envelope (§7). |
| **Severity per finding** | `fail` \| `warn` \| `info` — drives `verdict` and `guard.cert.severity_floor` (`agent-ship.md` §4.2). |

---

## 4. Cert profile contract (stubs)

### 4.1 `none`

- **Behavior:** **Skip** the cert phase entirely: emit **`verdict: "skip"`** immediately with **zero** checks executed and an **info**-class finding noting skip rationale (`internal build` policy).  
- **Outputs:** Minimal `report.md` MAY contain a single line: "Cert profile `none` — phase skipped." Harness post-cert policy: `agent-ship.md` §7 (severity floor **N/A**).  
- **Status: stub (full impl M3-P2)** — skip path is normative for M3 stubs; wiring idempotency **M3-P3**.

### 4.2 `indie-light`

- **Intent:** Generic, **public-safe** checks suitable for small-team shipping discipline:  
  - Per-platform **file size budget** vs configured thresholds.  
  - **Required manifest fields** presence in cooked tree or sidecar metadata (engine-specific resolution **M8-P2**).  
  - **Executable naming** conventions (stem matches project key or declared product name pattern).  
  - **No `TODO` strings** in selected binary metadata slices where deterministic scanning is supported (**stub** until tooling exists).  
- **Full implementation:** **M8-P2**.  
- **Status: stub (full impl M8-P2)** — checklist engine + thresholds in hub YAML (**TBD milestone**).

### 4.3 `platform-strict`

- **Intent:** **Platform-specific** certification checklists required by storefronts or first-party hardware programs.  
- **Cuebert stance:** This document defines **interface only**: profile name, finding envelope shape, severity floor, and **operator-supplied** checklist id hooks. **Do not** paste proprietary vendor requirements, test case IDs, or console-specific compliance prose into cuebert repositories. Operators attach **external** runbooks and map outcomes into findings.  
- **Status: stub (contract only, operator implements per platform)** — no PS/Xbox/Switch/etc. vendor content in-repo.

---

## 5. Profile resolution order

Highest precedence wins (aligns with vault + manifest patterns in `agent-ship.md` §5.3 spirit):

1. **Vault** — Optional future **`cert.*`** config blocks resolved per **`docs/_ai_system/standards/vault-standard.md`** when teams centralize thresholds (names only in Task envelopes — **post-M8**).  
2. **Workspace manifest** — `projects.{key}` cert overrides / profile defaults when documented (**M3-P3** schema).  
3. **Ship plan** — explicit `cert_profile` field.  
4. **Hub defaults** — `.cuebert/config/ship-guards.yaml` or companion cert config when introduced (**M3-P3**).

**Status: stub (full impl M3-P3)** — merge implementation.

---

## 6. Finding envelope (single finding)

Mirror the **evidence contract** pattern in **`docs/_ai_system/standards/play-preview-guards.md` §5** — stable ids, typed evidence, non-vacuous attachments for `fail` / `warn`.

```json
{
  "check_id": "cert.indie-light.exec-name",
  "profile": "indie-light",
  "severity": "fail",
  "evidence": {
    "type": "file",
    "path": ".cuebert/traces/ship/2026-04-20T120000Z/cooked/Win64/MyGame-Win64-Shipping.exe",
    "detail": "Executable stem does not match declared product_name pattern."
  },
  "message": "Short human-readable reason."
}
```

**`evidence.type`:** `file` \| `log` \| `text` \| `manifest` (extensible with version bump).

**`check_id` namespace:** prefix `cert.<profile>.<slug>` for stable API surface (**M8-P2** catalog).

---

## 7. Output envelope (aggregated)

```json
{
  "profile": "indie-light",
  "verdict": "pass",
  "findings": [],
  "platform_summaries": {
    "Win64": { "checks_run": 0, "fail": 0, "warn": 0, "info": 0 },
    "Mac": { "checks_run": 0, "fail": 0, "warn": 0, "info": 0 }
  },
  "report_path": ".cuebert/traces/ship/2026-04-20T120000Z/cert/report.md"
}
```

**`verdict` enum:** `pass` \| `warn` \| `fail` \| `skip`

**Composition (normative intent):**

- **`skip`** when `cert_profile: none`.  
- **`fail`** if any finding has `severity: fail` after policy resolution.  
- **`warn`** if no fails but at least one `warn`.  
- **`pass`** otherwise.

**`platform_summaries`:** counts per platform; exact inner schema **additive** at M8.

---

## 8. Protocol

1. **Load profile config** — Resolve §5 ordering; fail fast if `cooked_paths` missing a platform in `target_platforms`.  
2. **Iterate cooked paths per platform** — Normalize paths; ensure directories exist (else `fail` finding with `evidence.type: file`).  
3. **Run each check** — According to §4 profile; record §6 objects.  
4. **Collect findings** — Stable sort by `check_id` then `severity` for deterministic envelopes.  
5. **Compute verdict** — §7 rules; respect harness **severity floor** when supplied (**M8-P2**).  
6. **Write report** — Markdown at `report_path`; include links/paths to evidence files.  
7. **Emit envelope** — Write **`cert/envelope.json`** (name aligned with harness **M3-P3**) beside `report.md` **or** embed in ship aggregate only — pick **one** canonical on-disk layout at wiring time; this doc recommends **`.../cert/envelope.json`** co-located with `report.md`.

---

## 9. Artifact storage

```text
.cuebert/traces/ship/<timestamp>/cert/report.md
.cuebert/traces/ship/<timestamp>/cert/envelope.json   # recommended — M3-P3 naming lock
```

Hub-only traces per **`control-plane-paths.md`**. Cert reports may contain sensitive **local** notes — do not upload unless an explicit upload phase policy allows (`agent-ship.md` §14).

**Status: stub (full impl M3-P2)** — stub writers may emit placeholder markdown.

---

## 10. Non-goals

| Non-goal | Redirect |
|----------|----------|
| **Cook / UAT** | `agent-ship-cook.md` |
| **Packaging** | `agent-ship-package.md` |
| **Upload** | `agent-ship-upload.md` |
| **Automatic signing / notarization** | Operator or CI per `agent-ship.md` §14 — cert may **reference** requirements but does not invoke Apple/GPG/portal tools by default |
| **Vendor-secret checklist text** | External operator docs only |

---

## 11. Memory hooks

- **Subagent:** Does **not** call `milestone_commit` or `troubleshoot_commit` directly.  
- **Harness:** Commits memory based on session outcome after **Attest** (`agent-ship.md` §13).  
- **Artifacts:** Writes under `.cuebert/traces/ship/.../cert/` only.

---

## 12. Task envelope sketch (harness → Cert)

```text
## Cuebert /ship — Cert
**First action:** Read docs/_ai_system/agents/agent-ship-cert.md

PROJECT_KEY: [manifest key]
CERT_PROFILE: [none|indie-light|platform-strict]
COOKED_PATHS_JSON: [{ "Win64": "..." , "Mac": "..." }]
TARGET_PLATFORMS: [Win64, Mac]
REPORT_PATH: [.cuebert/traces/ship/<timestamp>/cert/report.md]
```

---

## 13. Post-cert guard alignment

| Guard id | Consumer fields |
|----------|------------------|
| `guard.cert.severity_floor` | `findings[].severity`, harness floor |
| `guard.cert.required_checklists` | `check_id` coverage vs profile requirements (**M8-P2**) |
| `guard.cert.report_emitted` | `report_path` exists and non-empty when profile != `none` |

**Status: stub (full impl M8-P2)**

---

## 14. Relationship to `agent-play-qa.md` (informational)

Both produce **findings** + **verdict** vocabulary. **Cert** is **ship-time**, **artifact-rooted** on **cooked** trees; **QA** is **preview-time** on **editor logs/screenshots**. Deduplication is **not required** across harnesses.

---

## 15. Waivers and operator overrides (contract only)

Some orgs allow **waived** checks with signed approvals. Waiver schema is **out of scope M3-P2**; reserve `finding.waiver_id` **optional** field at **M8-P2** without breaking §6 shape.

---

## 16. Evidence quality

For **`fail`** / **`warn`**, **`evidence`** MUST be **non-vacuous** — mirror **`play-preview-guards.md` §5** empty-evidence policy. The harness MUST treat vacuous cert results as **blocked** sessions.

---

## 17. Severity mapping stub

| Finding severity | Typical harness effect |
|------------------|------------------------|
| `fail` | Post-cert **fail** unless waived (**M8-P2**) |
| `warn` | Continue if floor allows; else **fail** |
| `info` | Record only |

**Status: stub (full impl M8-P2)**

---

## 18. Check catalog placeholder (`indie-light`)

| `check_id` | Intent | Status |
|------------|--------|--------|
| `cert.indie-light.size-budget` | Cooked tree under byte cap | stub |
| `cert.indie-light.manifest-fields` | Required metadata files present | stub |
| `cert.indie-light.exec-name` | Executable naming convention | stub |
| `cert.indie-light.todo-bin` | Scan for forbidden TODO markers | stub |

**Status: stub (full impl M8-P2)**

---

## 19. `platform-strict` operator checklist hook (contract only)

Operators supply **external** checklist ids; the harness passes **`required_checklist_ids`** (future field). Cert subagent records **PASS/WARN/FAIL** per id without embedding vendor **how-to** text in cuebert.

**Status: stub (contract only, operator implements per platform)**

---

## 20. Negative examples (must REJECT)

- Request to paste **first-party** compliance PDF content into `report.md` → **refuse**; store pointers only.  
- Running cert **before** cook envelope exists → **fail** with missing `cooked_paths` evidence.  
- Silently upgrading `none` to `indie-light` → **forbidden**; profile must match ship plan.

---

## 21. Cross-references

| Doc | Use |
|-----|-----|
| `agent-ship.md` | Cert phase in chain, guard ids, security posture |
| `play-preview-guards.md` §5 | Finding + evidence envelope pattern |
| `control-plane-paths.md` | Trace roots |
| `agent-ship-package.md` | Upstream consumer of cert `verdict` |

---

## 22. Verdict → Package gating

`agent-ship-package.md` requires **`verdict != fail`** before bundling. **`warn`** packaging policy is **harness-level** (**M3-P3**); default recommendation: **allow** with explicit operator acknowledgement flag (future).

---

## 23. Stub writer behavior (M3-P2)

Until M8 evaluators exist, stub implementation **MAY** emit `verdict: pass` with **`findings: []`** **only** when `spec_only_as_info`-style policy applies — **never** a content-free pass when real checks were required and skipped without `info` findings. Align with Ship Guard **`spec_only`** philosophy (`play-preview-guards.md` §3.4).

**Status: stub (full impl M3-P3)** — policy flag parity for cert.

---

## 24. Platform summary defaults

When no checks run (early stub), set `checks_run: 0` and `verdict: skip` for `none`; for active profiles, emit **`info`** finding `cert.stub.no_evaluators` until M8 (**recommended**).

---

Status: M3-P2 (protocol stub). indie-light impl: M8-P2. platform-strict: contract only, operator implements per platform per vendor NDA constraints.
