# Cuebert Control Plane — Paths

> **SYSTEM ROLE:** Canonical locations for **plans**, **project knowledge**, and **project rules** when using the hub as the single control plane.

## Zero-footprint invariant (hard constraint)

> Cuebert MUST NOT create, require, or validate any files in application repositories solely for Cuebert. The hub discovers app repos through the Cursor multi-root workspace. Credentials needed by running applications are written to `.env` as part of normal coding tasks, not as a Cuebert onboarding step. **`/onboard`** and **`/update`** operate on the **hub** (project registration under `docs/projects/{name}/`, hub Git pull, profile re-scan) — not a copy-from-hub lifecycle inside app repos.

## 1. Principles

- **Hub repository** (`cuebert`): hosts shared agents, standards, registry, and **`docs/projects/{project}/`** for every registered workspace project.
- **Application repositories** are discovered **only** via the **Cursor multi-root workspace** (and path heuristics such as open files). They do **not** host a required Cuebert tree, marker files, or hub-only knowledge copies for Cuebert to function.
- **`{project}`** is the workspace manifest key / logical project name. Authoritative registration lives in **`.cuebert/workspace-manifest.json`** (`projects` keys) and is mirrored by **`docs/projects/{project}/`** after `/onboard`.

## 2. Active plans (implementation specs)

**Notation:** In agent protocols, **`⟨CuebertActivePlans⟩`** means the directory resolved from this table (no trailing ambiguity — always include `/` when concatenating paths).

| Where you are working | `⟨CuebertActivePlans⟩` |
|----------------------|------------------------|
| **Paths relative to the `cuebert` hub repo root** (typical when the open folder is the hub) | `docs/projects/{project}/plans/active/` |
| **Paths from another workspace root** (e.g. an application repo; prefix with the hub checkout) | `<hubRoot>/docs/projects/{project}/plans/active/` |

`<hubRoot>` is the absolute or workspace-relative path to the `cuebert` repo (from the multi-root workspace layout, or from hub-relative resolution in agent handoffs).

**Hub meta/tooling:** When the active project is the hub itself (Cuebert-on-Cuebert work), `{project}` is typically `cuebert` — e.g. `docs/projects/cuebert/plans/active/` — matching registration under `docs/projects/{project}/` (§1).

**Archive:** Same subtree with `archive` instead of `active`.

## 3. Project knowledge (API maps, integration docs)

| Location | Path |
|----------|------|
| Per-project maps & guides | `<hubRoot>/docs/projects/{project}/knowledge/` |
| Hub-shared templates & multi-project maps | `docs/_ai_system/knowledge/` (only files that are explicitly shared — templates, cross-cutting references) |

When loading domain knowledge for coding: prefer `docs/projects/{active-project}/knowledge/`, then fall back to hub-shared `docs/_ai_system/knowledge/`.

## 4. Project rules (checklists, project-only standards)

| Location | Path |
|----------|------|
| Per-project rules | `<hubRoot>/docs/projects/{project}/rules/` |

## 5. Resolving `{active-project}` (Supervisor Step 0.7)

1. **`--project <name>`** in the user message (if present).
2. **`REPO`** / **project** field in a handoff block.
3. **Open-file heuristic:** path segment under the developer workspace root matching a `docs/projects/{name}` entry or manifest key.
4. **`workspace-manifest.json`:** `projects` keys under `.cuebert/workspace-manifest.json`.
5. **Default:** if working directory is the hub repo → treat as hub meta work under `docs/projects/{project}/plans/active/` (typically `{project}` = `cuebert` when that tree exists); else use repo folder name **if** it exists under `docs/projects/`.

## 6. Local automation (optional)

Workspaces may use project-local automation folders where teams choose to keep them. Plan files referenced in payloads must use the **resolved** plan path (hub `docs/projects/...` for application work).

## 7. Registration source of truth

Project keys, relative disk paths, and engine metadata are recorded in **`.cuebert/workspace-manifest.json`**. Run **`/onboard`** to add or refresh the paired **`docs/projects/{project}/`** tree (including `profile.md`).
