"""Smoke test for core.services.user_theory_of_mind.

The user model should synthesize relationship texture and emotional history
into concrete patterns, predictions, and a prompt-friendly summary.
"""

import json

from core.services import user_theory_of_mind


def test_build_user_mental_model_combines_history_and_current_state(monkeypatch) -> None:
    monkeypatch.setattr(
        user_theory_of_mind,
        "get_latest_cognitive_relationship_texture",
        lambda: {
            "productive_hours": json.dumps({"14": 4, "15": 3}),
            "correction_patterns": json.dumps(["vær mere konkret"]),
            "unspoken_rules": json.dumps(["vær direkte"]),
            "conversation_rhythm": json.dumps({"avg_turns": 8}),
        },
    )
    monkeypatch.setattr(
        user_theory_of_mind,
        "list_cognitive_user_emotional_states",
        lambda limit=20: [
            {"detected_mood": "frustrated"},
            {"detected_mood": "frustrated"},
            {"detected_mood": "impatient"},
            {"detected_mood": "impatient"},
            {"detected_mood": "impatient"},
        ],
    )
    monkeypatch.setattr(
        user_theory_of_mind,
        "get_latest_cognitive_user_emotional_state",
        lambda: {"detected_mood": "frustrated", "confidence": 0.92},
    )
    monkeypatch.setattr(
        user_theory_of_mind,
        "list_cognitive_conversation_signatures",
        lambda limit=5: [
            {
                "signature_type": "architecture",
                "count": 4,
                "success_rate": 0.75,
            },
        ],
    )

    model = user_theory_of_mind.build_user_mental_model()
    prompt = user_theory_of_mind.format_user_model_for_prompt(model)

    assert model["traits"] == ["vær direkte"]
    assert any("Mest produktiv kl" in item for item in model["patterns"])
    assert model["current_state"]["mood"] == "frustrated"
    assert "user_now: frustrated" in prompt
