# Game project Git LFS (Cuebert standard)

## 0. Purpose

Cuebert is a **control-plane hub**. Application repositories onboarded through `/onboard` hold the real binary art, audio, level data, and engine-authored assets. Without Git LFS, those blobs (often tens to hundreds of megabytes each) inflate normal Git objects, slow every `git clone` and `git fetch`, and make diffs meaningless.

This document defines **Cuebert’s recommended LFS posture** for Unreal, Unity, and Godot game projects: which extensions to track, which files to leave as plain text, how to install the hub-authored template, and how to avoid common operational traps (CI, provider quotas, history rewrites).

Historical engine defaults evolve; Epic’s Unreal `.gitattributes` on the public mirror (for example [EpicGames/UnrealEngine `release` branch `.gitattributes`](https://github.com/EpicGames/UnrealEngine/blob/release/.gitattributes)) is a useful cross-check, but teams should treat Cuebert’s template plus this standard as the **contract** for hub-driven onboarding.

## 1. Who this applies to

This standard applies to any project registered via `/onboard` (`docs/_ai_system/agents/agent-ops-onboard.md`) where `profile.engine` is one of:

- `unreal`
- `unity`
- `godot`

Web stacks, backend services, and tooling-only repositories **without** an engine marker are **out of scope** for this document. Those repos should not install the game LFS template.

## 2. Why LFS over alternatives

- **Git-native workflow:** Artists and engineers stay in one VCS; pointers stay small even when payloads are huge.
- **Broad hosting support:** GitHub, GitLab, Gitea, and other providers implement LFS with documented quotas (see §9).
- **Predictable checkout cost:** Working trees pay for large bytes when LFS smudge runs, not on every history walk through unrelated commits.
- **Operational clarity:** Attribute rules live beside the repo; onboarding a new contractor is “install Git LFS, clone, work” instead of bespoke rsync recipes.
- **Alternatives (explicitly out of scope here):** Unity YAML SmartMerge for selected YAML types, Perforce or Plastic for binary-heavy pipelines, external artifact stores. Teams may combine those with LFS; Cuebert does not prescribe them.

LFS is not magic: it **does not deduplicate** identical binaries across unrelated files the way some DCC asset browsers might, and it **does not replace** a DAM for source PSDs that should never enter Git at all. It simply keeps the Git object database healthy for the subset of binaries you choose to version.

## 3. What to LFS-track

The authoritative pattern list ships in two places:

- Hub reference: `.gitattributes` at the cuebert repo root (patterns are **no-ops** in the hub because no matching files exist).
- Downstream copy template: `docs/projects/_templates/game-project-gitattributes.template`.

### Unreal Engine

| Pattern | Rationale |
|---------|-----------|
| `*.uasset` | Engine binary asset; large; non-diffable as text. |
| `*.umap` | Level binary; same as uasset class of content. |
| `*.ubulk`, `*.uexp` | Serialized bulk / export payloads; binary. |
| `*.pak` | Packaged distribution blobs; very large. |

### Unity

| Pattern | Rationale |
|---------|-----------|
| `*.prefab`, `*.unity`, `*.asset` | Serialized YAML/binary mix; often large; **judgment call** if SmartMerge is enabled (see template comments). |
| `*.meta` | Sidecar metadata; **judgment call** — small in many repos, but Cuebert defaults to LFS for uniformity with other Unity serialized assets. |
| `*.anim`, `*.mat` | Timeline / material payloads; typically heavy binary or long YAML. |

### Godot

| Pattern | Rationale |
|---------|-----------|
| `*.tscn`, `*.tres` | Scene and resource serialization; **judgment call** — many teams keep these as normal text for readable diffs. The template documents how to opt out. |
| `*.res` | Binary resource container; treat as LFS by default. |
| `*.import` (optional) | Importer cache sidecar; often small text; uncomment in template only when justified. |

### Shared (engine-agnostic)

| Pattern | Rationale |
|---------|-----------|
| `*.fbx`, `*.obj`, `*.blend` | Mesh and DCC sources; large binary. |
| `*.psd`, `*.tga`, `*.exr`, `*.png`, `*.jpg` | Raster and HDR sources; large. PNG/JPEG are especially relevant for **Cuebert M4** raster exports into `Content/Art/` (or equivalent). |
| `*.wav`, `*.ogg`, `*.mp3` | Lossless / compressed audio; large. |
| `*.mp4`, `*.mov` | Video plates and cinematics. |
| `*.zip` | Archives; rarely committed, listed for completeness. |

Additional DCC or pipeline formats sometimes committed by art teams (enable only if you actually version them):

| Pattern | Rationale |
|---------|-----------|
| `*.tif`, `*.tiff` | Lossless scans; can exceed Git’s comfort zone quickly. |
| `*.bmp` | Uncompressed bitmaps; large on disk. |
| `*.abc` | Alembic caches; simulation-heavy scenes. |
| `*.usd`, `*.usda`, `*.usdc` | OpenUSD payloads — **judgment call** (`usda` is ASCII; `usdc` is binary; teams often LFS the binary crate only). |

If a format is both **text** and **small** in your pipeline, prefer normal Git tracking so diffs remain usable.

When in doubt, sample ten largest files in your `Content/` or `Assets/` tree (`du -ah | sort -rh | head`) and LFS-track the extensions that dominate disk usage.

## 4. What NOT to LFS-track

Keep the following as **normal Git text blobs** unless your team has an exceptional reason:

- **Engine and app configuration:** `*.ini`, `*.cfg`, `*.toml`, `*.json`, `*.yaml`, `*.yml` when they are small, hand-edited text.
- **Source code:** `*.cpp`, `*.h`, `*.cs`, `*.gd`, `*.py`, `*.ts`, `*.js`, etc.
- **Documentation:** `*.md`, plain text `README*`, license files.
- **Unreal project descriptor:** `*.uproject` (JSON text, small).
- **Unreal plugin descriptors:** `*.uplugin` when treated as small JSON text.
- **Unity solution artifacts:** `*.csproj`, `*.sln` (text, diffable).
- **Unity `Packages/manifest.json`:** dependency list; must stay text.
- **Godot project file:** `project.godot` (text).
- **Godot `export_presets.cfg`:** text configuration for export pipelines.
- **Repository metadata:** `.gitignore`, `.gitattributes` themselves (attributes must remain text rules, not LFS objects).
- **Shaders:** `*.usf`, `*.ush`, `*.hlsl`, `*.glsl` — text unless you have an unusual generated-binary pipeline (then document explicitly).

| Category | Examples | Reason |
|----------|----------|--------|
| Build recipes | `CMakeLists.txt`, `Makefile`, `*.props`, `*.targets` | Small text; merge-friendly. |
| CI definitions | `.github/workflows/*.yml`, `.gitlab-ci.yml` | Must diff in review. |
| Cursor / editor config | `.editorconfig`, `.clang-format` | Text; tiny. |
| Localization tables | `*.csv`, `*.po` when UTF-8 text | Diffable strings; avoid LFS unless extremely large. |
| Certificates / keys | `*.pem` (if ever committed — prefer not) | Never use LFS to “hide” secrets; use vault flows instead. |

## 5. Cuebert’s template

Downstream repositories should copy:

`docs/projects/_templates/game-project-gitattributes.template`

into the **game project root** as `.gitattributes`, or **append** the delimited block from that file beneath existing attribute rules.

The template includes:

- Human-oriented header comments.
- Optional Unity SmartMerge stanza (commented).
- Optional Godot text-first guidance (commented).
- A `<<<BEGIN_CUEBERT_GAME_LFS_V1>>>` … `<<<END_CUEBERT_GAME_LFS_V1>>>` span used by `scripts/install-game-lfs.sh` for idempotent merges.

**Monorepo note:** If the game lives in a subdirectory of a larger repository (for example `games/ue5/MyGame/`), Git attributes apply **relative to the repo root**. Either place `.gitattributes` at the repository root with scoped paths (for example `games/ue5/MyGame/Content/**/*.uasset filter=lfs ...`) or maintain a dedicated repository for the Unreal tree. The stock Cuebert template assumes a **single-root game project**; path-scoped variants are a team customization outside this standard.

## 6. Install helper

Path: `scripts/install-game-lfs.sh`

Typical usage from a clone of the cuebert hub:

```bash
bash scripts/install-game-lfs.sh /path/to/MyGame
```

What it does:

1. Resolves the hub root from the script location and reads the template file above.
2. If `<project-path>/.gitattributes` is **missing**, writes the **full** template.
3. If `.gitattributes` **exists**, **appends** the marked LFS block (or refreshes that block when `--force` is passed and a prior Cuebert block is present). It **never** deletes unrelated user rules.
4. Runs `git lfs install` in the target repository unless `--no-lfs-install` is set.
5. Prints next-step reminders (`git add`, `git commit`).

The helper does **not** run `git lfs track '*.uasset'` style commands: declarative `.gitattributes` rules are preferred because they are reviewable in a single diff. If operators run `git lfs track` manually, Git will mutate `.gitattributes` in equivalent ways; avoid mixing conflicting duplicates.

**Operational checklist (new game repo):**

1. Install Git LFS on workstations (`git lfs version`).
2. Run `scripts/install-game-lfs.sh <project-root>` from a cuebert hub checkout **or** merge the template manually.
3. Commit `.gitattributes` on a feature branch and announce to the team.
4. Spot-check attributes: `git check-attr filter -- path/to/example.uasset` should print `filter: lfs` once rules exist (path may be hypothetical).
5. Update CI to fetch LFS objects (§11).
6. Set `lfs_configured: true` in the hub-side profile after the game repo commit lands.

**Verification (hub reference tree):** On cuebert, `git check-attr filter -- example.uasset` should report `lfs` even though the file does not exist. Hub placeholders named `*.png.txt` must **not** match `*.png` rules; `git check-attr filter -- some/dir/file.png.txt` should stay `unspecified` for `filter`.

## 7. Merge strategy with existing `.gitattributes`

Rules for humans and for the install script:

- **No file present:** install the entire template verbatim.
- **File present, no Cuebert block:** append the `BEGIN…END` block with a short banner comment. Emit a **warning** if the file already contains any `filter=lfs` line (possible overlap with another template).
- **File present with an older Cuebert block:** without `--force`, the script should refuse to append a second block; with `--force`, replace only the delimited Cuebert span.
- **Never** strip third-party `filter=lfs` lines outside the Cuebert span.

**Collaboration tip:** When two branches both touch `.gitattributes`, treat merges like any other config merge: prefer **one** authoritative block per extension. If both sides add identical `filter=lfs` lines, Git usually auto-merges cleanly; divergent patterns (one side SmartMerge YAML, the other LFS) require human resolution — pick one policy per file type and document it in the team wiki.

## 8. History rewrite warning

Adding LFS rules **does not retroactively** move blobs that were already committed as normal Git objects. Future commits will honor the new mapping after files are re-added.

For one-shot migration of history, Git LFS supplies tools such as:

```bash
git lfs migrate import --include="*.uasset,*.umap,..."
```

**Warning:** rewriting history requires coordinated `git push --force` (or equivalent) and invalidates existing clones. Treat this as a **planned migration** with backup, communication, and CI updates — not something the hub automates.

**Communication template (internal):** “We are migrating historical `*.uasset` blobs to LFS on branch `infra/lfs-migration`. Expect force-push to `main` at {date}. Everyone must re-clone or run the documented fetch reset steps. CI caches will be wiped.” Adjust dates and branch names per your process.

## 9. Provider quotas

Approximate defaults (verify on your provider before large imports):

- **GitHub (free tier):** on the order of **1 GiB** LFS storage and **1 GiB/month** bandwidth unless billing add-ons are enabled. Large teams should purchase packs or use a dedicated remote.
- **GitLab:** bundled LFS allowance is typically **larger** on SaaS; self-managed depends on administrator configuration.
- **Gitea / self-hosted:** entirely dependent on server settings and attached object storage.

Quota exhaustion surfaces as failed `git lfs push` or HTTP 402-style errors from the remote.

**Bandwidth planning:** A fresh clone after months of art landing in LFS may download **gigabytes**. Encourage artists to use shallow clones where workflow permits (`git clone --depth 1`) and document expected first-sync time in the team handbook.

**Storage planning:** Deleted branches still retain LFS objects until garbage collection policies on the server reclaim them. Large binary churn increases storage monotonically unless operators prune.

## 10. Reproducibility and Cuebert’s M4 asset pipeline

The `/asset` flow (M4) writes raster outputs (commonly `.png`) into the game project under paths such as `Content/Art/`. Once LFS rules are active, those files should be **LFS pointers in Git** while the binary payload lives in LFS storage.

The per-project lockfile **`.cuebert-assets.lock.yaml`** (see `docs/_ai_system/standards/asset-manifest.md`) records **SHA-256** (and related metadata) for generated assets. For audits, the hash in the lockfile should match the bytes represented by the LFS object after checkout (or the smudged working-tree file).

## 11. CI / CD considerations

CI runners must have the **Git LFS client** installed and should run `git lfs install` before checkout **or** use checkout plugins that fetch LFS objects automatically.

If a job checks out **without** LFS fetch, tracked paths appear as **tiny pointer stubs** (text files containing OID metadata), not real images or audio. Tests that read binary headers will fail mysteriously unless this is understood.

Document in your pipeline:

- When to `git lfs pull` (if checkout is sparse).
- Cache strategy for LFS objects if builds are frequent.

**Troubleshooting (common cases):**

| Symptom | Likely cause | Mitigation |
|---------|--------------|------------|
| `git push` fails with LFS errors | Remote quota or credentials | Inspect provider billing / tokens for the LFS endpoint. |
| CI cannot open PNGs | Pointer stub checked out | Enable LFS in checkout; run `git lfs pull`. |
| Conflicts in `.gitattributes` | Double-installed templates | Keep one `filter=lfs` line per pattern; merge manually. |
| Repository still huge | Old commits store raw blobs | Plan `git lfs migrate import` (§8). |
| Workstation cannot push | Missing LFS CLI | Install from [git-lfs.com](https://git-lfs.com); run `git lfs install`. |

## 12. Non-goals

Cuebert’s LFS standard does **not** cover:

- Hosting or scaling LFS object servers themselves.
- Automatic migration of legacy non-LFS histories without operator intent.
- Per-artist storage enforcement.
- Perforce / Helix integrations.

**Hygiene:** Review `.gitattributes` in code review. Do not use LFS as a secrets store; use vault standards instead (`docs/_ai_system/standards/vault-standard.md`). Pin LFS client versions in CI images when practical.

**Future tooling:** Later milestones may add read-only diagnostics (for example oversize non-LFS blob detection). This document stays **normative**; any `git-lfs-toolkit` will link here rather than fork the extension matrix.

## 13. Cross-references

| Artifact | Role |
|----------|------|
| `docs/projects/_templates/game-project-gitattributes.template` | Verbatim downstream `.gitattributes` source. |
| `scripts/install-game-lfs.sh` | Idempotent installer + `git lfs install` helper. |
| `docs/_ai_system/agents/agent-ops-onboard.md` | `/onboard` flow; LFS prompt and `lfs_configured` field. |
| `docs/_ai_system/standards/asset-manifest.md` | Raster manifests, lockfiles, and trace contracts. |
| `.gitattributes` (hub root) | Reference pattern mirror (safe no-op in cuebert). |

## 14. Footer

Status: **M5-P2**. Helper script ships in M5-P2. `/onboard` integration is a **manual operator prompt** in M5-P2; optional auto-run behind a flag is explicitly deferred to **M5-P3+** planning.

Maintainers: keep this file, the template, and `.gitattributes` (hub reference) in sync when extending supported extensions.
