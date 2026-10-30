"""FoodVerse AI – FastAPI application.

Run:  uvicorn app.main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""
from __future__ import annotations

import os
from typing import Literal

from fastapi import APIRouter, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .services import cooking, freshness, history, hygiene, llm, mealplan, recognition
from .services.nutrition_db import FOODS

MAX_IMAGE_MB = 10
MAX_VIDEO_MB = 100

app = FastAPI(title="FoodVerse AI", version="1.0.0",
              description="Multimodal food intelligence: recognition, nutrition, freshness, hygiene, cooking, meal plans.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("FOODVERSE_CORS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
    allow_methods=["*"], allow_headers=["*"],
)


async def _read(upload: UploadFile, max_mb: int, kinds: tuple[str, ...]) -> bytes:
    if upload.content_type and not upload.content_type.startswith(kinds):
        raise HTTPException(415, f"Unsupported file type '{upload.content_type}'.")
    data = await upload.read()
    if not data:
        raise HTTPException(400, "Empty file.")
    if len(data) > max_mb * 1024 * 1024:
        raise HTTPException(413, f"File too large (max {max_mb} MB).")
    return data


# ───────────────────────── system ─────────────────────────
@app.get("/api/health")
def health():
    return {"status": "ok", "llm_enabled": llm.available(), "known_foods": sorted(FOODS)}


# ───────────────────────── recognition + nutrition ─────────────────────────
food = APIRouter(prefix="/api/food", tags=["food"])


@food.post("/recognize")
async def recognize(file: UploadFile = File(...)):
    data = await _read(file, MAX_IMAGE_MB, ("image/",))
    try:
        res = recognition.recognize(data, file.filename, file.content_type or "image/jpeg")
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    return res


class FoodItem(BaseModel):
    food: str
    servings: float = Field(1.0, gt=0, le=20)


class NutritionRequest(BaseModel):
    items: list[FoodItem] = Field(..., min_length=1, max_length=30)
    log: bool = True


@food.post("/nutrition")
def nutrition(req: NutritionRequest):
    res = recognition.analyze_nutrition([i.model_dump() for i in req.items])
    if res["totals"] is None:
        raise HTTPException(422, f"No recognised foods. Known: {', '.join(sorted(FOODS))}")
    if req.log:
        history.log("nutrition", res)
    return res


# ───────────────────────── freshness ─────────────────────────
fresh = APIRouter(prefix="/api/freshness", tags=["freshness"])


@fresh.post("/analyze")
async def freshness_analyze(file: UploadFile = File(...)):
    data = await _read(file, MAX_IMAGE_MB, ("image/",))
    try:
        res = freshness.analyze(data)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    history.log("freshness", res)
    return res


# ───────────────────────── hygiene ─────────────────────────
hyg = APIRouter(prefix="/api/hygiene", tags=["hygiene"])


@hyg.post("/analyze")
async def hygiene_analyze(file: UploadFile = File(...)):
    data = await _read(file, MAX_VIDEO_MB, ("video/", "application/octet-stream"))
    suffix = os.path.splitext(file.filename or "")[1] or ".mp4"
    try:
        res = hygiene.analyze_video_bytes(data, suffix)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    history.log("hygiene", {k: v for k, v in res.items() if k != "timeline"})
    return res


# ───────────────────────── cooking ─────────────────────────
cook = APIRouter(prefix="/api/cooking", tags=["cooking"])


class SuggestRequest(BaseModel):
    ingredients: list[str] = Field(..., min_length=1, max_length=40)
    diet: Literal["any", "vegetarian", "vegan", "eggetarian"] = "any"
    max_minutes: int | None = Field(None, ge=5, le=240)


@cook.post("/suggest")
def cook_suggest(req: SuggestRequest):
    return cooking.suggest(req.ingredients, req.diet, req.max_minutes)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=500)
    context: dict | None = None


@cook.post("/ask")
def cook_ask(req: AskRequest):
    return cooking.ask(req.question, req.context)


# ───────────────────────── meal plan ─────────────────────────
plan = APIRouter(prefix="/api/mealplan", tags=["mealplan"])


class ProfileRequest(BaseModel):
    age: int = Field(..., ge=10, le=100)
    sex: Literal["male", "female"] = "male"
    height_cm: float = Field(..., ge=100, le=250)
    weight_kg: float = Field(..., ge=25, le=250)
    activity: Literal["sedentary", "light", "moderate", "active"] = "light"
    goal: Literal["lose", "maintain", "gain"] = "maintain"
    diet: Literal["any", "vegetarian", "vegan", "eggetarian"] = "any"
    avoid: list[str] = []
    days: int = Field(3, ge=1, le=7)


@plan.post("/generate")
def meal_plan(req: ProfileRequest):
    try:
        return mealplan.build_plan(req.model_dump(), req.days)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e


# ───────────────────────── insights ─────────────────────────
ins = APIRouter(prefix="/api/insights", tags=["insights"])


@ins.get("")
def get_insights():
    return history.insights()


@ins.get("/history")
def get_history(kind: str | None = None, limit: int = 50):
    return history.recent(kind, min(limit, 200))


@ins.delete("")
def clear_history():
    history.clear()
    return {"cleared": True}


for r in (food, fresh, hyg, cook, plan, ins):
    app.include_router(r)
