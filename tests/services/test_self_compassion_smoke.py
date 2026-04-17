"""Smoke test for core.services.self_compassion.

Self-compassion should turn repeated failures into a concrete acceptance
narrative instead of returning an empty placeholder.
"""

from core.services import self_compassion


def test_process_failure_toward_acceptance_returns_high_support_for_many_failures() -> None:
    result = self_compassion.process_failure_toward_acceptance(
        failure_count_recent=6,
        regret_level=0.8,
        lesson_learned="check assumptions earlier",
    )
    resilience = self_compassion.build_resilience_narrative(
        consecutive_failures=6,
        current_bearing="hold the line",
    )

    assert result["needed"] is True
    assert result["level"] == "high"
    assert "check assumptions earlier" in result["narrative"]
    assert "6 fejl i træk" in resilience
