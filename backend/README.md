# FoodVerse AI – Multimodal Food Intelligence Agent

A full-stack platform that analyses food through **images, video and text**:
food recognition, nutrition & health score, freshness/spoilage detection, restaurant
hygiene monitoring, smart cooking assistance, personalised meal plans, and an insights dashboard.

**Stack:** React (Vite) frontend · FastAPI backend · Python (OpenCV, NumPy, Pillow) · optional Claude LLM reasoning · SQLite history.

## Requirement → module map

| # | Requirement | Where |
|---|-------------|-------|
| 1 | Multimodal food intelligence platform | whole app (`backend/app/main.py`, `frontend/src/App.jsx`) |
| 2 | Food recognition from uploaded images | `services/recognition.py` → `POST /api/food/recognize` |
| 3 | Nutrition analysis (kcal, protein, carbs, fat, health score) | `services/recognition.py`, `nutrition_db.py` → `POST /api/food/nutrition` |
| 4 | Freshness: Fresh / Moderately Fresh / Spoiled | `services/freshness.py` → `POST /api/freshness/analyze` |
| 5 | Restaurant hygiene from kitchen video | `services/hygiene.py` → `POST /api/hygiene/analyze` |
| 6 | Smart cooking assistance | `services/cooking.py` → `/api/cooking/suggest`, `/api/cooking/ask` |
| 7 | Personalised meal plans | `services/mealplan.py` → `POST /api/mealplan/generate` |
| 8 | Combine vision + LLM reasoning | `services/llm.py` (used by every module when a key is set) |
| 9 | ReactJS + FastAPI, modular services | `frontend/`, `backend/app/services/` |
| 10 | Dashboards, alerts, summaries, guidance | `services/history.py` → `GET /api/insights`, Dashboard page |

## Run it

Prerequisites: Python 3.9+ and Node 18+.

```bash
# 1) Backend
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000               # API docs: http://localhost:8000/docs

# 2) Frontend (new terminal)
cd frontend
npm install
npm run dev                                             # http://localhost:5173
```

Optional – enable vision-LLM recognition and natural-language explanations:

```bash
export ANTHROPIC_API_KEY=sk-ant-...      # Windows PowerShell: $env:ANTHROPIC_API_KEY="sk-ant-..."
```

Without a key everything still works using local heuristics.

## Tests

```bash
cd backend && python -m pytest -q
```

Covers nutrition maths, recognition fallback, freshness ordering (fresh vs spoiled images),
hygiene scoring on synthetic good/bad kitchen videos, recipe matching, meal-plan constraints, and insights.

## Honest limitations (good to mention in your viva/report)

* **No trained deep-learning models are bundled.** Recognition without an API key is a colour-matching baseline over
  18 foods (a filename like `apple.jpg` is also used as a hint). For better accuracy plug in a food classifier
  (e.g. a Food-101 fine-tuned CNN/ViT) inside `recognition.recognize()` – the rest of the app doesn't change.
* **Freshness and hygiene are explainable heuristics** (colour, texture, region analysis), not certified food-safety tools.
  For production, replace `hygiene.analyze_frame()` with a person/hand/glove detector (e.g. YOLO).
* Nutrition values are typical-serving estimates, not lab data. Meal plans are not medical advice.
* The "audio" modality from the brief is not implemented; the pipeline accepts image, video and text.
  A natural next step is speech-to-text (e.g. Whisper) feeding `/api/cooking/ask`.

## Project layout

```
foodverse-ai/
├── backend/
│   ├── app/main.py                 FastAPI routes + validation
│   ├── app/services/               recognition, freshness, hygiene, cooking, mealplan, history, llm
│   └── tests/test_services.py
└── frontend/src/                   App.jsx, api.js, components.jsx, pages/*
```

## Submission checklist (Add Demo Link / Add GitHub Link)

1. `git init && git add . && git commit -m "FoodVerse AI"` and push to a GitHub repo → paste as the GitHub link.
2. Record a 2-3 min screen capture of each tab working → upload and paste as the demo link.
