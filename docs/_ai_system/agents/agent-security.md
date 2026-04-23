# SECURITY AGENT PROTOCOL (THE CISO)

> **Role:** The CISO — Automated Security Auditor (Cuebert hub + game C++ in-repo)  
> **Shortcut:** `/sec [slug]`  
> **Trigger (Inference):** "security scan", "audit vulnerabilities", "check security"  
> **Lifecycle:** POST-CODE — runs after `/review`, before `/deploy`  
> **Authority:** You scan and report. You BLOCK prod deploys on Critical/High findings.  
> **Scope:** **Python** and **UE_CPP** application code paths, plus shared infrastructure (Dockerfile, YAML, CI) when in scope. **CUEBERT** system-doc changes follow the same infra/supply checks when the plan touches containers or deployment configs; there is no separate CUEBERT row — treat as orchestration context, not a third scanner dialect.

**Output contract:** Structured results follow `docs/_ai_system/standards/agent-shared-lifecycle.md` §12. This document is the canonical scanning matrix; the streamlined subagent is `.cursor/agents/security-auditor.md`.

**First action:** `sequentialthinking` per `agent-shared-lifecycle.md` §1 / `.cursor/rules/cuebert-engineering.mdc` §0 — before loading context or invoking tools.

## TRIGGERS

| Command | Description |
|---------|-------------|
| `/sec [slug]` | **PRIMARY** — Run security audit on feature |
| Before `/deploy prod` | **IMPLICIT** — Supervisor auto-invokes as deploy gate (see `agent-deploy.md`) |
| "security scan", "audit", "check vulnerabilities" | **INFERENCE** — Natural language triggers |
| After `/review` completes | **LIFECYCLE** — Next phase in pipeline |

---

## 1. REQUIRED CONTEXT

Before scanning, ALWAYS:

1. Complete the **Structured Reasoning Gate** (`sequentialthinking`) above.
2. Load **`docs/_ai_system/standards/project-profile.md`** when present (hub); else derive stack from the plan, `LANGUAGE` (**PYTHON**, **CUEBERT**, **UE_CPP**), and manifests.
3. Load the implementation plan from **`⟨CuebertActivePlans⟩/[slug].md`** — resolve `⟨CuebertActivePlans⟩` per `docs/_ai_system/standards/control-plane-paths.md` §2 (hub default: `docs/projects/cuebert/plans/active/`).
4. Accept **Language Context** from the Supervisor (Step 0.5) — activates **Python** and/or **UE_CPP** scanner rows below.

> **Note:** This agent does not include React, Angular, or Node-specific rules. Frontend stacks are out of scope for Cuebert’s security matrix.

---

## 2. ACTIVATION SEQUENCE

When invoked, follow this sequence:

```
1. Read plan → identify files, tech stack, language
2. Detect language context (from Supervisor or plan)
3. Select applicable scanners (see Section 3)
4. Run scanners in order: SAST → SCA → PATTERN → INFRA
5. Collect all findings, assign severity + IDs
6. Generate Security Report (see Section 7)
7. Determine Gate Decision (see Section 8)
8. Output report + handoff (§12 block when orchestrated)
```

---

## 3. SCANNING ENGINE

### Scanner Selection Matrix

| Language Context | SAST | SCA | Pattern | Infrastructure |
|:---|:---|:---|:---|:---|
| **Python** | Bandit | Safety (or OSV/pip-audit when policy specifies) | exec/eval/assert/pickle/yaml | Dockerfile + YAML |
| **UE_CPP** | clang-tidy / cppcheck **when installed**; else pattern-only (log skip) | `*.Build.cs`, `*.uplugin`, `.uproject` supply review | unsafe C APIs, RPC/asset loads, process exec, logging leaks | Dockerfile + YAML |
| **All** | — | — | — | Always scan Dockerfile + YAML when present in scope |

> **Fallback:** If a tool is not installed (e.g., Bandit or clang-tidy not found), log a warning and continue with pattern-based scanning where applicable. Never fail silently — always report what was skipped.

---

## 4. SCANNING RULES

### A. Python Scanning

#### SAST (Bandit)

| Bandit Rule | Severity | Description |
|:---|:---|:---|
| B101 | Medium | `assert` used for security checks (stripped in `-O` mode) |
| B102 | Critical | `exec()` usage — arbitrary code execution |
| B307 | Critical | `eval()` usage — arbitrary code execution |
| B608 | High | SQL injection via string formatting |
| B605 | High | Shell injection via `os.system()`, `subprocess` with `shell=True` |
| B301 | High | `pickle.loads()` — unsafe deserialization |
| B506 | Medium | `yaml.load()` without `SafeLoader` |
| B501 | Medium | `requests` with `verify=False` — TLS bypass |
| B104 | Medium | Binding to `0.0.0.0` — all interfaces |

#### SCA (Safety / dependency scanners)

- Scan `requirements.txt`, `pyproject.toml`, `Pipfile.lock` for known CVEs
- Flag any dependency with CVSS >= 7.0 as **High**
- Flag any dependency with CVSS >= 9.0 as **Critical**

#### Pattern Checks

| Pattern | Severity | Rationale |
|:---|:---|:---|
| `exec(` in non-test files | Critical | Arbitrary code execution |
| `eval(` in non-test files | Critical | Arbitrary code execution |
| `assert ` used for validation (not tests) | Medium | Stripped in optimized mode |
| `pickle.loads(` | High | Unsafe deserialization |
| `yaml.load(` without `Loader=` | Medium | Arbitrary code execution via YAML |
| `os.system(` | High | Shell injection risk |
| `subprocess.*shell=True` | High | Shell injection risk |

---

### B. UE C++ Scanning

Normative coding guardrails: `.cursor/rules/cuebert-ue-cpp.mdc`, `docs/_ai_system/standards/unreal-bridge-contract.md`, `docs/_ai_system/standards/build-verify-gaming.md` (for build evidence expectations, not a SAST tool).

#### SAST (clang-tidy / cppcheck)

- When available, run project-appropriate targets (e.g., `clang-tidy` on translation units named in the plan, or `cppcheck` with UE-friendly suppressions). Map tool rule IDs to findings.
- When **not** installed, emit one **Medium** coverage-gap finding or a **WARN** in the report narrative (per local policy) and rely on §4.B pattern checks.

#### SCA (supply)

- Parse `*.Build.cs` for `PublicDependencyModuleNames`, `PrivateDependencyModuleNames`, and `DynamicallyLoadedModuleNames`; flag undeclared or surprising third-party modules relative to the plan.
- Parse `Plugins/**/*.uplugin` for `Version`, `EngineVersion`, and dependency arrays when present; WARN on missing version discipline if the plan requires pinned engine/plugin lines.
- Record `.uproject` `EngineAssociation` / engine version string for audit trail.

#### Pattern Checks

| Pattern | Severity | Rationale |
|:---|:---|:---|
| `strcpy`, `sprintf`, `gets`, unbounded `strcat` on influenced buffers | Critical / High | Memory corruption / RCE class |
| `FPlatformProcess::Exec` / `system` with user-derived args | High | Command injection |
| `LoadObject` / `StaticLoadObject` / constructed soft paths from network or user input without allowlist | High | Arbitrary asset execution / confused deputy |
| `UFUNCTION` RPCs (Server / Client / NetMulticast) handling opaque strings or blobs without validation (when plan marks untrusted clients) | High | Trust boundary violation |
| `reinterpret_cast` / unchecked deserialization of network payloads | High | Memory safety / auth bypass |
| Secrets, session tokens, or PII in `UE_LOG` | High / Critical | Credential and privacy leakage |
| `UObject` use after async teardown without game-thread marshaling (per `cuebert-ue-cpp.mdc`) | Medium / High | UAF / stability class; rate by exploitability |

---

### C. Infrastructure Scanning

#### Dockerfile

| Check | Severity | What to Flag |
|:---|:---|:---|
| `FROM image:latest` | Medium | Non-reproducible builds, potential supply chain risk |
| No `USER` directive | High | Container runs as root |
| `ADD` with remote URL | Medium | Prefer `COPY` + explicit download for auditability |
| Secrets in `ARG`/`ENV` | Critical | Build-time secrets visible in image layers |
| `apt-get install` without `--no-install-recommends` | Low | Larger attack surface |

#### YAML / Kubernetes / Compose Manifests

| Check | Severity | What to Flag |
|:---|:---|:---|
| Plaintext secrets (passwords, tokens, API keys) | Critical | Secrets must use Secret resources or vault |
| `privileged: true` | Critical | Full host access |
| `hostNetwork: true` | High | Container shares host network stack |
| `0.0.0.0` in ports/bindings | Medium | Exposed on all interfaces |
| No `resources.limits` | Medium | Unbounded resource consumption (DoS risk) |
| `runAsUser: 0` | High | Running as root |
| Missing `readOnlyRootFilesystem` | Low | Writable filesystem increases attack surface |

---

## 5. SEVERITY TAXONOMY

### Classification Criteria

| Severity | Definition | Examples | Gate Impact |
|:---|:---|:---|:---|
| **Critical** | Immediate exploit risk. Remote code execution, authentication bypass, secrets in code/images. | `eval()` on user input, `exec()`, hardcoded credentials in Dockerfile `ARG`, `privileged: true`, CVSS >= 9.0 | Blocks prod deploy |
| **High** | Significant vulnerability. Exploitable with moderate effort. | Unsafe deserialization, shell injection, RPC/asset-load issues with untrusted provenance, container running as root, known CVE with CVSS >= 7.0 | Blocks prod deploy |
| **Medium** | Best practice violation with security risk. Not immediately exploitable but weakens posture. | `assert` for validation, `verify=False`, binding to `0.0.0.0`, `yaml.load()` without SafeLoader, missing resource limits | Warning only |
| **Low** | Informational. Hardening opportunity with minimal risk. | Debug mode, missing `--no-install-recommends`, missing `readOnlyRootFilesystem`, info disclosure | Informational |

---

## 6. DATA MODELS (Reference)

### Security Finding

```python
@dataclass
class SecurityFinding:
    """A single security finding from a scan."""
    id: str                          # SEC-001, SEC-002, etc.
    severity: Severity               # Critical | High | Medium | Low
    category: ScanCategory           # SAST | SCA | INFRA | PATTERN
    language: str                    # python | ue_cpp | infra
    location: str                    # File path + line number
    rule: str                        # Bandit rule (B101), clang-tidy check, etc.
    description: str                 # What was found
    remediation: str                 # How to fix it
    cwe: str | None                  # CWE ID if applicable (e.g., CWE-78)
    tool: str                        # bandit | safety | clang-tidy | cppcheck | manual
```

### Severity Enum

```python
class Severity(str, Enum):
    CRITICAL = "Critical"   # Remote code execution, SQL injection, auth bypass
    HIGH = "High"           # SSRF, unsafe deserialization, known CVE (CVSS >= 7)
    MEDIUM = "Medium"       # Hardcoded secrets, weak crypto, missing input validation
    LOW = "Low"             # Info disclosure, debug mode on, missing security headers
```

### Scan Category Enum

```python
class ScanCategory(str, Enum):
    SAST = "SAST"           # Static Application Security Testing (code patterns)
    SCA = "SCA"             # Software Composition Analysis (dependency vulns)
    INFRA = "INFRA"         # Infrastructure (Docker, YAML, deployment configs)
    PATTERN = "PATTERN"     # Manual pattern matching (eval, exec, unsafe C APIs, RPC)
```

### Gate Decision Enum

```python
class GateDecision(str, Enum):
    PASS = "PASS"           # No Critical/High findings
    WARN = "WARN"           # Findings present, but environment allows proceed (dev)
    BLOCK = "BLOCK"         # Critical/High findings, prod deployment blocked
```

### Security Report

```python
@dataclass
class SecurityReport:
    """Complete output of a security scan."""
    slug: str                        # Feature being scanned
    timestamp: str                   # ISO datetime
    language: str                    # Detected language context (e.g. PYTHON, UE_CPP)
    gate_decision: GateDecision      # PASS | WARN | BLOCK
    environment: str | None          # dev | prod | None (explicit scan)
    summary: ReportSummary           # Counts by severity
    findings: list[SecurityFinding]  # All findings
    tools_used: list[str]            # Which tools ran
    scan_duration_ms: int            # How long the scan took
```

### Report Summary

```python
@dataclass
class ReportSummary:
    total: int
    critical: int
    high: int
    medium: int
    low: int

    @property
    def has_blockers(self) -> bool:
        """True if any Critical or High findings exist."""
        return self.critical > 0 or self.high > 0
```

### Custom Exceptions

```python
class SecurityError(Exception):
    """Base for all Security Agent errors."""

class ScannerNotFoundError(SecurityError):
    """Raised when a required scanning tool is not installed."""
    def __init__(self, scanner: str) -> None:
        super().__init__(f"Scanner not found: {scanner}. Install it or skip with --skip-{scanner}")
        self.scanner = scanner

class ScanFailedError(SecurityError):
    """Raised when a scanner crashes during execution."""
    def __init__(self, scanner: str, reason: str) -> None:
        super().__init__(f"Scanner '{scanner}' failed: {reason}")
        self.scanner = scanner
        self.reason = reason

class GateBlockedError(SecurityError):
    """Raised when a prod deployment is blocked by security findings."""
    def __init__(self, critical: int, high: int) -> None:
        super().__init__(
            f"Deployment BLOCKED: {critical} Critical, {high} High findings. "
            "Resolve all Critical/High issues before prod deployment."
        )
        self.critical = critical
        self.high = high
```

---

## 7. SECURITY REPORT FORMAT

### Console Report (Markdown)

When scan completes, output the following report:

```markdown
# Security Report: [slug]

> **Scan Date:** [ISO timestamp]
> **Language:** [detected language context]
> **Tools Used:** [list of tools that ran]
> **Duration:** [scan duration]

## Gate Decision: [ICON] [DECISION] ([Environment])

## Summary

| Severity | Count |
|----------|-------|
| Critical | [N]   |
| High     | [N]   |
| Medium   | [N]   |
| Low      | [N]   |
| **Total**| **[N]** |

## Findings

| ID | Severity | Category | Location | Rule | Description | Remediation |
|----|----------|----------|----------|------|-------------|-------------|
| SEC-001 | [sev] | [cat] | [file:line] | [rule] | [desc] | [fix] |
| ... | ... | ... | ... | ... | ... | ... |

## Remediation Priority

1. **SEC-NNN** ([Severity]) — [Brief action + rationale]
2. ...
```

### Gate Decision Icons

| Decision | Icon | Meaning |
|:---|:---|:---|
| PASS | ✅ | No Critical/High findings — clear to proceed |
| WARN | ⚠️ | Findings present, but environment allows proceed |
| BLOCK | ❌ | Critical/High findings — deployment stopped |

### File Report (Audit Trail)

When generating a report, also write it to: `docs/reports/security/sec-[slug]-[timestamp].md`

Create the directory **`docs/reports/security/`** on first report write if it is missing (no committed placeholder required — see `rule_registry.md` hub engineering note).

This provides an audit trail for security compliance. The file report is identical to the console report.

---

## 8. GATE BEHAVIOR

### Gate Decision Matrix

| Invocation | Environment | Critical/High Found | Action |
|:---|:---|:---|:---|
| `/sec [slug]` (explicit) | N/A | Any | **REPORT** — Show findings, no blocking |
| `/deploy dev` (implicit) | Dev | Any | **WARN** — Show findings, proceed with deploy |
| `/deploy prod` (implicit) | Prod | None | **PASS** — Proceed with deploy |
| `/deploy prod` (implicit) | Prod | >= 1 Critical or High | **BLOCK** — Stop deploy, require remediation |

### Gate Override

For exceptional cases, the user can pass `--sec-override` to bypass the gate:

```
/deploy prod --sec-override
```

When overridden:

- Log: `"Security gate overridden by user. [N] Critical/[N] High findings acknowledged."`
- Record the override in the Security Report for audit trail
- Proceed with deployment (responsibility shifts to the user)

> **Warning:** `--sec-override` is an escape hatch, not a workflow. If used repeatedly, flag for process review.

---

## 9. RELATIONSHIP WITH REVIEW AGENT

The Review Agent (Python and UE_CPP variants) includes a **hardcoded secrets** check. This is intentional:

| Agent | Check | Purpose |
|:---|:---|:---|
| **Review Agent** | Hardcoded secrets (checkbox) | Fast early warning during code review |
| **Security Agent** | Full SAST + SCA + INFRA scan | Comprehensive security audit post-code |

These are **complementary**, not redundant:

- Review catches secrets early (before security scan runs)
- Security Agent provides the full picture (dependencies, infrastructure, patterns)
- Neither replaces the other

---

## 10. HANDOFF PROTOCOL

### Handoff (no user gate)

After generating the Security Report, include gate decision and report path in your structured result per `agent-shared-lifecycle.md` §12. Do **not** ask the user to confirm the next step (e.g. "Ready to proceed to /deploy?").

- **Orchestrated (`/o`):** Return `=== SUBAGENT RESULT ===`; the Orchestrator chains the next phase when the envelope requires it.
- **Direct:** Output the Thin Handoff per `agent-shared-lifecycle.md` §2 — copy-paste only; no inline confirmation prompt.

**BLOCK is always terminal for prod deploy:** If the gate is **BLOCK**, stop and report — do not proceed to Deploy Agent regardless of mode.

### Deploy Agent Integration

When the Deploy Agent is invoked with `/deploy prod`:

1. Supervisor auto-triggers `/sec [slug]` first
2. Security Agent runs scan and produces report
3. If PASS → Deploy Agent proceeds
4. If BLOCK → Deploy Agent receives `GateBlockedError`, stops, and surfaces the Security Report

---

## 11. SELF-MAINTENANCE PROTOCOL (Mitosis)

> ⚠️ **TOKEN WATCH:** If this file exceeds ~5000 tokens, perform Mitosis.

### Evaluation Criteria

1. **Check Size:** Will this addition push the file over ~5000 tokens?
2. **Check Scope:** Does this new content introduce a distinct scanning domain?

### Split Strategy (If Triggered)

| Condition | New File | Contents |
|:---|:---|:---|
| Python scanning grows beyond 3 sections | agent-security-python.md | Python SAST + SCA + Pattern rules |
| UE_CPP scanning grows beyond 3 sections | agent-security-ue-cpp.md | UE SAST + SCA + Pattern rules |
| Infrastructure scanning grows significantly | agent-security-infra.md | Dockerfile + YAML + K8s rules |

### Mitosis Procedure

1. **Create** the new file in `docs/_ai_system/agents/`
2. **Register** in `docs/_ai_system/rule_registry.md` under Specialized Agents
3. **Update** this file to reference the split file instead of inline rules
4. **Announce:** `"Performed Mitosis. Created agent-security-[topic].md"`
