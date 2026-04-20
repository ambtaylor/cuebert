# `.cuebert/config` — Hub defaults

## 1. Purpose

This directory holds **Cuebert hub configuration** that **ships with the repository**. Files here are **per-hub defaults**: checked into `cuebert`, versioned, and shared by everyone using the hub checkout. Runtime tooling loads these first, then applies **per-project overrides** from `.cuebert/workspace-manifest.json` where a standard defines them.

**Session artifacts** (for example `.cuebert/traces/play/<timestamp>/guards/envelope.json`) are **not** stored here. Traces live under `.cuebert/traces/` per `docs/_ai_system/standards/control-plane-paths.md`; this folder only ships **defaults**.

## 2. Files

| File | Purpose | Authoritative spec |
|------|---------|-------------------|
| `play-guards.yaml` | Default **Preview Guards** thresholds, enables, and timing for `/play` | `docs/_ai_system/standards/play-preview-guards.md` |

Additional config files will be listed here as milestones add them (for example engine regex packs under a future subdirectory). Until then, guard **pattern catalogs** remain documented as **future work** in M5/M6 standards.

**Related hub docs (operational context):**

| Topic | Path |
|-------|------|
| `/play` harness overview | `docs/_ai_system/agents/agent-play.md` §4 |
| Preview phase | `docs/_ai_system/agents/agent-play-preview.md` §5 |
| QA overlap | `docs/_ai_system/agents/agent-play-qa.md` §4 |

## 3. Per-project overrides

Projects MAY override guard behavior without editing shipped YAML — for example tuning log noise floors for a legacy title.

Use **`.cuebert/workspace-manifest.json`** under:

`projects.<projectKey>.playGuards.overrides`

Resolution order and field semantics are defined in **`docs/_ai_system/standards/play-preview-guards.md` §4** (project override wins over hub defaults).

Other manifest keys may gain similar `overrides` blocks in future milestones; always read the linked standard for the active contract.

**Guidance:** Prefer **manifest overrides** for per-title tuning so hub defaults stay reviewable in one place. Forks of cuebert MAY edit `play-guards.yaml` directly for org-wide policy, but should bump `version` only when schema changes per §4 below.

## 4. Schema versioning

Each config file declares **`version: N`** (integer) at the top. **Additive** keys within the same major doc release keep the version until a **breaking** layout change requires bumping the integer. Cuebert tooling **MUST** read the version and **fail loudly** on unknown versions so misaligned binaries never silently mis-parse policy.

**Compatibility rule:** Adding a **new guard id** under `guards:` is additive for the same `version`. Renaming keys, moving `global` fields, or changing the meaning of `threshold` objects is **breaking** and requires a version bump plus a short migration note in the standard doc.

## 5. Footer

**Introduced:** **M2-P3** — Preview Guards contract scaffold (`play-guards.yaml` + this readme). Evaluator implementations follow in **M5/M6** per the `cuebert-gaming-system` plan in the Cue workspace (`docs/projects/cue/plans/active/cuebert-gaming-system.md`).
