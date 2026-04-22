<img width="1024" height="1024" alt="Q-bert" src="https://github.com/user-attachments/assets/23531588-ea29-474e-8686-4967b07e5cea" />


# Cuebert

An AI-powered development harness for game projects. Cuebert runs inside [Cursor](https://cursor.com) and gives you prompt-driven control over your game engine, build pipeline, and asset generation through three specialized commands.

- **`/play`** -- Edit code or content, preview it live in-editor, and commit only when guards pass
- **`/ship`** -- Cook, certify, package, and optionally upload a distributable build with full audit trail
- **`/asset`** -- Generate 2D textures and art from a declarative YAML manifest via ComfyUI

Without credentials configured, all tools operate in **dry-run mode** automatically -- returning simulated responses so you can explore every phase, guard, and tool before connecting to a real engine or service.

---

## Cheatsheet

### Commands

| Command | What it does |
|---------|-------------|
| `/play --preview` | Health-check the system without changing anything |
| `/play` | Full iteration loop: plan, edit, preview in-editor, QA, commit |
| `/play --project hello-level` | Target a specific registered project |
| `/ship --preview` | Preview the build pipeline without running it |
| `/ship` | Cook + certify + package a distributable build |
| `/asset --preview` | Check ComfyUI connection and manifest validity |
| `/asset` | Generate all assets declared in your manifest |
| `/onboard my-project` | Register a new game project with cuebert |

### Setup (one time)

```bash
git clone https://github.com/ambtaylor/cuebert.git
cd cuebert
bash scripts/bootstrap.sh
```

Then open the folder in Cursor and verify four green dots in **Settings > MCP**:
`cuebert-core`, `cuebert-engine`, `cuebert-asset`, `cuebert-qa`

### Vault credentials

Copy any `.example` file to `credentials.yaml` and fill in your values:

```bash
# Required for live Unreal connection:
cp .cuebert/vault/shared/unreal/credentials.yaml.example \
   .cuebert/vault/shared/unreal/credentials.yaml

# Optional for AI asset generation:
cp .cuebert/vault/shared/comfyui/credentials.yaml.example \
   .cuebert/vault/shared/comfyui/credentials.yaml
```

Never commit `credentials.yaml` to git (blocked by `.gitignore`).

### Environment variables (alternative to vault files)

| Variable | Purpose | Default |
|----------|---------|---------|
| `CUEBERT_UNREAL_BASE_URL` | Unreal Remote Control API | `http://localhost:30010` |
| `CUEBERT_UNREAL_MODE` | `live` or `dry_run` | `dry_run` |
| `CUEBERT_UNREAL_ENGINE_PATH` | Path to your UE install | (none) |
| `CUEBERT_COMFYUI_BASE_URL` | ComfyUI server | `http://127.0.0.1:8188` |
| `CUEBERT_COMFYUI_MODE` | `live` or `dry_run` | `dry_run` |
| `CUEBERT_MEMORY_MODE` | `text` or `hybrid` | `text` |

---

## How Cuebert Works

### The Supervisor

Every message you type in Cursor chat passes through the **Supervisor** (`.cursor/rules/cuebert-supervisor.mdc`) before anything else happens. The Supervisor:

- Recognizes commands (`/play`, `/ship`, `/asset`) and routes them to the correct harness
- Resolves which project you are targeting from the workspace manifest
- Prevents unsafe operations (e.g., blocks spawning disallowed agent types)
- Falls through to normal chat when no command is detected

You never call the Supervisor yourself -- it intercepts every message silently.

### Harnesses

A **harness** is a multi-phase pipeline that executes directly in your chat session. Each harness:

- Decomposes work into ordered **phases** (e.g., Plan > Author > Preview > QA > Merge)
- Spawns a purpose-built **subagent** for each phase so no single agent does too much
- Evaluates **guards** between phases -- automated pass/fail checks that block progression on failure
- Persists a **trace** (logs, screenshots, guard verdicts) to `.cuebert/traces/` for later review

```
┌─────────────────────────────────────────────────────────┐
│                    CUEBERT SUPERVISOR                    │
│            Routes every chat message to the              │
│            correct harness or direct agent               │
└─────────┬──────────────────┬──────────────────┬─────────┘
          │                  │                  │
          ▼                  ▼                  ▼
   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
   │   /asset    │   │   /play     │   │   /ship     │
   │             │   │             │   │             │
   │ AI-generate │   │ Edit and    │   │ Cook, cert, │
   │ 2D assets   │   │ preview in  │   │ package for │
   │ from YAML   │   │ the editor  │   │ distribution│
   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
          │                  │                  │
          ▼                  ▼                  ▼
   ┌─────────────────────────────────────────────────────┐
   │              SHARED INFRASTRUCTURE                   │
   │                                                      │
   │  MCP Tools    Vault       Memory     Traces          │
   │  (12 skills)  (YAML       (SQLite    (per-session    │
   │               secrets)    FTS5)      artifacts)      │
   └─────────────────────────────────────────────────────┘
```

### MCP Tools

Cuebert's capabilities come from **MCP tools** -- Python functions the AI calls on your behalf during a harness run. They are split across four server processes so each loads only what it needs:

- **cuebert-core** -- Vault credential resolution, system health checks, and persistent memory (milestone tracking, troubleshooting recall)
- **cuebert-engine** -- Live Unreal Editor control (Remote Control API), UBT/UAT build invocation, cook/package orchestration
- **cuebert-asset** -- ComfyUI image generation, manifest diffing, and asset pipeline guard evaluation
- **cuebert-qa** -- Screenshot comparison and perceptual diffing, production readiness scans, QA resilience analysis, platform certification checklists

### Guards

Guards are automated checks that run between harness phases. They prevent unwanted or silent issues from blocking or progressing through the pipeline.

**`/play` preview guards:**

| Guard | What it checks |
|-------|---------------|
| G-1 Engine reachability | Can cuebert talk to the Unreal Editor? |
| G-2 Compile sanity | Do affected modules compile without errors? |
| G-3 Critical log patterns | Are there asserts, fatal errors, or crash signatures in the logs? |
| G-4 Asset reference integrity | Do all referenced `.uasset` files exist on disk? |
| G-5 Scope containment | Did the edit stay within the declared file scope? |

**`/ship` gates:**

| Gate | Behavior |
|------|----------|
| Production readiness | **Blocks** the build if shipping config is wrong (debug symbols on, logging verbose, etc.) |
| QA resilience | **Blocks** the build if critical performance or stability issues are found |
| Cook/package | **Blocks** if UAT returns a non-zero exit code |
| Certification | **Advisory only** -- reports platform checklist findings but never blocks |

### The Vault

The vault stores secrets and connection details (engine paths, API URLs, upload keys) that tools need at runtime. It resolves credentials through a tiered overlay -- more specific files win over general ones:

1. **Project-level** (`.cuebert/vault/{project}/`) -- overrides for a single game project
2. **Shared** (`.cuebert/vault/shared/`) -- defaults that apply to all projects

Template files (`.yaml.example`) ship with the repo so you can see the expected structure. Copy any template to `credentials.yaml` and fill in real values. Git ignores all `credentials.yaml` files automatically.

### Memory

Cuebert maintains a persistent knowledge base across sessions so context is never lost between runs:

- **Milestone commits** -- What was accomplished, what was deferred, and what failed -- recorded at each phase boundary so you can trace decisions back to the run that produced them
- **Troubleshooting sessions** -- Symptoms, root causes, and verified resolutions stored so the same problem is recognized and resolved faster next time

Search uses **text-only mode** by default (SQLite FTS5/BM25 ranking). No embedding model or API key is needed. Optionally enable **hybrid mode** for vector-ranked search by setting `CUEBERT_MEMORY_MODE=hybrid` and pointing the vault to an OpenAI-compatible embeddings endpoint.

---

## The Three Harnesses in Detail

### `/play` -- Fast Iteration

Use `/play` when you want to make a targeted change to code, content, or assets and verify it visually in the editor before committing.

**Phase chain:**

```
  Plan ──▶ Author ──▶ Preview ──▶ QA ──▶ Merge
   │          │           │         │        │
   │          │           │         │        └─ Commit to local branch
   │          │           │         └─ Log scan + visual diff
   │          │           └─ Launch PIE, capture screenshots
   │          └─ Edit source, assets, content
   └─ Produce change list and scope declaration
```

**Key behaviors:**
- Guards evaluate both before and after the editor preview, catching issues at the earliest possible point
- If any guard returns REJECT, the session is **blocked** -- no merge happens, but the trace is preserved for diagnosis
- `/play` commits to a local branch only; it **never pushes** to a remote unless you explicitly ask
- Add `--preview` to walk the full chain without spawning agents or modifying files -- useful for verifying system health

**Session outcomes:**
- `complete` -- All guards passed, QA passed, changes committed
- `blocked` -- A guard failed; trace written, no merge
- `not_applicable` -- Engine or automation not available; manual instructions provided
- `running` -- A phase is still in progress

### `/ship` -- Distribution Build

Use `/ship` when you are ready to produce a distributable build. Every `/ship` run is fully audited -- success or failure, the result is recorded to memory and traced to disk.

**Phase chain:**

```
  Pre-cook ──▶ Cook ──▶ Post-cook ──▶ Package ──▶ Cert ──▶ Upload
      │           │          │            │          │         │
      │           │          │            │          │         └─ Optional (Steam/Epic/itch)
      │           │          │            │          └─ Advisory only (never blocks)
      │           │          │            └─ Create distributable archive
      │           │          └─ QA resilience scan (blocks on critical)
      │           └─ UAT BuildCookRun (blocks on failure)
      └─ Production readiness scan (blocks on misconfiguration)
```

**Key behaviors:**
- Cert covers Steam, Epic, GOG, and itch.io platform checklists -- advisory only, never a blocker
- Xbox, PlayStation, and Nintendo are deliberately excluded (require NDA SDKs that cannot be distributed)
- `--override=accept-risk` bypasses blocking gates when you accept the risk -- the override itself is audit-logged

### `/asset` -- AI Asset Generation

Use `/asset` to generate 2D textures, icons, and concept art from a declarative manifest. Assets are validated against dimension, format, and size guards before being placed into your project tree.

**How it works:**

1. You declare assets in a `.cuebert-assets.yaml` file:

```yaml
assets:
  - id: hero-texture
    prompt: "A stylized 512x512 hero character portrait, flat game art style"
    workflow: "txt2img-sdxl"
    destination: "Content/Textures/T_Hero_D.png"
    dimensions: [512, 512]
```

2. Run `/asset` and cuebert will:
   - Read the manifest and diff against the lockfile
   - Send each asset to ComfyUI for generation
   - Validate dimensions, format, and file size
   - Copy approved assets into your project's `Content/` tree
   - Update the lockfile and commit to memory

**Typical workflow:** `/asset` (generate art) then `/play` (preview in editor) then `/ship` (distribute)

---

## Engine Support

| Engine | Support Level | What Works |
|--------|-------------|------------|
| **Unreal Engine 5** | Full | PIE preview, Remote Control API, UAT build/cook/package, Gauntlet testing, visual QA |
| **Unity** | Stubs | Detection and routing exist; live automation is planned |
| **Godot** | Stubs | Detection exists; live automation is planned |

Unreal Engine 5 is the primary target with full live automation. Unity and Godot projects can be registered and will route through the correct harness phases, but their engine adapters are stubs -- the harness will execute in dry-run mode and provide manual step instructions until live adapters are implemented.

---

## Vault Credential Reference

| Service | File | Required For |
|---------|------|-------------|
| Unreal Engine | `.cuebert/vault/shared/unreal/credentials.yaml` | `/play` live preview, `/ship` cook/package |
| ComfyUI | `.cuebert/vault/shared/comfyui/credentials.yaml` | `/asset` image generation |
| Stores | `.cuebert/vault/shared/stores/credentials.yaml` | `/ship` upload phase (Steam, Epic, GOG, itch.io) |
| Memory | `.cuebert/vault/shared/memory/credentials.yaml` | Hybrid search mode only (text mode needs no config) |

---

## MCP Tool Inventory

| Skill | Tools | Server | What It Does |
|-------|------:|--------|-------------|
| memory-toolkit | 6 | core | Milestone tracking, troubleshooting history, full-text search |
| comfyui-toolkit | 5 | asset | ComfyUI health, image generation, workflow listing, manifest validation |
| unreal-bridge | 6 | engine | Editor health check, preset queries, property reads/writes, function calls |
| unreal-build | 5 | engine | UBT/UAT compilation, cook, commandlets, Gauntlet test runner, log tailing |
| cook-package-game | 2 | engine | Orchestrates cook + package via UAT with platform matrix |
| vision-qa | 4 | qa | Screenshot comparison, perceptual hashing, histogram analysis |
| qa-resilience-game | 2 | qa | Scans logs for frame hitches, memory leaks, crashes, streaming stalls |
| prod-readiness-game | 2 | qa | Scans project configs for shipping misconfigurations |
| cert-game | 2 | qa | Advisory certification checklists (Steam, Epic, GOG, itch.io) |
| play-guards | 1 | qa | Evaluates the 5 `/play` preview guards |
| ship-guards | 1 | qa | Dispatches `/ship` pipeline gates |
| asset-guards | 1 | asset | Evaluates `/asset` pipeline guards (format, dimensions, duplicates) |

---

## Troubleshooting

### Helpful Prompts

Your entire workflow with cuebert is prompt-driven -- you type in chat, cuebert acts. When something goes wrong or you want to understand the system, these prompts are designed to get you unstuck fast:

**Health checks and diagnostics:**

```
/play --preview
```
> Runs a full system diagnostic. Shows which MCP servers are loaded, whether
> vault credentials are configured, which guards are live vs stubbed, and
> whether the engine is reachable.

```
/ship --preview
```
> Same idea but for the build pipeline. Shows production readiness, cook/package
> availability, cert scanner status, and platform support.

```
/asset --preview
```
> Checks ComfyUI connectivity, manifest validity, and asset guard status.

**Understanding the system:**

```
Explain how /play works step by step
```
> Ask cuebert to walk you through the phase chain in plain language.

```
What MCP tools are available for Unreal?
```
> Lists all unreal-bridge and unreal-build tools with descriptions.

```
Show me the play guards and explain what each one checks
```
> Breaks down G-1 through G-5 with examples of what triggers each.

```
What does the vault credential file for Unreal need to contain?
```
> Shows the expected YAML structure and explains each field.

**When something breaks:**

```
/play --preview says cuebert-engine is not loaded. How do I fix this?
```
> Cuebert will check MCP server status and walk you through restarting it.

```
I got a "not_configured" error for Unreal. What do I need to set up?
```
> Guides you through vault credential setup and environment variables.

```
The /ship pre-cook gate rejected my build. What failed?
```
> Reads the production readiness scan results and explains each finding.

```
My /asset run failed with "ComfyUI unreachable". Help me debug this.
```
> Checks vault config, environment variables, and tries to reach the ComfyUI server.

```
Can you check if my Unreal Remote Control plugin is working?
```
> Calls `unreal_health_check` and reports what it finds.

**Project management:**

```
/onboard my-game-project
```
> Registers a new project in the workspace manifest.

```
What projects are registered in cuebert?
```
> Reads the workspace manifest and lists all onboarded projects.

```
Show me the last /ship trace — what happened?
```
> Reads the most recent trace directory and summarizes the run.

### Common Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| MCP servers show red dots in Settings | Python environment missing dependencies | Run `bash scripts/bootstrap.sh` and restart Cursor |
| "not_configured" on every tool call | Vault credentials not set up | Copy `.example` files to `credentials.yaml` (see Cheatsheet) |
| `/play` says engine is unreachable | Unreal Editor not running or Remote Control plugin disabled | Open UE, enable plugin via Edit > Plugins > "Remote Control API" |
| `/asset` says ComfyUI unreachable | ComfyUI server not running | Start ComfyUI (`python main.py`) and verify `http://localhost:8188` loads |
| Tools run but always return dry-run data | Mode is set to `dry_run` | Set `build_mode: "live"` in vault credential or `CUEBERT_UNREAL_MODE=live` |
| `/ship` pre-cook gate rejects the build | Production readiness scan found issues | Run the prompt: "What failed in the prod readiness scan?" |
| Cursor asks to approve every tool call | Auto-run not configured | Settings > search "auto-run" > set to "Run Everything" |
| `sequential-thinking` shows red dot | Node.js not installed or server not configured | Install Node from nodejs.org, add the MCP server entry (see Getting Started guide) |
| Memory/search returns no results | Database not yet created | Memory DB is created on first `milestone_commit` or `troubleshoot_commit` call |

### Cursor Settings Checklist

If cuebert is not responding to commands or tools are failing silently, verify these Cursor settings:

- **MCP servers:** Settings > MCP -- all five servers should show green dots
  - `cuebert-core`, `cuebert-engine`, `cuebert-asset`, `cuebert-qa`, `sequential-thinking`
- **Auto-run:** Settings > search "auto-run" -- should be set to "Run Everything"
- **Agent mode:** Make sure you are in Agent mode (not Ask mode) when running harness commands
- **Workspace:** The cuebert folder must be added as a workspace root (File > Add Folder to Workspace)

Run the diagnostic script for a comprehensive check:
```bash
bash scripts/check-cursor-mcp-status.sh
```

---

## Repository Structure

```
cuebert/
├── .cuebert/                          # Hub data directory
│   ├── registry/skills.yaml           # Registered skills and their MCP groups
│   ├── config/                        # Guard and rule engine configs (YAML)
│   ├── vault/shared/                  # Credential templates (*.yaml.example)
│   ├── traces/                        # Session artifacts (play/, ship/, asset/)
│   ├── memory/                        # SQLite FTS5 database (created at runtime)
│   └── workspace-manifest.json        # Registered projects
│
├── .cursor/
│   ├── agents/                        # Subagent dispatch envelopes (10 files)
│   ├── mcp-server/                    # MCP server + core tools
│   ├── skills/                        # 12 skill folders with Python tool implementations
│   ├── rules/cuebert-supervisor.mdc   # Supervisor routing rules
│   └── mcp.json                       # MCP server configuration for Cursor
│
├── docs/
│   ├── _ai_system/agents/             # Canonical agent protocol specs
│   ├── _ai_system/standards/          # Guard specs, cook commands, checklists
│   ├── _ai_system/examples/           # Worked dry-run samples
│   ├── images/                        # Logo and documentation images
│   └── GETTING-STARTED.md             # Full setup guide
│
├── examples/HelloLevel/               # Sample UE5 project for testing
├── scripts/                           # Bootstrap, vault setup, Cursor diagnostics
├── .github/workflows/ci.yaml          # CI validation (Python, YAML, JSON)
└── .cursorrules                       # IDE-level rules
```

---

## License

TBD.
