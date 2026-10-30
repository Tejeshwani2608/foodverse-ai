"""Personalised meal planning (Module 7).

Uses the Mifflin-St Jeor equation for BMR, an activity multiplier for TDEE,
and goal adjustments, then fills a 1-7 day plan from the built-in food table
under the user's diet constraints. Estimates only – not medical advice.
"""
from __future__ import annotations

import random

from .nutrition_db import FOODS

ACTIVITY = {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "active": 1.725}
GOAL_DELTA = {"lose": -400, "maintain": 0, "gain": 400}
SPLIT = {"breakfast": 0.25, "lunch": 0.35, "snack": 0.10, "dinner": 0.30}

SLOT_FOODS = {
    "breakfast": ["poha", "idli", "egg", "banana", "apple", "roti", "paneer"],
    "lunch": ["rice", "roti", "dal", "paneer", "chicken", "salad", "broccoli", "carrot"],
    "snack": ["apple", "banana", "orange", "carrot", "egg"],
    "dinner": ["roti", "dal", "paneer", "chicken", "salad", "broccoli", "tomato", "rice"],
}


def targets(age: int, sex: str, height_cm: float, weight_kg: float, activity: str, goal: str) -> dict:
    s = 5 if sex.lower().startswith("m") else -161
    bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + s
    tdee = bmr * ACTIVITY.get(activity, 1.375)
    kcal = max(1200, tdee + GOAL_DELTA.get(goal, 0))
    protein = weight_kg * (1.6 if goal == "gain" else 1.2 if goal == "lose" else 1.0)
    fat = kcal * 0.27 / 9
    carbs = max(0, (kcal - protein * 4 - fat * 9) / 4)
    bmi = weight_kg / ((height_cm / 100) ** 2)
    return {"bmr": round(bmr), "tdee": round(tdee), "kcal": round(kcal), "protein_g": round(protein),
            "carbs_g": round(carbs), "fat_g": round(fat), "bmi": round(bmi, 1)}


def _allowed(name: str, diet: str, avoid: set[str]) -> bool:
    tags = FOODS[name]["tags"]
    if name in avoid:
        return False
    if diet == "vegan":
        return "vegan" in tags
    if diet == "vegetarian":
        return "vegetarian" in tags
    if diet == "eggetarian":
        return "meat" not in tags
    return True


def _fill_slot(slot: str, kcal_target: float, pool: list[str], rng: random.Random) -> list[dict]:
    items, total = [], 0.0
    options = [f for f in SLOT_FOODS[slot] if f in pool] or pool
    tries = 0
    while total < kcal_target * 0.9 and tries < 8 and options:
        tries += 1
        name = rng.choice(options)
        k = FOODS[name]["kcal"]
        servings = max(0.5, min(3.0, round((kcal_target - total) / k * 2) / 2)) if not items else 1.0
        servings = min(servings, 2.0 if slot != "snack" else 1.0)
        if any(i["food"] == name for i in items):
            continue
        items.append({"food": name, "servings": servings, "serving": FOODS[name]["serving"],
                      "kcal": round(k * servings)})
        total += k * servings
    return items


def build_plan(profile: dict, days: int = 3, seed: int | None = None) -> dict:
    t = targets(int(profile["age"]), profile.get("sex", "male"), float(profile["height_cm"]),
                float(profile["weight_kg"]), profile.get("activity", "light"), profile.get("goal", "maintain"))
    diet = profile.get("diet", "any")
    avoid = {a.strip().lower() for a in profile.get("avoid", [])}
    pool = [n for n in FOODS if _allowed(n, diet, avoid)]
    if len(pool) < 3:
        raise ValueError("Too many restrictions: not enough foods left to build a plan.")
    rng = random.Random(seed)
    plan = []
    for d in range(1, max(1, min(days, 7)) + 1):
        meals, day_k, day_p = {}, 0, 0.0
        for slot, share in SPLIT.items():
            items = _fill_slot(slot, t["kcal"] * share, pool, rng)
            meals[slot] = items
            for i in items:
                day_k += i["kcal"]
                day_p += FOODS[i["food"]]["protein"] * i["servings"]
        plan.append({"day": d, "meals": meals, "kcal": day_k, "protein_g": round(day_p, 1)})
    notes = []
    if t["bmi"] < 18.5:
        notes.append("BMI is in the underweight range – consider talking to a doctor or dietitian.")
    elif t["bmi"] >= 30:
        notes.append("BMI is in the obese range – a doctor or dietitian can give personalised guidance.")
    notes.append("Estimates only; adjust portions to hunger and consult a professional for medical conditions.")
    return {"targets": t, "plan": plan, "notes": notes}
