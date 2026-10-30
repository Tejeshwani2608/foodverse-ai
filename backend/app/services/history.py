"""SQLite event log + insights/alerts (Module 10)."""
from __future__ import annotations

import json
import os
import sqlite3
import time
from contextlib import closing

DB_PATH = os.getenv("FOODVERSE_DB", os.path.join(os.path.dirname(__file__), "..", "..", "data", "foodverse.db"))


def _conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, kind TEXT, payload TEXT)")
    return c


def log(kind: str, payload: dict) -> None:
    with closing(_conn()) as c, c:
        c.execute("INSERT INTO events (ts, kind, payload) VALUES (?,?,?)", (time.time(), kind, json.dumps(payload)))


def recent(kind: str | None = None, limit: int = 50) -> list[dict]:
    with closing(_conn()) as c:
        q = "SELECT id, ts, kind, payload FROM events" + (" WHERE kind=?" if kind else "") + " ORDER BY id DESC LIMIT ?"
        rows = c.execute(q, (kind, limit) if kind else (limit,)).fetchall()
    return [{"id": r[0], "ts": r[1], "kind": r[2], "data": json.loads(r[3])} for r in rows]


def clear() -> None:
    with closing(_conn()) as c, c:
        c.execute("DELETE FROM events")


def insights() -> dict:
    ev = recent(limit=500)
    by = lambda k: [e for e in ev if e["kind"] == k]  # noqa: E731
    nutrition, fresh, hyg = by("nutrition"), by("freshness"), by("hygiene")

    cards, alerts = [], []
    if nutrition:
        avg_k = sum(e["data"]["totals"]["kcal"] for e in nutrition) / len(nutrition)
        avg_s = sum(e["data"]["health_score"] for e in nutrition) / len(nutrition)
        cards.append({"title": "Avg. meal calories", "value": f"{avg_k:.0f} kcal", "sub": f"{len(nutrition)} meals logged"})
        cards.append({"title": "Avg. health score", "value": f"{avg_s:.0f}/100", "sub": "higher is better"})
        if avg_s < 55:
            alerts.append({"level": "warn", "text": "Your logged meals average a low health score – add fibre and protein."})
    if fresh:
        spoiled = [e for e in fresh if e["data"]["label"] == "Spoiled"]
        cards.append({"title": "Freshness checks", "value": str(len(fresh)), "sub": f"{len(spoiled)} flagged spoiled"})
        if spoiled:
            alerts.append({"level": "danger", "text": f"{len(spoiled)} item(s) were flagged as spoiled – discard them safely."})
    if hyg:
        last = hyg[0]["data"]
        cards.append({"title": "Latest hygiene score", "value": f"{last['overall_score']}/100", "sub": last["status"]})
        for a in last.get("alerts", [])[:3]:
            alerts.append({"level": "danger" if a["severity"] == "high" else "warn", "text": a["message"]})

    series = {
        "nutrition": [{"ts": e["ts"], "kcal": e["data"]["totals"]["kcal"], "score": e["data"]["health_score"]}
                      for e in reversed(nutrition)],
        "freshness": [{"ts": e["ts"], "score": e["data"]["freshness_score"], "label": e["data"]["label"]}
                      for e in reversed(fresh)],
        "hygiene": [{"ts": e["ts"], "score": e["data"]["overall_score"], "status": e["data"]["status"]}
                    for e in reversed(hyg)],
    }
    return {"cards": cards, "alerts": alerts, "series": series, "total_events": len(ev)}
