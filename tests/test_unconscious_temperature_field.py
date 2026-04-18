from __future__ import annotations

from core.services.chat_sessions import append_chat_message, create_chat_session


def test_temperature_field_derives_frustrated_from_recent_user_messages(
    isolated_runtime,
) -> None:
    field = isolated_runtime.unconscious_temperature_field
    session = create_chat_session(title="Temp field")
    session_id = str(session["id"])
    append_chat_message(session_id=session_id, role="user", content="Det virker ikke stadig, du har misforstået det.")
    append_chat_message(session_id=session_id, role="user", content="Nej, stadig broken. Kom nu.")

    surface = field.build_unconscious_temperature_field_surface(force_refresh=True)
    hint = field.build_unconscious_temperature_hint()

    assert surface["active"] is True
    assert surface["current_field"] == "frustrated"
    assert "irritation" in surface["hint"]
    assert hint is not None
    assert "current_field=frustrated" in hint


def test_temperature_field_uses_cached_state_when_fresh(
    isolated_runtime,
) -> None:
    field = isolated_runtime.unconscious_temperature_field
    isolated_runtime.db.set_runtime_state_value(
        "unconscious_temperature_field.state",
        {
            "current_field": "playful",
            "scores": {"playful": 3.0},
            "message_count": 4,
            "confidence_band": "medium",
            "hint": "Tillad lidt leg og lethed, men uden at miste retning.",
            "rebuilt_at": "2099-01-01T00:00:00+00:00",
        },
    )

    surface = field.build_unconscious_temperature_field_surface()

    assert surface["current_field"] == "playful"
    assert surface["message_count"] == 4


def test_mission_control_runtime_and_endpoint_expose_temperature_field(
    isolated_runtime,
    monkeypatch,
) -> None:
    surface = {
        "active": True,
        "enabled": True,
        "current_field": "warm",
        "confidence_band": "high",
        "hint": "Brug en rolig og samarbejdende tone; varme ser ud til at bære feltet.",
        "scores": {"warm": 5.2, "frustrated": 0.8},
        "message_count": 12,
        "lookback_days": 7,
        "rebuilt_at": "2026-04-18T12:00:00+00:00",
        "summary": "warm field from 12 user messages",
        "visibility": "system-hint-only",
        "authority": "soft-derived",
    }
    monkeypatch.setattr(
        isolated_runtime.unconscious_temperature_field,
        "build_unconscious_temperature_field_surface",
        lambda force_refresh=False: surface,
    )
    monkeypatch.setattr(
        isolated_runtime.mission_control,
        "build_unconscious_temperature_field_surface",
        lambda: surface,
    )

    runtime = isolated_runtime.mission_control.mc_runtime()
    endpoint = isolated_runtime.mission_control.mc_unconscious_temperature_field()

    assert runtime["runtime_unconscious_temperature_field"]["current_field"] == "warm"
    assert endpoint["confidence_band"] == "high"
