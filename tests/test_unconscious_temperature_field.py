from __future__ import annotations


# NOTE: the keyword-based implementation that used to live in
# unconscious_temperature_field was retired — the module is now a
# backwards-compat wrapper that delegates to user_temperature_engine (the
# two-stream engine, covered by tests/services/test_user_temperature_engine.py).
# These two cases therefore verify the wrapper's delegation contract rather than
# the removed keyword/cache internals (_recent_user_messages, the DB state key).


def test_temperature_field_surface_delegates_to_engine(
    isolated_runtime,
    monkeypatch,
) -> None:
    field = isolated_runtime.unconscious_temperature_field

    engine_surface = {
        "active": True,
        "enabled": True,
        "current_field": "frustrated",
        "valens": -0.6,
        "arousal": 0.4,
        "intensity": 0.7,
        "conflict": 0.1,
        "rationale": "irritation markers dominate",
        "summary": "frustrated field",
    }
    monkeypatch.setattr(
        "core.services.user_temperature_engine.get_active_field_surface",
        lambda *, workspace_id="default", force_refresh=False: engine_surface,
    )

    surface = field.build_unconscious_temperature_field_surface(force_refresh=True)

    assert surface["active"] is True
    assert surface["current_field"] == "frustrated"


def test_temperature_hint_delegates_to_engine(
    isolated_runtime,
    monkeypatch,
) -> None:
    field = isolated_runtime.unconscious_temperature_field
    monkeypatch.setattr(
        "core.services.user_temperature_engine.format_temperature_field_for_heartbeat",
        lambda *, workspace_id="default": "temperature: current_field=frustrated",
    )

    hint = field.build_unconscious_temperature_hint()

    assert hint is not None
    assert "current_field=frustrated" in hint


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
