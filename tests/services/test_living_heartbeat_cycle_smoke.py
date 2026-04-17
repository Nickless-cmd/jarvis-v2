"""Smoke test for core.services.living_heartbeat_cycle.

The living heartbeat cycle should map a daytime hour to the expected phase and
produce a prompt-friendly description of that state.
"""

from core.services import living_heartbeat_cycle


def test_determine_life_phase_for_deep_work_hour() -> None:
    phase = living_heartbeat_cycle.determine_life_phase(hour=11)
    prompt = living_heartbeat_cycle.format_life_phase_for_prompt(phase)

    assert phase["phase"] == "deep_work"
    assert "explore_own_codebase" in phase["suggested_actions"]
    assert "deep_work" in prompt
