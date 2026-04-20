# ASSET PLACE — Destination Copy, Backup, Lockfile Rows

> **Role:** `/asset` harness — **Place** phase subagent (logical role)  
> **Parent protocol:** `docs/_ai_system/agents/agent-asset.md` — read **section 2.3 (Place)**, **section 9 (Lockfile)**, **section 13 (Rollback)**, and **section 6 (guards)** before executing. This document is the normative stub for the **`agent-asset-place`** roster row.  
> **Dispatch:** Only from the **`/asset`** harness. **`subagent_type`** remains **`generalPurpose`**.

---

## 1. Role

You take a **validated per-asset generate envelope** (trace-local PNG path + checksum) and a manifest **`destination`** string, then **safely copy** bytes into **`APP_REPO`** at the declared relative path. You create **backups** when overwriting, enforce **atomicity** (temp file + rename), verify **checksum** after copy, and return a **placement envelope** for the coordinator to merge into **`.cuebert-assets.lock.yaml`**. You **do not** call ComfyUI.

---

## 2. Inputs

| Input | Required | Description |
|-------|----------|-------------|
| **`APP_REPO`** | Yes | Absolute project root. |
| **`ASSET_ID`** | Yes | Stable id. |
| **`MANIFEST_DESTINATION`** | Yes | Project-relative **`destination`** string from manifest row. |
| **`TRACE_PNG_PATH`** | Yes | Absolute path to generated raster in hub trace tree. |
| **`EXPECTED_SHA256`** | Yes | Checksum from Generate envelope. |
| **`TRACE_BACKUP_DIR`** | Yes | **`.../backups/`** directory for this session. |
| **`PRIOR_LOCKFILE_ROW`** | No | Previous row for this **`id`** when updating — informs rollback checksum. |

---

## 3. Outputs

| Output | Description |
|--------|-------------|
| **`final_path`** | Repo-relative **`MANIFEST_DESTINATION`** echo. |
| **`final_sha256`** | Post-copy checksum over **`APP_REPO`** bytes. |
| **`backup_path`** | Path to **`.bak`** when a prior file existed; **`null`** when fresh write. |
| **`status`** | **`placed`**, **`failed`**, **`rolled_back`**. |

---

## 4. Scope guardrails

1. **Destination validation** — Reject **`..`**, absolute paths, and paths escaping **`APP_REPO`** after `realpath` normalization (**M5** impl).  
2. **Engine root policy** — Prefer destinations under **`Content/`**, **`Assets/`**, or declared **`defaults.destination_root`** — emit **`warn`** finding when outside (**M5**).  
3. **Read-only hub** — Do not write new files under **`HUB_REPO`** except trace backups already under **`TRACE_BACKUP_DIR`**.  
4. **No partial visible writes** — Atomic rename policy (**section 6**).  
5. **Lockfile** — Subagent returns **structured row** only; coordinator performs single atomic lockfile rewrite to avoid inter-task races (**M4-P4**).

---

## 5. Protocol

1. **Validate destination** — Normalize to absolute under **`APP_REPO`**; ensure parent directories exist (`mkdir -p` semantics) with permissions checked (**`guard.place.destination_writable`** precursor).  
2. **Verify source checksum** — Re-hash **`TRACE_PNG_PATH`**; mismatch vs **`EXPECTED_SHA256`** → **`failed`**, do not copy.  
3. **Backup** — If destination exists, copy bytes to **`TRACE_BACKUP_DIR/<ASSET_ID>.bak`** (or hashed name on collisions — **M4-P4**).  
4. **Atomic write** — Write to **`destination.tmp.<random>`** beside final name (or fixed staging name per OS), **`fsync`**, then **`rename`** into final **`destination`**.  
5. **Verify destination checksum** — Must equal **`EXPECTED_SHA256`** unless toolkit explicitly allows transcoding (**not in M4**).  
6. **Emit placement envelope** — Section 7 JSON.

---

## 6. Atomicity

**Never** leave a **partial PNG** visible at the final **`destination`**. If **`rename`** fails, delete temp and return **`failed`**. If destination had a backup, coordinator may invoke rollback (**`agent-asset.md`** section 13).

---

## 7. Output envelope (JSON shape)

```json
{
  "id": "hero_idle",
  "status": "placed",
  "final_path": "Content/Art/Heroes/hero_idle.png",
  "final_sha256": "sha256:789...",
  "backup_path": ".cuebert/traces/asset/2026-04-20T12-00-00Z/backups/hero_idle.bak",
  "notes": null
}
```

---

## 8. Rollback

When **`guard.place.lockfile_updated`** fails after a successful copy, the harness restores from **`backup_path`** when available and deletes the new partial row from the in-memory lockfile structure before rewrite.

---

## 9. Failure modes

| Failure | `status` | Notes |
|---------|----------|-------|
| Destination not writable | **`failed`** | errno evidence |
| Checksum mismatch post-copy | **`failed`** | disk corruption or race |
| Source missing on disk | **`failed`** | Generate/trace inconsistency |
| Atomic rename unsupported edge | **`failed`** | rare cross-volume — **M5** may add copy+verify fallback |

---

## 10. Relationship to post-place guards

**`guard.place.destination_writable`** and **`guard.place.lockfile_updated`** consume this envelope plus on-disk reality. See **`asset-pipeline-guards.md`**.

---

## 11. Non-goals

| Non-goal | Redirect |
|----------|----------|
| **ComfyUI calls** | `agent-asset-generate.md` |
| **`git commit`** | Operator / separate policy |
| **`.uasset` creation** | **M5** Unreal bridge |
| **Perforce checkouts** | Human / CI integration |

---

## 12. Task envelope sketch (harness → Place)

```text
## Cuebert /asset — Place
**First action:** Read docs/_ai_system/agents/agent-asset-place.md

APP_REPO: [absolute]
ASSET_ID: [id]
MANIFEST_DESTINATION: [repo-relative]
TRACE_PNG_PATH: [absolute]
EXPECTED_SHA256: [digest]
TRACE_BACKUP_DIR: [absolute]
```

---

## 13. Cross-references

| Doc | Use |
|-----|-----|
| `agent-asset.md` | Rollback + lockfile coordinator policy |
| `agent-asset-generate.md` | Upstream checksum + trace path |
| `asset-manifest.md` | Destination validation rules |
| `asset-pipeline-guards.md` | Post-place gates |
| `control-plane-paths.md` | Trace root conventions |

---

## 14. Negative examples (must REJECT)

- Attempt to place into **`../outside/`** tree → **`failed`**, **`security.path_traversal_destination`**.  
- Skip checksum verify “because it looked fine” → protocol violation.

---

## 15. Destination directory creation

When parent directories are missing, create them with default **`umask`** per harness policy (**M4-P4**). Do **not** set world-writable permissions.

---

## 16. Windows vs POSIX rename

On Windows, atomic replace of an existing destination may require **`replace`** semantics (**Python 3.3+**) — document platform branch in harness impl (**M5**). Until then, coordinator may fall back to **copy + verify + delete old** inside a **session mutex** (**M4-P4**).

---

## 17. Case sensitivity

Assume case-sensitive destinations (typical macOS/Linux dev). Windows case-insensitivity collisions (**`Hero.png`** vs **`hero.png`**) → **`failed`**, **`error_code: case_collision`** when detectable (**M5**).

---

## 18. Symlink destinations

If **`MANIFEST_DESTINATION`** resolves to a symlink pointing outside **`APP_REPO`**, **`failed`** **`security.symlink_escape`** — never follow blindly.

---

## 19. EXR reserved path

If extension is **`.exr`**, placement is allowed by manifest schema reserve — still verify binary signature in **M5** when HDR pipeline ships; **M4** treats like PNG for copy purposes only.

---

## 20. Example failure envelope

```json
{
  "id": "hero_idle",
  "status": "failed",
  "final_path": "Content/Art/Heroes/hero_idle.png",
  "final_sha256": null,
  "backup_path": null,
  "notes": "rename() failed: permission denied"
}
```

---

## 21. Example success with backup

```json
{
  "id": "hero_idle",
  "status": "placed",
  "final_path": "Content/Art/Heroes/hero_idle.png",
  "final_sha256": "sha256:789...",
  "backup_path": ".cuebert/traces/asset/2026-04-20T12-00-00Z/backups/hero_idle.bak",
  "notes": "Prior 1024-byte PNG backed up before overwrite."
}
```

---

## 22. Interaction with lockfile coordinator

Return a **`lockfile_row`** object snippet for coordinator merge:

```yaml
id: hero_idle
workflow_hash: sha256:abc...
prompt_hash: sha256:def...
params_hash: sha256:123...
seed: 42
result_path: Content/Art/Heroes/hero_idle.png
result_sha256: sha256:789...
comfyui_version: "0.3.0"
```

Exact field order is **not** normative; alphabetical sort in writer is **M4-P4** choice.

---

## 23. Partial multi-asset sessions

When batch placing, continue after single failure unless **`FAIL_FAST`** envelope flag true — mirrors generate policy (**`agent-asset.md`** section 7).

---

## 24. Read-only filesystem detection

If **`os.access(..., W_OK)`** lies (NFS quirks), catch **`PermissionError`** on temp write and map to **`failed`**, **`error_code: ro_filesystem`**.

---

## 25. Revision history

**M4-P3:** initial protocol stub.

---

Status: **M4-P3** (protocol stub). Real filesystem adapter + lockfile CAS: **M4-P4**.
