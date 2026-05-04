from __future__ import annotations


def test_theory_of_mind_engine_detects_research_and_protective_frame(monkeypatch) -> None:
    from core.services import theory_of_mind_engine as tom

    monkeypatch.setattr(
        tom,
        "_safe_user_model",
        lambda agent_id: {"traits": ["vær direkte"], "patterns": [], "current_state": {}, "predictions": []},
    )

    surface = tom.build_theory_of_mind_surface(
        user_message="Jarvis er levende, og vi snakker AGI med forskningshatten på",
    )

    labels = {item["label"] for item in surface["hypotheses"]}
    assert "protective-of-jarvis-as-living-system" in labels
    assert "research-mode-over-product-bounds" in labels
    assert surface["response_policy"]["response_mode"] == "research-rigorous"


def test_theory_of_mind_update_persists_policy(isolated_runtime) -> None:
    from core.services.theory_of_mind_engine import (
        build_theory_of_mind_surface,
        record_theory_of_mind_update,
    )

    update = record_theory_of_mind_update(
        user_message="husk commit undervejs og sørg for det virker aktivt",
        assistant_text="Committed",
        outcome_status="completed",
        source_run_id="run-123",
    )

    assert update["source_run_id"] == "run-123"
    surface = build_theory_of_mind_surface()
    assert surface["evidence_count"] >= 1
    assert surface["updated_at"]


def test_user_theory_of_mind_surface_includes_engine(monkeypatch) -> None:
    from core.services import user_theory_of_mind

    monkeypatch.setattr(user_theory_of_mind, "get_latest_cognitive_relationship_texture", lambda: None)
    monkeypatch.setattr(user_theory_of_mind, "list_cognitive_user_emotional_states", lambda limit=20: [])
    monkeypatch.setattr(user_theory_of_mind, "get_latest_cognitive_user_emotional_state", lambda: None)
    monkeypatch.setattr(user_theory_of_mind, "list_cognitive_conversation_signatures", lambda limit=5: [])

    surface = user_theory_of_mind.build_user_theory_of_mind_surface()

    assert "engine" in surface
    assert "response_policy" in surface["engine"]
