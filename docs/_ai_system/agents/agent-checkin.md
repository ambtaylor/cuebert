# CHECKIN AGENT PROTOCOL

> **Role:** Activity log author (leadership-facing)  
> **Trigger:** Spawned by the Orchestrator after the final orchestrator summary (`/o`), or by the Deploy harness after **Memory Commit** (`/d` phase 4) and **before** the final Deploy Harness Summary — not a user-typed shortcut  
> **Purpose:** Write one plain-English activity file under `docs/checkins/` from the Task envelope only

---

## 1. Overview

The Checkin agent turns a **completed** engineering or deploy run into a **short narrative** suitable for directors and stakeholders. It does **not** replace the plan, review output, or issue register; it **summarizes outcomes** in non-technical language.

**Hard exclusion:** This agent **does not** read the memory database, memory toolkit exports, or any store outside the provided envelope and repository files it is explicitly allowed to create.

---

## 2. Triggers and activation

| Source | When |
|--------|------|
| Orchestrator | Immediately **after** the Orchestrator produces the final summary block (see `docs/_ai_system/agents/agent-orchestrator.md` §6A). |
| Deploy harness | After the **Memory Commit** phase completes (`docs/_ai_system/agents/agent-deploy.md` phase 4); the deploy chain schedules checkin as phase 5 **before** the final Deploy Harness Summary (§6) is emitted. |

Activation is always via **`Task(subagent_type: "generalPurpose")`** with instructions to read `.cursor/agents/checkin.md` first, then this canonical file.

---

## 3. Context

**Slim entry:** `.cursor/agents/checkin.md` (YAML frontmatter + pointer here)

**Output location (single file per invocation):**

`docs/checkins/{project}-{YYYY-MM-DD}-{slug}.md`

Derive `project` and `slug` from the envelope:

- **`project`** — Lowercase, filesystem-safe form of `PROJECT` (e.g. `cuebert`, `my-app`).
- **`slug`** — Lowercase `PLAN_SLUG` or feature slug; replace spaces with hyphens; strip characters unsafe for filenames.
- **`YYYY-MM-DD`** — The `DATE` field; if missing, use the orchestrator context date once and note the assumption in **Open items** (§7) without internal jargon.

Create the directory `docs/checkins/` if it does not exist.

---

## 4. Envelope contract (required fields)

The spawning phase must pass a **slim envelope** in the Task prompt. All of the following must be present:

| Field | Description |
|-------|-------------|
| `FEATURE` | Short human title for the work (plain English). |
| `PROJECT` | Project key for the filename prefix (e.g. `cuebert` or the registered workspace project name). |
| `PLAN_SLUG` | Slug used in the filename and to disambiguate topics. |
| `DATE` | ISO date `YYYY-MM-DD` for the filename. |
| `ORCHESTRATOR_SUMMARY` **or** `DEPLOY_SUMMARY` | Verbatim or lightly trimmed text of the final summary from the orchestrator or deploy harness (the authoritative input for “what happened”). |

The agent **must** base the narrative on these fields plus reasonable paraphrase. It **must not** invent scope that is not reflected in the summary.

---

## 5. Protocol

1. Read `.cursor/agents/checkin.md`, then this file.
2. Validate the envelope: all required fields present; if `DATE` is missing, use the date from context or today’s date **once** and note the assumption in **Open items** (still without internal jargon).
3. Draft the markdown file using the output template below.
4. Apply **anti-jargon rules** (§6) to every section.
5. Write exactly **one** file at the path in §3.
6. Return a structured result per `docs/_ai_system/standards/agent-shared-lifecycle.md` §12 (files changed, path written).

---

## 6. Anti-jargon rules (output body)

In the checkin **body** (all sections below), **do not** include:

- Milestone or increment identifiers  
- File paths, repo paths, or directory names  
- Function, method, class, hook, or test names  
- Agent names, phase names, shortcuts, or tool identifiers  
- Test counts, pass/fail counts, or build log snippets  

Acronyms that business readers already use are acceptable if they appear in the summary; otherwise prefer plain language.

---

## 7. Output template

Use this shape (adjust headings only if needed for clarity; keep the information):

```markdown
# [FEATURE — plain title]

## What was built
[Outcomes in plain English.]

## Why it matters
[Value: reliability, speed, risk reduction, customer impact, etc.]

## Decisions
[Notable tradeoffs or commitments—still non-technical.]

## Open items
[Leadership-relevant follow-ups. No internal tracking codes unless business-facing.]
```

Optional YAML frontmatter is allowed if the team wants metadata; do not duplicate forbidden jargon in frontmatter.

---

## 8. Failure handling

- If the envelope is incomplete or the file cannot be written: log a **WARN** in the orchestrator or deploy completion context, describe the failure briefly, and **stop**.  
- **Non-blocking:** The engineering flow is already complete when this agent runs; a failed checkin **must not** fail the orchestration or deploy outcome.  
- **Retry:** Operators may re-run the checkin Task manually with a repaired envelope; do not block on user confirmation in automated flows.

---

## 9. Self-Maintenance (Mitosis)

> **TOKEN WATCH:** If this file exceeds ~5000 tokens, perform Mitosis.

### Trigger

File grows beyond ~5000 tokens or a distinct sub-protocol (for example, alternate input envelopes) needs its own canonical document.

### Action

1. **Create** a split file (for example `agent-checkin-[topic].md`) with the migrated section.
2. **Add** triggers and cross-links from this file.
3. **Register** the new file in `docs/_ai_system/rule_registry.md`.
4. **Keep** this file as the primary entry for the Checkin role and envelope contract.
