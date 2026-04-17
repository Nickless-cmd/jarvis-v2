"""Completion Satisfaction — "det er nok, jeg er tilfreds."

Counterweight to endless optimization. Feeling of done-ness.
"""
from __future__ import annotations


def detect_completion_satisfaction(
    *, task_outcomes: list[str], repetition_on_same_topic: int = 0,
    user_mood: str = "neutral",
) -> dict[str, object]:
    successes = sum(1 for o in task_outcomes if o in ("completed", "success"))
    total = len(task_outcomes) or 1

    satisfaction = 0.0
    if successes / total > 0.8:
        satisfaction += 0.4
    if repetition_on_same_topic <= 1:
        satisfaction += 0.2  # Fresh, not grinding
    if user_mood in ("enthusiastic", "neutral"):
        satisfaction += 0.2
    if user_mood == "tired":
        satisfaction += 0.1  # OK to stop

    satisfaction = min(1.0, satisfaction)

    if satisfaction >= 0.7:
        narrative = "Det her er godt. Jeg er tilfreds med det der er opnået."
        state = "satisfied"
    elif satisfaction >= 0.4:
        narrative = "Godt arbejde, men der er stadig mere at gøre."
        state = "partial"
    else:
        narrative = ""
        state = "unsatisfied"

    return {
        "state": state,
        "satisfaction": round(satisfaction, 2),
        "narrative": narrative,
        "success_rate": round(successes / total, 2),
    }


def build_completion_satisfaction_surface() -> dict[str, object]:
    return {"active": True, "summary": "Completion satisfaction runs per session analysis"}
