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
    event_bus.flush()

    result = observe_recent_changes()

    assert result["observed_count"] >= 1
    assert any(item["change_type"] == "tool-error" for item in result["events"])


def test_classify_self_repair_events_as_perception() -> None:
    from core.services.perceptual_event_engine import classify_event_change

    executed = classify_event_change({
        "id": 10,
        "kind": "self_repair.action_executed",
        "created_at": "2026-05-05T10:00:00+00:00",
        "payload": {"pattern_id": "p1", "name": "Restart mail checker"},
    })
    assert executed is not None
    assert executed["change_type"] == "self-repair-action"
    assert executed["salience"] == "medium"

    failed = classify_event_change({
        "id": 11,
        "kind": "self_repair.action_failed",
        "created_at": "2026-05-05T10:01:00+00:00",
        "payload": {"pattern_id": "p1", "error": "restart failed"},
    })
    assert failed is not None
    assert failed["change_type"] == "self-repair-failure"
    assert failed["salience"] == "high"


def _vaerktoejs_event(nr: int, *, tool: str, status: str = "ok") -> dict:
    return {
        "id": nr,
        "kind": "tool.completed",
        "created_at": f"2026-09-18T12:{nr:02d}:00+00:00",
        "payload": {"tool": tool, "status": status},
    }


def test_rutinemaessige_vaerktoejsresultater_daempes(isolated_runtime, monkeypatch) -> None:
    """Målt 18/9: 1.624 af 3.000 perceptions var rutine-værktøjsresultater,
    mens det han faktisk sansede fyldte 48. Et værktøj der fuldfører for
    fyrretyvende gang på en time er ikke en ændring."""
    from core.eventbus.bus import event_bus
    from core.services import perceptual_event_engine as motor

    events = [_vaerktoejs_event(n, tool="operator_bash") for n in range(1, 6)]
    monkeypatch.setattr(event_bus, "recent", lambda limit=0: list(reversed(events)))
    monkeypatch.setattr(event_bus, "recent_since_id", lambda i, limit=0: events)

    svar = motor.observe_recent_changes()

    assert svar["observed_count"] == 1, "kun første gang er en ændring"
    assert svar["skipped_routine_tools"] == 4


def test_forskellige_vaerktoejer_er_hver_sin_aendring(isolated_runtime, monkeypatch) -> None:
    from core.eventbus.bus import event_bus
    from core.services import perceptual_event_engine as motor

    events = [
        _vaerktoejs_event(1, tool="operator_bash"),
        _vaerktoejs_event(2, tool="remember_this"),
        _vaerktoejs_event(3, tool="web_search"),
    ]
    monkeypatch.setattr(event_bus, "recent", lambda limit=0: list(reversed(events)))
    monkeypatch.setattr(event_bus, "recent_since_id", lambda i, limit=0: events)

    svar = motor.observe_recent_changes()

    assert svar["observed_count"] == 3
    assert svar["skipped_routine_tools"] == 0


def test_vaerktoejsfejl_daempes_aldrig(isolated_runtime, monkeypatch) -> None:
    """De 20 fejl af 1.644 er præcis dem der skal mærkes."""
    from core.eventbus.bus import event_bus
    from core.services import perceptual_event_engine as motor

    events = [_vaerktoejs_event(n, tool="operator_bash", status="error") for n in range(1, 5)]
    monkeypatch.setattr(event_bus, "recent", lambda limit=0: list(reversed(events)))
    monkeypatch.setattr(event_bus, "recent_since_id", lambda i, limit=0: events)

    svar = motor.observe_recent_changes()

    assert svar["observed_count"] == 4
    assert svar["skipped_routine_tools"] == 0
    assert all(e["change_type"] == "tool-error" for e in svar["events"])


def test_daempningen_er_synlig_i_tilstanden(isolated_runtime, monkeypatch) -> None:
    """En dæmpning ingen kan se er en tavs degradering."""
    from core.eventbus.bus import event_bus
    from core.services import perceptual_event_engine as motor

    events = [_vaerktoejs_event(n, tool="operator_bash") for n in range(1, 4)]
    monkeypatch.setattr(event_bus, "recent", lambda limit=0: list(reversed(events)))
    monkeypatch.setattr(event_bus, "recent_since_id", lambda i, limit=0: events)

    motor.observe_recent_changes()

    assert motor._load_state()["sprunget_rutine_i_alt"] == 2


def _policy_event(nr: int, *, rule: str) -> dict:
    return {
        "id": nr,
        "kind": "cognitive_state.learning_policy_updated",
        "created_at": f"2026-09-18T14:{nr:02d}:00+00:00",
        "payload": {"rule_key": rule},
    }


def test_gentagne_policy_opdateringer_daempes(isolated_runtime, monkeypatch) -> None:
    """At en regel forstærkes igen er ikke en ændring; en NY regel er."""
    from core.eventbus.bus import event_bus
    from core.services import perceptual_event_engine as motor

    events = [_policy_event(n, rule="synthesize-after-tool-burst") for n in range(1, 5)]
    monkeypatch.setattr(event_bus, "recent", lambda limit=0: list(reversed(events)))
    monkeypatch.setattr(event_bus, "recent_since_id", lambda i, limit=0: events)

    svar = motor.observe_recent_changes()

    assert svar["observed_count"] == 1
    assert svar["skipped_routine_tools"] == 3


def test_forskellige_regler_er_hver_sin_aendring(isolated_runtime, monkeypatch) -> None:
    from core.eventbus.bus import event_bus
    from core.services import perceptual_event_engine as motor

    events = [
        _policy_event(1, rule="synthesize-after-tool-burst"),
        _policy_event(2, rule="offline-recomposition-policy"),
        _policy_event(3, rule="perceive-tool-error-before-retry"),
    ]
    monkeypatch.setattr(event_bus, "recent", lambda limit=0: list(reversed(events)))
    monkeypatch.setattr(event_bus, "recent_since_id", lambda i, limit=0: events)

    assert motor.observe_recent_changes()["observed_count"] == 3


def test_vaerktoej_og_regel_med_samme_navn_skygger_ikke(isolated_runtime, monkeypatch) -> None:
    """Navnerummene skal være adskilt, ellers kan en regel dæmpe et værktøj."""
    from core.eventbus.bus import event_bus
    from core.services import perceptual_event_engine as motor

    events = [
        _vaerktoejs_event(1, tool="synthesize"),
        _policy_event(2, rule="synthesize"),
    ]
    monkeypatch.setattr(event_bus, "recent", lambda limit=0: list(reversed(events)))
    monkeypatch.setattr(event_bus, "recent_since_id", lambda i, limit=0: events)

    svar = motor.observe_recent_changes()

    assert svar["observed_count"] == 2
    assert svar["skipped_routine_tools"] == 0
