"""8x8 average-hash style 64-bit perceptual fingerprint (not cryptographic DCT-phash)."""

from __future__ import annotations

from _image_io import resize_bilinear, to_grayscale_rgb


def compute_phash(pixels_rgb: bytes, width: int, height: int, hash_size: int = 8) -> int:
    """64-bit hash: grayscale, resize to hash_size^2, threshold by mean, row-major MSB-first."""
    gray = to_grayscale_rgb(pixels_rgb, width, height)
    small = resize_bilinear(gray, width, height, hash_size, hash_size, channels=1)
    n = hash_size * hash_size
    total = sum(small)
    mean = total / n if n else 0.0
    h = 0
    for i in range(n):
        h = (h << 1) | (1 if small[i] >= mean else 0)
    return h


def hamming_distance(a: int, b: int, hash_size: int = 8) -> int:
    bits = hash_size * hash_size
    mask = (1 << bits) - 1
    return bin((a ^ b) & mask).count("1")


def similarity_from_hamming(dist: int, hash_size: int = 8) -> float:
    denom = float(hash_size * hash_size)
    if denom <= 0:
        return 0.0
    sim = 1.0 - (dist / denom)
    return max(0.0, min(1.0, sim))
