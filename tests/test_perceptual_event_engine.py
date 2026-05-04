from __future__ import annotations


def test_classify_interruption_as_high_salience_change() -> None:
    from core.services.perceptual_event_engine import classify_event_change

    percept = classify_event_change({
        "id": 42,
        "kind": "runtime.visible_run_interrupted",
        "created_at": "2026-05-04T10:00:00+00:00",
        "payload": {"summary": "followup timeout", "run_id": "run-1"},
    })

    assert percept is not None
    assert percept["change_type"] == "runtime-interruption"
    assert percept["salience"] == "high"
    assert "followup timeout" in percept["summary"]


def test_record_perceptual_event_builds_active_surface_and_learning_rule(isolated_runtime) -> None:
    from core.services.learning_policy_engine import build_learning_policy_surface
    from core.services.perceptual_event_engine import (
        build_perception_surface,
        record_perceptual_event,
    )

    record_perceptual_event(
        change_type="runtime-interruption",
        summary="Visible run interrupted after read_file",
        salience="high",
        source_kind="runtime.visible_run_interrupted",
        source_event_id=100,
        evidence={"run_id": "run-1"},
    )

    surface = build_perception_surface(scan=False)
    assert surface["active"] is True
    assert surface["events"][0]["change_type"] == "runtime-interruption"
    assert "interruption" in surface["directive"].lower()

    learning = build_learning_policy_surface()
    assert any(rule["rule_key"] == "perceive-interruption-as-change" for rule in learning["rules"])


def test_observe_recent_changes_scans_eventbus(isolated_runtime) -> None:
    from core.eventbus.bus import event_bus
    from core.services.perceptual_event_engine import observe_recent_changes

    event_bus.publish("tool.completed", {"tool": "bash", "status": "error"})

    result = observe_recent_changes()

    assert result["observed_count"] >= 1
    assert any(item["change_type"] == "tool-error" for item in result["events"])
