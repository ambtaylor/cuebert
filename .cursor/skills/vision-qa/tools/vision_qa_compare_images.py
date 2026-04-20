"""MCP tool: compare two images (phash + histogram + dimensions)."""

from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from _histogram import histogram_similarity
from _image_io import load_image, pillow_available
from _phash import compute_phash, hamming_distance, similarity_from_hamming
from _vision_common import (
    effective_tool_mode,
    troubleshoot_commit_safe,
    validate_image_path,
)

logger = logging.getLogger(__name__)

_MAX_TOTAL_PX = 128_000_000
_PER_IMAGE_PX = 67_108_864


def _err(code: str, message: str) -> dict[str, Any]:
    return {"code": code, "message": message}


def _vision_qa_compare_images_impl(
    path_a: str,
    path_b: str,
    phash_threshold: float = 0.90,
    histogram_threshold: float = 0.85,
    caller: str = "user-direct-debug",
) -> dict[str, Any]:
    err_a, rp_a = validate_image_path(path_a)
    err_b, rp_b = validate_image_path(path_b)
    pil_ok = pillow_available()
    need_pillow = False
    if rp_a is not None and rp_a.suffix.lower() != ".png":
        need_pillow = True
    if rp_b is not None and rp_b.suffix.lower() != ".png":
        need_pillow = True
    mode = effective_tool_mode(
        paths_must_exist=[path_a, path_b],
        require_pillow_for_non_png=need_pillow,
        pillow_available=pil_ok,
    )

    if mode == "dry_run":
        return {
            "status": "dry_run",
            "mode": "dry_run",
            "path_a": path_a,
            "path_b": path_b,
            "phash_similarity": 0.99,
            "histogram_similarity": 0.99,
            "dimensions_match": True,
            "dim_a": [1920, 1080],
            "dim_b": [1920, 1080],
            "phash_threshold": phash_threshold,
            "histogram_threshold": histogram_threshold,
            "error": None,
            "memory_id": None,
        }

    if err_a:
        mem = troubleshoot_commit_safe(
            problem="vision_qa_compare_images: load error",
            what_tried={"path_a": path_a, "code": err_a},
            tags="severity=error,vision_qa",
            agent=caller,
        )
        mid = mem.get("id") if isinstance(mem, dict) else None
        return {
            "status": "error",
            "mode": "live",
            "path_a": path_a,
            "path_b": path_b,
            "phash_similarity": 0.0,
            "histogram_similarity": 0.0,
            "dimensions_match": False,
            "dim_a": None,
            "dim_b": None,
            "phash_threshold": phash_threshold,
            "histogram_threshold": histogram_threshold,
            "error": _err(err_a, "path_a invalid or inaccessible"),
            "memory_id": mid if isinstance(mid, str) else None,
        }
    if err_b:
        mem = troubleshoot_commit_safe(
            problem="vision_qa_compare_images: load error",
            what_tried={"path_b": path_b, "code": err_b},
            tags="severity=error,vision_qa",
            agent=caller,
        )
        mid = mem.get("id") if isinstance(mem, dict) else None
        return {
            "status": "error",
            "mode": "live",
            "path_a": path_a,
            "path_b": path_b,
            "phash_similarity": 0.0,
            "histogram_similarity": 0.0,
            "dimensions_match": False,
            "dim_a": None,
            "dim_b": None,
            "phash_threshold": phash_threshold,
            "histogram_threshold": histogram_threshold,
            "error": _err(err_b, "path_b invalid or inaccessible"),
            "memory_id": mid if isinstance(mid, str) else None,
        }

    la = load_image(str(rp_a), max_px=_PER_IMAGE_PX)
    if "error" in la:
        mem = troubleshoot_commit_safe(
            problem="vision_qa_compare_images: load error",
            what_tried={"path_a": str(rp_a), "load": la},
            tags="severity=error,vision_qa",
            agent=caller,
        )
        mid = mem.get("id") if isinstance(mem, dict) else None
        code = str(la.get("code", "vision.load_error"))
        return {
            "status": "error",
            "mode": "live",
            "path_a": path_a,
            "path_b": path_b,
            "phash_similarity": 0.0,
            "histogram_similarity": 0.0,
            "dimensions_match": False,
            "dim_a": None,
            "dim_b": None,
            "phash_threshold": phash_threshold,
            "histogram_threshold": histogram_threshold,
            "error": _err(code, str(la.get("error", "load failed"))),
            "memory_id": mid if isinstance(mid, str) else None,
        }

    wa, ha = int(la["width"]), int(la["height"])
    lb = load_image(str(rp_b), max_px=_PER_IMAGE_PX)
    if "error" in lb:
        mem = troubleshoot_commit_safe(
            problem="vision_qa_compare_images: load error",
            what_tried={"path_b": str(rp_b), "load": lb},
            tags="severity=error,vision_qa",
            agent=caller,
        )
        mid = mem.get("id") if isinstance(mem, dict) else None
        code = str(lb.get("code", "vision.load_error"))
        return {
            "status": "error",
            "mode": "live",
            "path_a": path_a,
            "path_b": path_b,
            "phash_similarity": 0.0,
            "histogram_similarity": 0.0,
            "dimensions_match": False,
            "dim_a": [wa, ha],
            "dim_b": None,
            "phash_threshold": phash_threshold,
            "histogram_threshold": histogram_threshold,
            "error": _err(code, str(lb.get("error", "load failed"))),
            "memory_id": mid if isinstance(mid, str) else None,
        }

    wb, hb = int(lb["width"]), int(lb["height"])
    if wa * ha + wb * hb > _MAX_TOTAL_PX:
        mem = troubleshoot_commit_safe(
            problem="vision_qa_compare_images: pixel budget exceeded",
            what_tried={"pixels": wa * ha + wb * hb},
            tags="severity=error,vision_qa",
            agent=caller,
        )
        mid = mem.get("id") if isinstance(mem, dict) else None
        return {
            "status": "error",
            "mode": "live",
            "path_a": path_a,
            "path_b": path_b,
            "phash_similarity": 0.0,
            "histogram_similarity": 0.0,
            "dimensions_match": False,
            "dim_a": [wa, ha],
            "dim_b": [wb, hb],
            "phash_threshold": phash_threshold,
            "histogram_threshold": histogram_threshold,
            "error": _err("vision.pixel_budget", "combined decompressed pixels exceed cap"),
            "memory_id": mid if isinstance(mid, str) else None,
        }

    pa = bytes(la["pixels_rgb"])
    pb = bytes(lb["pixels_rgb"])
    ha_val = compute_phash(pa, wa, ha)
    hb_val = compute_phash(pb, wb, hb)
    dist = hamming_distance(ha_val, hb_val)
    ph_sim = similarity_from_hamming(dist)
    hist_sim = histogram_similarity(pa, wa, ha, pb, wb, hb)
    dims_match = wa == wb and ha == hb
    ok = (
        ph_sim >= phash_threshold
        and hist_sim >= histogram_threshold
        and dims_match
    )
    st = "pass" if ok else "fail"
    mem_id: str | None = None
    if st == "fail":
        mem = troubleshoot_commit_safe(
            problem="vision_qa_compare_images: visual divergence",
            what_tried={
                "path_a": str(rp_a),
                "path_b": str(rp_b),
                "phash_similarity": ph_sim,
                "histogram_similarity": hist_sim,
                "dimensions_match": dims_match,
            },
            tags="severity=warn,vision_qa",
            agent=caller,
        )
        mid = mem.get("id") if isinstance(mem, dict) else None
        mem_id = mid if isinstance(mid, str) else None

    return {
        "status": st,
        "mode": "live",
        "path_a": path_a,
        "path_b": path_b,
        "phash_similarity": ph_sim,
        "histogram_similarity": hist_sim,
        "dimensions_match": dims_match,
        "dim_a": [wa, ha],
        "dim_b": [wb, hb],
        "phash_threshold": phash_threshold,
        "histogram_threshold": histogram_threshold,
        "error": None,
        "memory_id": mem_id,
    }


def register(mcp: FastMCP) -> None:
    """Register ``vision_qa_compare_images`` on the MCP server."""

    @mcp.tool()
    def vision_qa_compare_images(
        path_a: str,
        path_b: str,
        phash_threshold: float = 0.90,
        histogram_threshold: float = 0.85,
        caller: str = "user-direct-debug",
    ) -> dict[str, Any]:
        """Compare two images by phash + histogram."""
        return _vision_qa_compare_images_impl(
            path_a,
            path_b,
            phash_threshold=phash_threshold,
            histogram_threshold=histogram_threshold,
            caller=caller,
        )
