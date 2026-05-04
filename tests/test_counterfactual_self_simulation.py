from __future__ import annotations


def test_counterfactual_simulation_from_episode_feeds_learning(isolated_runtime) -> None:
    from core.services.cognitive_episodes import record_runtime_episode
    from core.services.counterfactual_self_simulation import build_counterfactual_surface
    from core.services.learning_policy_engine import build_learning_policy_surface

    record_runtime_episode(
        source_run_id="run-cf-1",
        outcome_status="interrupted",
        summary="Visible run interrupted by timeout",
        tool_names=["read_file"],
        error="timed out",
    )

    surface = build_counterfactual_surface()
    assert surface["active"] is True
    assert "resume" in surface["directive"].lower()

    learning = build_learning_policy_surface()
    assert any(rule["rule_key"] == "counterfactual-preferred-policy" for rule in learning["rules"])


def test_counterfactual_prompt_section_is_compact(isolated_runtime) -> None:
    from core.services.cognitive_episodes import record_runtime_episode
    from core.services.counterfactual_self_simulation import build_counterfactual_prompt_section

    record_runtime_episode(
        source_run_id="run-cf-2",
        outcome_status="completed",
        summary="Proposal edit completed after exact context read",
        tool_names=["read_file", "propose_source_edit"],
    )

    section = build_counterfactual_prompt_section()
    assert section is not None
    assert "Counterfactual self-simulation" in section
    assert len(section) < 600
