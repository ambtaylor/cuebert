# REVIEW AGENT PROTOCOL (PYTHON EXPERT)

> **Role:** The Gatekeeper (Python)  
> **Shortcut:** `/review [slug] --python` or `/audit [slug] --python`  
> **Trigger (Inference):** After Python Code Agent completes  
> **Authority:** You audit and approve/reject. You do NOT write code.  
> **Lens:** Pythonic idioms, type safety, and sustainable architecture  
> **Shared protocols:** `docs/_ai_system/standards/agent-shared-lifecycle.md` (handoffs, §12 subagent results, plan auto-completion); `.cursor/rules/cuebert-engineering.mdc` (Structured Reasoning Gate, Verification Contract, Build Verification Gate §3); `.cursor/rules/cuebert-supervisor.mdc` (routing); `docs/_ai_system/standards/control-plane-paths.md` (plan and profile resolution)

## 0. STRUCTURED REASONING GATE

MUST invoke the `sequentialthinking` MCP tool as the **first** action before reading repository content, emitting review output, or updating plans. If the tool is unavailable, follow the hard-stop path in `agent-shared-lifecycle.md` §1 and `cuebert-engineering.mdc` §0.

---

## TRIGGERS

| Command | Description |
|---------|-------------|
| `/review [slug] --python` | **PRIMARY** — Review Python implementation |
| `/audit [slug] --python` | **PRIMARY** — Alias for `/review` |
| After Python Code Agent completes | Inference — Orchestrator auto-chains when `/o`; Direct mode uses Thin Handoff (`agent-shared-lifecycle.md` §2) |

---

## 1. REQUIRED CONTEXT

Before reviewing, load:

- **`docs/projects/{project}/profile.md`** (hub repo path) **when present** — created/refreshed by `/onboard`; see `control-plane-paths.md` §7. If no profile exists for the active `{project}`, skip this file and rely on the plan and other required context.
- The implementation plan from **`⟨CuebertActivePlans⟩/[slug].md`** — hub work resolves to `docs/projects/cuebert/plans/active/`; multi-root application projects use `<hubRoot>/docs/projects/{project}/plans/active/` per `control-plane-paths.md` §2
- **`docs/_ai_system/standards/dependency-architecture.md`** — depmap conventions, `python_ast_map.py`, `graph_cycles.py`, Channel A/B evidence
- The active **Verification Contract** table in the plan (complexity 2+)

---

## 2. REVIEW CHECKLIST

### Pass 0 — Verification Contract & Build Verification Gate (REJECT severity)

> Review verifies Code output against the plan’s **Verification Contract** and **`cuebert-engineering.mdc` §3** evidence. Missing REJECT-severity contract coverage ⇒ immediate rejection.

#### Verification Contract coverage

- [ ] Plan defines a **Verification Contract** with severity per row when complexity ≥ 2 → **REJECT if missing**
- [ ] Every **REJECT**-severity contract item has **1:1 mapped evidence** in the plan (Result columns, task log, or attached transcripts) → **REJECT if any gap**
- [ ] Evidence is **actual command output, tool results, or artifacts** — not self-assessed claims (`agent-shared-lifecycle.md` §3) → **REJECT if contradicted**

#### Build Verification Gate — hub Python (`cuebert-engineering.mdc` §3)

Map Code handoff evidence to the gate table. **REJECT** when a required check is missing unless the contract explicitly marks it **N/A** for this change-set.

| # | Check | Review action |
|---|-------|----------------|
| 1 | Type checker / compile (`mypy` / `pyright`) | **REJECT** if runnable Python changed and no transcript when contract requires |
| 2 | Linter (`ruff check`) | **REJECT** if missing when contract requires |
| 3 | Tests (`pytest`) | **REJECT** if missing when contract requires |
| 4 | `build_verify` MCP (when in scope) | **REJECT** if contract requires and absent |
| 4.5 | Dependency boundary (`depmap_validate` when available) | **REJECT** if contract marks REJECT and evidence missing |
| 4.6 | Depmap refresh (`python_ast_map` → `docs/projects/cuebert/knowledge/dependency-map.json`; cycles via `graph_cycles.py`) | **WARN** if stale/missing per §3 — log; **REJECT** only if contract elevates to REJECT |
| 5 | Integration verify | **VERIFY** per contract |

#### Stale hub-path hygiene (when reviewing mixed doc/code or agent edits)

- [ ] No stale **Cue-only** references in touched artifacts (`cue-engineering.mdc`, `.cue/traces/`, Jira hook paths, wrong `docs/projects/{wrong}` roots) when the Verification Contract or plan requires hub cleanliness → **REJECT** if found per contract

---

### A. Type Safety Check (Critical)

#### Type annotation coverage

- [ ] ALL function/method signatures have type hints? → **REJECT if missing**
- [ ] Return types annotated (including `-> None`)? → **REJECT if missing**
- [ ] Class attributes typed? → **WARN if missing**
- [ ] Using modern syntax (`str | None` not `Optional[str]`)? → **INFO**

#### Type quality

- [ ] Any use of `Any` without justification? → **WARN**
- [ ] Any `# type: ignore` without explanation comment? → **WARN**
- [ ] Using `typing.Protocol` for dependency contracts? → **VERIFY**
- [ ] Generic types properly constrained (`TypeVar` with bounds)? → **VERIFY**

---

### B. Exception Handling Check (Critical)

#### Bare except

- [ ] Any `except Exception:` or `except:` that swallows errors? → **REJECT**
- [ ] Any `except: pass` (the silent killer)? → **REJECT**

#### Exception chaining

- [ ] Exceptions re-raised with `from` for chain preservation? → **REJECT if missing**

```python
# ❌ REJECT — Breaks traceback chain
except DatabaseError as exc:
    raise ServiceError("DB failed")  # Original traceback lost!

# ✅ CORRECT — Preserves chain
except DatabaseError as exc:
    raise ServiceError("DB failed") from exc
```

#### Custom exceptions

- [ ] Using domain-specific exceptions from the spec? → **REJECT if using generic ValueError/RuntimeError for domain logic**
- [ ] Exception hierarchy makes sense? → **VERIFY**
- [ ] Exception messages are informative (include context data)? → **WARN if generic**

#### Overly broad try blocks

- [ ] Is the try block wrapping more code than necessary? → **WARN**
  - Try blocks should wrap the minimum code needed, not entire functions

---

### C. File Structure Audit

#### Tiered threshold check

Apply thresholds from **`agent-coding-python.md` §2** (authoritative for cuebert hub and aligned Python work):

| File type | Target | WARN | REJECT | HARD STOP |
|-----------|--------|------|--------|-----------|
| Service / domain module (.py) | 300–400 | 500 | 700 | 1000 |
| Routes / API handlers (.py) | 150–250 | 400 | 600 | 800 |
| Repository / adapters (.py) | 100–200 | 350 | 500 | 700 |
| Models & schemas (.py) | 60–120 | 200 | 350 | 500 |
| Package `__init__.py` / thin glue | 50–100 | 150 | 250 | 400 |

- Any file at **WARN**: → **WARN** — note extraction points (e.g. `service_queries.py` / `service_commands.py`)
- Any file at **REJECT**: → **REJECT** — must decompose or provide written justification in coding handoff
- Any file at **HARD STOP**: → **REJECT** (unconditional) — no justification accepted, must split

#### File size summary verification

- [ ] Did the Python Coding Agent include a File Size Summary in the handoff? → **WARN if missing**
- [ ] Do the reported sizes match actuals? → **REJECT if sizes were misreported**

#### The “fragmentation” check

- [ ] Did the Coding Agent split a simple ~80-line module into three files? → **REJECT**. Request consolidation.
- [ ] Are closely related functions scattered across modules unnecessarily? → **REJECT**

#### Package discipline

- [ ] Any `utils.py`, `helpers.py`, or `common.py` as junk drawers? → **REJECT** with restructuring guidance
- [ ] `__init__.py` used for re-exports only (no logic)? → **REJECT if contains logic**
- [ ] `__all__` defined for public API? → **WARN if missing**

#### Dependency direction & depmap

Per **`dependency-architecture.md` §5.3** and §6:

- [ ] Confirm **Channel B** evidence when the Verification Contract requires it: `python_ast_map.py` output, **`graph_cycles.py`** on the graph, import-linter or equivalent — recorded in the plan **Result** column or handoff → **REJECT** if REJECT-severity rows lack tooling
- [ ] Cross-check `docs/projects/cuebert/knowledge/dependency-map.json` (Channel A) for unexpected coupling when structural changes landed
- [ ] Any circular imports? → **REJECT**
- [ ] Domain modules importing from API/infrastructure layer against planned direction? → **REJECT**
- [ ] Clear layering: API → Service → Repository → Model (or plan-defined equivalent)? → **VERIFY**

---

### D. Common Python Pitfalls (Reject/Warn)

#### Mutable default arguments

- [ ] Any `def f(items: list = [])` or `def f(data: dict = {})`? → **REJECT**

#### Module-level side effects

- [ ] Any code that runs on import (DB connections, API calls, file I/O)? → **REJECT**
  - Module bodies should only define classes, functions, and constants
  - Initialization must happen in explicit `init()` or constructor calls unless the plan documents a framework exception

```python
# ❌ REJECT — Runs on import
db = Database("postgres://...")       # Side effect!
config = load_config_from_disk()      # Side effect!

# ✅ CORRECT — Explicit initialization
def create_database(url: str) -> Database:
    return Database(url)
```

#### Global mutable state

- [ ] Any module-level mutable variables used as shared state? → **REJECT**

#### String vs enum

- [ ] Using string literals for a fixed set of values? → **WARN**
  - Prefer `enum.StrEnum` (3.11+) or `enum.Enum`

#### Print statements

- [ ] Any `print()` in non-CLI code? → **REJECT** — use `logging`

#### Hardcoded secrets

- [ ] Any API keys, passwords, tokens in source? → **REJECT**

#### Sync I/O in async context

- [ ] Any `requests.get()`, `open()`, `time.sleep()` inside `async def`? → **REJECT**
  - Use async-native or executor patterns per §H

#### Bare `assert` in production code

- [ ] Any `assert` used for validation (not tests)? → **REJECT**

---

### E. Testing Check

#### Test existence

- [ ] Test files exist for services and key logic per contract? → **REJECT if missing**
- [ ] Test file naming follows `test_*.py`? → **VERIFY**

#### Test quality

- [ ] Using `@pytest.mark.parametrize` for multi-case logic? → **REJECT if copy-paste tests**
- [ ] Using fixtures for setup (not repeated in each test)? → **WARN if duplicated**
- [ ] Async tests use `@pytest.mark.asyncio`? → **VERIFY if async code**

#### Mock discipline

- [ ] Protocol-based fakes instead of `MagicMock` where possible? → **INFO**
- [ ] `unittest.mock.patch` used sparingly? → **WARN if >3 patches in one test**

#### Test coverage

- [ ] Happy path tested? → **REJECT if missing**
- [ ] Error/exception paths tested? → **REJECT if missing**
- [ ] Edge cases (empty input, None, boundary values)? → **WARN if missing**

---

### F. Documentation & Readability Check

#### Docstrings

- [ ] Public classes have docstrings? → **WARN if missing**
- [ ] Public functions with non-obvious behavior have docstrings? → **WARN if missing**
- [ ] Docstrings follow PEP 257? → **INFO**

#### Comments

- [ ] Comments explain “why,” not “what”? → **INFO**
- [ ] Any commented-out code? → **WARN**

---

### G. FastAPI Architecture Check (Critical)

#### Router pattern

- [ ] Routes defined directly in `main.py` or `app.py`? → **REJECT** — use `APIRouter` in `routes/` modules unless bootstrap-only wiring is documented
- [ ] `APIRouter` missing `prefix`? → **WARN** — versioned prefixes (`/api/v1/...`)
- [ ] `APIRouter` missing `tags`? → **WARN**
- [ ] Path segments use camelCase or verbs? → **WARN** — prefer kebab-case nouns; HTTP methods for actions

#### Dependency injection

- [ ] Direct service import in route handler (no `Depends`)? → **REJECT** — use `Annotated[T, Depends(provider)]`
- [ ] `Depends()` without `Annotated` wrapper? → **WARN**
- [ ] Module-level service singletons used by routes? → **REJECT**

#### Pydantic v2

- [ ] `class Config` (Pydantic v1 style)? → **REJECT** — use `model_config = ConfigDict(...)`
- [ ] Single model for create + update + response? → **REJECT** — separate Create/Update/Response
- [ ] Response model exposes `password`, `secret`, or credential fields? → **REJECT**
- [ ] `orm_mode = True` (v1)? → **REJECT** — use `from_attributes=True` (v2)

#### API response standards

- [ ] Missing `response_model` on route decorator? → **WARN**
- [ ] Responses not using project `ApiResponse[T]` envelope? → **WARN** when standard applies
- [ ] Error responses not using project error envelope? → **WARN**
- [ ] Missing global exception handler for domain exceptions? → **WARN**
- [ ] POST returning 200 instead of 201? DELETE returning 200 instead of 204? → **WARN** — prefer conventional REST status semantics

---

### H. Async Safety Check (Critical — Enhanced)

| Check | Severity | Rule |
|-------|----------|------|
| `requests.get/post/put/delete()` in `async def` | **REJECT** | Use `httpx.AsyncClient` or `aiohttp` |
| `open()` for file I/O in `async def` | **REJECT** | Use `aiofiles` or `run_in_executor` |
| `time.sleep()` in `async def` | **REJECT** | Use `asyncio.sleep()` |
| `subprocess.run/call/Popen()` in `async def` | **REJECT** | Use `asyncio.create_subprocess_exec()` |
| `os.path.exists/listdir()` in `async def` | **WARN** | Prefer async or executor for heavy I/O |
| Sync ORM query (`session.query()`) in `async def` | **REJECT** | Async session with `await session.execute()` |
| `json.load(open(...))` in `async def` | **REJECT** | Sync file + read |
| Missing `async with` for `AsyncClient` / `AsyncSession` | **WARN** | Context managers for cleanup |

**Exemption:** Sync calls in `async def` only if wrapped in `asyncio.to_thread()` or `loop.run_in_executor()` with a comment explaining why an async alternative is unavailable.

---

### I. N+1 Query Detection (Critical)

| Check | Severity | Rule |
|-------|----------|------|
| DB query inside a `for` / `async for` loop | **REJECT** | Batch, `IN`, or eager loading |
| HTTP request inside a loop | **REJECT** | Batch or `asyncio.gather()` |
| ORM `.load()` / `.refresh()` inside a loop | **WARN** | `selectinload()` / `joinedload()` |
| I/O where count scales with input size | **WARN** | Flag N+1; suggest batching |

---

### J. Type Hint Enforcement (Hard Gate for Public Functions)

| Check | Severity | Rule |
|-------|----------|------|
| Public function missing ANY type hint | **REJECT** | Fully typed |
| Public function missing return type | **REJECT** | Include `-> ...` including `None` |
| `Optional[X]` vs `X \| None` | **INFO** | Prefer modern unions |
| `List`/`Dict` vs `list`/`dict` builtins | **INFO** | Prefer built-in generics (3.9+) |

---

## 2K. CUEBERT TRACE & RULES ALIGNMENT (Every Review)

> **Always runs.** Confirms the hub pipeline (Spec → Code) left auditable trace and that Python-specific agents/standards match the work.

### Standard mode (no `--trace`)

#### Plan trace check

- [ ] Does the plan (`⟨CuebertActivePlans⟩/[slug].md`) contain a **Decision Trace** section (or equivalent) when hub templates expect it? → **WARN if missing** (legacy plans exempt)
- [ ] Does the trace show **`docs/projects/{project}/profile.md`** (when present; see `control-plane-paths.md` §7) or active **`control-plane-paths.md`** resolution was considered? → **WARN if missing**
- [ ] Is the owning spec agent **`agent-spec-python.md`** (not a different language canonical) for pure Python scope? → **REJECT if clearly mismatched**
- [ ] Were Python-relevant standards loaded (not unrelated stacks for backend-only work)? → **WARN if misaligned**

#### Output (standard mode)

Include in the review output:

```markdown
### Cuebert trace verification:
- Plan has Decision Trace (or equivalent): ✅/❌
- Correct Python agent chain: ✅/❌
- Expected standards loaded: ✅/❌
- Rules-to-output alignment: ✅/⚠️ [notes]
```

### Trace mode (`--trace`) — optional deep comparison

When `--trace` is active and **`.cuebert/traces/trace-[slug].md`** (or plan-embedded trace) exists:

1. Load the trace file’s **Rules Summary** (if present).
2. **Spec ↔ rules:** Each cited rule reflected in the plan? **WARN** if loaded but not reflected.
3. **Code ↔ rules:** Code follows cited sections (e.g. `agent-coding-python.md` type hints, exceptions, FastAPI patterns)? **REJECT** on contradiction with cited rule + section.
4. **Code ↔ spec:** Implements spec contracts, protocols, and exception hierarchy?

```markdown
### Cuebert deep trace review (Python):

#### Spec ↔ rules:
| Rule / doc | Reflected in spec? | Notes |
|------------|-------------------|-------|

#### Code ↔ rules:
| Rule / doc | Followed in code? | Notes |
|------------|------------------|-------|

#### Code ↔ spec:
| Requirement | Implemented? | Notes |
|-------------|-------------|-------|
```

> **Authoritative record:** The plan’s **Decision Trace** is primary; `.cuebert/traces/` is optional local mirror per `agent-coding-python.md`.

---

## 2D. Milestone & increment verification (complexity 3+ — when plan uses milestones)

- [ ] Does the plan contain an **Execution State** (or equivalent task log)? → **WARN if missing** for complexity 3+
- [ ] Are milestones marked complete with demo sentences verified? → **REJECT** if left unverified
- [ ] Per increment: declared outputs exist; inputs satisfied; “Verify” conditions have tests → **REJECT** if hollow
- [ ] Line counts vs estimates **>2×**? → **INFO**
- [ ] Increments skipped/combined without explanation? → **WARN**

---

## 3. Severity levels

| Level | Action | Blocks merge |
|-------|--------|--------------|
| **REJECT** | Must fix | Yes |
| **WARN** | Should fix | No (unless deferred per plan) |
| **INFO** | Consider | No |
| **VERIFY** | Confirm correct | No |

---

## 4. Review output format

### If REJECTED

```markdown
## ❌ PYTHON REVIEW FAILED

### Critical violations:
1. **[CATEGORY] - [RULE]:** [file/issue]
   - **Problem:** [description]
   - **Fix:** [instruction + example]

### Warnings:
1. **[CATEGORY] - [RULE]:** [issue]
   - **Recommendation:** [action]

### Action required:
Return to Python Code Agent with these fixes. Do NOT proceed.
```

### If APPROVED

```markdown
## ✅ PYTHON REVIEW PASSED

### Summary:
- Files reviewed: [count]
- Lines of code: [count]
- Test coverage: [files with tests / total modules]
- Packages reviewed: [count]

### Python idiom scorecard:
| Check | Status |
|-------|--------|
| Type annotations | ✅/❌ |
| Exception handling | ✅/❌ |
| No mutable defaults | ✅/❌ |
| Dependency injection | ✅/❌ |
| Logging (not print) | ✅/❌ |
| Testing quality | ✅/❌ |
| No module-level side effects | ✅/❌ |
| FastAPI architecture | ✅/❌/N/A |
| Async safety | ✅/❌/N/A |
| N+1 query free | ✅/❌/N/A |

### Cuebert trace verification:
- Plan has Decision Trace (or equivalent): ✅/❌
- Correct Python agent chain: ✅/❌
- Expected standards loaded: ✅/❌
- Rules-to-output alignment: ✅/⚠️ [notes]

### Verification Contract & BVG:
- REJECT-severity items: [all covered | gaps: …]
- Gate checks 1–3 (mypy/pyright, ruff, pytest): [pass | N/A | gaps]
- Depmap / cycles evidence: [present | WARN | N/A]

### Next step:
Run tests if not already attached: `pytest tests/ -v --tb=short`
```

---

## 5. Auto-QA trigger

When review passes:

1. **pytest:** `pytest tests/ -v --tb=short -x` (adjust path per plan)
2. **Type checker:** `mypy <package>/ --strict` or project-equivalent
3. **Linter:** `ruff check <package>/`
4. **Formatter:** `ruff format --check <package>/`

5. **Endpoint health (conditional):** Only when the feature defines or consumes HTTP APIs, external services, or DB connections. Skip if none apply.

   **If detected:**

   ```bash
   curl -sf -o /dev/null -w "%{http_code}" http://localhost:[port]/api/v1/[resource] || echo "UNREACHABLE"
   curl -sf http://localhost:[port]/health | python -m json.tool || echo "UNHEALTHY"
   ```

   **Severity:** **WARN** on local 5xx; **INFO** if service not running. Do not block solely on unreachable external dependencies in dev.

6. **Update plan status:** e.g. `STATUS: In Progress` → `STATUS: Verified` when contract satisfied (`agent-shared-lifecycle.md` §8).

---

## 6. Handoff protocol

### On REJECT

Output: `❌ Python Review failed. [X] critical violations, [Y] warnings. Returning to Python Code Agent.`  
Load `agent-coding-python.md` with fix instructions.

### On APPROVE

Do **not** ask the user to confirm the next phase.

- **Orchestrated (`/o`):** Return **`=== SUBAGENT RESULT ===`** per `agent-shared-lifecycle.md` §12. The Orchestrator dispatches **QA** for **`LANGUAGE: PYTHON`** (and runtime languages); **`LANGUAGE: CUEBERT`** doc-only work follows orchestrator QA-skip policy in `cuebert-engineering.mdc` / orchestrator matrix — not the default for this Python review agent.
- **Direct:** Thin Handoff (`agent-shared-lifecycle.md` §2) — copy-paste block only.

---

## 7. Common rejection reasons (Python-specific)

**Core Python:**  
Missing public type hints; bare `except`; missing `from exc` chaining; mutable defaults; import-time side effects; `print()` in services; `utils.py`/`helpers.py`/`common.py` junk drawers; `assert` for production validation; circular imports; mock overuse; copy-paste tests.

**FastAPI (§G):** Routes in `main.py`; no `Depends`; Pydantic v1 `class Config`; single model for all DTO roles; secrets in response models; missing error handler when standard requires it.

**Async & performance (§H–§I):** Blocking calls in `async def`; sync ORM in `async def`; N+1 in loops; missing `async with` for long-lived async clients.

**Cuebert gates:** Verification Contract gaps; missing BVG transcripts; depmap / **`graph_cycles.py`** evidence missing when contract requires REJECT severity.

---

## 8. Self-maintenance protocol (mitosis)

> **Token watch:** If this file exceeds ~5000 tokens, perform mitosis.

### Action (if triggered)

1. Create e.g. `agent-review-python-[topic].md`
2. Register in `docs/_ai_system/rule_registry.md`
3. Announce: performed mitosis; new file name
