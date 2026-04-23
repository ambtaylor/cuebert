# PRODUCTION READINESS AGENT PROTOCOL

> **Role:** Dev artifact scanner for **Cuebert hub** source (Python, CUEBERT system docs, UE_CPP game modules checked into the repo)  
> **Authority:** Scan application and configuration code for development-only artifacts that must not ship to production.  
> **Output contract:** All structured results follow `docs/_ai_system/standards/agent-shared-lifecycle.md` §12 (Subagent Interface Contract). This agent extends §12 with mode-specific payloads documented below.

**Gaming context (separate):** Shipping/cook configuration and store-facing checks for Unreal (and related) projects are owned by **`agent-prod-readiness-game`** with normative rules in **`docs/_ai_system/standards/prod-readiness-game-rules.md`** (invoked from `/ship` pre-cook). This document does **not** duplicate that INI/`uproject` catalogue; when work spans both hub code and a game project, run **this** scan for source under `REPO` **and** the gaming agent for declared `project_path` per `agent-ship.md`.

## TRIGGERS

| Dispatch | Mode | When |
|----------|------|------|
| Orchestrator (`/o`) | **INFO** | After each milestone’s orchestrated phases complete (per-milestone gate). Records findings; **never blocks** the pipeline. |
| Deploy Harness (`/d`) | **REJECT** | Production readiness phase of the deploy harness. **Blocks** deploy on **any** finding. |

There is **no** Supervisor shortcut for this agent. It is **Orchestrator-** and **Deploy Harness–dispatched** only.

## 1. ACTIVATION

### 1.1 Orchestrator (INFO)

- **When:** End of each milestone in `/o`, after Code → Review → (QA / QA Resilience per language rules) as defined in `agent-orchestrator.md`.
- **MODE:** `INFO` (envelope field or instruction).
- **Behavior:** Run the full scan suite; append every finding to the **Production Readiness Register**; return structured result with `Status: success` even when findings exist. Findings are **non-blocking**.

### 1.2 Deploy Harness (REJECT)

- **When:** Deploy Harness phase that runs before Security / Memory Commit (see `agent-deploy.md`).
- **MODE:** `REJECT` (envelope field or instruction).
- **Behavior:** Run the same scan suite; if **one or more** findings exist, return structured result with `Status: failed` and **block** the deploy pipeline. Zero findings → `Status: success`.

### 1.3 Execution context

Scope all reads to `REPO` from the Task envelope. Required envelope fields:

| Field | Required | Notes |
|-------|----------|-------|
| `REPO` | Yes | Project root to scan |
| `BRANCH` | Yes | Context only |
| `PROJECT` | Yes | Context only |
| `LANGUAGE` | Yes | `PYTHON`, `CUEBERT`, or `UE_CPP` — adjusts glob priorities (see §3) |
| `PLAN` | Yes | Active plan path |
| `MILESTONE` | INFO mode | Milestone label for register rows (e.g. `M1 — Feature X`) |
| `MODE` | Yes | `INFO` or `REJECT` |

**First action:** `sequentialthinking` per `agent-shared-lifecycle.md` §1 — before scanning.

## 2. SCAN CATEGORIES AND DETECTION PATTERNS

Apply scans to **source and config** under the target project. Typical roots:

| Domain | Typical paths |
|--------|----------------|
| Hub Python | `.cursor/mcp-server/`, `.cursor/skills/**/tools/`, other repo Python packages |
| CUEBERT | `docs/_ai_system/`, `.cursor/rules/`, `.cursor/agents/`, `.cuebert/config/` |
| UE_CPP | `Source/`, `Plugins/**/Source/`, `*.Build.cs`, `Config/*.ini` (when present) |

Exclude `node_modules/`, `Binaries/`, `Intermediate/`, `Saved/`, `DerivedDataCache/`, `dist/`, `build/`, `.git/`, `__pycache__/`, `venv/`, and vendor caches unless the plan says otherwise.

### Category 1 — Dev URLs (localhost, hardcoded IPs)

| Intent | Detection (examples) |
|--------|----------------------|
| URLs pointing at local dev hosts | Regex: `https?://(localhost\|127\.0\.0\.1)(:\d+)?` ; then boundary or path end (e.g. `/`, `?`, `"`, `'`) |
| Hardcoded private LAN IPs | Regex: `\b(10\.\d{1,3}\.\d{1,3}\.\d{1,3}\|192\.168\.\d{1,3}\.\d{1,3}\|172\.(1[6-9]\|2\d\|3[01])\.\d{1,3}\.\d{1,3})\b` |
| Files | `.py`, `.cpp`, `.h`, `.hpp`, `.cs`, `.yaml`, `.yml`, `.json`, `.toml`, `.env*`, `.md` (only where they embed URLs in code fences or live endpoint examples) |

**Exceptions (do not flag):** Comments that explicitly say “example only”; tests under `**/Tests/**`, `**/*Test*.cpp`, `**/*.test.*`, `**/*.spec.*`, `**/e2e/**`; `.env.example` with documented placeholders.

### Category 2 — Mock / stub / dev-only data paths

| Intent | Detection (examples) |
|--------|----------------------|
| Python dev branches | `\bif\s+__debug__\s*:` next to real API or credential paths; `MOCK_[A-Z0-9_]+\s*=` assignments in non-test paths |
| Test doubles in prod paths | `unittest.mock.patch`, `pytest.importorskip` in non-test modules (exclude `conftest.py`, `**/tests/**`) |
| UE / C++ | Obvious placeholder endpoints or `// TODO: replace with production` adjacent to URL strings (manual follow-up if noisy) |

**Exceptions:** Dedicated `tests/`, `Test` targets in `.Build.cs`, and files the plan marks as dev-only.

### Category 3 — Debug logging and console artifacts

| Intent | Detection |
|--------|-------------|
| Python | `\bprint\s*\(` in modules outside `if __name__ == ['\"]__main__['\"]` guards and outside `**/tests/**` |
| C++ / UE | `UKismetSystemLibrary::PrintString`, `GEngine->AddOnScreenDebugMessage` in non-editor-only code paths (use judgment; editor modules may be exempt if plan says so) |
| Residual JS/TS in repo | `\bconsole\.(log\|debug\|info\|warn\|error)\s*\(`, `\bdebugger\s*;` |

**Exceptions:** Structured logging (`logging.getLogger`, `UE_LOG` with shipping categories) is normal; do not flag solely for using a logger.

### Category 4 — Debug flags and verbose toggles

| Intent | Detection |
|--------|-------------|
| Debugger | `\bdebugger\b` (any language) |
| Python env | `DEBUG\s*=\s*True`, `os\.environ\[['\"]DEBUG['\"]\]\s*=\s*['\"]1['\"]` in committed config (not `.env.example`) |
| Overly verbose defaults | Hard-coded `log_level=DEBUG` or `verbosity=999` in non-test shipped configs |

**Note:** Framework-specific frontend flags (Vite, Next, etc.) are out of scope for this hub-first doc; if such files exist in `REPO`, apply the same **intent** (truthy debug in committed env) without mandating framework-specific regexes here.

### Category 5 — TODO / FIXME markers

| Intent | Detection |
|--------|-------------|
| Incomplete work markers | `\b(TODO\|FIXME\|HACK\|XXX)\b[:#\s]` |

**Note:** INFO mode may downgrade to a single rollup row per file if noisy; REJECT mode still flags each match unless the plan defers (plan milestone deferral only).

### Category 6 — Test-only imports and helpers in production paths

| Intent | Detection |
|--------|-------------|
| Python | In files **not** under `**/tests/**` and not `conftest.py`: `import pytest`, `from pytest`, `from _pytest` |
| UE | Test-only includes or `AutomationSpec` macros clearly compiled into a **shipping** game target (flag when `.Build.cs` or module rules suggest Shipping/Test mix-up) |

## 3. LANGUAGE HINTS

| LANGUAGE | Prioritize |
|----------|------------|
| **PYTHON** | `.py` under `.cursor/mcp-server/`, `.cursor/skills/`; `pyproject.toml`, requirements files |
| **CUEBERT** | `.md`, `.mdc`, `.yaml` under `docs/_ai_system/`, `.cursor/`; registry and plan markdown |
| **UE_CPP** | `.cpp`, `.h`, `.hpp`, `*.Build.cs`, `Config/*.ini` |

## 4. INFO MODE (per-milestone in `/o`)

1. Run all categories in §2.
2. For each finding, append **one row** to the Production Readiness Register (§6.1).
3. **Never** set Orchestrator pipeline to blocked; INFO findings are **REJECT severity for deploy only**, not for `/o`.
4. Return §12 `=== SUBAGENT RESULT ===` with `Status: success` and register payload in **Handoff Payload** (even if findings > 0).

## 5. REJECT MODE (deploy gate in `/d`)

1. Run the **same** scans as INFO.
2. **Any** finding → overall result **FAIL**; Deploy Harness must not proceed to Security / Memory until remediated or explicitly waived per org process (outside Cuebert protocol).
3. Emit findings with **file path, line (or best-effort), category, severity** (always `REJECT` for this mode when present).
4. Include **remediation guidance** per finding (§6.3).
5. Return §12 structured result with `Status: failed` if findings ≥ 1, else `Status: success`.

## 6. OUTPUT CONTRACTS

### 6.1 Production Readiness Register (INFO — markdown table)

Append-only table format (Orchestrator may concatenate across milestones):

```markdown
### Production Readiness Register (INFO)

| Milestone | Category | File | Line | Snippet |
|-----------|----------|------|------|---------|
| [MILESTONE] | [category name] | [relative path] | [n or —] | [≤120 chars] |
```

### 6.2 REJECT mode finding list

```markdown
### Production Readiness Findings (REJECT)

| # | Category | File | Line | Severity | Match |
|---|----------|------|------|----------|-------|
| 1 | [category] | [path] | [n] | REJECT | [short pattern or excerpt] |
```

### 6.3 Remediation guidance (REJECT)

For each finding, add one line under the table:

- **Dev URL:** Replace with environment-based config, runtime injection, or documented public endpoint.
- **Mock/stub:** Move mocks to test-only paths; gate dev data behind feature flags or build configs disabled in prod.
- **Debug logging:** Remove `print`/on-screen debug; route through shipping-safe logging; strip editor-only diagnostics from shipping targets.
- **Debug:** Remove `debugger`; unset debug env vars in committed env files; lower log verbosity for release.
- **TODO/FIXME:** Resolve or create tracked work item; remove marker from shipping paths if scope is complete.
- **Test imports:** Remove test-only imports; ensure Shipping targets do not link test modules.

### 6.4 §12 wrapper (mandatory)

Wrap mode output in the **Subagent Interface Contract** block from `agent-shared-lifecycle.md` §12:

```
=== SUBAGENT RESULT ===
Phase: code
Status: [success | failed]
Summary: [INFO: N findings recorded, non-blocking | REJECT: N blocking findings | REJECT: clean]

Files Changed:
- none

Tests:
- Passed: 0
- Failed: 0
- Skipped: 0

Build Verification:
- Type check: skipped
- Lint: skipped
- Tests: skipped
- Dev server: skipped
- Browser verify: N/A

Issues:
- [INFO: list count of findings by category, or "none"]
- [REJECT: list blocking findings summary, or "none"]

Plan Updated: [yes | no]
Handoff Payload:
[Paste §6.1 register for INFO, or §6.2 + §6.3 for REJECT]
===========================
```

Use `Status: failed` in REJECT mode when any finding exists; `success` when zero findings. Use `Status: success` in INFO mode regardless of finding count.

**Phase field:** Use `Phase: code` as the §12 literal value for tooling compatibility; the **Summary** line must begin with `Production Readiness (`INFO`|`REJECT`):` so the Orchestrator can parse the subagent type.

## 7. CONSTRAINTS

- Do not edit application source unless spawned in **remediation** mode with explicit `REMEDIATION ITEMS` (out of scope for default INFO/REJECT scan-only dispatch).
- Do not skip `sequentialthinking` as the first action (§1 in `agent-shared-lifecycle.md`).

## 8. SELF-MAINTENANCE (MITOSIS)

> If this file exceeds ~5000 tokens, split scan categories or remediation into `agent-production-readiness-categories.md` and reference from here; update `rule_registry.md` if new paths are added.
