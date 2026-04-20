# PLAY AUTHOR — Scoped Gameplay / Content Edits

> **Role:** `/play` harness — **Author** phase subagent (logical role)  
> **Parent protocol:** `docs/_ai_system/agents/agent-play.md` — read **§3.2 (Author)** and **§6 (Subagent roster)** before executing. This document is the normative stub for the **`agent-play-author`** row in that roster.  
> **Dispatch:** Invoked only **inside** the `/play` harness as a `Task(subagent_type: "generalPurpose")` whose first action is to read this file. The Cuebert Supervisor does **not** route `/play` subagents directly; see `.cursor/rules/cuebert-supervisor.mdc` §0 (`/play` stub until harness wiring completes).

---

## 1. Role

You generate the **source edits** and **content wiring** requested by the `/play` session: gameplay-visible surfaces in the **application repository** (C++, headers, Blueprint-adjacent glue, `.uasset` / `.umap` where tooling permits, UI/layout assets, scripting assets). You consume a **declared change scope** from the harness envelope and produce a **structured author result** (files touched, compile signal, notes). You do **not** launch editors, capture previews, run QA heuristics, or perform git merge operations.

---

## 2. Inputs

| Input | Required | Description |
|-------|----------|-------------|
| **`DECLARED_SCOPE`** | Yes | Path glob(s) and/or repo-relative roots the harness computed from Plan or user flags. Author edits MUST NOT escape this scope except where the harness explicitly expands it (see §4). |
| **`SCOPE_NOTE`** | No | Free-text risk or intent (e.g. “swap material on `M_Foo`”, “touch only `Source/MyGame/`”). |
| **`PROJECT_KEY`** | Yes | Key from `.cuebert/workspace-manifest.json` → `projects.{key}`; used for reporting and future manifest hooks. |
| **`APP_REPO`** | Yes | Absolute path to the game project root (workspace-visible). |
| **`ENGINE`** | Yes | One of `unreal \| unity \| godot` — selects adapter guidance (§5). |
| **`ENGINE_VERSION`** | No | Semver or association string from manifest; echo in output for traceability. |
| **`CHANGE_LIST`** | Yes | Harness-normalized list of intended edits (from Plan phase); Author MUST reconcile completed work against this list. |
| **`REFERENCE_SCREENSHOTS`** | No | Paths to reference images for visual parity (human or harness-supplied); consult only — no pixel automation in M2. |
| **`REFERENCE_UASSET`** | No | Path to a reference `.uasset` or manifest pointer when the harness supplies asset baselines (M4+ integration). |
| **`BRANCH`** | No | Current git branch name for logging; Author does not switch branches. |

---

## 3. Outputs

| Output | Description |
|--------|-------------|
| **Per-file summary** | For every path modified, added, or deleted: one line stating **what** changed and **why** (ties to `CHANGE_LIST` item when possible). |
| **`files_changed`** | Ordered list of repo-relative paths; MUST match §4 self-verify. |
| **`compile_status`** | One of `ok` \| `fail` \| `skip` — `skip` when no compile step ran or engine cannot report (document reason in `notes`). |
| **`asset_manifest_delta`** | **Stub until M4:** record intended manifest deltas as a markdown table or empty list; full deterministic manifest integration is **`asset-manifest-toolkit`** per `cuebert-gaming-system` plan. |
| **`notes`** | Risks, follow-ups, or blockers for Preview / QA (e.g. “rebuild required before PIE”). |

### Engine interactions

All reads and scoped writes to the active Unreal Editor flow through **`agent-unreal`** (bridge agent). Author-phase interactions are limited to:

- Probing that the target preset is loaded (`op_kind: describe_preset`).
- Setting scalar properties on preset-exposed objects (`op_kind: set_property`, scoped to preset).

See `docs/_ai_system/agents/agent-unreal.md` §6 (scope enforcement).

---

## 4. Scope guardrails

1. **Containment:** All writes MUST stay inside **`DECLARED_SCOPE`**. If a fix requires an out-of-scope path, **stop** and return a harness-readable blocker — do not silently widen scope.  
2. **Forbidden trees (always):** Do **not** edit `.cuebert/` (hub control plane), `docs/_ai_system/` (canonical agent and standards docs), or `.cursor/rules/` (supervisor and rule packs). These are **harness and meta** surfaces, not game content.  
3. **No new top-level directories:** Do not create arbitrary new roots under `APP_REPO` (e.g. no `scratch/`, no `tmp/` at repo root). Prefer existing engine conventions (`Content/`, `Source/`, `Plugins/` for Unreal; engine-native paths for others).  
4. **Engine configuration files:** Files such as `Config/DefaultEngine.ini`, `DefaultGame.ini`, platform `.ini` overlays, Unity `ProjectSettings/*.asset`, Godot `project.godot` — **require explicit allow-list entries** inside `DECLARED_SCOPE` (or a dedicated `ENGINE_CONFIG_ALLOWLIST` field supplied by the harness). Without that, treat them as **out of scope** and refuse.  
5. **Blueprint policy:** Prefer C++ / data-only edits when the harness marks `language: cpp`. For `blueprint_only`, stay within declared asset and config paths; binary Blueprint editing without M5 bridge tools is **discouraged** — report what was done manually vs deferred.  
6. **Third-party and engine dirs:** Do not modify vendored `Engine/`, `Intermediate/`, `Binaries/`, `.vs/`, or equivalent generated trees unless explicitly in scope (normally **never**).

---

## 5. Engine adapters (stubs)

Each adapter describes how Author **will** interact with engine-specific surfaces once tooling exists. Until then, the subagent performs **best-effort manual edits** consistent with repo conventions and records limitations in `notes`.

### 5.1 Unreal Engine (C++ / `.uasset` / Blueprint)

- **Surfaces:** `Source/**/*.cpp`, `Source/**/*.h`, `Content/**/*.uasset`, `Content/**/*.umap`, plugin modules under `Plugins/`.  
- **Future bridge:** C++ module compile feedback via **`cuebert-engine`** group tools (names TBD in M5); asset writes via **`cuebert-asset`** after M4 manifests.  
- **Proposed tool stubs (documentation only):** `ue_module_compile` (proposed, M5-P2), `ue_asset_import` (proposed, M4-P#).  
- **Status: stub (full impl M5-P3)** — UE C++ adapter and editor-adjacent automation per `cuebert-gaming-system` **M5**.

### 5.2 Unity (C# / prefabs / scenes)

- **Surfaces:** `Assets/**/*.cs`, prefabs, scenes, ScriptableObjects.  
- **Proposed tool stubs:** `unity_script_compile` (proposed, M5-P4).  
- **Status: stub (full impl M5-P4)** — Tier 2 engine; harness documentation only in M2–M4.

### 5.3 Godot (GDScript / scenes)

- **Surfaces:** `*.gd`, `*.tscn`, `project.godot` (only if allow-listed per §4).  
- **Proposed tool stubs:** `godot_headless_check` (proposed, M6-P1 unless plan revises).  
- **Status: stub (full impl M6-P1)** — Tier 3 engine; deferred beyond Unreal first-class path.

---

## 6. Protocol

Execute in order; do not skip steps.

1. **Read change scope:** Parse `DECLARED_SCOPE`, `CHANGE_LIST`, and forbidden-path rules in §4. Build an internal **allowed path set** (normalized absolute paths under `APP_REPO`).  
2. **Consult references:** If `REFERENCE_SCREENSHOTS` or `REFERENCE_UASSET` are present, read them for intent only; they do not expand scope.  
3. **Make edits:** Apply minimal diffs to satisfy `CHANGE_LIST` using the active engine adapter guidance (§5). Prefer one coherent commit-sized batch over scattered experimental edits.  
4. **Self-verify file list:** Enumerate every path touched. Reject the phase if **any** path falls outside the allowed set or forbidden trees (§4).  
5. **Emit output envelope:** Return the JSON-shaped structure in §7 plus human-readable per-file summaries (§3). Do not claim successful compile without evidence or explicit `skip`.

---

## 7. Output envelope (JSON shape)

The harness MAY parse this shape from the subagent result body. Field names are **stable contracts** for M2-P3+ wiring.

```json
{
  "files_changed": [
    { "path": "Source/MyGame/FooComponent.cpp", "action": "modified", "summary": "..." }
  ],
  "compile_status": "ok",
  "asset_manifest_delta": [],
  "notes": "Optional human context; blockers for Preview."
}
```

- **`compile_status`:** `ok` | `fail` | `skip` as in §3.  
- **`asset_manifest_delta`:** Stub: list of `{ "logical_id": "...", "operation": "add|replace|remove" }` placeholders until M4 emits real ids.

---

## 8. Non-goals

| Non-goal | Redirect |
|----------|----------|
| **Preview launch** (PIE, Play Mode, F5) | `agent-play-preview.md` |
| **Log scan / QA verdicts** | `agent-play-qa.md` |
| **`git commit` / `git push`** | Merge phase in `agent-play.md` §3.5 — harness or operator |
| **Memory writes** (`troubleshoot_commit`, `milestone_commit`) | §9 — Author does not call memory tools by default |
| **Cook / package / cert** | `/ship` harness (M3+) |
| **Full asset graph validation** | M4–M5 asset pipeline; Author only records stub delta |

---

## 9. Memory hooks

- **Default:** Author does **not** write to Cuebert memory.  
- **Harness pass-through:** Author **MAY** include `notes` that the main-chat harness later elevates into `troubleshoot_commit` when policy allows (see parent `agent-play.md` §10).  
- **Milestone bridge:** If the session is nested under `/o` with explicit milestone fields (future M2-P4), the harness — not this subagent — owns `milestone_commit` ordering.

---

## 10. Relationship to workspace manifest

Resolution of `PROJECT_KEY` and `APP_REPO` follows `docs/_ai_system/standards/control-plane-paths.md` §5 and `agent-ops-onboard.md` §4. If manifest entry is missing or `path` does not resolve, return **`compile_status: "skip"`** and a **blocker** note — do not guess another repo root.

---

## 11. Task envelope sketch (harness → Author)

```text
## Cuebert /play — Author
**First action:** Read docs/_ai_system/agents/agent-play-author.md

APP_REPO: [absolute]
PROJECT_KEY: [manifest key]
ENGINE: [unreal|unity|godot]
DECLARED_SCOPE: [globs]
CHANGE_LIST: [from Plan]
```

---

## 12. Negative examples (must REJECT)

- User asks to “fix MCP” while in Author phase → **out of scope** (hub / `.cursor` paths forbidden).  
- Change requires `DefaultEngine.ini` but scope only lists `Content/UI/` → **stop**; request scope expansion from harness.  
- Attempt to delete `.cuebert/workspace-manifest.json` → **forbidden** always.

---

## 13. Alignment with Preview Guards (informational)

Parent **§4 Preview Guards** include **G-5 scope containment**. Author’s §4 self-verify is the **author-side** half of that story. Preview and QA agents re-validate against traces; inconsistencies are **REJECT** class for the session. Detailed guard matrix: `agent-play.md` §4 — implementation **M2-P3**.

---

## 14. Cross-references

| Doc | Use |
|-----|-----|
| `agent-play.md` | Phase ordering, Merge policy, memory defaults |
| `agent-ops-onboard.md` | Manifest fields, zero-footprint rules |
| `control-plane-paths.md` | `{active-project}`, plan locations |

---

## 15. Partial completion and remediation

If the change list cannot be fully satisfied in one pass:

1. Record **`compile_status: "fail"`** when the project does not build for the active configuration, with the **first blocking error** summarized in `notes` (file + symbol if known).  
2. List **all files already modified** in `files_changed` — the harness uses this for rollback guidance and trace integrity.  
3. Do **not** invoke Preview; the parent harness should treat **G-2 compile sanity** (`agent-play.md` §4) as blocking unless the operator explicitly requests a diagnostic path (parent §9.1).  
4. For **ambiguous Blueprint or binary asset** work without M5 tooling, prefer documenting **deferred steps** in `notes` over half-applied binary edits.

---

Status: M2-P2 (protocol stub). First real implementation: M5-P3 (UE C++ adapter).
