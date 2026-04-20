# ONBOARD AGENT PROTOCOL (Cuebert)

> **Role:** Cuebert Onboarder  
> **Shortcut:** `/onboard [project-name]`  
> **Trigger (Inference):** "Register a game project", "Add UE project to Cuebert", "Onboard this Unreal repo", "Create hub project entry"  
> **Output:** Hub-only — creates or updates metadata under `docs/projects/{name}/` on the **Cuebert hub**, and adds an entry to `.cuebert/workspace-manifest.json`. **Zero** new files in the application repository.

## Zero-footprint model

Cuebert discovers application context through the **Cursor multi-root workspace** and hub paths under `docs/projects/{project}/` (see `docs/_ai_system/standards/control-plane-paths.md`). Do not copy hub agents, rules, or standards into app repos. This mirrors Cue's zero-footprint model.

## Scope — gaming-first

Cuebert onboards **game projects only**:

- Unreal Engine 5 (primary): detected by `*.uproject` at the workspace-visible app root
- Unity (secondary, deferred tooling): detected by `ProjectSettings/` + `*.sln`, or `*.unitypackage` as a weaker fallback
- Godot (secondary, deferred tooling): detected by `project.godot`

Also scan **`package.json`** and **`pyproject.toml`** secondarily for build scripts, content pipelines, and tooling — but they **do not** qualify a repo alone.

**Non-game stacks** (React, Angular, standalone Python/Node services) are **out of scope**. If the agent detects a web/server stack **without** any engine marker, return an error:

> This looks like a web/server project, not a game project. Cuebert is for gaming (UE/Unity/Godot). Consider using Cue (the parent project) at ~/CursorProjects/cue, or install Cue's onboard flow instead.

## 1. Detect workspace visibility

1. Confirm the app repo is opened in the same Cursor multi-root workspace as the Cuebert hub (the repo that contains `docs/_ai_system/` and `.cuebert/`).
2. If the app folder is missing from the workspace, instruct the user to **Add Folder to Workspace** — do not scaffold files inside the app repo.

## 2. Auto-detect engine

From read-only inspection of the app tree, look for engine markers in this order:

| Marker | Engine | Primary? |
|--------|--------|----------|
| `*.uproject` | Unreal Engine | YES |
| `ProjectSettings/` + `*.sln` | Unity | deferred |
| `project.godot` | Godot | deferred |
| `*.unitypackage` (fallback) | Unity | deferred |

Record:

- `engine`: one of `unreal | unity | godot`
- `engine_version` (if discoverable, e.g. from `.uproject` `"EngineAssociation": "5.4"`)
- `language`: `cpp` for UE with C++ module, `blueprint_only` for no C++, `csharp` for Unity, `gdscript` for Godot
- Top-level source directories (`Source/`, `Content/`, `Assets/`, etc.)

If no engine marker is detected → return the "not a game project" error above.

## 3. Create hub project entry

1. Ensure `docs/projects/{project-name}/` exists on the cuebert hub.
2. Create or refresh **`profile.md`** using `docs/projects/_templates/gaming-profile.md` as the structural template; fill in engine, version, language, and source dirs from Step 2.
3. Preserve any existing **`knowledge/`** or **`plans/`** subtrees if re-onboarding.

## 4. Update workspace-manifest.json

Add or update the project entry in `.cuebert/workspace-manifest.json`:

```json
{
  "projects": {
    "{project-name}": {
      "path": "../{project-name-as-on-disk}",
      "engine": "unreal",
      "engine_version": "5.4",
      "language": "cpp",
      "description": "<one-line from user or '(not set)'>",
      "installed": "YYYY-MM-DD"
    }
  }
}
```

Use the detected engine info from Step 2. Write the date as today's UTC date.

## 5. MCP auto-run readiness (mandatory check)

Run from the cuebert hub root:

```bash
bash scripts/check-cursor-mcp-status.sh
```

- **Exit 0**: report `MCP auto-run: READY` and list the four cuebert MCP servers (`cuebert-core`, `cuebert-asset`, `cuebert-engine`, `cuebert-qa`).
- **Exit 1**: report failures. Remediation:
  - `mcp.json` / `sequential-thinking` / `alwaysAllow` issues: run `node scripts/update-cuebert.mjs` from hub root to merge required servers into `~/.cursor/mcp.json`.
  - `state.vscdb` / modes / IDE flags: close Cursor, run `bash scripts/fix-cursor-mcp-autorun.sh`, reopen Cursor, re-run the diagnostic.

This is one-time operator setup, not per-project. See Issue I-4 (platform support) for macOS-only scope.

## 6. Activation sequence (summary)

1. Resolve `[project-name]` (explicit arg, `--project`, or inferred from workspace path).
2. Validate multi-root workspace contains both hub and app root.
3. Scan app tree for engine markers (Step 2); secondarily note `package.json` / `pyproject.toml` for tooling context only.
4. If a non-game stack is detected (e.g. React/Angular/manifest-only Node or Python **without** engine markers) → error + exit.
5. Upsert `docs/projects/{project-name}/` on the hub using `gaming-profile.md` template.
6. Upsert entry in `.cuebert/workspace-manifest.json`.
7. Run MCP readiness check.
8. Report.

## 7. Report

After onboard, output:

- **Project name** and **workspace-visible app path**
- **Engine + version + language**
- **Hub paths touched:** `docs/projects/{name}/profile.md`, `.cuebert/workspace-manifest.json`
- **MCP status:** READY / NEEDS_FIX
- **Next steps:** populate `knowledge/`, open a `/spec` for first feature once M2 ships

## CONSTRAINTS

- **Never** create spoke directories or credentials in app repos.
- **Never** run `npm install` / `pip install` as part of onboard.
- **Never** scaffold `.cuebert/` inside app repos. The hub is this cuebert repo only.
- **Always** keep registration and profile work on the hub under `docs/projects/{name}/`.
- **Always** update `.cuebert/workspace-manifest.json` atomically (read → modify → write with `json.dumps(..., indent=2)` or equivalent stable JSON pretty-print).
- **Never** onboard non-gaming stacks (see Scope).
