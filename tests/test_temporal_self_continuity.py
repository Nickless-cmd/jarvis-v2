from __future__ import annotations


def test_temporal_self_continuity_records_handoff(isolated_runtime) -> None:
    from core.services.cognitive_episodes import record_runtime_episode
    from core.services.temporal_self_continuity import (
        build_temporal_self_continuity_prompt_section,
        build_temporal_self_continuity_surface,
    )

    record_runtime_episode(
        source_run_id="run-tsc-1",
        trigger="visible-run",
        outcome_status="completed",
        summary="Learning policy updated",
        tool_names=["bash"],
    )

    surface = build_temporal_self_continuity_surface()
    assert surface["active"] is True
    assert surface["handoffs"][0]["source_run_id"] == "run-tsc-1"
    assert surface["directive"]

    section = build_temporal_self_continuity_prompt_section()
    assert section is not None
    assert "Temporal self-continuity" in section
