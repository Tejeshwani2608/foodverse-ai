"""Restaurant kitchen hygiene monitoring from video (Module 5).

Frames are sampled from an uploaded video with OpenCV and scored for four
indicators using colour/region heuristics:

  glove_usage      – glove-coloured (blue/purple/white/black nitrile) pixels vs exposed skin
                     in the central "hands" band of the frame
  hair_cap         – cap-coloured (white/blue/black) pixels vs hair/skin in the top band
  food_handling    – penalises large areas of bare skin in the hands band
  cleanliness      – bright, low-saturation, low-clutter surfaces in the lower half

IMPORTANT: these are lightweight, explainable heuristics for a college
project / demo. They do not detect people or hands with a trained model, so
they can be wrong with unusual lighting or uniforms. Swap in a YOLO/pose
model behind `analyze_frame` for production accuracy.
"""
from __future__ import annotations

import os
import tempfile

import cv2
import numpy as np

from . import llm

WEIGHTS = {"glove_usage": 0.3, "hair_cap": 0.25, "food_handling": 0.25, "cleanliness": 0.2}


def _skin_mask(hsv: np.ndarray) -> np.ndarray:
    h, s, v = hsv[..., 0] * 2.0, hsv[..., 1] / 255.0, hsv[..., 2] / 255.0
    return ((h <= 50) | (h >= 345)) & (s >= 0.18) & (s <= 0.75) & (v >= 0.35)


def _glove_mask(hsv: np.ndarray) -> np.ndarray:
    h, s, v = hsv[..., 0] * 2.0, hsv[..., 1] / 255.0, hsv[..., 2] / 255.0
    blue_purple = (h >= 190) & (h <= 290) & (s >= 0.3) & (v >= 0.25)
    black = (v < 0.18)
    white_latex = (s < 0.1) & (v > 0.85)
    return blue_purple | black | white_latex


def analyze_frame(frame_bgr: np.ndarray) -> dict:
    frame = cv2.resize(frame_bgr, (320, int(320 * frame_bgr.shape[0] / frame_bgr.shape[1])))
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)
    H = hsv.shape[0]
    top = hsv[: int(H * 0.28)]
    hands = hsv[int(H * 0.35): int(H * 0.75)]
    bottom = hsv[int(H * 0.5):]

    # --- hands band: gloves vs skin
    skin = _skin_mask(hands).mean()
    glove = _glove_mask(hands).mean()
    if glove + skin < 0.02:
        glove_score = 0.5  # nothing informative in view
    else:
        glove_score = float(glove / (glove + skin + 1e-6))
    handling = float(1.0 - min(skin / 0.25, 1.0))  # >25 % bare skin = poor handling

    # --- top band: head covering vs exposed hair/skin
    tglove = _glove_mask(top).mean()
    tskin = _skin_mask(top).mean()
    hair = ((top[..., 2] / 255.0 < 0.3) & (top[..., 1] / 255.0 < 0.5)).mean()
    cap_score = float(tglove / (tglove + tskin + hair * 0.5 + 1e-6)) if (tglove + tskin + hair) > 0.02 else 0.5

    # --- cleanliness: bright & unsaturated surface share, minus clutter (edge density)
    s_n, v_n = bottom[..., 1] / 255.0, bottom[..., 2] / 255.0
    clean_surface = ((s_n < 0.2) & (v_n > 0.6)).mean()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)[int(H * 0.5):]
    clutter = (cv2.Canny(gray, 80, 160) > 0).mean()
    dark_grime = (v_n < 0.2).mean()
    clean_score = float(np.clip(clean_surface * 1.4 - clutter * 2.0 - dark_grime * 0.8 + 0.25, 0, 1))

    return {"glove_usage": glove_score, "hair_cap": cap_score, "food_handling": handling,
            "cleanliness": clean_score}


def sample_frames(path: str, max_frames: int = 24) -> tuple[list[tuple[float, np.ndarray]], float]:
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise ValueError("Could not open the video. Try MP4/AVI/MOV (H.264).")
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frames: list[tuple[float, np.ndarray]] = []
    if n > 0:
        idxs = np.linspace(0, n - 1, min(max_frames, n)).astype(int)
        for i in idxs:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
            ok, fr = cap.read()
            if ok:
                frames.append((float(i / fps), fr))
    else:  # unknown length: read sequentially
        i = 0
        while len(frames) < max_frames:
            ok, fr = cap.read()
            if not ok:
                break
            if i % int(fps) == 0:
                frames.append((i / fps, fr))
            i += 1
    cap.release()
    if not frames:
        raise ValueError("No frames could be read from the video.")
    return frames, n / fps if n else frames[-1][0]


def analyze_video_bytes(data: bytes, suffix: str = ".mp4") -> dict:
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        return analyze_video_path(path)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def analyze_video_path(path: str) -> dict:
    frames, duration = sample_frames(path)
    per_frame = []
    for t, fr in frames:
        s = analyze_frame(fr)
        per_frame.append({"t": round(t, 1), **{k: round(v, 3) for k, v in s.items()}})

    avg = {k: float(np.mean([f[k] for f in per_frame])) for k in WEIGHTS}
    overall = int(round(100 * sum(avg[k] * w for k, w in WEIGHTS.items())))

    alerts = []
    labels = {"glove_usage": "Gloves", "hair_cap": "Hair cap / head covering",
              "food_handling": "Bare-hand food handling", "cleanliness": "Surface cleanliness"}
    for k, name in labels.items():
        bad = [f["t"] for f in per_frame if f[k] < 0.4]
        if avg[k] < 0.5 or len(bad) >= max(3, len(per_frame) // 3):
            alerts.append({
                "indicator": name,
                "severity": "high" if avg[k] < 0.3 else "medium",
                "message": f"{name}: likely non-compliant in {len(bad)} of {len(per_frame)} sampled frames.",
                "timestamps_s": bad[:8],
            })
    status = "Compliant" if overall >= 70 and not alerts else "Needs attention" if overall >= 45 else "Non-compliant"

    recs = {
        "Gloves": "Require single-use gloves for ready-to-eat food and change them between tasks.",
        "Hair cap / head covering": "Ensure every food handler wears a hair cap/net before entering the kitchen.",
        "Bare-hand food handling": "Use tongs, utensils or gloves instead of bare hands.",
        "Surface cleanliness": "Wipe and sanitise counters; clear clutter from prep surfaces.",
    }
    out = {
        "overall_score": overall,
        "status": status,
        "duration_s": round(duration, 1),
        "frames_analyzed": len(per_frame),
        "indicator_scores": {k: round(v * 100) for k, v in avg.items()},
        "alerts": alerts,
        "recommendations": [recs[a["indicator"]] for a in alerts] or ["Keep up the good hygiene practices."],
        "timeline": per_frame,
        "disclaimer": "Heuristic colour/region analysis for demonstration – not a certified inspection.",
    }
    expl = llm.explain("kitchen hygiene", {"overall": overall, "status": status, "alerts": [a["message"] for a in alerts]})
    if expl:
        out["ai_explanation"] = expl
    return out
