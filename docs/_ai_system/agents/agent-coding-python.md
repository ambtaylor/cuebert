# CODING AGENT PROTOCOL (PYTHON EXPERT)

> **Role:** The Builder (Python)  
> **Shortcut:** `/code [slug] --python` or `/build [slug] --python`  
> **Trigger (Inference):** After Python Spec Agent completes (auto or manual)  
> **Input:** Implementation plan from `⟨CuebertActivePlans⟩/[slug].md` — **`⟨CuebertActivePlans⟩` resolves to `docs/projects/cuebert/plans/active/`** for hub Cuebert work; for application projects in a multi-root workspace, use `<hubRoot>/docs/projects/{project}/plans/active/` per `docs/_ai_system/standards/control-plane-paths.md` §2  
> **Style:** Pythonic, explicit, type-safe, and clean  
> **Shared protocols:** `docs/_ai_system/standards/agent-shared-lifecycle.md` (handoffs, MCP usage, traceability, knowledge loading, plan auto-completion, issue register, mitosis); `.cursor/rules/cuebert-engineering.mdc` (scope, decomposition, Verification Contract, build gate, memory tools); `.cursor/rules/cuebert-supervisor.mdc` (routing).

## 0. STRUCTURED REASONING GATE

MUST invoke the `sequentialthinking` MCP tool as the **first** action before reading repository content, writing code, or emitting handoffs. If the tool is unavailable, follow the hard-stop / documented fallback in `docs/_ai_system/standards/agent-shared-lifecycle.md` §1 and `.cursor/rules/cuebert-engineering.mdc` §0.

---

## TRIGGERS

| Command | Description |
|---------|-------------|
| `/code [slug] --python` | **PRIMARY** — Start Python coding from plan |
| `/build [slug] --python` | **PRIMARY** — Alias for /code |
| After Python Spec Agent completes | Inference — Orchestrator auto-chains when `/o`; Direct mode uses Thin Handoff (`agent-shared-lifecycle.md` §2) |

---

## 1. REQUIRED CONTEXT

Before coding, ALWAYS read:

- The implementation plan from `⟨CuebertActivePlans⟩/[slug].md` (hub: `docs/projects/cuebert/plans/active/[slug].md`)
- **Project profile** — per `docs/_ai_system/standards/control-plane-paths.md` §5 (typically `docs/projects/{project}/profile.md` after registration)

> **Note:** Python agents do NOT load UI-specific standards unless the plan explicitly includes a frontend component.

---

## 1A. ISSUE REGISTER COMPLIANCE (DURING IMPLEMENTATION)

When encountering a WARN or INFO during implementation that is **not blocking the current task**, do NOT only mention it in chat — **append a row to the active plan’s Issue Register** (see `docs/projects/cuebert/plans/active/` plan templates and `agent-shared-lifecycle.md` §8). This keeps deferred issues visible for final review.

Format: Phase Found, Severity, Description, Resolution Target, Status (e.g. OPEN).

---

## 1B. KNOWLEDGE LOADING PROTOCOL

### When to load

During the REQUIRED CONTEXT step (Section 1), ALSO check:

1. Does `docs/_ai_system/knowledge/` or `docs/projects/{active-project}/knowledge/` exist?
2. Does either tree contain `api-map-*.md` (or project-specific integration docs)?

If YES:

1. Read the **Aliases** line from each API map header (if present).
2. If the user’s request mentions any alias (case-insensitive), load that material into context.
3. Use it to align endpoint paths, HTTP methods, payload shapes, response handling, and auth patterns **as documented there** — do not invent contract details.

### Matching rules

- Match is case-insensitive on names and aliases.
- If multiple maps match, load all of them.
- If no map matches but the user references an external API, note the gap in the plan’s Decision Trace and follow the Verification Contract for how strict the integration must be.

### Example

User says: “Add a client for the Example Service API.”

1. Agent scans project + hub knowledge → finds `api-map-example.md` (Aliases: Example, Example Service).
2. Agent loads the documented domains.
3. Agent implements calls using the documented endpoints, payloads, and errors from the map.

---

## 2. FILE SIZE THRESHOLDS (ENFORCED)

### Tiered thresholds

> These thresholds support an AI-first pipeline where agents implement, review, and QA. Files in the ~400–500 line range fit typical single-pass comprehension.

| File Type | Target | WARN | REJECT | HARD STOP |
|-----------|--------|------|--------|-----------|
| Service / domain module (.py) | 300–400 | 500 | 700 | 1000 |
| Routes / API handlers (.py) | 150–250 | 400 | 600 | 800 |
| Repository / adapters (.py) | 100–200 | 350 | 500 | 700 |
| Models & schemas (.py) | 60–120 | 200 | 350 | 500 |
| Package `__init__.py` / thin glue | 50–100 | 150 | 250 | 400 |

| Level | Meaning | Action |
|-------|---------|--------|
| **Target** | Ideal range | Aim here |
| **WARN** | Approaching limit | Evaluate extraction points; log warning in task log |
| **REJECT** | Must decompose OR provide written justification | Sub-decompose before continuing; Review Agent rejects without justification |
| **HARD STOP** | Unconditional rejection | Must split before writing more code; no justification accepted |

### Class size guideline

- **Target:** 150–300 lines per class
- A class with >20 methods is suspicious — look for a second responsibility
- Prefer composition over deep inheritance (max ~2 levels)

### Extraction playbook (when approaching WARN)

```
Does the service mix reads and writes?
  → Split into service_queries.py + service_commands.py

Does a module mix HTTP handling with business logic?
  → Separate routes.py from service.py

Are ORM models mixed with Pydantic schemas?
  → Separate models.py from schemas.py

Are there >5 route handlers in one file?
  → Split by resource: routes/users.py, routes/billing.py

Is validation logic mixed with business logic?
  → Extract to validators.py
```

### Per-task size gate

Before writing code for any task, estimate output lines. If estimated output exceeds ~400 lines (WARN tier for primary domain modules), sub-decompose first. After completing a task, record actual line counts in the plan task log (`.cursor/rules/cuebert-engineering.mdc` §5).

---

## 2A. EXECUTION MODEL

Read the plan’s **Complexity Assessment** and follow `.cursor/rules/cuebert-engineering.mdc`:

- **Complexity 0–2:** Execute tasks sequentially using the test-first loop (`cuebert-engineering.mdc` §3)
- **Complexity 3+:** Use the **Milestone & Increment model** with **Milestone Isolation** (`cuebert-engineering.mdc` §2):
  1. **One milestone per chat session** — do NOT implement multiple milestones in a single chat. Produce a handoff after each milestone.
  2. Read the plan’s milestone/increment decomposition and I/O contracts
  3. Execute increments one at a time: read I/O contract → write test → implement (~30–100 lines) → verify → log
  4. After all increments in a milestone: run milestone-level integration check
  5. Update the plan’s **Execution State** after each increment
  6. If an increment grows beyond ~100 lines, split into sub-increments before continuing
  7. **Context budget** — if the milestone exceeds ~800 lines of new code, split into sub-milestones (`cuebert-engineering.mdc` §3)
- **Complexity 4+:** Read the Bailout Plan before starting; test-first is mandatory for every testable increment
- **Complexity 6:** Decompose into phases; checkpoint with user after each phase

---

## 3. CRITICAL CODING RULES (THE PYTHON IDIOMS)

### A. Type hints everywhere (non-negotiable)

Every function, method, and class attribute MUST have type annotations.

```python
# ✅ CORRECT — Fully typed
def find_user_by_email(
    email: str,
    *,
    include_inactive: bool = False,
) -> User | None:
    ...

# ❌ WRONG — Untyped
def find_user_by_email(email, include_inactive=False):
    ...
```

Use modern syntax (Python 3.10+):

```python
# ✅ Prefer
def process(items: list[str]) -> dict[str, int] | None: ...

# ❌ Avoid (old style)
from typing import List, Dict, Optional
def process(items: List[str]) -> Optional[Dict[str, int]]: ...
```

### B. Exception handling (the discipline)

```python
# ❌ NEVER catch bare Exception (hides bugs)
try:
    do_something()
except Exception:
    pass

# ❌ NEVER silently swallow errors
try:
    do_something()
except ValueError:
    pass  # Why? What happened?

# ✅ ALWAYS catch specific exceptions with context
try:
    user = await repo.find_by_id(user_id)
except DatabaseConnectionError as exc:
    logger.error("Failed to fetch user %s: %s", user_id, exc)
    raise ServiceUnavailableError(f"Database unreachable while fetching user {user_id}") from exc

# ✅ Use 'from' to chain exceptions (preserves traceback)
try:
    data = json.loads(raw)
except json.JSONDecodeError as exc:
    raise ValidationError(f"Invalid JSON payload: {raw[:100]}") from exc

# ✅ Use custom exception hierarchies from the spec
class UserNotFoundError(DomainError): ...
class EmailAlreadyTakenError(DomainError): ...
```

### C. Logging (not print statements)

```python
# ✅ CORRECT — Structured logging
import logging

logger = logging.getLogger(__name__)

logger.info("User created", extra={"user_id": user.id, "email": user.email})
logger.error("Failed to process payment", extra={"order_id": order_id}, exc_info=True)

# ❌ WRONG — Print statements in production code
print(f"User created: {user.id}")
print(f"Error: {e}")
```

### D. Imports (the order matters)

Follow isort / PEP 8 grouping:

```python
# 1. Standard library
import logging
from datetime import datetime, timezone
from pathlib import Path

# 2. Third-party
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

# 3. Local / project
from mypackage.domain.user.models import User
from mypackage.domain.user.service import UserService
```

Rules:

- **Prefer explicit imports** over star imports: `from module import X, Y` not `from module import *`
- **Avoid circular imports** — if two modules import each other, one has the wrong responsibility
- **TYPE_CHECKING guard** for import-only-for-types to break cycles:

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mypackage.domain.billing import BillingService
```

### E. Async discipline (when using async/await)

```python
# ✅ CORRECT — Async all the way down
async def get_user_with_orders(user_id: str) -> UserWithOrders:
    user, orders = await asyncio.gather(
        user_repo.find_by_id(user_id),
        order_repo.find_by_user(user_id),
    )
    return UserWithOrders(user=user, orders=orders)

# ❌ WRONG — Blocking call inside async function
async def get_user(user_id: str) -> User:
    return requests.get(f"/users/{user_id}")  # Blocks the event loop!

# ✅ Use context managers for resources
async with aiohttp.ClientSession() as session:
    async with session.get(url) as response:
        data = await response.json()
```

Rules:

- NEVER call synchronous I/O (`requests`, `open()`, `time.sleep()`, …) inside an async function without offload
- Use `asyncio.gather()` for concurrent I/O when tasks are independent
- Use `async with` for resources that need cleanup (DB connections, HTTP sessions)

### F. Context managers for resources

```python
# ✅ CORRECT — Context manager for resource cleanup
with open(path, "r") as f:
    content = f.read()

# ✅ Custom context manager for domain resources
from contextlib import asynccontextmanager

@asynccontextmanager
async def database_transaction(db: Database):
    tx = await db.begin()
    try:
        yield tx
        await tx.commit()
    except Exception:
        await tx.rollback()
        raise
```

### G. Dataclasses and Pydantic (know the difference)

| Use Case | Tool | Why |
|----------|------|-----|
| Internal domain models | `dataclass` or `attrs` | Lightweight, no validation overhead |
| API request/response | Pydantic `BaseModel` | Validation, serialization |
| Configuration | Pydantic `BaseSettings` | Env var loading, type coercion |
| Simple value objects | `NamedTuple` or `dataclass(frozen=True)` | Immutable, hashable |

```python
# Internal domain — dataclass
@dataclass
class User:
    id: str
    email: str
    is_active: bool = True

# API boundary — Pydantic
class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=100)
```

### H. No mutable default arguments (critical)

```python
# ❌ DANGEROUS — Shared mutable default
def add_item(item: str, items: list[str] = []) -> list[str]:
    items.append(item)  # Mutates the DEFAULT object!
    return items

# ✅ CORRECT — Use None sentinel
def add_item(item: str, items: list[str] | None = None) -> list[str]:
    if items is None:
        items = []
    items.append(item)
    return items
```

### I. String formatting

```python
# ✅ Prefer f-strings for readability
message = f"User {user.name} ({user.email}) created at {user.created_at:%Y-%m-%d}"

# ✅ Use % formatting ONLY in logging (lazy evaluation)
logger.info("User %s created", user.id)

# ❌ Avoid .format() and + concatenation for complex strings
message = "User {} created".format(user.id)
message = "User " + user.id + " created"
```

### J. FastAPI router pattern (when using FastAPI)

All HTTP routes SHOULD be defined on `APIRouter` instances in dedicated route modules. The application entry point (`main.py` / `app.py`) SHOULD compose routers rather than grow unbounded inline routes.

```python
# ✅ CORRECT — Router in dedicated module
# src/mypackage/api/routes/users.py
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/users", tags=["users"])

@router.get("/{user_id}")
async def get_user(user_id: str) -> UserResponse:
    ...

# src/mypackage/api/app.py — composition only
from fastapi import FastAPI
from mypackage.api.routes import users, billing

app = FastAPI(title="My Service")
app.include_router(users.router)
app.include_router(billing.router)

# ❌ WRONG — Many routes inlined in main without modular routers
app = FastAPI()

@app.get("/users/{user_id}")  # Avoid unbounded growth here
async def get_user(user_id: str):
    ...
```

**Router naming conventions (REST):**

- File: `routes/users.py` → Variable: `router = APIRouter(...)`
- Prefix: `/api/v1/{resource}` — versioned (`v1`, `v2`), **plural** resource nouns where applicable
- Path segments: **kebab-case** (e.g. `/service-requests`, not `/serviceRequests`)
- No verbs in paths — prefer HTTP methods (`POST /users`, not `/createUser`)
- Sub-resources: keep nesting shallow (`/users/{id}/orders`, avoid deep trees)
- Tags: e.g. `["users"]` for OpenAPI grouping

### K. FastAPI dependency injection (when using FastAPI)

Use `Annotated[T, Depends(provider)]` for injected dependencies. Avoid importing and calling stateful services directly in route handlers.

```python
from typing import Annotated
from fastapi import Depends

# Define dependency providers
async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with async_session_maker() as session:
        yield session

async def get_user_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserService:
    return UserService(session=session)

# Use in routes with Annotated
@router.get("/{user_id}")
async def get_user(
    user_id: str,
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    return await service.find_by_id(user_id)

# ❌ WRONG — Direct import, no DI
from mypackage.services import user_service  # Module-level singleton!

@router.get("/{user_id}")
async def get_user(user_id: str):
    return user_service.find_by_id(user_id)  # Untestable!
```

**Reusable DI aliases** (put in `dependencies.py`):

```python
# src/mypackage/api/dependencies.py
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
```

### L. Pydantic v2 patterns (when using Pydantic)

All Pydantic models MUST use v2 conventions. Separate models by purpose.

```python
from pydantic import BaseModel, ConfigDict, Field, EmailStr

# ✅ Response model — uses ConfigDict for ORM mode
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, strict=True)

    id: str
    email: str
    name: str
    is_active: bool

# ✅ Create model — validation on input
class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8)

# ✅ Update model — all fields optional
class UserUpdate(BaseModel):
    email: EmailStr | None = None
    name: str | None = Field(default=None, min_length=2, max_length=100)

# ❌ WRONG — Pydantic v1 style
class User(BaseModel):
    class Config:          # v1 pattern!
        orm_mode = True    # Renamed to from_attributes in v2

# ❌ WRONG — One model for everything (leaks secrets to response)
class User(BaseModel):
    id: str | None = None
    email: str
    password: str | None = None  # Exposes password in response!
```

**Model separation rules:**

| Suffix | Purpose | Required |
|--------|---------|----------|
| `Create` | Input for POST | All required fields, validation rules |
| `Update` | Input for PUT/PATCH | All fields optional (partial update) |
| `Response` | Output for GET/list | `ConfigDict(from_attributes=True)`, no secrets |
| `Filter` | Query parameters | Optional fields with defaults |

### M. Standard JSON response envelope (when exposing HTTP APIs)

When the service uses a shared JSON envelope, keep success and error shapes consistent.

```python
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")

class ResponseMeta(BaseModel):
    """Metadata for paginated or contextual responses."""
    model_config = ConfigDict(strict=True)

    request_id: str | None = None
    page: int | None = None
    page_size: int | None = None
    total_count: int | None = None

class ApiResponse(BaseModel, Generic[T]):
    """Standard JSON envelope: {"data": ..., "meta": ...}"""
    data: T
    meta: ResponseMeta = ResponseMeta()

class ApiErrorDetail(BaseModel):
    code: str          # SCREAMING_SNAKE_CASE (e.g. RESOURCE_NOT_FOUND)
    message: str
    detail: str | None = None
    field: str | None = None

class ApiErrorResponse(BaseModel):
    """Standard error envelope."""
    errors: list[ApiErrorDetail]
    meta: ResponseMeta = ResponseMeta()
```

**Usage in routes:**

```python
@router.get("/{user_id}", response_model=ApiResponse[UserResponse])
async def get_user(
    user_id: str,
    service: Annotated[UserService, Depends(get_user_service)],
) -> ApiResponse[UserResponse]:
    user = await service.find_by_id(user_id)
    return ApiResponse(data=UserResponse.model_validate(user))

@router.get("/", response_model=ApiResponse[list[UserResponse]])
async def list_users(
    service: Annotated[UserService, Depends(get_user_service)],
    page: int = 1,
    page_size: int = 20,
) -> ApiResponse[list[UserResponse]]:
    users, total = await service.list_paginated(page=page, page_size=page_size)
    return ApiResponse(
        data=[UserResponse.model_validate(u) for u in users],
        meta=ResponseMeta(page=page, page_size=page_size, total_count=total),
    )
```

**Typical HTTP status mapping (REST):**

| Operation | Success | Client error | Server error |
|-----------|---------|--------------|--------------|
| GET (single) | 200 | 404 | 500 |
| GET (list) | 200 | 400 (bad filter) | 500 |
| POST (create) | 201 | 400, 409, 422 | 500 |
| PUT (replace) | 200 | 400, 404, 422 | 500 |
| PATCH (partial) | 200 | 400, 404, 422 | 500 |
| DELETE | 204 | 404 | 500 |

**Global exception handler** — register domain → HTTP mapping appropriate to your framework:

```python
async def domain_exception_handler(request: Request, exc: DomainError) -> JSONResponse:
    status_map = {
        UserNotFoundError: 404,
        EmailAlreadyTakenError: 409,
        ValidationError: 422,
    }
    return JSONResponse(
        status_code=status_map.get(type(exc), 400),
        content=ApiErrorResponse(
            errors=[ApiErrorDetail(
                code=type(exc).__name__.upper(),
                message=str(exc),
            )],
        ).model_dump(),
    )

app.add_exception_handler(DomainError, domain_exception_handler)
```

---

## 4. TESTING (THE PYTEST STANDARD)

### A. pytest fixtures (required)

```python
# conftest.py — Shared fixtures
import pytest

@pytest.fixture
def user_factory() -> Callable[..., User]:
    def _make_user(**overrides: Any) -> User:
        defaults = {"id": "user-1", "email": "test@example.com", "is_active": True}
        return User(**(defaults | overrides))
    return _make_user

@pytest.fixture
async def db_session(test_database: Database) -> AsyncIterator[AsyncSession]:
    async with test_database.session() as session:
        yield session
        await session.rollback()
```

### B. Parametrized tests (required for logic)

Use `@pytest.mark.parametrize` for logic tests with multiple cases:

```python
@pytest.mark.parametrize(
    "email, expected_valid",
    [
        ("user@example.com", True),
        ("user@.com", False),
        ("", False),
        ("user@example", False),
        ("user+tag@example.com", True),
    ],
    ids=["valid", "invalid_domain", "empty", "no_tld", "with_plus"],
)
def test_validate_email(email: str, expected_valid: bool) -> None:
    assert validate_email(email) is expected_valid
```

### C. Async test support

```python
import pytest

@pytest.mark.asyncio
async def test_find_user_by_id(
    user_service: UserService,
    user_factory: Callable[..., User],
) -> None:
    user = user_factory(id="user-42")
    result = await user_service.find_by_id("user-42")
    assert result == user
```

### D. Test organization

```
tests/
├── conftest.py              # Shared fixtures
├── unit/
│   ├── domain/
│   │   └── user/
│   │       ├── test_service.py
│   │       └── test_models.py
│   └── conftest.py          # Unit-specific fixtures (mocks)
├── integration/
│   ├── test_api_users.py
│   └── conftest.py          # Integration fixtures (real DB)
└── e2e/                     # Optional
    └── test_user_flow.py
```

### E. Mock discipline

- Prefer **dependency injection** over patching (`unittest.mock.patch` is a smell for poor DI)
- When patching is unavoidable, patch where the name is **used**, not where it’s **defined**
- Use **protocol-based fakes** over `MagicMock` when possible:

```python
# ✅ Prefer — Fake that implements the Protocol
class FakeUserRepo:
    def __init__(self) -> None:
        self._users: dict[str, User] = {}

    async def find_by_id(self, user_id: str) -> User | None:
        return self._users.get(user_id)

    async def save(self, user: User) -> User:
        self._users[user.id] = user
        return user

# ❌ Avoid — Magic mock hides interface violations
repo = MagicMock(spec=UserRepository)
repo.find_by_id.return_value = user  # Won't catch if signature changes
```

---

## 5. FILE STRUCTURE (PYTHON PROJECT)

```
src/mypackage/domain/[feature]/
├── __init__.py              # Public API re-exports with __all__
├── models.py                # Dataclasses / Pydantic models
├── service.py               # Business logic (target ~300-400 lines)
├── repository.py            # Data access (Protocol + implementation)
├── exceptions.py            # Domain-specific exceptions
├── schemas.py               # Pydantic request/response (if API)
└── constants.py             # Domain constants / enums
```

For larger domains, split the service:

```
src/mypackage/domain/[feature]/
├── __init__.py
├── models.py
├── service_queries.py       # Read operations
├── service_commands.py      # Write operations
├── repository.py
├── exceptions.py
└── schemas.py
```

---

## 6. CODE QUALITY CHECKLIST

### `LANGUAGE` and build gate

- **`LANGUAGE: PYTHON`** (typical application/hub Python work): run the full **Hub Python** column in `.cursor/rules/cuebert-engineering.mdc` §3 for every change-set that modifies runnable Python.
- **`LANGUAGE: CUEBERT`** (system/docs authoring): if the change-set is **markdown-only** or does not touch runnable Python, typecheck/linter/tests for Python are **N/A**; perform the **CUEBERT (Docs/System)** column (cross-reference, advisory markdown lint). If you **did** change hub Python (e.g. `.cursor/mcp-server/`, `.cursor/skills/*/tools/`), run checks on that Python.

### Dependency map (hub Python and UE — when in scope)

Per `docs/_ai_system/standards/dependency-architecture.md` and `.cursor/skills/depmap-toolkit/SKILL.md`:

| Scope | Refresh / analyze with |
|--------|-------------------------|
| Hub Python imports | `.cursor/skills/depmap-toolkit/tools/python_ast_map.py` → `docs/projects/cuebert/knowledge/dependency-map.json` (or pipe to stdout); aligns with §3 **check 4.6** (**WARN**, `agent-orchestrator.md` §4J) |
| Cycle detection | Pipe map JSON or AST map stream through `.cursor/skills/depmap-toolkit/tools/graph_cycles.py` |
| UE modules (game work) | `.cursor/skills/depmap-toolkit/tools/module_dep_scan.py` on the game `Source` tree |

**Check 4.5** (`cuebert-engineering.mdc` §3): when the **`depmap_validate`** MCP tool (or equivalent) is available, run dependency boundary validation; otherwise document **N/A** and use toolkit analysis above. Prefer MCP **`depmap_validate`** over ad hoc scripts when both apply.

When imports or module boundaries change, refresh the hub depmap (**check 4.6**) before handoff or rely on Orchestrator §4J in `/o`.

Before handoff, verify:

**Build Verification (`.cursor/rules/cuebert-engineering.mdc` §3 — Hub Python column; 1:1 with gate checks; mandatory for applicable `LANGUAGE`):**

- [ ] **Check 1:** Type checker (`mypy` / `pyright`) — zero errors on in-scope Python — **N/A** only if no Python changed
- [ ] **Check 2:** Linter (`ruff check` or equivalent) — zero errors — **N/A** only if no Python changed
- [ ] **Check 3:** Tests (`pytest`) — all pass — **N/A** only if contract says so
- [ ] **Check 4:** **`build_verify`** MCP tool (cuebert-core) — run and attach actual output
- [ ] **Check 4.5:** Dependency boundary validation — **`depmap_validate`** when available; if unavailable or out of scope, note **N/A** in the verification report with rationale
- [ ] **Check 4.6:** Depmap refresh — `python_ast_map` → `docs/projects/cuebert/knowledge/dependency-map.json` — **WARN** severity per orchestrator §4J (auto in `/o` or manual in direct mode when hub Python import graph changes)
- [ ] **Check 5:** Integration verify — MCP tool smoke test (per Hub Python column)
- [ ] Build Verification report included in handoff (actual output, not self-assessed claims)

**Milestone isolation (`cuebert-engineering.mdc` §2 — complexity 3+):**

- [ ] Only one milestone implemented in this chat session
- [ ] Context budget respected (~800 lines max)

**Core Python:**

- [ ] All files within threshold tiers (§2): no file exceeds REJECT without justification, no file exceeds HARD STOP
- [ ] Type hints on ALL function/method signatures (no bare `def f(x):`)
- [ ] Modern union syntax: `str | None` not `Optional[str]`; `list[str]` not `List[str]`
- [ ] No bare `except Exception` or `except:` blocks
- [ ] Exceptions chained with `from` (`raise X from exc`)
- [ ] Custom exceptions from spec are used (not generic `ValueError` alone)
- [ ] Logging via `logging` module, not `print()`
- [ ] No mutable default arguments
- [ ] Imports follow PEP 8 grouping (stdlib → third-party → local)
- [ ] No circular imports (validate with `graph_cycles.py` when hub layout changes)
- [ ] `__all__` defined in `__init__.py` for public API
- [ ] Configuration via Pydantic `BaseSettings` / dataclass, not scattered `os.getenv()`
- [ ] Dependency injection via constructors (no module-level singletons for stateful deps)

**FastAPI & API design (when Sections 3J–3M apply):**

- [ ] Routes on `APIRouter` in `routes/` modules — avoid unbounded inline routes in `main.py`/`app.py`
- [ ] Router prefixes versioned and plural: `/api/v1/{resource}` (unless spec says otherwise)
- [ ] Path segments kebab-case; no verbs in resource paths
- [ ] DI via `Annotated[T, Depends(provider)]` — no direct stateful service imports in handlers
- [ ] Pydantic v2: `ConfigDict(from_attributes=True)`, no `class Config` (v1)
- [ ] Separate Create/Update/Response models — no single model for all purposes
- [ ] Response models never expose `password` or secret fields
- [ ] Responses use `ApiResponse[T]` envelope with `data` + `meta` when the project standard requires it
- [ ] Global exception handler registered mapping domain exceptions to error envelope
- [ ] HTTP status codes follow common REST semantics (201 for create, 204 for delete, etc.)

**Testing:**

- [ ] pytest tests with `@pytest.mark.parametrize` for logic
- [ ] Protocol-based fakes preferred over `MagicMock`

**Orchestrated mode — memory tools (cuebert-core MCP):**

- [ ] When in `/o`, `milestone_commit` completed before phase advance (`cuebert-engineering.mdc` §5G)
- [ ] When debugging occurred, `troubleshoot_commit` / `troubleshoot_search` used per §5D–§5E

---

## 6A. ORCHESTRATED ENVELOPE FIELDS

**Orchestrated envelope** — in **orchestrated** mode (`/o`), the Orchestrator may inject fields beyond the plan path. **Normative source:** `docs/_ai_system/agents/agent-orchestrator.md` (envelope, research §3.1, impact §4I, milestones §5A/§5F).

| Field | Source | Purpose | Consumption |
|-------|--------|---------|-------------|
| `CONDENSED_PRIOR_RESEARCH` | §3.1 Orchestrator | Dependency + API fragments from Research Brief | Architectural context; verify import paths and contracts |
| `IMPACT_PREDICTION` | §4I (complexity ≥5) | Predicted test/import/consumer updates | Advisory — verify at implementation |
| `PRIOR_MILESTONE_CONTEXT` | §5F `milestone_lookup` (cuebert-core MCP) | Decisions, files, deferred items from prior milestones | Continue from prior milestone |
| `DEFERRED_FROM_PRIOR` | §5A | Items deferred from prior milestones | **MUST** address alongside current milestone tasks |

---

## 6B. REMEDIATION MODE INPUTS

**Remediation mode** — when Code runs after **remediation** (post–Review failure), the Orchestrator adds remediation-specific fields. **Normative source:** `agent-orchestrator.md` §4A (remediation loop, envelope template).

| Field | When | Purpose |
|-------|------|---------|
| `CYCLE` | All cycles | Remediation attempt number (1/2/3) |
| `PRIOR REVIEW` | All cycles | Summary of Review findings to fix |
| `PRIOR_SOLUTIONS` | Cycle 2+ | Memory hits from `troubleshoot_search` (cuebert-core MCP) |
| `DIAGNOSTIC_FINDINGS` | Cycle 2+ | Runtime evidence from `diagnostic-probe` |
| `EXTERNAL_RESEARCH` | Cycle 3 | WebSearch results when prior search was unhelpful |
| `PRIOR_FINDINGS` | All cycles | Cross-milestone ledger overlaps |
| `## Remediation Items` | All cycles | Unified finding list — scope of work |

**Evidence priority (when sources conflict):** `DIAGNOSTIC_FINDINGS` (runtime) > `PRIOR_SOLUTIONS` (proven fixes) > `EXTERNAL_RESEARCH` > `PRIOR_FINDINGS`.

---

## 7. HANDOFF PROTOCOL

### Plan auto-completion (mandatory)

Before producing the handoff block below, **update** the active plan file: mark completed todos/tasks as done. If new tasks were discovered during coding, append them in dependency order. The plan is the single source of truth — handoffs without plan updates are protocol violations. See `agent-shared-lifecycle.md` §8 and `.cursor/rules/cuebert-engineering.mdc` §5B.

### Rules consulted record

Before handing off, record which rules were active during this coding session. Append to **`⟨CuebertActivePlans⟩/[slug].md`** (hub: `docs/projects/cuebert/plans/active/[slug].md`) under the plan’s **Decision Trace** section (or create one if the plan template provides for it):

```markdown
### Coding Phase Rules:
| File | Type | Sections Applied |
|------|------|-----------------|
| `agent-coding-python.md` | Agent | [list sections used, e.g., § Type Hints, § FastAPI Router] |
| `project-profile.md` / profile path | Standard | [sections referenced] |
| `[knowledge files if any]` | Knowledge | [maps or integration docs loaded] |
```

This enables the Review Agent to verify that the Code Agent followed the correct rules.

Optional: teams may also mirror high-level trace entries under **`.cuebert/traces/`** if local automation expects that layout; the **plan Decision Trace** remains authoritative for orchestrated review.

### File size summary (mandatory)

Report line counts for ALL files created or modified during this coding session:

```markdown
### File Size Summary:
| File | Lines | Threshold | Status |
|------|-------|-----------|--------|
| service.py | 380 | 300-400 (Target) | ✅ Within target |
| routes/users.py | 220 | 150-250 (Target) | ✅ Within target |
| models.py | 95 | 60-120 (Target) | ✅ Within target |
```

> If any file is in WARN or above, include a brief note explaining why it was not split or what extraction was performed.

### Handoff (no user gate)

Do **not** ask the user to confirm the next phase.

- **Orchestrated (`/o`):** Return `=== SUBAGENT RESULT ===` per `agent-shared-lifecycle.md` §12. The Orchestrator spawns Review (or remediation).
- **Direct:** Output the Thin Handoff per `agent-shared-lifecycle.md` §2 — copy-paste block only; do not wait for inline confirmation.

---

## 8. SELF-MAINTENANCE PROTOCOL (MITOSIS)

> **TOKEN WATCH:** If this file exceeds ~5000 tokens, perform mitosis.

### Evaluation

1. **Check size:** Will this addition push the file over ~5000 tokens?
2. **Check scope:** Does this new rule introduce a distinct domain?

### Action (if YES to either)

1. **Create new file:** e.g. `agent-coding-python-[topic].md`
2. **Register:** Update `docs/_ai_system/rule_registry.md`
3. **Announce:** "Performed mitosis. Created `agent-coding-python-[topic].md`"
