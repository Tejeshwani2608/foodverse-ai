"""Optional LLM reasoning layer.

If ANTHROPIC_API_KEY is set, FoodVerse asks Claude for (a) vision-based food
identification and (b) natural-language explanations. Without a key every
caller falls back to the local rule-based logic, so the app always works.
Uses only the standard library (urllib) to avoid extra dependencies.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.request

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = os.getenv("FOODVERSE_MODEL", "claude-sonnet-5-5")


def available() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def _call(content: list[dict], system: str, max_tokens: int = 600) -> str | None:
    if not available():
        return None
    body = json.dumps({
        "model": MODEL,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": content}],
    }).encode()
    req = urllib.request.Request(API_URL, data=body, headers={
        "content-type": "application/json",
        "x-api-key": os.environ["ANTHROPIC_API_KEY"],
        "anthropic-version": "2023-06-01",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
        return "".join(b.get("text", "") for b in data.get("content", []))
    except Exception:  # noqa: BLE001 - network/API problems must never break the app
        return None


def identify_food_image(image_bytes: bytes, media_type: str, known: list[str]) -> list[dict] | None:
    """Ask the vision model which known foods are visible. Returns [{food, confidence}] or None."""
    b64 = base64.b64encode(image_bytes).decode()
    text = _call(
        [
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
            {"type": "text", "text": (
                "Identify the foods in this photo. Choose ONLY from this list: "
                + ", ".join(known)
                + '. Reply with JSON only: [{"food": "<name>", "confidence": <0-1>}]. '
                  "Return [] if none match.")},
        ],
        system="You are a precise food recognition module. Output valid JSON only.",
    )
    if not text:
        return None
    try:
        start, end = text.index("["), text.rindex("]") + 1
        items = json.loads(text[start:end])
        return [i for i in items if i.get("food") in known]
    except (ValueError, json.JSONDecodeError):
        return None


def explain(topic: str, facts: dict) -> str | None:
    """Short plain-language explanation of an analysis result."""
    return _call(
        [{"type": "text", "text": f"Topic: {topic}\nFacts (JSON): {json.dumps(facts)}\n"
                                  "In 2-3 sentences, explain this to a non-expert and give one practical tip. "
                                  "Do not invent numbers that are not in the facts."}],
        system="You are FoodVerse AI, a careful food-safety and nutrition assistant. "
               "You are not a doctor; avoid medical claims.",
        max_tokens=250,
    )
