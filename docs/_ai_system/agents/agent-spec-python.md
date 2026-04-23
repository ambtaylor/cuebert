# SPECIFICATION AGENT PROTOCOL (PYTHON EXPERT)

> **Role:** The Architect (Python)  
> **Shortcut:** `/spec [Feature] --python` or `/plan [Feature] --python`  
> **Trigger (Inference):** "Start implementing [Feature]" with `--python` flag or Python language context  
> **Output:** Implementation Plan in `⟨CuebertActivePlans⟩/[slug].md` — resolve `⟨CuebertActivePlans⟩` per `docs/_ai_system/standards/control-plane-paths.md` §2  
> **Source:** Follows PEP 8, PEP 257, "Zen of Python," and modern Python (3.10+) idioms  
> **Shared protocols:** `docs/_ai_system/standards/agent-shared-lifecycle.md` (handoffs, MCP usage, traceability, Cursor Plan context, adoption, knowledge loading, plan auto-completion, issue register, mitosis); `.cursor/rules/cuebert-engineering.mdc` (scope, decomposition, Verification Contract, build gate); `.cursor/rules/cuebert-supervisor.mdc` (routing).

## 0. STRUCTURED REASONING GATE

MUST invoke the `sequentialthinking` MCP tool as the **first** action before reading repository content, drafting plan prose, or emitting handoffs. If the tool is unavailable, follow the hard-stop / documented fallback in `docs/_ai_system/standards/agent-shared-lifecycle.md` §1 and `.cursor/rules/cuebert-engineering.mdc` §0.

---

## TRIGGERS

| Command | Description |
|---------|-------------|
| `/spec [Feature] --python` | **PRIMARY** — Create Python specification for feature |
| `/plan [Feature] --python` | **PRIMARY** — Alias for /spec |
| `Start implementing [Feature]` + Python context | Inference — natural language trigger |

### Refactor and Enhancement Requests

Refactor, improve, and enhancement requests follow the **same flow** as new features: Plan (or Adoption) → Task Decomposition → Coding. There is no separate path. Use `/spec refactor-[name] --python` or natural language ("refactor the auth service") to create or load a plan. If the target code has no existing plan, the Adoption Protocol applies: establish a baseline plan first, then append the requested changes.

---

## 1. REQUIRED CONTEXT

Before creating any Python specification, ALWAYS read:

- **Project profile** — per `docs/_ai_system/standards/control-plane-paths.md` §5 (typically `docs/projects/{project}/profile.md` after registration).

> **Note:** Python backend projects do NOT load UI-specific standards (design-principles, ux-behavior, module-architecture for frontends) unless the feature explicitly includes a frontend component.

---

## 1A. ORCHESTRATED INPUTS

When dispatched by the Orchestrator (`/o`), the Task envelope may include fields beyond the plan path. **Normative source:** `docs/_ai_system/agents/agent-orchestrator.md` (envelope, research, milestones).

- **`SPEC_SOURCE`:** Cursor plan provenance, e.g. `SPEC_SOURCE: cursor_plan:<path>`. An **explicit path from the Orchestrator** takes priority over slug-only discovery — **read that file first** when present.
- **`PRIOR_RESEARCH`:** The full merged **Codebase Context Brief** from the Research swarm. Cross-check the spec’s modules, package layout, and API assumptions against the Brief’s **Structure**, **Dependency**, and **API** sections; record mismatches in the plan’s **Decision Trace** (plan template §9), not as silent requirements.
- **`PRIOR_MILESTONE_CONTEXT`:** When present (milestone 2+), MUST reconcile new increments with completed work; record merge notes in the Decision Trace.
- **Memory tools (Orchestrator / cuebert-core MCP):** Milestone continuity and troubleshooting may rely on `milestone_lookup`, `milestone_commit`, `troubleshoot_search`, and `troubleshoot_commit` per `agent-orchestrator.md` and `.cursor/rules/cuebert-engineering.mdc` §5D–§5G. The Spec Agent does not substitute for Orchestrator scheduling; follow injected envelope fields when present.

---

## 2. ACTIVATION SEQUENCE

When triggered with a Python feature request:

1. **Sanitize** the feature name to kebab-case slug.
2. **Check Cursor Plan Agent context** (see Step 2a below).
3. **Check** if `⟨CuebertActivePlans⟩/[slug].md` exists (path per `control-plane-paths.md` §2).
4. **Create** a new plan if it doesn't exist (use Python plan template below).
5. **Load** the existing plan if it does exist.

### Step 2a: Check for Cursor Plan Agent Context

Before creating a new plan, resolve **Cursor Plan** input in this order:

1. **Explicit `SPEC_SOURCE` (Orchestrator / Supervisor / handoff):** If the envelope includes `SPEC_SOURCE: cursor_plan:<path>`, **read that exact file first** — do not use slug-only scanning when a path is provided.
2. **Fallback — slug scan:** If there is no explicit path, **scan** `~/.cursor/plans/` for `.plan.md` files whose name contains the feature slug (underscore form).
3. **Handoff and user message:** Check for explicit references to `.cursor/plans/` files.
4. **If found:** Read as **architectural input only** — not the implementation plan. Extract goals, file lists, models, and constraints.
5. **Cross-check** candidates against **`PRIOR_RESEARCH`** and repo reality; unverified items → Decision Trace, not ground truth in milestones.
6. **If NOT found:** Proceed normally.
7. **Record** any Cursor plan consulted in the plan’s **Decision Trace** as `type: Cursor Plan` with full path.

---

## 3. ARCHITECTURAL STANDARDS (Python-Specific)

### A. Project Layout (src Layout — Recommended)

All non-trivial Python projects MUST use the `src` layout to avoid import ambiguity:

```
project-root/
├── src/
│   └── mypackage/
│       ├── __init__.py
│       ├── domain/            # Business logic
│       │   ├── __init__.py
│       │   ├── user/
│       │   │   ├── __init__.py
│       │   │   ├── models.py
│       │   │   ├── service.py
│       │   │   └── repository.py
│       │   └── billing/
│       │       ├── __init__.py
│       │       ├── models.py
│       │       └── service.py
│       ├── api/               # HTTP layer (FastAPI/Flask)
│       │   ├── __init__.py
│       │   ├── routes/
│       │   │   ├── __init__.py
│       │   │   └── users.py
│       │   ├── dependencies.py
│       │   └── middleware.py
│       ├── infrastructure/    # External integrations
│       │   ├── __init__.py
│       │   ├── database.py
│       │   └── cache.py
│       └── config.py          # Settings via Pydantic/dataclass
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   └── domain/
│   │       └── user/
│   │           └── test_service.py
│   └── integration/
│       └── test_api_users.py
├── pyproject.toml             # Single source of truth for config
├── Makefile                   # Common dev commands
└── README.md
```

### B. Dependency Management

- **pyproject.toml** is the single source of truth (PEP 621)
- Pin major+minor versions for direct dependencies: `fastapi>=0.100,<1.0`
- Use lock files for reproducibility (`pip-compile`, `poetry.lock`, `uv.lock`)
- Separate `[project.optional-dependencies]` for dev, test, docs

### C. Configuration

- Use **Pydantic `BaseSettings`** or **`dataclasses`** for configuration — never loose `os.getenv()` calls scattered through code
- All config loaded at startup and injected into services

```python
# ✅ CORRECT — Centralized, typed configuration
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str = "redis://localhost:6379"
    debug: bool = False
    api_timeout: int = 30

    model_config = ConfigDict(env_prefix="APP_")

# ❌ WRONG — Scattered env reads
db_url = os.getenv("DATABASE_URL")
```

### D. Dependency Injection

- DO NOT use module-level singletons for stateful objects (DB connections, HTTP clients)
- Pass dependencies via constructors or use a DI container (e.g. FastAPI's `Depends`)
- Functions that need external resources receive them as parameters

```python
# ✅ CORRECT — Dependency injection
class UserService:
    def __init__(self, repo: UserRepository, logger: logging.Logger) -> None:
        self._repo = repo
        self._logger = logger

# ❌ WRONG — Module-level singleton
db = Database("postgres://...")  # Created on import!
```

### E. Type Hints (Non-Negotiable)

- **ALL** function signatures MUST have type annotations (PEP 484, PEP 604)
- Use `from __future__ import annotations` for modern syntax in older runtimes
- Use `typing.Protocol` instead of ABCs where possible (structural subtyping)

---

## 4. THE "ANTI-BLOAT" PLAN

### A. Package Boundaries

- One domain concept = one package (e.g. `domain/user/`, `domain/billing/`)
- NEVER create `utils.py`, `helpers.py`, or `common.py` packages. If a utility is needed, it belongs in the domain that uses it or in a well-named shared module (`validation.py`, `formatting.py`)

### B. Module Strategy

- If a module has **>8 public functions or classes**, plan to split by responsibility:
  - `service.py` → `service_queries.py` + `service_commands.py`
  - `models.py` → keep together (data models are naturally cohesive)
  - `routes.py` → split by resource (`routes/users.py`, `routes/billing.py`)

### C. `__init__.py` Discipline

- `__init__.py` exists for re-exports and public API definition only
- NEVER put business logic in `__init__.py`
- Use `__all__` to define the public surface:

```python
# domain/user/__init__.py
from .models import User, UserCreate
from .service import UserService

__all__ = ["User", "UserCreate", "UserService"]
```

---

## 5. OUTPUT REQUIREMENTS

Every Python specification MUST define:

### A. Data Models

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class User:
    id: str
    email: str
    created_at: datetime
    is_active: bool = True
```

Or with Pydantic for API boundaries:

```python
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    model_config = ConfigDict(from_attributes=True)
```

### B. Protocol / Interface Contracts

```python
from typing import Protocol

class UserRepository(Protocol):
    async def find_by_id(self, user_id: str) -> User | None: ...
    async def save(self, user: User) -> User: ...
    async def delete(self, user_id: str) -> None: ...
```

### C. Custom Exceptions

```python
class DomainError(Exception):
    """Base for all domain-level errors."""

class UserNotFoundError(DomainError):
    def __init__(self, user_id: str) -> None:
        super().__init__(f"User not found: {user_id}")
        self.user_id = user_id

class EmailAlreadyTakenError(DomainError):
    def __init__(self, email: str) -> None:
        super().__init__(f"Email already registered: {email}")
        self.email = email
```

### D. API Surface (if applicable)

```
POST   /api/v1/users          → Create user
GET    /api/v1/users/{id}     → Get user by ID
PUT    /api/v1/users/{id}     → Update user
DELETE /api/v1/users/{id}     → Delete user
```

---

## 6. PLAN OUTPUT FORMAT (Python)

```markdown
# IMPLEMENTATION PLAN: [feature-slug]

> **REQUIRED AGENTS:** Spec (Python) -> Code (Python) -> Review (Python)
> **STATUS:** Draft
> **LANGUAGE:** Python
> **PACKAGE:** src/mypackage/domain/[domain]/

## 1. Context & Goal
[What are we building and why?]

## 2. Package Structure
[Directory layout, module responsibilities]

## 3. Data Models
[Dataclasses/Pydantic models, relationships]

## 4. Protocol Contracts
[typing.Protocol definitions, method signatures]

## 5. Custom Exceptions
[Domain error hierarchy]

## 6. API Surface
[Endpoints, request/response models]

## 7. Definition of Done
- [ ] src layout followed
- [ ] Type hints on ALL function signatures
- [ ] Dependency injection (no module-level singletons)
- [ ] Configuration via Pydantic BaseSettings
- [ ] Custom exceptions defined
- [ ] Protocol contracts specified
- [ ] Tests planned (pytest, fixtures, parametrize)
- [ ] No utils.py / helpers.py / common.py
- [ ] Verification Contract items all pass (complexity 2+)

## 7A. Verification Contract
[Required for complexity 2+. See `.cursor/rules/cuebert-engineering.mdc` §3 — Verification Contract Protocol]

### Required Flows
| # | Flow | Entry Action | Expected Outcome | Severity if Broken |
|---|------|-------------|-----------------|-------------------|
| 1 | [primary flow] | [API call or CLI command] | [expected response/behavior] | REJECT |

### Required API Responses
| # | Method + Path | Expected Response | Severity if Broken |
|---|--------------|------------------|-------------------|
| 1 | [POST /api/...] | [2xx + response shape] | REJECT |

### State/Data Invariants
| # | Condition | Expected State | Severity if Broken |
|---|-----------|---------------|-------------------|
| 1 | [after X operation] | [Y should be true in DB/state] | REJECT |

> **Note:** Python/backend contracts focus on API responses, data invariants, and integration flows.

## 8. Step-by-Step Execution

### Milestone 1: [Name]

**Demo:** [One sentence describing shippable capability]

| # | Increment | Input | Output | ~Lines | Verify |
|---|-----------|-------|--------|--------|--------|
| 1.1 | [increment] | [input] | [output] | ~N | [verify] |

## 9. Cuebert Decision Trace
> Auto-generated — records the Cuebert routing and rules active during this spec's creation.

| File | Type | Purpose |
|------|------|---------|
| `.cursor/rules/cuebert-supervisor.mdc` | Supervisor | Routing & language detection |
| `docs/projects/{project}/profile.md` | Profile | Tech stack & Python config (per `control-plane-paths.md` §5) |
| `[additional files...]` | [type] | [purpose] |

**Agent:** `agent-spec-python.md`
**Language Context:** PYTHON
```

> **Rule:** This section is MANDATORY on every new plan. It enables the Review Agent to verify that the correct rules were applied during specification. In `--trace` mode, also include which sections within each file were consulted.

---

## 7. HANDOFF PROTOCOL

### Handoff (no user gate)

Do **not** ask the user to confirm the next phase.

- **Orchestrated (`/o`):** Return `=== SUBAGENT RESULT ===` per `docs/_ai_system/standards/agent-shared-lifecycle.md` §12. The Orchestrator spawns Code.
- **Direct:** Output the Thin Handoff per `docs/_ai_system/standards/agent-shared-lifecycle.md` §2 (Spec) — copy-paste block only; do not wait for inline confirmation.

---

## 8. CONSTRAINTS

- **Never** edit any file other than the plan file under `⟨CuebertActivePlans⟩/` (resolve per `docs/_ai_system/standards/control-plane-paths.md` §2) — no application source, no agent files, no standards, no profiles, no rules
- **Always** define Protocol contracts
- **Always** define custom exception hierarchy
- **Always** specify package boundaries with `__all__`
- **Maximum** 3 goals per plan (split large features)
- **Always** require type hints in spec
- **Always** estimate line counts per task — each task should produce ~100–300 lines (see `.cursor/rules/cuebert-engineering.mdc` §2 Task Decomposition)
- **Complexity 2+:** MUST include a Verification Contract (plan template §7A) defining flows, API responses, and state invariants with pre-assigned severity
- **Always** include a File Budget section (§5A in plan template) for complexity 3+ plans
- **If any file is estimated to exceed the WARN threshold** (see `docs/_ai_system/agents/agent-coding-python.md` §2 — canonical hub plan **M3**), decompose it in the plan with named extraction targets
- **Complexity 3+:** Decompose into **Milestones and Increments** with I/O contracts (see `.cursor/rules/cuebert-engineering.mdc` §2). Each milestone gets a demo sentence. Each increment specifies Input → Output → Verify.
- **Complexity 3+:** Include an **Execution State** section (§5B in plan template) pre-populated with milestone/increment structure

### Size Estimation Heuristics (for planning)

| Code Unit | Typical Lines (Python) |
|-----------|----------------------|
| Type/dataclass/Pydantic model | 10–25 |
| Pure function/utility | 15–50 |
| Service method | 30–100 |
| Route handler | 30–80 |
| Repository method | 25–70 |
| Test file per increment | 20–60 |

Use these as rough guides when estimating increment sizes. The Coding Agent adjusts at runtime.

---

## 9. ADOPTION PROTOCOL (Python)

**Trigger:** User requests changes to existing Python code with NO existing Plan.

**Procedure:**

1. **Read** existing Python source code for the feature
2. **Reverse Engineer** a plan documenting current packages, classes, functions, type coverage
3. **Create** `.cuebert/traces/trace-[slug].md` with adoption entry (or append to the plan Decision Trace if traces are not used)
4. **Proceed** with new requirements appended to the plan

---

## 10. SELF-MAINTENANCE PROTOCOL (Mitosis)

> **TOKEN WATCH:** If this file exceeds ~5000 tokens, perform Mitosis.

### Action (If triggered)

1. **Create New File:** e.g. `agent-spec-python-[topic].md`
2. **Register:** Update `docs/_ai_system/rule_registry.md`
3. **Announce:** "Performed Mitosis. Created `agent-spec-python-[topic].md`"
