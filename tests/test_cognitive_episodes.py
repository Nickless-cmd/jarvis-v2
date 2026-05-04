from __future__ import annotations


def test_record_runtime_episode_persists_active_directives(isolated_runtime) -> None:
    from core.services.cognitive_episodes import (
        build_cognitive_episode_surface,
        record_runtime_episode,
    )

    result = record_runtime_episode(
        source_run_id="run-1",
        session_id="chat-1",
        trigger="visible-run:ollama/glm",
        outcome_status="completed",
        summary="Proposal flow completed",
        tool_names=["read_file", "propose_source_edit"],
        user_message="det er synd for ham han bliver afbrudt",
        assistant_text="Klar med proposals",
    )

    assert result["episode_id"].startswith("ce-")
    rows = isolated_runtime.db.list_cognitive_episodes(limit=5)
    assert len(rows) == 1
    assert rows[0]["source_run_id"] == "run-1"

    surface = build_cognitive_episode_surface()
    assert surface["active"] is True
    directives = surface["directives"]
    assert "emotion" in directives["social"] or "relational" in directives["social"]
    assert directives["next_behavior"]


def test_interrupted_episode_prioritizes_resume_policy() -> None:
    from core.services.cognitive_episodes import derive_episode_fields

    fields = derive_episode_fields(
        outcome_status="interrupted",
        error="timed out",
        tool_names=["read_file", "bash"],
        user_message="prøv igen",
    )

    assert fields["attention"]["salience"] == "high"
    assert "Resume" in fields["metacognition"]["self_check"]
    assert "resume" in fields["policy"]["next_behavior"]
    assert fields["policy"]["prompt_priority"] == "high"
