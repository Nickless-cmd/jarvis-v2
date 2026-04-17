"""Smoke test for core.services.completion_satisfaction.

Completion satisfaction should recognize a mostly successful recent run and
produce a concrete "done enough" narrative instead of staying empty.
"""

from core.services import completion_satisfaction


def test_detect_completion_satisfaction_returns_satisfied_state() -> None:
    result = completion_satisfaction.detect_completion_satisfaction(
        task_outcomes=["success", "completed", "success", "completed"],
        repetition_on_same_topic=1,
        user_mood="neutral",
    )
    surface = completion_satisfaction.build_completion_satisfaction_surface()

    assert result["state"] == "satisfied"
    assert result["satisfaction"] >= 0.7
    assert result["narrative"]
    assert surface["active"] is True
