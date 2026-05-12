from __future__ import annotations

from datetime import UTC, datetime


def _memory_store(monkeypatch):
    from core.services import world_model_signal_tracking as wm

    state: list[dict[str, object]] = []
    monkeypatch.setattr(wm, "_load_predictions", lambda: [dict(item) for item in state])

    def save(items):
        state.clear()
        state.extend(dict(item) for item in items)

    monkeypatch.setattr(wm, "_save_predictions", save)
    return wm, state


def test_record_world_model_prediction_is_non_executing(monkeypatch):
    wm, state = _memory_store(monkeypatch)

    result = wm.record_runtime_world_model_prediction(
        subject="runtime planning",
        expectation="A stale approved plan will need a replan prompt.",
        horizon="next heartbeat",
        confidence="medium",
        evidence=["approved plan is older than three days"],
        source="test",
        now=datetime(2026, 5, 12, tzinfo=UTC),
    )

    assert result["status"] == "ok"
    prediction = result["prediction"]
    assert prediction["status"] == "open"
    assert prediction["confidence"] == "medium"
    assert "do_not_auto_act" in prediction["allowed_effects"]
    assert state[0]["prediction_id"] == prediction["prediction_id"]


def test_resolve_world_model_prediction_updates_calibration(monkeypatch):
    wm, _state = _memory_store(monkeypatch)
    recorded = wm.record_runtime_world_model_prediction(
        subject="tool invention",
        expectation="Thin skill proposals will receive nudges.",
        confidence="high",
    )
    prediction_id = recorded["prediction"]["prediction_id"]

    resolved = wm.resolve_runtime_world_model_prediction(
        prediction_id,
        observed="Validation returned thin_instructions and weak_trigger nudges.",
        outcome="supported",
        now=datetime(2026, 5, 12, tzinfo=UTC),
    )
    surface = wm.build_runtime_world_model_prediction_surface()

    assert resolved["status"] == "ok"
    assert surface["active"] is False
    assert surface["summary"]["resolved_count"] == 1
    assert surface["summary"]["supported_count"] == 1
    assert surface["summary"]["calibration"] == 1.0
    assert surface["items"][0]["outcome"] == "supported"


def test_world_model_signal_surface_includes_prediction_skeleton(
    isolated_runtime, monkeypatch,
):
    wm, _state = _memory_store(monkeypatch)
    wm.record_runtime_world_model_prediction(
        subject="workspace",
        expectation="Jarvis work will stay inside jarvis-v2.",
        confidence="medium",
    )

    surface = wm.build_runtime_world_model_signal_surface()

    prediction_surface = surface["prediction_skeleton"]
    assert prediction_surface["active"] is True
    assert prediction_surface["summary"]["open_count"] == 1
    assert prediction_surface["items"][0]["subject"] == "workspace"
