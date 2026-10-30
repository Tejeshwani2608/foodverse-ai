"""Smart cooking assistant (Module 6): recipes, ingredient lists, steps, contextual tips."""
from __future__ import annotations

from . import llm
from .nutrition_db import canonical

RECIPES = [
    dict(name="Vegetable Poha", cuisine="Indian", minutes=20, diet=["vegan", "vegetarian"],
         ingredients=["poha", "onion", "tomato", "carrot", "peanuts", "turmeric", "mustard seeds", "curry leaves", "lemon"],
         steps=["Rinse poha gently and drain for 5 minutes.",
                "Heat oil, splutter mustard seeds, add curry leaves and peanuts.",
                "Add chopped onion, carrot and tomato; sauté 4-5 minutes.",
                "Add turmeric and salt, then the drained poha; toss gently for 3 minutes.",
                "Finish with lemon juice and coriander."],
         tips=["Don't over-soak poha – it turns mushy.", "Add peas for extra protein."]),
    dict(name="Dal Tadka", cuisine="Indian", minutes=35, diet=["vegan", "vegetarian"],
         ingredients=["dal", "onion", "tomato", "garlic", "turmeric", "cumin", "ghee"],
         steps=["Pressure-cook washed dal with turmeric and water until soft (3-4 whistles).",
                "Mash lightly and simmer with salt.",
                "In a pan heat ghee/oil, add cumin, garlic, onion, then tomato; cook until soft.",
                "Pour the tadka over the dal, mix and simmer 3 minutes."],
         tips=["Use oil instead of ghee to keep it vegan."]),
    dict(name="Paneer Bhurji", cuisine="Indian", minutes=15, diet=["vegetarian"],
         ingredients=["paneer", "onion", "tomato", "capsicum", "turmeric", "cumin", "green chilli"],
         steps=["Crumble the paneer.", "Sauté cumin, onion, chilli and capsicum.",
                "Add tomato and spices; cook until soft.", "Add paneer, cook 2-3 minutes; garnish with coriander."],
         tips=["Don't overcook paneer or it turns rubbery."]),
    dict(name="Egg Fried Rice", cuisine="Indo-Chinese", minutes=20, diet=["egg"],
         ingredients=["rice", "egg", "carrot", "onion", "soy sauce", "spring onion"],
         steps=["Use cold, day-old cooked rice.", "Scramble eggs in a hot pan and set aside.",
                "Stir-fry vegetables on high heat 2 minutes.", "Add rice, soy sauce and eggs; toss 3 minutes."],
         tips=["High heat and cold rice prevent clumping."]),
    dict(name="Tomato Soup", cuisine="Continental", minutes=25, diet=["vegan", "vegetarian"],
         ingredients=["tomato", "onion", "carrot", "garlic", "pepper"],
         steps=["Sauté onion and garlic.", "Add chopped tomato and carrot with water; simmer 15 minutes.",
                "Blend until smooth, season with salt and pepper."],
         tips=["A pinch of sugar balances acidity."]),
    dict(name="Veg Pulao", cuisine="Indian", minutes=30, diet=["vegan", "vegetarian"],
         ingredients=["rice", "carrot", "onion", "peas", "cumin", "bay leaf", "cardamom"],
         steps=["Soak rice for 20 minutes.", "Fry whole spices and onion.", "Add vegetables and rice; sauté 1 minute.",
                "Add 1.75x water, cover and cook on low heat 12-15 minutes."],
         tips=["Rest 5 minutes before fluffing."]),
    dict(name="Fruit Salad", cuisine="Any", minutes=10, diet=["vegan", "vegetarian"],
         ingredients=["apple", "banana", "orange", "lemon"],
         steps=["Wash and chop the fruit.", "Toss with a squeeze of lemon juice (prevents browning).", "Chill and serve."],
         tips=["Serve fresh; banana softens quickly."]),
    dict(name="Chicken Curry", cuisine="Indian", minutes=45, diet=["meat"],
         ingredients=["chicken", "onion", "tomato", "garlic", "ginger", "turmeric", "garam masala"],
         steps=["Sauté onion until golden, add ginger-garlic paste.", "Add tomato and spices; cook to a thick masala.",
                "Add chicken and a little water; cover and cook 20-25 minutes until internal temp is 75 °C (165 °F)."],
         tips=["Always cook chicken to a safe internal temperature."]),
]

DIET_RANK = {"vegan": 0, "vegetarian": 1, "egg": 2, "meat": 3}  # higher = less restrictive-friendly


def _allowed(recipe_diet: list[str], user_diet: str | None) -> bool:
    if not user_diet or user_diet == "any":
        return True
    if user_diet == "vegan":
        return "vegan" in recipe_diet
    if user_diet == "vegetarian":
        return "vegetarian" in recipe_diet
    if user_diet == "eggetarian":
        return "meat" not in recipe_diet
    return True


def suggest(ingredients: list[str], diet: str | None = None, max_minutes: int | None = None, limit: int = 5) -> dict:
    have = {(canonical(i) or i.strip().lower()) for i in ingredients if i.strip()}
    scored = []
    for r in RECIPES:
        if not _allowed(r["diet"], diet) or (max_minutes and r["minutes"] > max_minutes):
            continue
        need = {canonical(i) or i for i in r["ingredients"]}
        matched = sorted(need & have)
        missing = sorted(need - have)
        if not matched:
            continue
        scored.append({
            "name": r["name"], "cuisine": r["cuisine"], "minutes": r["minutes"],
            "match_percent": round(100 * len(matched) / len(need)),
            "have": matched, "missing": missing,
            "ingredients": r["ingredients"], "steps": r["steps"], "tips": r["tips"],
        })
    scored.sort(key=lambda x: (-x["match_percent"], x["minutes"]))
    return {"recipes": scored[:limit], "searched_with": sorted(have)}


def ask(question: str, context: dict | None = None) -> dict:
    """Contextual Q&A: LLM when available, otherwise keyword-based kitchen tips."""
    answer = llm.explain("cooking question", {"question": question, "context": context or {}})
    if answer:
        return {"answer": answer, "method": "llm"}
    q = question.lower()
    rules = [
        (("substitute", "replace", "instead of"), "Swap like-for-like: curd ↔ buttermilk, paneer ↔ tofu, ghee ↔ oil, "
                                                   "cream ↔ blended soaked cashews."),
        (("rice", "clump", "sticky"), "Rinse rice until the water runs clear and use 1:2 rice:water for stovetop; rest 5 minutes."),
        (("salty", "too much salt"), "Add a peeled potato, a splash of lemon or extra unsalted base (tomato/curd) and simmer."),
        (("spicy", "too hot"), "Stir in curd, cream or a little sugar/coconut milk; serve with rice or roti."),
        (("chicken", "meat", "safe"), "Cook poultry to 75 °C (165 °F) internal temperature; refrigerate leftovers within 2 hours."),
        (("store", "leftover", "fridge"), "Cool quickly, keep in airtight containers, refrigerate ≤ 3-4 days, reheat until steaming hot."),
        (("healthy", "less oil", "diet"), "Prefer steaming, baking or air-frying; use a non-stick pan and measure oil with a teaspoon."),
    ]
    for keys, tip in rules:
        if any(k in q for k in keys):
            return {"answer": tip, "method": "rules"}
    return {"answer": "Tell me what ingredients you have and your diet, and I'll suggest recipes. "
                      "For free-form Q&A, set ANTHROPIC_API_KEY.", "method": "rules"}
