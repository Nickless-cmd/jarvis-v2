"""Habit Tracker — detects recurring patterns and friction points.

Tracks:
- Habit patterns: things Jarvis does repeatedly (good or bad)
- Friction signals: tasks that are consistently difficult
"""

from __future__ import annotations

import hashlib
import logging

from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_cognitive_friction_signals,
    list_cognitive_habit_patterns,
    upsert_cognitive_friction_signal,
    upsert_cognitive_habit_pattern,
)

logger = logging.getLogger(__name__)


def track_habit_from_run(
    *,
    run_id: str,
    task_signature: str,
    outcome_status: str,
    attempt_count: int = 1,
) -> dict[str, object] | None:
    """Track habit pattern and friction from a visible run."""
    if not task_signature:
        return None

    # Normalize task signature
    sig = _normalize_signature(task_signature)

    # Always track as habit pattern
    habit_result = upsert_cognitive_habit_pattern(
        pattern_key=sig,
        description=task_signature[:100],
    )

    event_bus.publish(
        "cognitive_habit.pattern_detected",
        {"pattern_key": sig, "recurrence": habit_result.get("recurrence_count")},
    )

    # Track friction if multiple attempts or failure
    if attempt_count > 2 or outcome_status in ("failed", "error"):
        inefficiency = min(1.0, attempt_count / 5.0)
        if outcome_status in ("failed", "error"):
            inefficiency = max(inefficiency, 0.5)

        upsert_cognitive_friction_signal(
            task_signature=sig,
            inefficiency_score=inefficiency,
            description=f"{task_signature[:80]} (attempts: {attempt_count}, status: {outcome_status})",
        )

        event_bus.publish(
            "cognitive_habit.friction_detected",
            {"task_signature": sig, "inefficiency": inefficiency},
        )

    return habit_result


def build_habit_surface() -> dict[str, object]:
    habits = list_cognitive_habit_patterns(limit=15)
    friction = list_cognitive_friction_signals(limit=10)
    return {
        "active": bool(habits) or bool(friction),
        "habits": habits,
        "friction": friction,
        "summary": (
            f"{len(habits)} habits, {len(friction)} friction points"
            if habits or friction else "No habits tracked yet"
        ),
    }


def _normalize_signature(text: str) -> str:
    """Create a stable signature from task description."""
    normalized = text.strip().lower()[:100]
    words = sorted(set(w for w in normalized.split() if len(w) > 3))[:5]
    key = "_".join(words) if words else normalized[:30]
    return hashlib.sha256(key.encode()).hexdigest()[:16]
