from __future__ import annotations


def test_eventbus_publish_triggers_matched_pattern_action(
    isolated_runtime, monkeypatch,
) -> None:
    """End-to-end: register pattern → start listener → publish matching event →
    handler called → audit row created."""
    import time
    from core.eventbus.bus import event_bus
    from core.runtime.db import list_recent_self_repair_attempts
    from core.services import self_repair_engine as eng

    eng.register_pattern(
        pattern_id="p1", name="X",
        trigger_event_kind="runtime.self_repair_test_trigger",
        trigger_match={"daemon": "mail_checker"},
        action_type="control_daemon",
        action_params={"name": "mail_checker", "action": "restart"},
        cooldown_seconds=0,
    )

    handler_calls = []
    monkeypatch.setitem(
        eng._ACTION_HANDLERS, "control_daemon",
        lambda params: handler_calls.append(params) or {"ok": True},
    )

    eng.start_listener()
    try:
        event_bus.publish(
            "runtime.self_repair_test_trigger",
            {"daemon": "mail_checker"},
        )
        attempts = []
        for _ in range(20):
            attempts = list_recent_self_repair_attempts(pattern_id="p1")
            if attempts:
                break
            time.sleep(0.1)
    finally:
        eng.stop_listener()

    assert len(handler_calls) == 1
    assert handler_calls[0] == {"name": "mail_checker", "action": "restart"}
    assert len(attempts) == 1
    assert attempts[0]["outcome"] == "executed"


def test_disabled_pattern_does_not_fire(isolated_runtime, monkeypatch) -> None:
    import time
    from core.eventbus.bus import event_bus
    from core.runtime.db import list_recent_self_repair_attempts
    from core.services import self_repair_engine as eng

    eng.register_pattern(
        pattern_id="p1", name="X",
        trigger_event_kind="runtime.self_repair_test_disabled",
        action_type="control_daemon",
        action_params={"name": "x", "action": "restart"},
        enabled=False,
    )

    handler_called = []
    monkeypatch.setitem(
        eng._ACTION_HANDLERS, "control_daemon",
        lambda params: handler_called.append(params),
    )

    eng.start_listener()
    try:
        event_bus.publish("runtime.self_repair_test_disabled", {})
        time.sleep(0.5)
    finally:
        eng.stop_listener()

    assert handler_called == []
    assert list_recent_self_repair_attempts(pattern_id="p1") == []


def test_matched_event_for_disabled_engine_does_nothing(
    isolated_runtime, monkeypatch,
) -> None:
    import time
    from core.eventbus.bus import event_bus
    from core.runtime.db import list_recent_self_repair_attempts
    from core.runtime import settings as settings_mod
    from core.services import self_repair_engine as eng

    eng.register_pattern(
        pattern_id="p1", name="X",
        trigger_event_kind="runtime.self_repair_test_engine_off",
        action_type="control_daemon",
        action_params={"name": "x", "action": "restart"},
    )

    original_load = settings_mod.load_settings
    def patched_load():
        s = original_load()
        s.self_repair_engine_enabled = False
        return s
    monkeypatch.setattr(settings_mod, "load_settings", patched_load)

    handler_called = []
    monkeypatch.setitem(
        eng._ACTION_HANDLERS, "control_daemon",
        lambda params: handler_called.append(params),
    )

    eng.start_listener()
    try:
        event_bus.publish("runtime.self_repair_test_engine_off", {})
        time.sleep(0.5)
    finally:
        eng.stop_listener()

    assert handler_called == []
    assert list_recent_self_repair_attempts(pattern_id="p1") == []


def test_failed_action_publishes_failure_event_and_pings_owner(
    isolated_runtime, monkeypatch,
) -> None:
    import time
    from core.eventbus.bus import event_bus
    from core.runtime.db import list_recent_self_repair_attempts
    from core.services import self_repair_engine as eng

    eng.register_pattern(
        pattern_id="p1", name="X",
        trigger_event_kind="runtime.self_repair_test_fail",
        action_type="control_daemon",
        action_params={"name": "x", "action": "restart"},
        cooldown_seconds=0,
    )

    def boom(params):
        raise RuntimeError("test failure")
    monkeypatch.setitem(eng._ACTION_HANDLERS, "control_daemon", boom)

    notify_calls = []
    monkeypatch.setattr(eng, "_notify_owner_async", lambda msg: notify_calls.append(msg))

    eng.start_listener()
    try:
        event_bus.publish("runtime.self_repair_test_fail", {})
        attempts = []
        for _ in range(20):
            attempts = list_recent_self_repair_attempts(pattern_id="p1")
            if attempts:
                break
            time.sleep(0.1)
    finally:
        eng.stop_listener()

    assert len(attempts) == 1
    assert attempts[0]["outcome"] == "failed"
    assert "test failure" in attempts[0]["error_summary"]
    assert any("Self-repair failed" in m for m in notify_calls)
