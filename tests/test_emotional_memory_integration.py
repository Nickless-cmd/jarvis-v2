from __future__ import annotations


def test_record_runtime_episode_captures_anchor(
    isolated_runtime, monkeypatch
) -> None:
    from core.runtime.db import list_emotional_memory_anchors
    from core.services import emotional_memory_engine as em
    from core.services.cognitive_episodes import record_runtime_episode

    monkeypatch.setattr(em, "_read_current_mood", lambda: ("frustrated", 0.6))
    monkeypatch.setattr(
        em,
        "_read_current_dimensions",
        lambda: {
            "confidence": 0.4, "curiosity": 0.3, "frustration": 0.7,
            "fatigue": 0.5, "trust": 0.6,
        },
    )

    record_runtime_episode(
        source_run_id="run-A",
        session_id="sess-1",
        trigger="visible-run:ollama/glm",
        outcome_status="interrupted",
        summary="Run interrupted mid-tool",
        tool_names=["read_file", "propose_source_edit"],
        error="upstream timeout",
    )

    anchors = list_emotional_memory_anchors(anchor_type="cognitive_episode")
    assert len(anchors) == 1
    anchor = anchors[0]
    assert anchor["mood"] == "frustrated"
    assert anchor["frustration"] == 0.7
    assert anchor["outcome_score"] is not None
    assert anchor["outcome_score"] < 0  # interrupted/timeout → negative


def test_capture_failure_does_not_break_episode_recording(
    isolated_runtime, monkeypatch
) -> None:
    from core.services import emotional_memory_engine as em
    from core.services.cognitive_episodes import record_runtime_episode

    def _broken(**_kwargs):
        raise RuntimeError("simulated capture failure")

    monkeypatch.setattr(em, "capture_emotional_anchor", _broken)

    result = record_runtime_episode(
        source_run_id="run-B",
        session_id="sess-1",
        trigger="x",
        outcome_status="completed",
        summary="ok",
    )
    assert result["episode_id"].startswith("ce-")
