from __future__ import annotations


def test_learning_policy_engine_reinforces_episode_policy(isolated_runtime) -> None:
    from core.services.cognitive_episodes import record_runtime_episode
    from core.services.learning_policy_engine import build_learning_policy_surface

    record_runtime_episode(
        source_run_id="run-learning-1",
        session_id="chat-1",
        trigger="visible-run",
        outcome_status="completed",
        summary="Proposal repaired after exact context read",
        tool_names=["read_file", "propose_source_edit"],
        user_message="vil du fixe det",
        assistant_text="proposal filed",
    )

    surface = build_learning_policy_surface()

    assert surface["active"] is True
    assert surface["rules"]
    assert any(rule["rule_key"] == "exact-context-before-edit" for rule in surface["rules"])
    assert "exact" in surface["directive"].lower()


def test_learning_policy_engine_prioritizes_resume_rule(isolated_runtime) -> None:
    from core.services.learning_policy_engine import (
        build_learning_policy_surface,
        reinforce_learning_policy,
    )

    reinforce_learning_policy({
        "rule_key": "resume-before-reexplore",
        "policy": "On retry intent, resume from checkpoint before broad analysis.",
        "lesson": "Interrupted runs need durable resume state.",
        "confidence": 0.7,
        "last_evidence": "interrupted provider timeout",
    })

    surface = build_learning_policy_surface()

    assert surface["active"] is True
    assert surface["rules"][0]["rule_key"] == "resume-before-reexplore"
    assert "resume" in surface["directive"].lower()
