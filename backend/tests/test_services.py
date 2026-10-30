"""Tests for the AI/service layer (no web framework needed).

Synthetic images/videos are generated on the fly so the suite is self-contained.
"""
import io
import os
import tempfile

import cv2
import numpy as np
import pytest
from PIL import Image

os.environ["FOODVERSE_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ.pop("ANTHROPIC_API_KEY", None)

from app.services import cooking, freshness, history, hygiene, mealplan, recognition  # noqa: E402
from app.services.nutrition_db import FOODS, canonical, nutrition_for  # noqa: E402


def png(arr: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(arr.astype(np.uint8)).save(buf, "PNG")
    return buf.getvalue()


def blob(rgb, size=200, bg=(255, 255, 255)):
    """Coloured disc on a white background, with mild texture noise."""
    img = np.full((size, size, 3), bg, np.uint8)
    cv2.circle(img, (size // 2, size // 2), size // 3, rgb[::-1][::-1], -1)
    noise = np.random.default_rng(1).normal(0, 4, img.shape)
    return np.clip(img + noise, 0, 255)


# ───────────── nutrition ─────────────
def test_aliases_and_scaling():
    assert canonical("Chapati") == "roti"
    n = nutrition_for("rice", 2)
    assert n["kcal"] == FOODS["rice"]["kcal"] * 2
    assert nutrition_for("unobtainium") is None


def test_nutrition_totals_and_score():
    res = recognition.analyze_nutrition([{"food": "dal", "servings": 1}, {"food": "roti", "servings": 2},
                                         {"food": "salad", "servings": 1}, {"food": "ghost"}])
    assert res["totals"]["kcal"] == 198 + 240 + 45
    assert res["unknown"] == ["ghost"]
    assert 0 <= res["health_score"] <= 100
    junk = recognition.analyze_nutrition([{"food": "burger"}, {"food": "samosa", "servings": 2}])
    assert junk["health_score"] < res["health_score"]


def test_nutrition_empty():
    assert recognition.analyze_nutrition([{"food": "nothing"}])["totals"] is None


# ───────────── recognition ─────────────
def test_recognition_filename_hint():
    res = recognition.recognize(png(blob((200, 40, 40))), "my_apple.png", "image/png")
    assert res["detected"][0]["food"] == "apple"
    assert "filename" in res["method"]


def test_recognition_colour_fallback_returns_known_foods():
    res = recognition.recognize(png(blob((235, 120, 30))), "img001.png", "image/png")
    assert res["method"] == "colour-heuristic"
    assert res["detected"] and all(d["food"] in FOODS for d in res["detected"])
    assert res["detected"][0]["food"] in {"carrot", "orange", "samosa", "roti", "pizza", "poha"}


def test_recognition_rejects_garbage():
    with pytest.raises(ValueError):
        recognition.recognize(b"not an image")


# ───────────── freshness ─────────────
def fresh_img():
    img = np.full((220, 220, 3), 255, np.uint8)
    cv2.circle(img, (110, 110), 80, (220, 40, 40), -1)  # vivid red, uniform
    return np.clip(img + np.random.default_rng(2).normal(0, 3, img.shape), 0, 255)


def spoiled_img():
    img = np.full((220, 220, 3), 255, np.uint8)
    cv2.circle(img, (110, 110), 80, (90, 55, 30), -1)           # dull brown base
    rng = np.random.default_rng(3)
    for _ in range(60):                                          # dark rot spots
        x, y = rng.integers(40, 180, 2)
        cv2.circle(img, (int(x), int(y)), int(rng.integers(3, 12)), (20, 15, 10), -1)
    for _ in range(40):                                          # greyish mould fuzz
        x, y = rng.integers(40, 180, 2)
        cv2.circle(img, (int(x), int(y)), int(rng.integers(3, 9)), (170, 175, 170), -1)
    return img


def test_freshness_orders_fresh_above_spoiled():
    f = freshness.analyze(png(fresh_img()))
    s = freshness.analyze(png(spoiled_img()))
    assert f["freshness_score"] > s["freshness_score"] + 25
    assert f["label"] == "Fresh"
    assert s["label"] in {"Spoiled", "Moderately Fresh"}
    assert s["findings"] and "disclaimer" in s


# ───────────── hygiene ─────────────
def make_video(path, frame_fn, n=30, size=(320, 240), fps=10):
    w = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), fps, size)
    assert w.isOpened(), "OpenCV cannot write mp4v in this environment"
    for i in range(n):
        w.write(frame_fn(i, size))
    w.release()


def good_frame(i, size):
    w, h = size
    f = np.full((h, w, 3), (235, 235, 235), np.uint8)                      # clean steel/white counters
    cv2.rectangle(f, (110, 0), (210, int(h * 0.26)), (255, 200, 120), -1)  # blue cap (BGR) in top band
    cv2.rectangle(f, (90, int(h * 0.4)), (230, int(h * 0.7)), (200, 90, 40), -1)  # blue gloves (BGR)
    return f


def bad_frame(i, size):
    w, h = size
    f = np.full((h, w, 3), (50, 60, 70), np.uint8)                          # grimy dark
    rng = np.random.default_rng(i)
    f = np.clip(f + rng.normal(0, 25, f.shape), 0, 255).astype(np.uint8)    # clutter
    cv2.rectangle(f, (110, 0), (210, int(h * 0.26)), (90, 130, 190), -1)    # skin/hair on head (BGR)
    cv2.rectangle(f, (90, int(h * 0.4)), (230, int(h * 0.7)), (120, 160, 220), -1)  # bare skin hands (BGR)
    return f


def test_hygiene_good_vs_bad_video(tmp_path):
    g, b = str(tmp_path / "good.mp4"), str(tmp_path / "bad.mp4")
    make_video(g, good_frame)
    make_video(b, bad_frame)
    rg, rb = hygiene.analyze_video_path(g), hygiene.analyze_video_path(b)
    assert rg["overall_score"] > rb["overall_score"] + 20
    assert rg["status"] in {"Compliant", "Needs attention"}
    assert rb["status"] in {"Non-compliant", "Needs attention"} and rb["alerts"]
    assert rg["frames_analyzed"] > 5 and rg["timeline"]


def test_hygiene_bad_file():
    with pytest.raises(ValueError):
        hygiene.analyze_video_bytes(b"definitely not a video")


# ───────────── cooking ─────────────
def test_recipe_matching_and_diet_filter():
    r = cooking.suggest(["Dal", "onion", "tomato", "garlic", "cumin"], diet="vegan")
    assert r["recipes"][0]["name"] == "Dal Tadka"
    assert all("Chicken" not in x["name"] and "Egg" not in x["name"] for x in r["recipes"])
    assert cooking.suggest(["chicken", "onion"], diet="vegetarian")["recipes"] == [] or \
        all("Chicken" not in x["name"] for x in cooking.suggest(["chicken", "onion"], diet="vegetarian")["recipes"])


def test_cooking_ask_rules():
    assert "75" in cooking.ask("is chicken safe to eat?")["answer"]


# ───────────── meal plan ─────────────
PROFILE = dict(age=21, sex="male", height_cm=175, weight_kg=70, activity="moderate", goal="maintain", diet="vegetarian")


def test_targets_mifflin():
    t = mealplan.targets(21, "male", 175, 70, "moderate", "maintain")
    assert t["bmr"] == round(10 * 70 + 6.25 * 175 - 5 * 21 + 5)
    assert mealplan.targets(21, "male", 175, 70, "moderate", "lose")["kcal"] < t["kcal"]


def test_plan_respects_diet_and_calories():
    out = mealplan.build_plan(PROFILE, days=3, seed=7)
    assert len(out["plan"]) == 3
    for day in out["plan"]:
        foods = {i["food"] for m in day["meals"].values() for i in m}
        assert not foods & {"chicken", "burger"}
        assert abs(day["kcal"] - out["targets"]["kcal"]) < out["targets"]["kcal"] * 0.5


def test_plan_impossible_constraints():
    with pytest.raises(ValueError):
        mealplan.build_plan({**PROFILE, "diet": "vegan", "avoid": list(FOODS)}, 1)


# ───────────── history / insights ─────────────
def test_insights_roundtrip():
    history.clear()
    history.log("nutrition", recognition.analyze_nutrition([{"food": "burger"}]))
    history.log("freshness", {"label": "Spoiled", "freshness_score": 20})
    out = history.insights()
    titles = {c["title"] for c in out["cards"]}
    assert {"Avg. meal calories", "Freshness checks"} <= titles
    assert any(a["level"] == "danger" for a in out["alerts"])
    history.clear()
    assert history.insights()["total_events"] == 0
