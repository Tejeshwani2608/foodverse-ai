"""Small built-in nutrition table (approximate values per typical serving).

Values are rough estimates for demo/educational use, not medical data.
Each entry: serving description, grams, kcal, protein, carbs, fat (g),
fibre (g), a typical dominant RGB colour used by the fallback recognizer,
and tags used by the meal planner.
"""

FOODS = {
    "apple": dict(serving="1 medium (180 g)", grams=180, kcal=95, protein=0.5, carbs=25, fat=0.3, fibre=4.4,
                  rgb=(190, 40, 40), tags=["fruit", "vegan", "vegetarian"]),
    "banana": dict(serving="1 medium (120 g)", grams=120, kcal=105, protein=1.3, carbs=27, fat=0.4, fibre=3.1,
                   rgb=(230, 200, 70), tags=["fruit", "vegan", "vegetarian"]),
    "orange": dict(serving="1 medium (130 g)", grams=130, kcal=62, protein=1.2, carbs=15, fat=0.2, fibre=3.1,
                   rgb=(240, 140, 30), tags=["fruit", "vegan", "vegetarian"]),
    "broccoli": dict(serving="1 cup (90 g)", grams=90, kcal=31, protein=2.5, carbs=6, fat=0.3, fibre=2.4,
                     rgb=(60, 120, 50), tags=["vegetable", "vegan", "vegetarian"]),
    "carrot": dict(serving="1 medium (60 g)", grams=60, kcal=25, protein=0.6, carbs=6, fat=0.1, fibre=1.7,
                   rgb=(235, 120, 30), tags=["vegetable", "vegan", "vegetarian"]),
    "tomato": dict(serving="1 medium (120 g)", grams=120, kcal=22, protein=1.1, carbs=4.8, fat=0.2, fibre=1.5,
                   rgb=(210, 50, 40), tags=["vegetable", "vegan", "vegetarian"]),
    "rice": dict(serving="1 cup cooked (160 g)", grams=160, kcal=206, protein=4.3, carbs=45, fat=0.4, fibre=0.6,
                 rgb=(235, 230, 215), tags=["grain", "vegan", "vegetarian"]),
    "roti": dict(serving="1 roti (40 g)", grams=40, kcal=120, protein=3.5, carbs=22, fat=2.5, fibre=2.0,
                 rgb=(215, 175, 120), tags=["grain", "vegan", "vegetarian"]),
    "dal": dict(serving="1 bowl (200 g)", grams=200, kcal=198, protein=11, carbs=30, fat=4, fibre=8,
                rgb=(215, 170, 50), tags=["legume", "vegan", "vegetarian", "protein"]),
    "paneer": dict(serving="100 g", grams=100, kcal=265, protein=18, carbs=1.2, fat=20, fibre=0,
                   rgb=(245, 240, 225), tags=["dairy", "vegetarian", "protein"]),
    "egg": dict(serving="1 large (50 g)", grams=50, kcal=72, protein=6.3, carbs=0.4, fat=4.8, fibre=0,
                rgb=(250, 245, 230), tags=["egg", "protein"]),
    "chicken": dict(serving="100 g cooked", grams=100, kcal=165, protein=31, carbs=0, fat=3.6, fibre=0,
                    rgb=(200, 150, 90), tags=["meat", "protein"]),
    "salad": dict(serving="1 bowl (150 g)", grams=150, kcal=45, protein=2, carbs=8, fat=0.5, fibre=3,
                  rgb=(90, 160, 70), tags=["vegetable", "vegan", "vegetarian"]),
    "pizza": dict(serving="1 slice (110 g)", grams=110, kcal=285, protein=12, carbs=36, fat=10, fibre=2.5,
                  rgb=(215, 150, 80), tags=["fast-food", "vegetarian"]),
    "burger": dict(serving="1 burger (200 g)", grams=200, kcal=540, protein=27, carbs=40, fat=30, fibre=2,
                   rgb=(150, 100, 60), tags=["fast-food", "meat"]),
    "samosa": dict(serving="1 piece (80 g)", grams=80, kcal=260, protein=4, carbs=28, fat=15, fibre=2,
                   rgb=(200, 140, 60), tags=["fried", "vegan", "vegetarian"]),
    "idli": dict(serving="2 pieces (100 g)", grams=100, kcal=130, protein=4, carbs=26, fat=0.5, fibre=1.5,
                 rgb=(245, 243, 235), tags=["grain", "vegan", "vegetarian"]),
    "poha": dict(serving="1 plate (180 g)", grams=180, kcal=250, protein=5, carbs=45, fat=6, fibre=3,
                 rgb=(235, 205, 80), tags=["grain", "vegan", "vegetarian"]),
}

# Aliases the recognizer/cooking assistant accept.
ALIASES = {"chapati": "roti", "phulka": "roti", "lentils": "dal", "daal": "dal", "eggs": "egg",
           "tomatoes": "tomato", "apples": "apple", "bananas": "banana", "oranges": "orange",
           "carrots": "carrot", "cottage cheese": "paneer"}


def canonical(name: str) -> str | None:
    n = name.strip().lower()
    n = ALIASES.get(n, n)
    return n if n in FOODS else None


def nutrition_for(name: str, servings: float = 1.0) -> dict | None:
    key = canonical(name)
    if key is None:
        return None
    f = FOODS[key]
    return {
        "food": key,
        "serving": f["serving"],
        "servings": servings,
        "kcal": round(f["kcal"] * servings),
        "protein_g": round(f["protein"] * servings, 1),
        "carbs_g": round(f["carbs"] * servings, 1),
        "fat_g": round(f["fat"] * servings, 1),
        "fibre_g": round(f["fibre"] * servings, 1),
    }


def health_score(kcal: float, protein: float, carbs: float, fat: float, fibre: float, grams: float) -> int:
    """0-100 heuristic: reward fibre/protein density, penalise energy density and fat share."""
    grams = max(grams, 1)
    kcal_density = kcal / grams            # kcal per gram
    fat_share = (fat * 9) / max(kcal, 1)   # fraction of energy from fat
    score = 60.0
    score += min(fibre / grams * 100, 8) * 3          # up to +24
    score += min(protein / grams * 100, 20) * 0.5     # up to +10
    score -= max(kcal_density - 1.2, 0) * 12          # penalty for dense foods
    score -= max(fat_share - 0.35, 0) * 40
    return int(max(0, min(100, round(score))))
