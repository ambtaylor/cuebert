"""Stdlib-first image loading with optional Pillow; bounded PNG parse."""

from __future__ import annotations

import logging
import struct
import warnings
import zlib
from pathlib import Path
from typing import Any

from _vision_common import check_dimensions, max_image_bytes, pillow_env_override_off, vault_pillow_enabled

logger = logging.getLogger(__name__)

_PNG_SIG = b"\x89PNG\r\n\x1a\n"


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _unfilter_rows(
    raw: bytes,
    width: int,
    height: int,
    bpp: int,
) -> bytes:
    """Remove PNG per-byte filters; return packed pixel channels (bpp bytes per pixel)."""
    stride = width * bpp
    expected = height * (1 + stride)
    if len(raw) != expected:
        raise ValueError("png_unfilter_length_mismatch")
    out = bytearray(height * stride)
    prior = bytearray(stride)

    for y in range(height):
        off = y * (1 + stride)
        ftype = raw[off]
        row = raw[off + 1 : off + 1 + stride]
        recon = bytearray(stride)
        for x in range(stride):
            raw_x = row[x]
            left = recon[x - bpp] if x >= bpp else 0
            up = prior[x]
            up_left = prior[x - bpp] if x >= bpp else 0
            if ftype == 0:
                val = raw_x
            elif ftype == 1:
                val = (raw_x + left) & 0xFF
            elif ftype == 2:
                val = (raw_x + up) & 0xFF
            elif ftype == 3:
                val = (raw_x + ((left + up) // 2)) & 0xFF
            elif ftype == 4:
                val = (raw_x + _paeth(left, up, up_left)) & 0xFF
            else:
                raise ValueError("png_bad_filter")
            recon[x] = val
        out[y * stride : (y + 1) * stride] = recon
        prior = recon
    return bytes(out)


def _load_png_stdlib(data: bytes, max_px_budget: int) -> dict[str, Any]:
    """Parse PNG (RGB8, RGBA8, grayscale8); return envelope or {error, code}."""
    if len(data) < 8 + 8 + 13 + 4:
        return {"error": "truncated png", "code": "format_unsupported"}
    if data[:8] != _PNG_SIG:
        return {"error": "bad png signature", "code": "format_unsupported"}

    pos = 8
    idat_parts: list[bytes] = []
    width = height = bit_depth = color_type = interlace = None

    while pos + 8 <= len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        ctype = data[pos + 4 : pos + 8]
        pos += 8
        if pos + length + 4 > len(data):
            return {"error": "truncated chunk", "code": "format_unsupported"}
        chunk = data[pos : pos + length]
        pos += length
        pos += 4  # crc

        if ctype == b"IHDR":
            if length != 13:
                return {"error": "bad IHDR", "code": "format_unsupported"}
            w, h, bd, ct, comp, filt, inter = struct.unpack(">IIBBBBB", chunk)
            if comp != 0 or filt != 0:
                return {"error": "unsupported compression/filter", "code": "format_unsupported"}
            if inter != 0:
                return {"error": "interlaced png not supported", "code": "format_unsupported"}
            if bd != 8:
                return {"error": "only 8-bit depth supported", "code": "format_unsupported"}
            if ct not in (0, 2, 6):
                if ct == 3:
                    return {"error": "indexed color requires PLTE", "code": "format_unsupported"}
                if ct == 4:
                    return {"error": "grayscale+alpha not supported", "code": "format_unsupported"}
                return {"error": f"unsupported color type {ct}", "code": "format_unsupported"}
            dim_err = check_dimensions(w, h)
            if dim_err:
                return {"error": dim_err, "code": dim_err}
            if w * h > max_px_budget:
                return {"error": "pixel budget exceeded", "code": "vision.pixel_budget"}
            width, height, bit_depth, color_type, interlace = w, h, bd, ct, inter
        elif ctype == b"IDAT":
            idat_parts.append(chunk)
        elif ctype == b"IEND":
            break

    if width is None or height is None:
        return {"error": "missing IHDR", "code": "format_unsupported"}

    if color_type == 2:
        bpp = 3
    elif color_type == 6:
        bpp = 4
    else:
        bpp = 1

    raw_budget = width * height * bpp
    compressed = b"".join(idat_parts)
    if len(compressed) > 10 * max(raw_budget, 1):
        return {"error": "compressed idat too large (zip bomb guard)", "code": "vision.decompression_bomb"}

    bufsize = min(max_px_budget * 4, max(raw_budget * 2 + height, 1))
    try:
        raw = zlib.decompress(compressed, bufsize=bufsize)
    except zlib.error as exc:
        return {"error": f"zlib error: {exc}", "code": "format_unsupported"}

    try:
        planes = _unfilter_rows(raw, width, height, bpp)
    except ValueError as exc:
        return {"error": str(exc), "code": "format_unsupported"}

    if color_type == 2:
        pixels_rgb = planes
    elif color_type == 0:
        pixels_rgb = bytes(v for g in planes for v in (g, g, g))
    else:
        out = bytearray(width * height * 3)
        o = 0
        for i in range(0, len(planes), 4):
            r, g, b, a = planes[i], planes[i + 1], planes[i + 2], planes[i + 3]
            if a == 255:
                out[o], out[o + 1], out[o + 2] = r, g, b
            elif a == 0:
                out[o], out[o + 1], out[o + 2] = 0, 0, 0
            else:
                out[o] = (r * a) // 255
                out[o + 1] = (g * a) // 255
                out[o + 2] = (b * a) // 255
            o += 3
        pixels_rgb = bytes(out)

    return {
        "mode": "png_stdlib",
        "width": width,
        "height": height,
        "pixels_rgb": pixels_rgb,
    }


def _pillow_allowed() -> bool:
    if pillow_env_override_off():
        return False
    v = vault_pillow_enabled()
    if v is False:
        return False
    return True


def _try_pillow_load(
    path: Path,
    max_bytes: int,
    max_px_budget: int,
) -> dict[str, Any] | None:
    if not _pillow_allowed():
        return None
    try:
        from PIL import Image as PILImage
    except ImportError:
        return None

    try:
        cap = min(128_000_000, max_px_budget)
        PILImage.MAX_IMAGE_PIXELS = int(cap)
        with warnings.catch_warnings():
            warnings.simplefilter("error", PILImage.DecompressionBombWarning)
            with PILImage.open(path) as im:
                im.verify()
        with warnings.catch_warnings():
            warnings.simplefilter("error", PILImage.DecompressionBombWarning)
            with PILImage.open(path) as im2:
                im2 = im2.convert("RGB")
                w, h = im2.size
                dim_err = check_dimensions(w, h)
                if dim_err:
                    return {"error": dim_err, "code": dim_err}
                if w * h > max_px_budget:
                    return {"error": "pixel budget exceeded", "code": "vision.pixel_budget"}
                pixels_rgb = im2.tobytes()
        return {"mode": "pillow", "width": w, "height": h, "pixels_rgb": pixels_rgb}
    except Exception as exc:
        logger.debug("pillow load failed: %s", exc)
        return {"error": str(exc), "code": "vision.pillow_error"}


def load_image(
    path: str,
    max_bytes: int | None = None,
    max_px: int = 67_108_864,
) -> dict[str, Any]:
    """Load image to RGB bytes or return ``{error, code}``."""
    mb = max_bytes if max_bytes is not None else max_image_bytes()
    try:
        p = Path(path).expanduser().resolve(strict=True)
    except (OSError, RuntimeError):
        return {"error": "path not found", "code": "vision.path_not_found"}
    if not p.is_file():
        return {"error": "not a file", "code": "vision.not_a_file"}
    try:
        st = p.stat()
    except OSError as exc:
        return {"error": str(exc), "code": "vision.stat_failed"}
    if st.st_size > mb:
        return {"error": "file too large", "code": "vision.file_too_large"}

    pl = _try_pillow_load(p, mb, max_px)
    if pl is not None and "pixels_rgb" in pl:
        return pl
    if pl is not None and "error" in pl:
        return pl

    if p.suffix.lower() != ".png":
        if pl and pl.get("code") == "vision.pillow_error":
            return pl
        return {"error": "stdlib png only; pillow missing or disabled", "code": "format_unsupported"}

    try:
        raw_file = p.read_bytes()
    except OSError as exc:
        return {"error": str(exc), "code": "vision.io_error"}
    if len(raw_file) > mb:
        return {"error": "file too large", "code": "vision.file_too_large"}
    parsed = _load_png_stdlib(raw_file, max_px)
    if "error" in parsed:
        return {"error": parsed["error"], "code": parsed.get("code", "format_unsupported")}
    return parsed


def to_grayscale_rgb(pixels_rgb: bytes, width: int, height: int) -> bytes:
    """Single channel bytes (Y) using BT.601 integer weights."""
    n = width * height
    out = bytearray(n)
    j = 0
    for i in range(n):
        r = pixels_rgb[j]
        g = pixels_rgb[j + 1]
        b = pixels_rgb[j + 2]
        j += 3
        y = (77 * r + 150 * g + 29 * b + 128) >> 8
        out[i] = y if y <= 255 else 255
    return bytes(out)


def resize_bilinear(
    pixels: bytes,
    src_w: int,
    src_h: int,
    dst_w: int,
    dst_h: int,
    channels: int,
) -> bytes:
    """Pure-Python bilinear resize."""
    if dst_w < 1 or dst_h < 1 or src_w < 1 or src_h < 1:
        return b""
    src_stride = src_w * channels
    out = bytearray(dst_w * dst_h * channels)
    for dy in range(dst_h):
        sy = (dy + 0.5) * src_h / dst_h - 0.5
        y0 = int(sy)
        y1 = min(y0 + 1, src_h - 1)
        wy = sy - y0
        if y0 < 0:
            y0 = 0
        for dx in range(dst_w):
            sx = (dx + 0.5) * src_w / dst_w - 0.5
            x0 = int(sx)
            x1 = min(x0 + 1, src_w - 1)
            wx = sx - x0
            if x0 < 0:
                x0 = 0
            for c in range(channels):
                i00 = y0 * src_stride + x0 * channels + c
                i10 = y0 * src_stride + x1 * channels + c
                i01 = y1 * src_stride + x0 * channels + c
                i11 = y1 * src_stride + x1 * channels + c
                v00 = pixels[i00]
                v10 = pixels[i10]
                v01 = pixels[i01]
                v11 = pixels[i11]
                top = v00 * (1 - wx) + v10 * wx
                bot = v01 * (1 - wx) + v11 * wx
                val = top * (1 - wy) + bot * wy
                out[dy * dst_w * channels + dx * channels + c] = int(round(val)) & 0xFF
    return bytes(out)


def pillow_available() -> bool:
    if not _pillow_allowed():
        return False
    try:
        import PIL.Image  # noqa: F401

        return True
    except ImportError:
        return False
