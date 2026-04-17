"""Smoke test for core.services.subjective_time.

Subjective time should reflect an intense recent interaction differently from a
quiet idle stretch.
"""

from core.services import subjective_time


def test_subjective_time_perception_marks_intense_recent_conversation() -> None:
    perception = subjective_time.build_subjective_time_perception(
        tick_count_last_hour=4,
        conversation_intensity=0.9,
        novelty_score=0.2,
        idle_hours=0.5,
    )
    surface = subjective_time.build_subjective_time_surface()

    assert "intens samtale" in perception["feel"]
    assert surface["active"] is True
