"""Food recognition + nutrition analysis (Modules 2 & 3).

Strategy
1. If an LLM key is configured, use the vision model (most accurate).
2. Otherwise use a local colour-matching fallback against the built-in food table.
   The fallback is a rough baseline – it can only pick among the foods it knows
   and is easily fooled by lighting – and the response says so via `method`.
"""
from __future__ import annotations

import math
import re

from . import imaging, llm
from .nutrition_db import FOODS, canonical, health_score, nutrition_for


def _colour_distance(a, b) -> float:
    # weighted Euclidean ("redmean") – closer to perceived difference than plain RGB
    rm = (a[0] + b[0]) / 2
    dr, dg, db = a[0] - b[0], a[1] - b[1], a[2] - b[2]
    return math.sqrt((2 + rm / 256) * dr * dr + 4 * dg * dg + (2 + (255 - rm) / 256) * db * db)


def _filename_hint(filename: str | None) -> str | None:
    if not filename:
        return None
    stem = re.sub(r"[^a-z ]", " ", filename.lower().rsplit(".", 1)[0])
    for word in stem.split():
        if canonical(word):
            return canonical(word)
    return None


def _colour_candidates(data: bytes, top: int = 3) -> list[dict]:
    rgb = imaging.load_rgb(data)
    mask = imaging.foreground_mask(rgb)
    centres = imaging.dominant_rgb(rgb, mask, k=3)
    scores: dict[str, float] = {}
    for rank, c in enumerate(centres):
        weight = 1.0 / (1 + rank)  # most frequent cluster counts most
        for name, f in FOODS.items():
            d = _colour_distance(c, f["rgb"])
            scores[name] = scores.get(name, 0) + weight * math.exp(-d / 120)
    total = sum(scores.values()) or 1
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])[:top]
    return [{"food": n, "confidence": round(min(0.85, s / total * 2.2), 2)} for n, s in ranked]


def recognize(data: bytes, filename: str | None = None, media_type: str = "image/jpeg") -> dict:
    imaging.load_rgb(data)  # validates the upload early (raises ValueError)
    method, items = None, None

    if llm.available():
        items = llm.identify_food_image(data, media_type, list(FOODS))
        method = "vision-llm" if items else None

    if not items:
        hint = _filename_hint(filename)
        items = _colour_candidates(data)
        method = "colour-heuristic"
        if hint:  # filename like "apple.jpg" is a strong user-provided signal
            items = [{"food": hint, "confidence": 0.9}] + [i for i in items if i["food"] != hint][:2]
            method = "filename+colour-heuristic"

    results = []
    for it in items:
        n = nutrition_for(it["food"])
        if n:
            results.append({**it, "nutrition": n})
    return {
        "method": method,
        "detected": results,
        "note": ("Colour-based fallback is approximate. Set ANTHROPIC_API_KEY for vision-model accuracy."
                 if method != "vision-llm" else "Identified with a vision model; values are estimates."),
    }


def analyze_nutrition(foods: list[dict]) -> dict:
    """foods: [{"food": "rice", "servings": 1.5}, ...] -> totals, per-item rows, health score."""
    rows, unknown = [], []
    for item in foods:
        n = nutrition_for(item.get("food", ""), float(item.get("servings", 1)))
        if n is None:
            unknown.append(item.get("food"))
            continue
        rows.append(n)
    if not rows:
        return {"items": [], "totals": None, "health_score": None, "unknown": unknown,
                "advice": ["No recognised foods were provided."]}
    t = {k: round(sum(r[k] for r in rows), 1) for k in ("kcal", "protein_g", "carbs_g", "fat_g", "fibre_g")}
    grams = sum(FOODS[r["food"]]["grams"] * r["servings"] for r in rows)
    score = health_score(t["kcal"], t["protein_g"], t["carbs_g"], t["fat_g"], t["fibre_g"], grams)
    advice = []
    if t["fibre_g"] < 5 and t["kcal"] > 300:
        advice.append("Low in fibre – add vegetables, salad or whole grains.")
    if t["protein_g"] < 12 and t["kcal"] > 300:
        advice.append("Protein is on the low side – consider dal, paneer, eggs or curd.")
    if t["fat_g"] * 9 > 0.4 * max(t["kcal"], 1):
        advice.append("More than 40% of energy comes from fat – try a less fried/oily option.")
    if not advice:
        advice.append("Balanced overall – nice choice.")
    out = {"items": rows, "totals": t, "health_score": score, "unknown": unknown, "advice": advice}
    expl = llm.explain("nutrition analysis", {"totals": t, "health_score": score})
    if expl:
        out["ai_explanation"] = expl
    return out
