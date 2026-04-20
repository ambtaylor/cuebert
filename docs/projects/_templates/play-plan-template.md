# /play plan: {PLAN_TITLE}

Project: {PROJECT_KEY} (must exist in `.cuebert/workspace-manifest.json` under `projects.{PROJECT_KEY}`)
Engine: {unreal|unity|godot}
Target: {PIE | PlayMode | F5}

---

## Change intent

{One to three sentences: what gameplay-visible outcome should change after this `/play` run? Describe behavior, visuals, or level state. Do not paste code.}

---

## Change scope (required)

Declare repo-relative globs the Author phase may touch. The harness and `guard.scope.*` evaluators treat this as the contract.

```text
- Source/Game/{SomeFeature}/**/*.cpp
- Source/Game/{SomeFeature}/**/*.h
- Content/Maps/{SomeMap}.umap
```

Edits **MUST** stay within these globs. Any changed file outside this set triggers `guard.scope.bleed` (post-author) and blocks Preview.

Optional: add `Content/{SomeFeature}/**/*.uasset` when asset edits are in scope.

---

## Reference inputs (optional)

- Screenshots or short screen recordings showing desired end state (paths under hub or linked artifact store).
- Reference `.uasset` / `.umap` paths if swapping from a known-good asset.
- Prior commit SHAs or tags if this run is a follow-up to an earlier change.

---

## Success criteria (QA-visible)

What does **pass** look like for `agent-play-qa` and a human spot-check?

- {Criterion 1 — observable in screenshot or log, e.g. object visible at spawn within N seconds of map load.}
- {Criterion 2 — e.g. no `LogLinker: Error` lines in the preview log window.}
- {Criterion 3 — e.g. compile reported `ok` in Author envelope or build log.}
- {Criterion 4 — optional.}
- {Criterion 5 — optional.}

---

## Preview map (optional)

`PREVIEW_MAP`: {`/Game/Maps/MyMap.MyMap` | Unity scene path | Godot main scene}

If omitted, the harness uses the project manifest field `defaultPreviewMap` (see `.cuebert/workspace-manifest.json` and onboard docs).

---

## Guards override (optional)

Per-run or project-level tuning uses `.cuebert/workspace-manifest.json` → `projects.<key>.playGuards.overrides` and the hub defaults in `.cuebert/config/play-guards.yaml`.

Example intent (not copy-paste truth — shape only):

```yaml
# Illustrative: tighten ERROR floor for this run
# Resolved by harness from manifest + play-guards.yaml — do not commit secrets here.
overrides:
  guard.log.error_floor:
    severity: fail
    threshold: { warn: 1, fail: 3 }
```

Document **why** an override is needed (noisy plugin, known benign warnings, and so on).

---

## Memory hooks

`memoryCommit`: {`on_fail` | `never` | `always`}

- **`on_fail`** (default): harness may call memory tooling only after guard or QA failure, per parent `agent-play.md` §10.
- **`never`**: no `troubleshoot_commit` / milestone writes from this session.
- **`always`**: opt-in verbose audit (discouraged for routine iteration).

---

## Non-goals

Explicitly out of scope for this `/play` run (pick what applies):

- No cook, package, or cert (`/ship` / M3+).
- No refactors outside **Change scope** above.
- No new gameplay systems / GDD-length design — iteration only.
- {Add project-specific boundaries.}

---

## Footer (harness)

```text
Status: DRAFT
Author: {USER}
Harness expected phase chain: pre-author guards → agent-play-author → post-author guards → agent-play-preview → post-preview guards → agent-play-qa → merge
```

When promoting from draft, set `Status: APPROVED` and link the trace directory path after the run (under `.cuebert/traces/play/<timestamp>/`).
