---
name: vision-qa
description: Visual QA for gameplay screenshots and Gauntlet artifacts. Provides perceptual hashing, histogram diffs, rule-based checks (e.g., "screenshot must not be all black") against image files on disk. Returns structured findings consumable by agent-play-qa and /ship gates. Stdlib-first; designed to upgrade to LLM/CLIP backends without envelope changes.
version: 0.1.0
status: alpha
---

## 0. Purpose

Visual QA for gameplay screenshots and Gauntlet artifacts. Stdlib-first perceptual hashing, histogram comparison, and simple rule-based checks (dimensions, dominant colour, mean brightness, solid-colour detection). Designed to upgrade to LLM-vision or CLIP-style backends without breaking consumer envelopes: tools expose a stable `mode` field (`live` | `dry_run`) and similarity scalars that future milestones can swap to `llm_vision` or `clip_match` implementations while keeping JSON shapes stable.

## 1. Prerequisites

- Python 3.12+ (stdlib `struct`, `io`, `zlib`, `re`, `pathlib`, and related modules).
- Pillow is **optional**. If absent, the toolkit parses **PNG** via a bounded stdlib decoder (see `reference.md`). If present, additional formats are supported (JPEG, WebP, TGA, BMP) on the Pillow path.
- No GPU, no network access, and no model weights in this milestone.

## 2. Operations

| Tool | Purpose | Dry-run behavior |
| --- | --- | --- |
| `vision_qa_status` | Probe Pillow availability, supported formats, and global caps | Reports `pillow: false` when Pillow is missing or disabled; envelope `status` remains `ok` in live probe mode unless `CUEBERT_VISION_QA_MODE=dry_run` |
| `vision_qa_compare_images` | Compare two images (perceptual hash similarity, histogram cosine, dimensions) | Synthetic `phash_similarity` / `histogram_similarity` near `0.99`, matching dimensions |
| `vision_qa_check_image` | Run up to 16 rule objects against one image | All findings synthesized as `pass` |
| `vision_qa_compare_screenshots` | Batch-compare matching basenames across two directories | Synthetic batch: three pairs, zero mismatches, zero missing |

## 3. Dry-run mode

Defaults to **live** when paths resolve, caps are respected, and format support is available. The toolkit switches to **dry_run** when any of the following holds:

- `CUEBERT_VISION_QA_MODE=dry_run` is set explicitly.
- Required image paths do not exist or fail validation (after `realpath` normalization).
- Pillow is absent **and** any input requires a non-PNG format on the Pillow-only path.

Dry-run envelopes set `"mode": "dry_run"` and `"status": "dry_run"` where applicable so harnesses can continue without binary fixtures.

## 4. Security

Image parsing is treated as a high-risk surface. Controls include:

- Maximum **50 MiB** per file on disk by default (`CUEBERT_VISION_QA_MAX_IMAGE_MB` override documented in `reference.md`).
- Maximum dimensions **8192 by 8192** pixels per decoded image.
- Maximum **128 million** decompressed pixels summed across all inputs in a single tool call.
- Stdlib PNG parsing validates magic bytes, IHDR fields, and colour types before `zlib.decompress` with a bounded `bufsize`. Compressed IDAT size must not exceed **10 times** the raw RGB(A) byte budget (zip-bomb guard).
- Pillow loads set `Image.MAX_IMAGE_PIXELS` to a bounded ceiling and treat `DecompressionBombWarning` as a hard failure for that load.
- Paths are `realpath`-normalized, must exist, must be regular files (or directories for batch compare), and must use extension allowlist `{".png", ".jpg", ".jpeg", ".webp", ".tga", ".bmp"}` for raster inputs.
- **No file writes** in this toolkit. Optional future diff visualization stays behind an explicit `emit_diff` flag (default off; not enabled in M6-P3 stubs).

## 5. Rule catalogue

`vision_qa_check_image` accepts a JSON list of rule objects (maximum 16 per call). Each object includes `rule_type` and optional `params`:

```json
{
  "rule_type": "not_solid_colour | min_brightness | max_brightness | dimensions_equal | dimensions_min | dimensions_max | dominant_colour_in | mean_rgb_in_range",
  "params": {}
}
```

Required parameters and pass semantics are documented in `reference.md`. Invalid `rule_type` strings fail that single rule as `rule_type: "unknown"` while the tool continues evaluating the rest.

## 6. Memory hooks

- `vision_qa_status`: query-only; **no** `troubleshoot_commit`.
- `vision_qa_compare_images`: on visual divergence (`status: fail`) or load failure (`status: error`), emit `troubleshoot_commit` via the shared memory helper (`severity` encoded in tags: `warn` vs `error`).
- `vision_qa_check_image`: on any rule failure (`status: fail`), emit `troubleshoot_commit` with failed rule count and the first five failed rows.
- `vision_qa_compare_screenshots`: on batch divergence (`status: fail`), emit `troubleshoot_commit` with the first five mismatch records.

## 7. Examples

**Status probe**

```json
{ "tool": "vision_qa_status", "args": {} }
```

**Screenshot sanity (agent-play-qa)**

```json
{
  "tool": "vision_qa_check_image",
  "args": {
    "path": ".cuebert/traces/play/<stamp>/preview/screenshots/frame_0001.png",
    "rules": [
      { "rule_type": "not_solid_colour", "params": { "tolerance": 0.005 } },
      { "rule_type": "min_brightness", "params": { "threshold": 0.05 } },
      { "rule_type": "dimensions_min", "params": { "width": 1280, "height": 720 } }
    ],
    "caller": "agent-play-qa"
  }
}
```

**Pairwise regression**

```json
{
  "tool": "vision_qa_compare_images",
  "args": {
    "path_a": "baseline/hud.png",
    "path_b": "preview/screenshots/hud.png",
    "phash_threshold": 0.9,
    "histogram_threshold": 0.85,
    "caller": "agent-play-qa"
  }
}
```

## 8. Non-goals

- LLM-vision analysis (future backend; same envelope fields).
- CLIP or other semantic similarity backends (same upgrade path).
- 3D mesh QA, audio, haptics, or full video timelines (single-frame screenshots only).

## 9. Cross-references

- `reference.md` for envelopes, caps, and PNG layout notes.
- `unreal-build` / Gauntlet for artifact producers feeding this toolkit.
- `docs/_ai_system/agents/agent-play-qa.md` for the primary consumer contract.
- M6-P4 `build_verify` hook for first-frame screenshot gates.

## 10. Footer

Status: alpha (M6-P3). Four MCP tools ship with stdlib PNG decoding and optional Pillow. LLM-vision backends remain deferred while preserving forward-compatible envelopes.

## Appendix A — Caller attribution

Every compare and check tool accepts a `caller` string (default `user-direct-debug`). Harnesses should set this to the logical agent name (`agent-play-qa`, `build_verify`, `gauntlet-runner`, and so on) so `troubleshoot_commit` rows remain searchable in FTS5 indexes.

## Appendix B — MCP process wiring

The `cuebert-qa` MCP server group (`python .cursor/mcp-server/server.py --group qa`) auto-discovers `vision_qa_*.py` modules under `.cursor/skills/vision-qa/tools/`. Each module exports `register(mcp: FastMCP) -> None` following the `unreal-build` convention. No manual registration list exists beyond the `GROUPS["qa"]["skills"]` array in `server.py`.

## Appendix C — Operator checklist

1. Confirm screenshots exist on disk and use allowed extensions.
2. Run `vision_qa_status` once per workspace to learn whether Pillow is active.
3. Prefer PNG for deterministic stdlib parsing in CI containers without Pillow.
4. Apply `vision_qa_check_image` before promoting previews when `qa.screenshot_sane` is enforced.
5. Use `vision_qa_compare_screenshots` only after Gauntlet copies artifacts into paired folders with identical basenames.

## Appendix D — FAQ

**Why average-hash instead of DCT pHash?** Average-hash keeps the implementation pure Python with predictable cost on large screenshots. DCT or wavelet hashes are deferred to optional native backends.

**Why cosine histogram similarity?** Cosine is scale-invariant to absolute pixel counts, which stabilizes comparisons between crops with different resolutions after resize-free histogramming on full frames.

**Does dry-run touch the vault?** `vision_qa_status` may read vault keys when resolving Pillow defaults, but never writes. Other tools only read vault for Pillow enablement.

**Are writes emitted?** No. This toolkit is read-only aside from optional memory inserts via `troubleshoot_commit_safe`.

## Appendix E — Rules JSON sketch

Rules are a JSON array of objects. Each object must contain `rule_type` (string) and may contain `params` (object). Example minimal payload:

```json
[
  { "rule_type": "not_solid_colour", "params": { "tolerance": 0.005 } },
  { "rule_type": "min_brightness", "params": { "threshold": 0.05 } }
]
```

Unknown `rule_type` values produce a synthetic finding with `"rule_type": "unknown"` while the tool keeps evaluating subsequent entries. Arrays longer than 16 elements short-circuit with `status: error` and `vision.too_many_rules`.

## Appendix F — Relationship to Gauntlet

Gauntlet (M6-P2) is responsible for materializing screenshot directories under trace roots. `vision_qa_compare_screenshots` assumes operators copied or mirrored those directories so basenames line up between reference and candidate trees. When filenames differ, use `vision_qa_compare_images` for explicit pairwise comparisons instead of batch mode.
