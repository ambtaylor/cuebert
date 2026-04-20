"""MCP tool: run rule-based checks on a single image."""

from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from _image_io import load_image, pillow_available
from _rules import dispatch_rule
from _vision_common import effective_tool_mode, troubleshoot_commit_safe, validate_image_path

logger = logging.getLogger(__name__)

_PER_IMAGE_PX = 67_108_864


def _err(code: str, message: str) -> dict[str, Any]:
    return {"code": code, "message": message}


def _mean_rgb_tuple(pixels_rgb: bytes, width: int, height: int) -> tuple[float, float, float]:
    n = width * height
    if n <= 0:
        return 0.0, 0.0, 0.0
    sr = sg = sb = 0
    j = 0
    for _ in range(n):
        sr += pixels_rgb[j]
        sg += pixels_rgb[j + 1]
        sb += pixels_rgb[j + 2]
        j += 3
    inv = 1.0 / float(n)
    return sr * inv, sg * inv, sb * inv


def _vision_qa_check_image_impl(
    path: str,
    rules: list[dict],
    caller: str = "user-direct-debug",
) -> dict[str, Any]:
    if not isinstance(rules, list):
        rules = []
    if len(rules) > 16:
        mem = troubleshoot_commit_safe(
            problem="vision_qa_check_image: too many rules",
            what_tried={"count": len(rules)},
            tags="severity=error,vision_qa",
            agent=caller,
        )
        mid = mem.get("id") if isinstance(mem, dict) else None
        return {
            "status": "error",
            "mode": "live",
            "path": path,
            "width": None,
            "height": None,
            "mean_rgb": None,
            "rules_evaluated": 0,
            "rules_failed": 0,
            "findings": [],
            "error": _err("vision.too_many_rules", "maximum 16 rules per call"),
            "memory_id": mid if isinstance(mid, str) else None,
        }

    err, rp = validate_image_path(path)
    pil_ok = pillow_available()
    need_pillow = bool(rp is not None and rp.suffix.lower() != ".png")
    mode = effective_tool_mode(
        paths_must_exist=[path],
        require_pillow_for_non_png=need_pillow,
        pillow_available=pil_ok,
    )

    if mode == "dry_run":
        findings = []
        for i, rule in enumerate(rules[:16]):
            rt = str((rule or {}).get("rule_type") or "unknown")
            findings.append(
                {
                    "rule_type": rt if rt else "unknown",
                    "pass": True,
                    "detail": "dry_run synthetic pass",
                    "params": (rule or {}).get("params") if isinstance(rule, dict) else {},
                },
            )
        return {
            "status": "dry_run",
            "mode": "dry_run",
            "path": path,
            "width": 1920,
            "height": 1080,
            "mean_rgb": [0.5, 0.5, 0.5],
            "rules_evaluated": len(findings),
            "rules_failed": 0,
            "findings": findings,
            "error": None,
            "memory_id": None,
        }

    if err:
        mem = troubleshoot_commit_safe(
            problem="vision_qa_check_image: path error",
            what_tried={"path": path, "code": err},
            tags="severity=error,vision_qa",
            agent=caller,
        )
        mid = mem.get("id") if isinstance(mem, dict) else None
        return {
            "status": "error",
            "mode": "live",
            "path": path,
            "width": None,
            "height": None,
            "mean_rgb": None,
            "rules_evaluated": 0,
            "rules_failed": 0,
            "findings": [],
            "error": _err(err, "path invalid or inaccessible"),
            "memory_id": mid if isinstance(mid, str) else None,
        }

    assert rp is not None
    loaded = load_image(str(rp), max_px=_PER_IMAGE_PX)
    if "error" in loaded:
        mem = troubleshoot_commit_safe(
            problem="vision_qa_check_image: load error",
            what_tried={"path": str(rp), "load": loaded},
            tags="severity=error,vision_qa",
            agent=caller,
        )
        mid = mem.get("id") if isinstance(mem, dict) else None
        code = str(loaded.get("code", "vision.load_error"))
        return {
            "status": "error",
            "mode": "live",
            "path": path,
            "width": None,
            "height": None,
            "mean_rgb": None,
            "rules_evaluated": 0,
            "rules_failed": 0,
            "findings": [],
            "error": _err(code, str(loaded.get("error", "load failed"))),
            "memory_id": mid if isinstance(mid, str) else None,
        }

    w = int(loaded["width"])
    h = int(loaded["height"])
    pixels = bytes(loaded["pixels_rgb"])
    mr, mg, mb = _mean_rgb_tuple(pixels, w, h)
    findings: list[dict[str, Any]] = []
    failed = 0
    for rule in rules:
        if not isinstance(rule, dict):
            findings.append(
                {
                    "rule_type": "unknown",
                    "pass": False,
                    "detail": "rule entry must be an object",
                    "params": {},
                },
            )
            failed += 1
            continue
        params = rule.get("params") if isinstance(rule.get("params"), dict) else {}
        disp = dispatch_rule({"rule_type": rule.get("rule_type"), "params": params}, pixels, w, h)
        passed = bool(disp["pass"])
        if not passed:
            failed += 1
        findings.append(
            {
                "rule_type": disp["rule_type"],
                "pass": passed,
                "detail": disp["detail"],
                "params": params,
            },
        )

    st = "pass" if failed == 0 else "fail"
    mem_id: str | None = None
    if st == "fail":
        failed_rules = [f for f in findings if not f["pass"]][:5]
        mem = troubleshoot_commit_safe(
            problem="vision_qa_check_image: rule failures",
            what_tried={
                "path": str(rp),
                "rules_failed": failed,
                "first_failed": failed_rules,
            },
            tags="severity=warn,vision_qa",
            agent=caller,
        )
        mid = mem.get("id") if isinstance(mem, dict) else None
        mem_id = mid if isinstance(mid, str) else None

    return {
        "status": st,
        "mode": "live",
        "path": path,
        "width": w,
        "height": h,
        "mean_rgb": [mr, mg, mb],
        "rules_evaluated": len(findings),
        "rules_failed": failed,
        "findings": findings,
        "error": None,
        "memory_id": mem_id,
    }


def register(mcp: FastMCP) -> None:
    """Register ``vision_qa_check_image`` on the MCP server."""

    @mcp.tool()
    def vision_qa_check_image(
        path: str,
        rules: list[dict],
        caller: str = "user-direct-debug",
    ) -> dict[str, Any]:
        """Run up to 16 rule-based checks against a single image."""
        return _vision_qa_check_image_impl(path, rules, caller=caller)
