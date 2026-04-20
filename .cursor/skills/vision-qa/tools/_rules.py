"""Rule-based single-image checks (regex-allowlisted rule_type)."""

from __future__ import annotations

import re
from typing import Any

_RULE_TYPE_RE = re.compile(
    r"^(not_solid_colour|min_brightness|max_brightness|dimensions_equal|"
    r"dimensions_min|dimensions_max|dominant_colour_in|mean_rgb_in_range)$",
)


def _mean_rgb(pixels_rgb: bytes, width: int, height: int) -> tuple[float, float, float]:
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


def _mean_brightness(pixels_rgb: bytes, width: int, height: int) -> float:
    n = width * height
    if n <= 0:
        return 0.0
    total = 0.0
    j = 0
    for _ in range(n):
        r = pixels_rgb[j]
        g = pixels_rgb[j + 1]
        b = pixels_rgb[j + 2]
        j += 3
        y = 0.299 * r + 0.587 * g + 0.114 * b
        total += y / 255.0
    return total / float(n)


def rule_not_solid_colour(
    pixels_rgb: bytes,
    width: int,
    height: int,
    params: dict[str, Any],
) -> dict[str, Any]:
    tol = float(params.get("tolerance", 0.005))
    tol = max(0.0, min(1.0, tol))
    mr, mg, mb = _mean_rgb(pixels_rgb, width, height)
    thr = tol * 255.0
    n = width * height
    near = 0
    j = 0
    for _ in range(n):
        r = float(pixels_rgb[j])
        g = float(pixels_rgb[j + 1])
        b = float(pixels_rgb[j + 2])
        j += 3
        if max(abs(r - mr), abs(g - mg), abs(b - mb)) <= thr:
            near += 1
    ratio = near / float(n) if n else 1.0
    ok = ratio <= 0.995
    detail = f"solid_ratio={ratio:.4f} mean=({mr:.1f},{mg:.1f},{mb:.1f})"
    return {"pass": ok, "detail": detail}


def rule_min_brightness(
    pixels_rgb: bytes,
    width: int,
    height: int,
    params: dict[str, Any],
) -> dict[str, Any]:
    th = float(params.get("threshold", 0.05))
    b = _mean_brightness(pixels_rgb, width, height)
    ok = b >= th
    return {"pass": ok, "detail": f"mean_brightness={b:.4f} threshold={th}"}


def rule_max_brightness(
    pixels_rgb: bytes,
    width: int,
    height: int,
    params: dict[str, Any],
) -> dict[str, Any]:
    th = float(params.get("threshold", 0.95))
    b = _mean_brightness(pixels_rgb, width, height)
    ok = b <= th
    return {"pass": ok, "detail": f"mean_brightness={b:.4f} threshold={th}"}


def rule_dimensions_equal(
    _pixels_rgb: bytes,
    width: int,
    height: int,
    params: dict[str, Any],
) -> dict[str, Any]:
    ew = int(params.get("width", -1))
    eh = int(params.get("height", -1))
    ok = width == ew and height == eh
    return {
        "pass": ok,
        "detail": f"actual={width}x{height} expected={ew}x{eh}",
    }


def rule_dimensions_min(
    _pixels_rgb: bytes,
    width: int,
    height: int,
    params: dict[str, Any],
) -> dict[str, Any]:
    mw = int(params.get("width", 0))
    mh = int(params.get("height", 0))
    ok = width >= mw and height >= mh
    return {"pass": ok, "detail": f"actual={width}x{height} min={mw}x{mh}"}


def rule_dimensions_max(
    _pixels_rgb: bytes,
    width: int,
    height: int,
    params: dict[str, Any],
) -> dict[str, Any]:
    mw = int(params.get("width", 10**9))
    mh = int(params.get("height", 10**9))
    ok = width <= mw and height <= mh
    return {"pass": ok, "detail": f"actual={width}x{height} max={mw}x{mh}"}


def rule_dominant_colour_in(
    pixels_rgb: bytes,
    width: int,
    height: int,
    params: dict[str, Any],
) -> dict[str, Any]:
    tol = float(params.get("tolerance", 0.1))
    tol = max(0.0, min(1.0, tol))
    colours = params.get("colours") or []
    mr, mg, mb = _mean_rgb(pixels_rgb, width, height)
    thr = tol * 255.0
    ok = False
    for c in colours:
        if not isinstance(c, (list, tuple)) or len(c) != 3:
            continue
        cr, cg, cb = float(c[0]), float(c[1]), float(c[2])
        if max(abs(mr - cr), abs(mg - cg), abs(mb - cb)) <= thr:
            ok = True
            break
    detail = f"mean=({mr:.1f},{mg:.1f},{mb:.1f}) tol={tol}"
    return {"pass": ok, "detail": detail}


def rule_mean_rgb_in_range(
    pixels_rgb: bytes,
    width: int,
    height: int,
    params: dict[str, Any],
) -> dict[str, Any]:
    lo = params.get("min") or [0, 0, 0]
    hi = params.get("max") or [255, 255, 255]
    mr, mg, mb = _mean_rgb(pixels_rgb, width, height)
    lr, lg, lb = float(lo[0]), float(lo[1]), float(lo[2])
    hr, hg, hb = float(hi[0]), float(hi[1]), float(hi[2])
    ok = lr <= mr <= hr and lg <= mg <= hg and lb <= mb <= hb
    return {
        "pass": ok,
        "detail": f"mean=({mr:.1f},{mg:.1f},{mb:.1f}) range=({lr},{lg},{lb})-({hr},{hg},{hb})",
    }


def dispatch_rule(
    rule: dict[str, Any],
    pixels_rgb: bytes,
    width: int,
    height: int,
) -> dict[str, Any]:
    rt = str(rule.get("rule_type") or "")
    params = rule.get("params") if isinstance(rule.get("params"), dict) else {}
    if not isinstance(params, dict):
        params = {}
    if not _RULE_TYPE_RE.match(rt):
        return {
            "rule_type": "unknown",
            "pass": False,
            "detail": f"unrecognized rule_type {rt!r}",
            "error": "invalid_rule_type",
        }
    try:
        if rt == "not_solid_colour":
            out = rule_not_solid_colour(pixels_rgb, width, height, params)
        elif rt == "min_brightness":
            out = rule_min_brightness(pixels_rgb, width, height, params)
        elif rt == "max_brightness":
            out = rule_max_brightness(pixels_rgb, width, height, params)
        elif rt == "dimensions_equal":
            out = rule_dimensions_equal(pixels_rgb, width, height, params)
        elif rt == "dimensions_min":
            out = rule_dimensions_min(pixels_rgb, width, height, params)
        elif rt == "dimensions_max":
            out = rule_dimensions_max(pixels_rgb, width, height, params)
        elif rt == "dominant_colour_in":
            out = rule_dominant_colour_in(pixels_rgb, width, height, params)
        else:
            out = rule_mean_rgb_in_range(pixels_rgb, width, height, params)
        return {
            "rule_type": rt,
            "pass": bool(out["pass"]),
            "detail": str(out["detail"]),
            "error": None,
        }
    except Exception as exc:
        return {
            "rule_type": rt,
            "pass": False,
            "detail": str(exc),
            "error": "rule_evaluation_error",
        }
