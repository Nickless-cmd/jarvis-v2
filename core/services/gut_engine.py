"""Gut Engine — intuition and calibration tracking.

Before execution, Jarvis generates a "hunch" (proceed/caution).
After execution, the outcome is compared to the hunch.
Over time, calibration score reveals how reliable Jarvis' gut feeling is.
"""

from __future__ import annotations

import logging

from core.eventbus.bus import event_bus
from core.runtime.db import (
    get_cognitive_gut_state,
    update_cognitive_gut_state,
)

logger = logging.getLogger(__name__)


def derive_gut_signal(
    *,
    task_description: str,
    confidence: float = 0.5,
    recent_error_count: int = 0,
    recent_success_count: int = 0,
) -> dict[str, object]:
    """Generate a gut-feel hunch about a task."""
    gut_state = get_cognitive_gut_state()
    calibration = float(gut_state.get("calibration_score", 0.5)) if gut_state else 0.5

    # Heuristic gut signal
    if recent_error_count > 3 and confidence < 0.6:
        hunch = "caution"
        hunch_confidence = 0.7
    elif recent_success_count > 5 and confidence > 0.7:
        hunch = "proceed"
        hunch_confidence = 0.8
    elif confidence < 0.3:
        hunch = "caution"
        hunch_confidence = 0.6
    else:
        hunch = "proceed"
        hunch_confidence = 0.5

    # Weight by calibration — if gut has been wrong, reduce confidence
    adjusted_confidence = hunch_confidence * calibration

    return {
        "hunch": hunch,
        "confidence": round(adjusted_confidence, 2),
        "calibration_score": calibration,
        "raw_confidence": confidence,
        "task_hint": task_description[:80],
    }


def record_gut_outcome(
    *,
    hunch: str,
    actual_outcome: str,
) -> dict[str, object]:
    """Record whether the gut hunch was correct."""
    predicted_success = hunch == "proceed"
    actual_success = actual_outcome in ("completed", "success")
    correct = predicted_success == actual_success

    result = update_cognitive_gut_state(
        prediction_correct=correct,
        last_hunch=f"{hunch} → {actual_outcome} ({'✓' if correct else '✗'})",
    )

    event_bus.publish(
        "cognitive_gut.outcome_recorded",
        {"correct": correct, "hunch": hunch, "actual": actual_outcome},
    )
    return result


def build_gut_surface() -> dict[str, object]:
    state = get_cognitive_gut_state()
    if not state:
        return {"active": False, "state": None, "summary": "No gut data yet"}
    return {
        "active": True,
        "state": state,
        "summary": (
            f"Calibration: {state['calibration_score']:.2f} "
            f"({state['calibrated_hits']}/{state['total_predictions']} correct)"
        ),
    }
