from __future__ import annotations


def test_modulator_witness_surface_exposes_hidden_effects(monkeypatch):
    from core.services import affect_modulation
    from core.services import dream_bias_engine
    from core.services import unconscious_modulation
    from core.services import user_temperature_engine
    from core.services.modulator_witness import build_modulator_witness_surface

    monkeypatch.setattr(
        dream_bias_engine,
        "get_active_dream_bias",
        lambda *, workspace_id="default": {
            "attention_bias": {"unfinished_business": 0.4},
            "threshold_bias": {"loop_persistence": 0.2},
            "intensity": 0.6,
            "last_dream_at": "2026-05-12T08:00:00Z",
            "ttl_expires_at": "2026-05-12T16:00:00Z",
            "accumulated_count": 2,
            "source_kinds": ["self_review_outcome.created"],
        },
    )
    monkeypatch.setattr(
        user_temperature_engine,
        "get_active_field",
        lambda *, workspace_id="default": {
            "field_texture": "alert",
            "field_intensity": 0.7,
            "field_conflict": False,
            "field_valens": 0.1,
            "field_arousal": 0.8,
            "struct_texture": "alert",
            "struct_confidence": 0.7,
            "llm_texture": "alert",
            "llm_confidence": 0.8,
            "last_structural_at": "2026-05-12T08:01:00Z",
            "last_llm_at": "2026-05-12T08:02:00Z",
        },
    )
    monkeypatch.setattr(
        user_temperature_engine,
        "get_response_style_modifiers",
        lambda *, workspace_id="default": {
            "preferred_length": "short",
            "warmth": "neutral",
            "pace": "quick",
        },
    )
    monkeypatch.setattr(
        unconscious_modulation,
        "compute_unconscious_modulation",
        lambda *, base_temperature=None, base_top_p=None, workspace_id="default": (0.82, 1.0),
    )
    monkeypatch.setattr(
        affect_modulation,
        "compute_affect_modulated_params",
        lambda: {"search_depth": "deep"},
    )

    surface = build_modulator_witness_surface()

    assert surface["active"] is True
    assert surface["summary"]["active_count"] == 4
    by_name = {item["name"]: item for item in surface["items"]}
    assert by_name["dream_bias"]["current_effect"]["attention_bias"]["unfinished_business"] == 0.4
    assert by_name["user_temperature"]["current_effect"]["response_style"]["pace"] == "quick"
    assert by_name["unconscious_sampling"]["current_effect"]["temperature"] == 0.82
    assert by_name["affect_modulation"]["current_effect"]["overrides"]["search_depth"] == "deep"
    assert "allowed_effects" in by_name["dream_bias"]


def test_modulator_witness_surface_keeps_inactive_sampling_visible(monkeypatch):
    from core.services import affect_modulation
    from core.services import dream_bias_engine
    from core.services import unconscious_modulation
    from core.services import user_temperature_engine
    from core.services.modulator_witness import build_modulator_witness_surface

    monkeypatch.setattr(dream_bias_engine, "get_active_dream_bias", lambda *, workspace_id="default": None)
    monkeypatch.setattr(user_temperature_engine, "get_active_field", lambda *, workspace_id="default": None)
    monkeypatch.setattr(
        user_temperature_engine,
        "get_response_style_modifiers",
        lambda *, workspace_id="default": {
            "preferred_length": "normal",
            "warmth": "neutral",
            "pace": "normal",
        },
    )
    monkeypatch.setattr(
        unconscious_modulation,
        "compute_unconscious_modulation",
        lambda *, base_temperature=None, base_top_p=None, workspace_id="default": (0.7, 1.0),
    )
    monkeypatch.setattr(affect_modulation, "compute_affect_modulated_params", lambda: {})

    surface = build_modulator_witness_surface()

    assert surface["active"] is False
    assert surface["summary"]["active_count"] == 0
    by_name = {item["name"]: item for item in surface["items"]}
    assert by_name["unconscious_sampling"]["active"] is False
    assert by_name["affect_modulation"]["active"] is False
