"""MCP tool: batch compare matching filenames across two directories."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from _histogram import histogram_similarity
from _image_io import load_image, pillow_available
from _phash import compute_phash, hamming_distance, similarity_from_hamming
from _vision_common import (
    effective_dir_tool_mode,
    troubleshoot_commit_safe,
    validate_dir_path,
    validate_image_path,
)

logger = logging.getLogger(__name__)

_ALLOWED_EXT = frozenset({".png", ".jpg", ".jpeg", ".webp", ".tga", ".bmp"})
_MAX_TOTAL_PX = 128_000_000
_PER_IMAGE_PX = 67_108_864


def _err(code: str, message: str) -> dict[str, Any]:
    return {"code": code, "message": message}


def _list_images(root: Path) -> list[Path]:
    out: list[Path] = []
    try:
        for ch in sorted(root.iterdir(), key=lambda p: p.name.lower()):
            if ch.is_file() and ch.suffix.lower() in _ALLOWED_EXT:
                out.append(ch)
    except OSError:
        return []
    return out


def _vision_qa_compare_screenshots_impl(
    dir_a: str,
    dir_b: str,
    phash_threshold: float = 0.90,
    histogram_threshold: float = 0.85,
    max_pairs: int = 50,
    caller: str = "user-direct-debug",
) -> dict[str, Any]:
    err_a, ra = validate_dir_path(dir_a)
    err_b, rb = validate_dir_path(dir_b)
    cap = max(0, min(int(max_pairs), 200))

    mode = effective_dir_tool_mode(
        dir_a=dir_a,
        dir_b=dir_b,
        require_pillow_for_non_png=False,
        pillow_available=True,
    )

    if mode == "dry_run":
        return {
            "status": "dry_run",
            "mode": "dry_run",
            "dir_a": dir_a,
            "dir_b": dir_b,
            "pairs_compared": 3,
            "pairs_matched": 3,
            "pairs_mismatched": 0,
            "pairs_missing_in_b": 0,
            "pairs_missing_in_a": 0,
            "first_5_mismatches": [],
            "error": None,
            "memory_id": None,
        }

    assert ra is not None and rb is not None
    files_a = _list_images(ra)
    files_b = _list_images(rb)
    names_a = {p.name for p in files_a}
    names_b = {p.name for p in files_b}
    common = sorted(names_a & names_b)
    missing_in_b = sorted(names_a - names_b)
    missing_in_a = sorted(names_b - names_a)

    if not common:
        mem = troubleshoot_commit_safe(
            problem="vision_qa_compare_screenshots: no matching files",
            what_tried={"dir_a": str(ra), "dir_b": str(rb)},
            tags="severity=error,vision_qa",
            agent=caller,
        )
        mid = mem.get("id") if isinstance(mem, dict) else None
        return {
            "status": "error",
            "mode": "live",
            "dir_a": dir_a,
            "dir_b": dir_b,
            "pairs_compared": 0,
            "pairs_matched": 0,
            "pairs_mismatched": 0,
            "pairs_missing_in_b": len(missing_in_b),
            "pairs_missing_in_a": len(missing_in_a),
            "first_5_mismatches": [],
            "error": _err("vision.no_matching_files", "no common basenames between directories"),
            "memory_id": mid if isinstance(mid, str) else None,
        }

    map_a = {p.name: p for p in files_a}
    map_b = {p.name: p for p in files_b}
    pil_ok = pillow_available()
    to_compare = common[:cap]
    need_pillow = any(
        map_a[n].suffix.lower() != ".png" or map_b[n].suffix.lower() != ".png"
        for n in to_compare
    )
    if need_pillow and not pil_ok:
        return {
            "status": "dry_run",
            "mode": "dry_run",
            "dir_a": dir_a,
            "dir_b": dir_b,
            "pairs_compared": 3,
            "pairs_matched": 3,
            "pairs_mismatched": 0,
            "pairs_missing_in_b": 0,
            "pairs_missing_in_a": 0,
            "first_5_mismatches": [],
            "error": None,
            "memory_id": None,
        }

    mismatches: list[dict[str, Any]] = []
    matched = 0
    compared = 0
    px_used = 0

    for name in to_compare:
        compared += 1
        pa = map_a[name]
        pb = map_b[name]
        ea, rpa = validate_image_path(str(pa))
        eb, rpb = validate_image_path(str(pb))
        if ea or eb:
            mismatches.append(
                {
                    "filename": name,
                    "phash_similarity": 0.0,
                    "histogram_similarity": 0.0,
                },
            )
            continue
        assert rpa is not None and rpb is not None
        la = load_image(str(rpa), max_px=_PER_IMAGE_PX)
        if "error" in la:
            mismatches.append(
                {
                    "filename": name,
                    "phash_similarity": 0.0,
                    "histogram_similarity": 0.0,
                },
            )
            continue
        wa, ha = int(la["width"]), int(la["height"])
        lb = load_image(str(rpb), max_px=_PER_IMAGE_PX)
        if "error" in lb:
            mismatches.append(
                {
                    "filename": name,
                    "phash_similarity": 0.0,
                    "histogram_similarity": 0.0,
                },
            )
            continue
        wb, hb = int(lb["width"]), int(lb["height"])
        budget = wa * ha + wb * hb
        if px_used + budget > _MAX_TOTAL_PX:
            mem = troubleshoot_commit_safe(
                problem="vision_qa_compare_screenshots: pixel budget exceeded",
                what_tried={"used": px_used, "pair": name},
                tags="severity=error,vision_qa",
                agent=caller,
            )
            mid = mem.get("id") if isinstance(mem, dict) else None
            return {
                "status": "error",
                "mode": "live",
                "dir_a": dir_a,
                "dir_b": dir_b,
                "pairs_compared": compared,
                "pairs_matched": matched,
                "pairs_mismatched": len(mismatches),
                "pairs_missing_in_b": len(missing_in_b),
                "pairs_missing_in_a": len(missing_in_a),
                "first_5_mismatches": mismatches[:5],
                "error": _err("vision.pixel_budget", "decompressed pixel budget exceeded"),
                "memory_id": mid if isinstance(mid, str) else None,
            }
        px_used += budget
        pxa = bytes(la["pixels_rgb"])
        pxb = bytes(lb["pixels_rgb"])
        dist = hamming_distance(compute_phash(pxa, wa, ha), compute_phash(pxb, wb, hb))
        ph_sim = similarity_from_hamming(dist)
        hist_sim = histogram_similarity(pxa, wa, ha, pxb, wb, hb)
        dims_ok = wa == wb and ha == hb
        ok = ph_sim >= phash_threshold and hist_sim >= histogram_threshold and dims_ok
        if ok:
            matched += 1
        else:
            mismatches.append(
                {
                    "filename": name,
                    "phash_similarity": ph_sim,
                    "histogram_similarity": hist_sim,
                },
            )

    mismatched = len(mismatches)
    miss_b = len(missing_in_b)
    miss_a = len(missing_in_a)
    overall_ok = mismatched == 0 and miss_b == 0 and miss_a == 0
    st = "pass" if overall_ok else "fail"
    mem_id: str | None = None
    if st == "fail":
        mem = troubleshoot_commit_safe(
            problem="vision_qa_compare_screenshots: divergence or missing files",
            what_tried={
                "dir_a": str(ra),
                "dir_b": str(rb),
                "pairs_mismatched": mismatched,
                "pairs_missing_in_b": miss_b,
                "pairs_missing_in_a": miss_a,
                "first_5": mismatches[:5],
            },
            tags="severity=warn,vision_qa",
            agent=caller,
        )
        mid = mem.get("id") if isinstance(mem, dict) else None
        mem_id = mid if isinstance(mid, str) else None

    return {
        "status": st,
        "mode": "live",
        "dir_a": dir_a,
        "dir_b": dir_b,
        "pairs_compared": compared,
        "pairs_matched": matched,
        "pairs_mismatched": mismatched,
        "pairs_missing_in_b": miss_b,
        "pairs_missing_in_a": miss_a,
        "first_5_mismatches": mismatches[:5],
        "error": None,
        "memory_id": mem_id,
    }


def register(mcp: FastMCP) -> None:
    """Register ``vision_qa_compare_screenshots`` on the MCP server."""

    @mcp.tool()
    def vision_qa_compare_screenshots(
        dir_a: str,
        dir_b: str,
        phash_threshold: float = 0.90,
        histogram_threshold: float = 0.85,
        max_pairs: int = 50,
        caller: str = "user-direct-debug",
    ) -> dict[str, Any]:
        """Batch compare matching filenames across two directories."""
        return _vision_qa_compare_screenshots_impl(
            dir_a,
            dir_b,
            phash_threshold=phash_threshold,
            histogram_threshold=histogram_threshold,
            max_pairs=max_pairs,
            caller=caller,
        )
