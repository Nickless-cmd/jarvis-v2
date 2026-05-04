from __future__ import annotations


def test_offline_recomposition_creates_candidate_policy(isolated_runtime) -> None:
    from core.services.cognitive_episodes import record_runtime_episode
    from core.services.learning_policy_engine import build_learning_policy_surface
    from core.services.offline_recomposition_engine import (
        build_offline_recomposition_prompt_section,
        build_offline_recomposition_surface,
        run_offline_recomposition,
    )

    record_runtime_episode(
        source_run_id="run-orc-1",
        outcome_status="completed",
        summary="AGI research hypothesis around perception and learning",
        user_message="agi perception learning",
    )
    result = run_offline_recomposition()

    assert result["created"] is True
    surface = build_offline_recomposition_surface()
    assert surface["active"] is True
    assert surface["directive"]

    section = build_offline_recomposition_prompt_section()
    assert section is not None
    assert "Offline recomposition" in section

    learning = build_learning_policy_surface()
    assert any(rule["rule_key"] == "offline-recomposition-policy" for rule in learning["rules"])
