# vision-qa reference

Detailed contract for the **vision-qa** toolkit (M6-P3). Stdlib-first decoding with optional Pillow. No subprocesses, no network I/O inside tools.

## Tool catalogue

### `vision_qa_status`

**Returns**

| Field | Type | Notes |
| --- | --- | --- |
| `status` | `ok` \| `dry_run` | `dry_run` when `CUEBERT_VISION_QA_MODE=dry_run` |
| `mode` | `live` \| `dry_run` | Effective toolkit mode |
| `pillow` | bool | `false` when Pillow missing or forced off |
| `supported_formats` | list[str] | Always includes `png`; adds raster formats when Pillow is active |
| `max_image_mb` | int | Derived from env default (50) |
| `max_decompressed_px` | int | `128000000` |
| `warnings` | list[str] | Non-fatal hints (for example stdlib-only PNG) |

**Errors:** none in normal operation; malformed host environment still returns a best-effort envelope.

### `vision_qa_compare_images`

**Args:** `path_a`, `path_b`, optional `phash_threshold` (default `0.90`), `histogram_threshold` (default `0.85`), `caller`.

**Returns:** `status` in `pass` \| `fail` \| `dry_run` \| `error`; `phash_similarity` and `histogram_similarity` in `0..1`; `dimensions_match`; `dim_a` / `dim_b` as `[w,h]` or `null` on hard failure; `error` object `{code,message}` or `null`; `memory_id` when a memory insert succeeds.

**Pass condition:** both similarities meet thresholds **and** dimensions match.

**Error modes:** invalid path, unsupported format, size or pixel budget exceeded, Pillow failure, I/O permission errors (surfaced as `vision.*` codes).

### `vision_qa_check_image`

**Args:** `path`, `rules` (list, max length **16**), optional `caller`.

**Returns:** `status` `pass` \| `fail` \| `dry_run` \| `error`; `mean_rgb` floats when decoded; `findings[]` with `{rule_type, pass, detail, params}`; `memory_id` on warn-level commits.

**Errors:** `vision.too_many_rules` when more than 16 rules are supplied; load failures mirror compare tool codes.

### `vision_qa_compare_screenshots`

**Args:** `dir_a`, `dir_b`, thresholds, `max_pairs` (default `50`, hard clamp `200`), `caller`.

**Returns:** counts for compared, matched, mismatched, missing in each directory; `first_5_mismatches` with filename plus similarity metrics; `status` union as above.

**Pass condition:** `pairs_mismatched == 0` **and** both missing counters are zero.

**Special error:** `vision.no_matching_files` when there is no shared basename between allowed raster files.

## Perceptual hash (64-bit average-hash)

This milestone implements an **8x8 average hash** (not a DCT-based pHash). The value is **not** cryptographic.

1. Decode the image to **RGB8** bytes (`width * height * 3`).
2. Convert to **grayscale** using BT.601 integer weights `Y = (77R + 150G + 29B) >> 8`.
3. **Bilinear resize** the grayscale buffer to `hash_size x hash_size` (default `8`), pure Python.
4. Compute the **arithmetic mean** of all `hash_size * hash_size` samples.
5. Emit bits in row-major order: bit `1` when `pixel >= mean`, else `0`. The MSB corresponds to the top-left sample; total bits equal `hash_size * hash_size` (64 when `hash_size` is 8).

**Hamming distance** between two hashes is the popcount of `a XOR b` masked to `hash_size * hash_size` bits.

**Similarity** is `1 - distance / (hash_size * hash_size)` clamped to `[0,1]`.

## Histogram comparison

Each channel (R, G, B) uses **32** equal bins spanning `0..255`. Counts are concatenated as `hist_R || hist_G || hist_B` (length `96`).

**Similarity** is the **cosine** of the two integer vectors. Zero vectors yield `0.0`.

## Rule catalogue (JSON)

Each rule object: `{ "rule_type": "<name>", "params": { ... } }`. Names are regex-allowlisted in code.

| `rule_type` | Params | Pass condition |
| --- | --- | --- |
| `not_solid_colour` | `tolerance` float default `0.005` (normalized `0..1`, scaled to `255` per channel vs mean) | Fraction of pixels within tolerance of the mean colour **must not** exceed `99.5%` |
| `min_brightness` | `threshold` default `0.05` | Mean luma (`0.299R+0.587G+0.114B` over `255`) **>=** threshold |
| `max_brightness` | `threshold` default `0.95` | Mean luma **<=** threshold |
| `dimensions_equal` | `width`, `height` ints | Exact dimension match |
| `dimensions_min` | `width`, `height` ints | Image **>=** both |
| `dimensions_max` | `width`, `height` ints | Image **<=** both |
| `dominant_colour_in` | `colours`: list of `[r,g,b]` ints `0..255`, `tolerance` default `0.1` | Mean RGB within tolerance (per-channel) of **any** listed colour |
| `mean_rgb_in_range` | `min`: `[r,g,b]`, `max`: `[r,g,b]` | Per-channel mean inside inclusive bounds |

**Severity:** rule failures surface as tool `status: fail` with `troubleshoot_commit` tags `severity=warn` unless the tool itself errors (`severity=error`).

## Security rails

- **File size:** default `50 MiB` per input (`CUEBERT_VISION_QA_MAX_IMAGE_MB`).
- **Dimensions:** reject when `width` or `height` is outside `1..8192`.
- **Decompressed pixels:** reject single loads above the per-call helper cap (`67_108_864` default argument) and reject combined totals above **128,000,000** pixels per MCP call for multi-input tools.
- **Zip bomb guard:** PNG IDAT compressed length must be `<= 10 * width * height * bytes_per_pixel`.
- **Magic bytes:** PNG parser requires the standard 8-byte signature before any zlib work.
- **Pillow:** `Image.MAX_IMAGE_PIXELS` clamped to `min(128_000_000, per-image budget)`; warnings promoted to errors for decompression bombs.
- **Path traversal:** every path is resolved with `Path.resolve(strict=True)` for files and directories separately.

## Dry-run semantics

Dry-run never reads pixel buffers from missing files. Envelopes still include synthetic metrics (`similarity` near `0.99`, batch summaries with three synthetic pairs) so downstream parsers remain stable.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `CUEBERT_VISION_QA_MODE` | `dry_run` forces synthetic envelopes |
| `CUEBERT_VISION_QA_MAX_IMAGE_MB` | Integer override for per-file cap (`1..500` interpreted as mebibytes-style multiplier on `1024*1024`) |
| `CUEBERT_VISION_QA_PILLOW_OK` | Set to `0`, `false`, `no`, or `off` to force the stdlib PNG path even when Pillow is installed (tests / CI) |

## Vault integration

Logical key `vision_qa.pillow_enabled` (documented tier: `shared/vision_qa/pillow_enabled`) may be set to boolean-like strings. `false` disables Pillow even when installed; `true` does not override `CUEBERT_VISION_QA_PILLOW_OK` off-switch.

## Failure modes (representative `error.code` values)

- `vision.path_not_found`, `vision.not_a_file`, `vision.extension_not_allowed`
- `vision.file_too_large`, `vision.dimensions_exceeded`, `vision.pixel_budget`
- `vision.decompression_bomb`, `format_unsupported`, `vision.pillow_error`
- `vision.io_error`, `vision.stat_failed`
- `vision.too_many_rules`, `vision.no_matching_files`

## Stdlib PNG parser (short)

Chunks follow PNG layout: `length(4) || type(4) || data || crc(4)`. `IHDR` must appear first with `bit_depth=8`, `compression=0`, `filter=0`, `interlace=0`. Supported `color_type` values: `0` (grayscale), `2` (RGB), `6` (RGBA). Indexed (`3`) and grayscale+alpha (`4`) are rejected. All `IDAT` payloads are concatenated in order and passed to `zlib.decompress` with a bounded `bufsize`. Scanlines apply PNG filters `None`, `Sub`, `Up`, `Average`, and `Paeth` per the specification.

## Proposed future tools

- `vision_qa_llm_analyze` — LLM-vision narrative QA while preserving top-level `status` and `mode`.
- `vision_qa_clip_similarity` — semantic similarity with CLIP embeddings.
- `vision_qa_diff_highlight` — optional visual diff overlays gated behind `emit_diff`.

## Example envelopes (illustrative)

### `vision_qa_status` (live, Pillow on)

```json
{
  "status": "ok",
  "mode": "live",
  "pillow": true,
  "supported_formats": ["png", "jpg", "jpeg", "webp", "tga", "bmp"],
  "max_image_mb": 50,
  "max_decompressed_px": 128000000,
  "warnings": []
}
```

### `vision_qa_compare_images` (pass)

```json
{
  "status": "pass",
  "mode": "live",
  "path_a": "/abs/a.png",
  "path_b": "/abs/b.png",
  "phash_similarity": 0.97,
  "histogram_similarity": 0.93,
  "dimensions_match": true,
  "dim_a": [1920, 1080],
  "dim_b": [1920, 1080],
  "phash_threshold": 0.9,
  "histogram_threshold": 0.85,
  "error": null,
  "memory_id": null
}
```

### `vision_qa_check_image` (fail on one rule)

```json
{
  "status": "fail",
  "mode": "live",
  "path": "/abs/frame.png",
  "width": 1920,
  "height": 1080,
  "mean_rgb": [2.1, 2.0, 2.2],
  "rules_evaluated": 2,
  "rules_failed": 1,
  "findings": [
    {
      "rule_type": "not_solid_colour",
      "pass": true,
      "detail": "solid_ratio=0.1200 mean=(2.1,2.0,2.2)",
      "params": {"tolerance": 0.005}
    },
    {
      "rule_type": "min_brightness",
      "pass": false,
      "detail": "mean_brightness=0.0082 threshold=0.05",
      "params": {"threshold": 0.05}
    }
  ],
  "error": null,
  "memory_id": "f2c2b2d2-...."
}
```

### `vision_qa_compare_screenshots` (fail with missing counterpart)

```json
{
  "status": "fail",
  "mode": "live",
  "dir_a": "/abs/preview/shots",
  "dir_b": "/abs/baseline/shots",
  "pairs_compared": 4,
  "pairs_matched": 4,
  "pairs_mismatched": 0,
  "pairs_missing_in_b": 1,
  "pairs_missing_in_a": 0,
  "first_5_mismatches": [],
  "error": null,
  "memory_id": "a1b1c1d1-...."
}
```

## Pairing algorithm (`vision_qa_compare_screenshots`)

1. Resolve both directories with `Path.resolve(strict=True)`; reject non-directories.
2. Collect immediate child files whose suffix is in the allowlist (non-recursive).
3. Build basename sets `A` and `B`; compute `common = sorted(A ∩ B)`.
4. `pairs_missing_in_b` counts files present under `dir_a` whose basename is absent from `dir_b` (same extension-aware allowlist).
5. `pairs_missing_in_a` is the symmetric gap from `dir_b`.
6. If `common` is empty, return `status: error` with `vision.no_matching_files` even when one side has orphan files.
7. Compare at most `min(max_pairs, 200)` names from `common` in lexicographic order, stopping early if the cumulative decompressed pixel budget would exceed `128_000_000`.

## Pixel budget accounting

| Tool | Budget rule |
| --- | --- |
| `vision_qa_compare_images` | `w_a*h_a + w_b*h_b <= 128_000_000` after both decodes succeed individually under `67_108_864` per image. |
| `vision_qa_check_image` | Single image `w*h <= 67_108_864` at load time. |
| `vision_qa_compare_screenshots` | Running sum across each successfully decoded pair; abort with `vision.pixel_budget` if the next pair would exceed the cap. |

## Memory helper (`troubleshoot_commit` mapping)

Tools never import the MCP memory server directly. They call `troubleshoot_commit_safe` in `_vision_common.py`, which mirrors the `unreal-build` pattern:

1. Locate `memory-toolkit/tools` adjacent to other skills.
2. Temporarily prepend that directory to `sys.path`.
3. Insert into SQLite via `_memory_db.get_db()` with `source="agent"`.
4. Return `{status:"ok", id:"<uuid>"}` or `{status:"skipped"|"error", ...}` without raising.

Tag conventions:

- `severity=warn,vision_qa` for divergence or rule failures.
- `severity=error,vision_qa` for hard errors (I/O, bombs, too many rules).

## Upgrade path (`mode` field)

Future backends should keep:

- `status` union: `pass` \| `fail` \| `dry_run` \| `error`.
- `mode` union: `live` \| `dry_run`.
- Similarity slots (`phash_similarity`, `histogram_similarity`) may later be joined by optional fields such as `semantic_similarity`, but existing consumers must continue to function when those keys are absent.

Do **not** return raw 64-bit hashes, raw histogram vectors, or latent tensors from MCP tools in this milestone; keep diagnostics in `detail` strings and memory payloads only.

## Troubleshooting

| Symptom | Likely cause | Mitigation |
| --- | --- | --- |
| `format_unsupported` on JPEG | Pillow disabled or missing | Install Pillow or convert to PNG |
| `vision.decompression_bomb` | hostile PNG | reject asset; inspect with external tools |
| `vision.pixel_budget` | 4K frames batch compared | raise `max_pairs` spacing or shrink captures |
| `pairs_missing_in_b` non-zero | harness did not copy baseline | sync Gauntlet output directories |
| Memory `skipped` | `memory-toolkit` absent | install skill; non-fatal to tool status |

## Versioning

| Artifact | Version |
| --- | --- |
| Skill metadata | `0.1.0` (`SKILL.md` frontmatter) |
| Toolkit status | `alpha` |

Breaking changes before `1.0.0` should be limited to adding optional JSON keys; removing or renaming keys requires a major bump coordinated with `agent-play-qa` and `build_verify` consumers.
