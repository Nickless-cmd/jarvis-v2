"""Smoke test for core.services.apophenia_guard.

The guard should reject patterns with too little evidence and upgrade stronger
patterns when observation count and confidence are sufficient.
"""

from core.services import apophenia_guard


def test_assess_pattern_distinguishes_rejected_and_upgraded_cases() -> None:
    rejected = apophenia_guard.assess_pattern(
        observation_count=2,
        base_confidence=0.95,
    )
    upgraded = apophenia_guard.assess_pattern(
        observation_count=12,
        base_confidence=0.78,
        competing_explanations=["noise"],
    )

    assert rejected["status"] == "rejected"
    assert upgraded["status"] == "upgraded"
    assert upgraded["confidence"] > rejected["confidence"]
