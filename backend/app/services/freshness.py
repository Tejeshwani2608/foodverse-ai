"""Food freshness / spoilage detection (Module 4).

Computer-vision indicators computed with OpenCV/NumPy:
  * dark/brown decay ratio     – browning, rot, bruising
  * mould-like ratio           – greyish-white/blue-green fuzzy patches
  * colour vividness           – saturation of the food region (fading = ageing)
  * surface irregularity       – speckle/edge density and brightness variance
These are combined into a 0-100 freshness score and mapped to
Fresh / Moderately Fresh / Spoiled. This is a heuristic screening aid, NOT a
food-safety guarantee: smell, storage time and dates matter too.
"""
from __future__ import annotations

import cv2
import numpy as np

from . import imaging, llm


def analyze(data: bytes) -> dict:
    rgb = imaging.load_rgb(data)
    mask = imaging.foreground_mask(rgb)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
    h, s, v = hsv[..., 0] * 2, hsv[..., 1] / 255, hsv[..., 2] / 255
    area = max(int(mask.sum()), 1)

    # dark pixels (rot/char) and brown decay (orange-brown hue, dark, moderately saturated)
    dark = float(((v < 0.22) & mask).sum() / area)
    brown = float((((h >= 15) & (h <= 45)) & (s > 0.3) & (v >= 0.15) & (v < 0.45) & mask).sum() / area)
    # mould: low-saturation light-grey/white-blue patches *inside* otherwise coloured food, or blue-green fuzz
    mouldy_grey = float((((s < 0.14) & (v > 0.55) & (v < 0.92)) & mask).sum() / area)
    mouldy_green = float((((h >= 150) & (h <= 200)) & (s > 0.25) & (v > 0.3) & mask).sum() / area)
    mould = min(1.0, mouldy_grey * 0.8 + mouldy_green)

    stats = imaging.hsv_stats(rgb, mask)
    vividness = stats["s_mean"]
    texture = imaging.texture_score(rgb, mask)
    uneven = stats["v_std"]

    penalty = (
        min(dark, 0.6) * 90
        + min(brown, 0.6) * 70
        + min(mould, 0.5) * 80
        + max(0.0, 0.45 - vividness) * 40
        + max(0.0, texture - 0.10) * 120
        + max(0.0, uneven - 0.22) * 60
    )
    score = int(round(max(0, min(100, 100 - penalty))))
    if score >= 70:
        label = "Fresh"
    elif score >= 40:
        label = "Moderately Fresh"
    else:
        label = "Spoiled"

    findings = []
    if dark > 0.12:
        findings.append(f"{dark:.0%} of the surface is very dark (possible rot or heavy bruising).")
    if brown > 0.15:
        findings.append(f"{brown:.0%} brown discolouration detected.")
    if mould > 0.12:
        findings.append("Fuzzy greyish/blue-green patches that may indicate mould.")
    if vividness < 0.25:
        findings.append("Colours look dull/faded compared with fresh produce.")
    if texture > 0.2:
        findings.append("Surface shows a lot of spots/irregular texture.")
    if not findings:
        findings.append("No visual signs of spoilage found.")

    advice = {
        "Fresh": "Looks good. Store properly and consume within the usual shelf life.",
        "Moderately Fresh": "Use soon and cook thoroughly. Cut away any bruised parts.",
        "Spoiled": "Visual signs of spoilage – when in doubt, throw it out. Never taste-test suspect food.",
    }[label]

    result = {
        "label": label,
        "freshness_score": score,
        "indicators": {
            "dark_ratio": round(dark, 3), "brown_ratio": round(brown, 3), "mould_ratio": round(mould, 3),
            "vividness": round(vividness, 3), "texture": round(texture, 3), "unevenness": round(uneven, 3),
        },
        "findings": findings,
        "advice": advice,
        "disclaimer": "Visual screening only – not a food-safety guarantee.",
    }
    expl = llm.explain("food freshness", {"label": label, "score": score, "findings": findings})
    if expl:
        result["ai_explanation"] = expl
    return result
