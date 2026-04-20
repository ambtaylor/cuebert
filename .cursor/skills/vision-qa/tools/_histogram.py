"""RGB histogram (per-channel bins) and cosine similarity."""

from __future__ import annotations


def compute_histogram(
    pixels_rgb: bytes,
    width: int,
    height: int,
    bins: int = 32,
) -> list[int]:
    """Flattened histogram length ``3 * bins`` (R, G, B concatenated)."""
    hist_r = [0] * bins
    hist_g = [0] * bins
    hist_b = [0] * bins
    n = width * height
    j = 0
    for _ in range(n):
        r = pixels_rgb[j]
        g = pixels_rgb[j + 1]
        b = pixels_rgb[j + 2]
        j += 3
        br = min(r * bins // 256, bins - 1)
        bg = min(g * bins // 256, bins - 1)
        bb = min(b * bins // 256, bins - 1)
        hist_r[br] += 1
        hist_g[bg] += 1
        hist_b[bb] += 1
    return hist_r + hist_g + hist_b


def cosine_similarity(a: list[int], b: list[int]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b, strict=True):
        dot += float(x) * float(y)
        na += float(x) * float(x)
        nb += float(y) * float(y)
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    val = dot / (na ** 0.5 * nb ** 0.5)
    return max(0.0, min(1.0, val))


def histogram_similarity(
    pixels_a: bytes,
    w_a: int,
    h_a: int,
    pixels_b: bytes,
    w_b: int,
    h_b: int,
    bins: int = 32,
) -> float:
    ha = compute_histogram(pixels_a, w_a, h_a, bins=bins)
    hb = compute_histogram(pixels_b, w_b, h_b, bins=bins)
    return cosine_similarity(ha, hb)
