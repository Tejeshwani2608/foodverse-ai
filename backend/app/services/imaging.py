"""Shared image helpers (Pillow + NumPy + OpenCV)."""
from __future__ import annotations

import io

import cv2
import numpy as np
from PIL import Image


def load_rgb(data: bytes, max_side: int = 512) -> np.ndarray:
    """Decode image bytes to an RGB uint8 array, downscaled for speed."""
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Could not read image. Upload a valid JPG/PNG/WebP file.") from exc
    img.thumbnail((max_side, max_side))
    return np.asarray(img, dtype=np.uint8)


def foreground_mask(rgb: np.ndarray) -> np.ndarray:
    """Rough food mask: drop near-white/near-black/very-low-saturation backgrounds.

    Falls back to the whole frame when the mask would be almost empty.
    """
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    s, v = hsv[..., 1], hsv[..., 2]
    mask = (v > 25) & ~((s < 18) & (v > 235))
    if mask.mean() < 0.05:
        mask = np.ones_like(mask, dtype=bool)
    return mask


def hsv_stats(rgb: np.ndarray, mask: np.ndarray | None = None) -> dict:
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
    if mask is None:
        mask = np.ones(rgb.shape[:2], dtype=bool)
    h, s, v = (hsv[..., i][mask] for i in range(3))
    return {
        "h_mean": float(h.mean() * 2),  # degrees
        "s_mean": float(s.mean() / 255),
        "v_mean": float(v.mean() / 255),
        "s_std": float(s.std() / 255),
        "v_std": float(v.std() / 255),
    }


def hue_fraction(rgb: np.ndarray, lo: float, hi: float, mask: np.ndarray, min_s: float = 0.25,
                 min_v: float = 0.2, max_v: float = 1.0) -> float:
    """Fraction of masked pixels whose hue (deg) lies in [lo, hi] with enough saturation/value."""
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
    h, s, v = hsv[..., 0] * 2, hsv[..., 1] / 255, hsv[..., 2] / 255
    sel = (h >= lo) & (h <= hi) & (s >= min_s) & (v >= min_v) & (v <= max_v) & mask
    return float(sel.sum() / max(mask.sum(), 1))


def dominant_rgb(rgb: np.ndarray, mask: np.ndarray, k: int = 3) -> list[tuple[int, int, int]]:
    """Top-k cluster centres (k-means) among masked pixels, most frequent first."""
    px = rgb[mask].reshape(-1, 3).astype(np.float32)
    if len(px) > 6000:
        px = px[np.random.default_rng(0).choice(len(px), 6000, replace=False)]
    k = min(k, len(px))
    if k == 0:
        return [(128, 128, 128)]
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 15, 1.0)
    _, labels, centers = cv2.kmeans(px, k, None, crit, 3, cv2.KMEANS_PP_CENTERS)
    counts = np.bincount(labels.ravel(), minlength=k)
    order = np.argsort(-counts)
    return [tuple(int(c) for c in centers[i]) for i in order]


def texture_score(rgb: np.ndarray, mask: np.ndarray) -> float:
    """Edge density (0-1) of the masked region – a cheap texture/roughness proxy."""
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 80, 160) > 0
    return float((edges & mask).sum() / max(mask.sum(), 1))
