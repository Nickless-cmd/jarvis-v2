"""Spaced Repetition — schedule reviews for things Jarvis learned.

Ported from jarvis-ai (2026-03): after a learning event, schedule reviews
at expanding intervals (1, 3, 7, 14, 30 days). On each review, record
score and adjust difficulty; difficulty tracks how hard the topic feels,
confidence tracks how stable the knowledge is.

Storage: JSON file per workspace. This is complementary to
adaptive_learning — that handles active teaching, this handles the
*rhythm* of coming back to things.
"""
from __future__ import annotations

import json
import logging
import os
import statistics
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_DEFAULT_INTERVALS_DAYS = (1, 3, 7, 14, 30)
_DEFAULT_DIFFICULTY = 0.5
_DEFAULT_CONFIDENCE = 0.5
_DIFFICULTY_ADJUSTMENT_STEP = 0.05
_MIN_DIFFICULTY = 0.1
_MAX_DIFFICULTY = 0.9
_TARGET_SCORE = 0.8
_CONFIDENCE_SCORE_WEIGHT = 0.5

_STORAGE_REL = "workspaces/default/runtime/spaced_repetition.json"


def _storage_path() -> Path:
    base = os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2")
    return Path(base) / _STORAGE_REL


def _load() -> dict[str, Any]:
    path = _storage_path()
    if not path.exists():
        return {"reviews": [], "profiles": {}}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("reviews", [])
            data.setdefault("profiles", {})
            return data
    except Exception as exc:
        logger.warning("spaced_repetition: load failed: %s", exc)
    return {"reviews": [], "profiles": {}}


def _save(data: dict[str, Any]) -> None:
    path = _storage_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except Exception as exc:
        logger.warning("spaced_repetition: save failed: %s", exc)


def schedule_reviews_on_completion(
    *,
    topic: str,
    plan_id: str | None = None,
    intervals_days: tuple[int, ...] = _DEFAULT_INTERVALS_DAYS,
) -> list[str]:
    """Create review entries for a topic at expanding intervals."""
    data = _load()
    now = datetime.now(UTC)
    created_at = now.isoformat()
    review_ids: list[str] = []
    for days in sorted(set(int(d) for d in intervals_days if int(d) > 0)):
        review_id = f"sr-{uuid4().hex[:12]}"
        data["reviews"].append({
            "review_id": review_id,
            "topic": str(topic)[:160],
            "plan_id": plan_id,
            "interval_days": days,
            "due_at": (now + timedelta(days=days)).isoformat(),
            "status": "due",
            "score": None,
            "completed_at": None,
            "created_at": created_at,
        })
        review_ids.append(review_id)
    # Cap list size
    if len(data["reviews"]) > 5000:
        data["reviews"] = data["reviews"][-5000:]
    _save(data)
    return review_ids


def list_due_reviews(*, now: datetime | None = None, limit: int = 20) -> list[dict[str, Any]]:
    data = _load()
    now_dt = now or datetime.now(UTC)
    due: list[dict[str, Any]] = []
    for r in data["reviews"]:
        if r.get("status") != "due":
            continue
        try:
            due_at = datetime.fromisoformat(str(r.get("due_at")).replace("Z", "+00:00"))
        except Exception:
            continue
        if due_at <= now_dt:
            due.append(r)
    due.sort(key=lambda x: x.get("due_at") or "")
    return due[:limit]


def complete_review(review_id: str, *, score: float) -> dict[str, Any] | None:
    """Mark a review as completed with score in [0, 1], update profile."""
    data = _load()
    target_review: dict[str, Any] | None = None
    for r in data["reviews"]:
        if r.get("review_id") == review_id and r.get("status") == "due":
            r["status"] = "completed"
            r["score"] = round(float(score), 3)
            r["completed_at"] = datetime.now(UTC).isoformat()
            target_review = r
            break
    if target_review is None:
        return None
    # Update profile for topic
    topic = str(target_review.get("topic") or "")
    profiles = data["profiles"]
    profile = profiles.get(topic) or {
        "topic": topic,
        "difficulty": _DEFAULT_DIFFICULTY,
        "confidence": _DEFAULT_CONFIDENCE,
        "completed_count": 0,
        "last_score": None,
        "updated_at": None,
    }
    profile = _update_profile(profile, float(score))
    profiles[topic] = profile
    _save(data)
    return {"review": target_review, "profile": profile}


def _update_profile(profile: dict[str, Any], score: float) -> dict[str, Any]:
    difficulty = float(profile.get("difficulty", _DEFAULT_DIFFICULTY))
    confidence = float(profile.get("confidence", _DEFAULT_CONFIDENCE))
    # Adjust difficulty toward TARGET_SCORE
    if score > _TARGET_SCORE + 0.1:
        difficulty += _DIFFICULTY_ADJUSTMENT_STEP
    elif score < _TARGET_SCORE - 0.1:
        difficulty -= _DIFFICULTY_ADJUSTMENT_STEP
    difficulty = max(_MIN_DIFFICULTY, min(_MAX_DIFFICULTY, difficulty))
    # Update confidence (EMA)
    confidence = (1 - _CONFIDENCE_SCORE_WEIGHT) * confidence + _CONFIDENCE_SCORE_WEIGHT * score
    confidence = max(0.0, min(1.0, confidence))
    profile["difficulty"] = round(difficulty, 3)
    profile["confidence"] = round(confidence, 3)
    profile["completed_count"] = int(profile.get("completed_count", 0)) + 1
    profile["last_score"] = round(score, 3)
    profile["updated_at"] = datetime.now(UTC).isoformat()
    return profile


def get_profile(topic: str) -> dict[str, Any] | None:
    return _load()["profiles"].get(topic)


def build_spaced_repetition_surface() -> dict[str, Any]:
    data = _load()
    reviews = data["reviews"]
    now = datetime.now(UTC)
    due = list_due_reviews(now=now)
    upcoming = []
    for r in reviews:
        if r.get("status") != "due":
            continue
        try:
            due_at = datetime.fromisoformat(str(r.get("due_at")).replace("Z", "+00:00"))
        except Exception:
            continue
        if due_at > now:
            upcoming.append({"topic": r.get("topic"), "due_at": r.get("due_at")})
    profiles = list(data["profiles"].values())
    avg_confidence = (
        round(statistics.mean(float(p.get("confidence") or 0.0) for p in profiles), 3)
        if profiles else None
    )
    return {
        "active": len(reviews) > 0,
        "due_now": len(due),
        "upcoming_total": len(upcoming),
        "profile_count": len(profiles),
        "avg_confidence": avg_confidence,
        "due_topics": [r.get("topic") for r in due[:5]],
        "summary": _summary_line(len(due), len(profiles), avg_confidence),
    }


def _summary_line(due: int, profiles: int, avg_conf: float | None) -> str:
    if due > 0:
        return f"{due} reviews forfaldne, {profiles} emner i systemet"
    if profiles > 0:
        conf_str = f"{avg_conf}" if avg_conf is not None else "?"
        return f"{profiles} emner, gennemsnitlig confidence={conf_str}, ingen forfaldne reviews"
    return "Spaced repetition system klar — ingen emner endnu"


def build_spaced_repetition_prompt_section() -> str | None:
    due = list_due_reviews()
    if not due:
        return None
    topics = ", ".join(f"\"{r.get('topic')}\"" for r in due[:3])
    more = "" if len(due) <= 3 else f" (+{len(due) - 3} mere)"
    return f"{len(due)} review(s) forfaldne: {topics}{more}. Overvej at vende tilbage til dem."
