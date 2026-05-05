from __future__ import annotations


def test_pattern_matches_event_exact_payload(isolated_runtime) -> None:
    from core.services.self_repair_engine import (
        SelfRepairPattern, _pattern_matches_event,
    )

    p = SelfRepairPattern(
        pattern_id="p1", name="x",
        trigger_event_kind="k",
        trigger_match={"daemon": "mail_checker"},
        action_type="control_daemon", action_params={},
        enabled=True, cooldown_seconds=300,
        max_attempts_per_window=3, window_seconds=3600,
        auto_disable_after_escalations=3, auto_disable_window_hours=24,
        source="manual", source_evidence=None,
    )
    assert _pattern_matches_event(
        p, {"kind": "k", "payload": {"daemon": "mail_checker"}}
    ) is True
    assert _pattern_matches_event(
        p, {"kind": "k", "payload": {"daemon": "other"}}
    ) is False


def test_pattern_does_not_match_wrong_kind(isolated_runtime) -> None:
    from core.services.self_repair_engine import (
        SelfRepairPattern, _pattern_matches_event,
    )

    p = SelfRepairPattern(
        pattern_id="p1", name="x",
        trigger_event_kind="kind.x",
        trigger_match={}, action_type="control_daemon", action_params={},
        enabled=True, cooldown_seconds=300,
        max_attempts_per_window=3, window_seconds=3600,
        auto_disable_after_escalations=3, auto_disable_window_hours=24,
        source="manual", source_evidence=None,
    )
    assert _pattern_matches_event(p, {"kind": "kind.y", "payload": {}}) is False


def test_pattern_does_not_match_missing_payload_key(isolated_runtime) -> None:
    from core.services.self_repair_engine import (
        SelfRepairPattern, _pattern_matches_event,
    )

    p = SelfRepairPattern(
        pattern_id="p1", name="x",
        trigger_event_kind="k", trigger_match={"key": "value"},
        action_type="control_daemon", action_params={},
        enabled=True, cooldown_seconds=300,
        max_attempts_per_window=3, window_seconds=3600,
        auto_disable_after_escalations=3, auto_disable_window_hours=24,
        source="manual", source_evidence=None,
    )
    assert _pattern_matches_event(p, {"kind": "k", "payload": {}}) is False


def test_payload_predicate_gt(isolated_runtime) -> None:
    from core.services.self_repair_engine import _payload_predicate_matches

    assert _payload_predicate_matches({"op": "gt", "value": 5}, 10) is True
    assert _payload_predicate_matches({"op": "gt", "value": 5}, 3) is False
    assert _payload_predicate_matches({"op": "gt", "value": 5}, "not-a-number") is False


def test_payload_predicate_lt(isolated_runtime) -> None:
    from core.services.self_repair_engine import _payload_predicate_matches

    assert _payload_predicate_matches({"op": "lt", "value": 5}, 3) is True
    assert _payload_predicate_matches({"op": "lt", "value": 5}, 10) is False


def test_payload_predicate_in(isolated_runtime) -> None:
    from core.services.self_repair_engine import _payload_predicate_matches

    p = {"op": "in", "values": ["a", "b", "c"]}
    assert _payload_predicate_matches(p, "a") is True
    assert _payload_predicate_matches(p, "z") is False


def test_payload_predicate_regex(isolated_runtime) -> None:
    from core.services.self_repair_engine import _payload_predicate_matches

    p = {"op": "regex", "pattern": r"timeout"}
    assert _payload_predicate_matches(p, "upstream timeout error") is True
    assert _payload_predicate_matches(p, "all good") is False
    p_bad = {"op": "regex", "pattern": "[unclosed"}
    assert _payload_predicate_matches(p_bad, "anything") is False


def test_decode_pattern_from_db_row(isolated_runtime) -> None:
    from core.services.self_repair_engine import _decode_pattern

    row = {
        "pattern_id": "p1", "name": "X",
        "trigger_event_kind": "k",
        "trigger_match_json": '{"daemon": "mail_checker"}',
        "action_type": "control_daemon",
        "action_params_json": '{"name": "mail_checker", "action": "restart"}',
        "enabled": 1, "cooldown_seconds": 300,
        "max_attempts_per_window": 3, "window_seconds": 3600,
        "auto_disable_after_escalations": 3, "auto_disable_window_hours": 24,
        "source": "manual", "source_evidence_json": None,
    }
    p = _decode_pattern(row)
    assert p.pattern_id == "p1"
    assert p.trigger_match == {"daemon": "mail_checker"}
    assert p.action_params == {"name": "mail_checker", "action": "restart"}
    assert p.enabled is True


def test_action_handlers_only_contain_allowlisted(isolated_runtime) -> None:
    from core.services.self_repair_engine import _ACTION_HANDLERS

    assert set(_ACTION_HANDLERS.keys()) == {"control_daemon"}


def test_action_control_daemon_calls_daemon_manager(
    isolated_runtime, monkeypatch
) -> None:
    from core.services import self_repair_engine as eng
    import core.services.daemon_manager as dm

    captured = {}

    def fake_control_daemon(name, action, *, interval_minutes=None):
        captured["name"] = name
        captured["action"] = action
        captured["interval_minutes"] = interval_minutes
        return {"ok": True, "name": name, "action": action}

    monkeypatch.setattr(dm, "control_daemon", fake_control_daemon)

    result = eng._action_control_daemon({
        "name": "mail_checker", "action": "restart",
    })
    assert captured == {
        "name": "mail_checker", "action": "restart", "interval_minutes": None,
    }
    assert result["ok"] is True


def test_action_control_daemon_passes_interval_minutes(
    isolated_runtime, monkeypatch
) -> None:
    from core.services import self_repair_engine as eng
    import core.services.daemon_manager as dm

    captured = {}

    def fake_control_daemon(name, action, *, interval_minutes=None):
        captured["interval_minutes"] = interval_minutes
        return {"ok": True}

    monkeypatch.setattr(dm, "control_daemon", fake_control_daemon)

    eng._action_control_daemon({
        "name": "x", "action": "set_interval", "interval_minutes": 15,
    })
    assert captured["interval_minutes"] == 15


def test_action_control_daemon_rejects_invalid_action(isolated_runtime) -> None:
    from core.services.self_repair_engine import _action_control_daemon

    import pytest
    with pytest.raises(ValueError, match="invalid control_daemon params"):
        _action_control_daemon({"name": "x", "action": "delete-everything"})

    with pytest.raises(ValueError, match="invalid control_daemon params"):
        _action_control_daemon({"name": "", "action": "restart"})


def test_check_cooldown_ok_when_no_recent_attempts(isolated_runtime) -> None:
    from core.runtime.db import insert_self_repair_pattern, get_self_repair_pattern
    from core.services.self_repair_engine import _check_cooldown, _decode_pattern

    insert_self_repair_pattern(
        pattern_id="p1", name="x", trigger_event_kind="k",
        action_type="control_daemon", source="manual",
    )
    p = _decode_pattern(get_self_repair_pattern("p1"))
    assert _check_cooldown(p) == "ok"


def test_check_cooldown_blocks_within_cooldown_seconds(
    isolated_runtime, monkeypatch,
) -> None:
    from datetime import UTC, datetime, timedelta
    from core.runtime.db import (
        insert_self_repair_pattern,
        get_self_repair_pattern,
        insert_self_repair_attempt,
    )
    from core.services import self_repair_engine as eng

    insert_self_repair_pattern(
        pattern_id="p1", name="x", trigger_event_kind="k",
        action_type="control_daemon", cooldown_seconds=300, source="manual",
    )
    now = datetime(2026, 5, 5, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(eng, "_now", lambda: now)

    insert_self_repair_attempt(
        pattern_id="p1",
        attempted_at=(now - timedelta(seconds=120)).isoformat(),
        triggered_by_event_id=1, outcome="executed",
        error_summary=None, elapsed_ms=10,
    )

    p = eng._decode_pattern(get_self_repair_pattern("p1"))
    reason = eng._check_cooldown(p)
    assert reason.startswith("cooldown")


def test_check_cooldown_blocks_at_window_cap(isolated_runtime, monkeypatch) -> None:
    from datetime import UTC, datetime, timedelta
    from core.runtime.db import (
        insert_self_repair_pattern,
        get_self_repair_pattern,
        insert_self_repair_attempt,
    )
    from core.services import self_repair_engine as eng

    insert_self_repair_pattern(
        pattern_id="p1", name="x", trigger_event_kind="k",
        action_type="control_daemon",
        cooldown_seconds=0,
        max_attempts_per_window=3, window_seconds=3600,
        source="manual",
    )
    now = datetime(2026, 5, 5, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(eng, "_now", lambda: now)

    for i, outcome in enumerate(["executed", "failed", "rate_limited"]):
        insert_self_repair_attempt(
            pattern_id="p1",
            attempted_at=(now - timedelta(minutes=i * 10)).isoformat(),
            triggered_by_event_id=i, outcome=outcome,
            error_summary=None, elapsed_ms=5,
        )

    p = eng._decode_pattern(get_self_repair_pattern("p1"))
    reason = eng._check_cooldown(p)
    assert reason.startswith("window-cap-reached")


def test_check_cooldown_returns_db_error_on_query_failure(
    isolated_runtime, monkeypatch,
) -> None:
    from core.runtime.db import insert_self_repair_pattern, get_self_repair_pattern
    from core.services import self_repair_engine as eng

    insert_self_repair_pattern(
        pattern_id="p1", name="x", trigger_event_kind="k",
        action_type="control_daemon", source="manual",
    )
    p = eng._decode_pattern(get_self_repair_pattern("p1"))

    def boom(**kwargs):
        raise RuntimeError("simulated DB failure")

    monkeypatch.setattr(eng, "count_recent_attempts", boom)
    assert eng._check_cooldown(p) == "db-error"


def test_register_pattern_validates_allowlist(isolated_runtime) -> None:
    from core.services.self_repair_engine import register_pattern

    import pytest
    with pytest.raises(ValueError, match="not in allowlist"):
        register_pattern(
            pattern_id="p1", name="x",
            trigger_event_kind="k",
            action_type="evil_action",
        )


def test_register_pattern_requires_identity_fields(isolated_runtime) -> None:
    from core.services.self_repair_engine import register_pattern

    import pytest
    with pytest.raises(ValueError, match="required"):
        register_pattern(
            pattern_id="", name="x",
            trigger_event_kind="k",
            action_type="control_daemon",
        )


def test_register_pattern_persists_with_settings_defaults(isolated_runtime) -> None:
    from core.services.self_repair_engine import register_pattern, list_patterns

    register_pattern(
        pattern_id="p1", name="x",
        trigger_event_kind="k",
        action_type="control_daemon",
        action_params={"name": "mail_checker", "action": "restart"},
    )
    patterns = list_patterns()
    assert len(patterns) == 1
    p = patterns[0]
    assert p["pattern_id"] == "p1"
    assert p["enabled"] == 1
    assert p["cooldown_seconds"] == 300


def test_enable_disable_delete_pattern(isolated_runtime) -> None:
    from core.services.self_repair_engine import (
        register_pattern, list_patterns,
        enable_pattern, disable_pattern, delete_pattern,
    )

    register_pattern(
        pattern_id="p1", name="x", trigger_event_kind="k",
        action_type="control_daemon",
    )
    assert disable_pattern("p1") is True
    assert list_patterns(enabled=False)[0]["pattern_id"] == "p1"
    assert enable_pattern("p1") is True
    assert list_patterns(enabled=True)[0]["pattern_id"] == "p1"
    assert delete_pattern("p1") is True
    assert list_patterns() == []


def test_list_recent_attempts(isolated_runtime) -> None:
    from core.runtime.db import (
        insert_self_repair_pattern, insert_self_repair_attempt,
    )
    from core.services.self_repair_engine import list_recent_attempts

    insert_self_repair_pattern(
        pattern_id="p1", name="x", trigger_event_kind="k",
        action_type="control_daemon", source="manual",
    )
    for i in range(3):
        insert_self_repair_attempt(
            pattern_id="p1",
            attempted_at=f"2026-05-05T10:0{i}:00+00:00",
            triggered_by_event_id=i, outcome="executed",
            error_summary=None, elapsed_ms=10,
        )
    rows = list_recent_attempts(limit=2)
    assert len(rows) == 2
    assert rows[0]["attempted_at"] > rows[1]["attempted_at"]


def test_build_self_repair_surface_returns_overview(isolated_runtime) -> None:
    from core.services.self_repair_engine import (
        register_pattern, build_self_repair_surface,
    )

    register_pattern(
        pattern_id="p1", name="X", trigger_event_kind="k",
        action_type="control_daemon",
    )
    surface = build_self_repair_surface()
    assert surface["engine_enabled"] is True
    assert surface["pattern_count"] == 1
    assert surface["enabled_pattern_count"] == 1
    assert surface["patterns"][0]["pattern_id"] == "p1"
    assert "recent_attempts" in surface


def test_attempt_repair_executes_action_and_records_executed(
    isolated_runtime, monkeypatch,
) -> None:
    from core.runtime.db import (
        list_recent_self_repair_attempts,
        get_self_repair_pattern,
    )
    from core.services import self_repair_engine as eng

    eng.register_pattern(
        pattern_id="p1", name="X", trigger_event_kind="k",
        trigger_match={"daemon": "mail_checker"},
        action_type="control_daemon",
        action_params={"name": "mail_checker", "action": "restart"},
    )

    captured = {}
    def fake_handler(params):
        captured["params"] = params
        return {"ok": True}
    monkeypatch.setitem(eng._ACTION_HANDLERS, "control_daemon", fake_handler)

    notify_calls = []
    monkeypatch.setattr(eng, "_notify_owner_async", lambda msg: notify_calls.append(msg))

    pattern = eng._decode_pattern(get_self_repair_pattern("p1"))
    eng._attempt_repair(
        pattern,
        {"id": 99, "kind": "k", "payload": {"daemon": "mail_checker"}},
    )

    assert captured["params"] == {"name": "mail_checker", "action": "restart"}
    attempts = list_recent_self_repair_attempts(pattern_id="p1")
    assert len(attempts) == 1
    assert attempts[0]["outcome"] == "executed"
    assert attempts[0]["triggered_by_event_id"] == 99
    assert notify_calls == []  # No Discord push on success


def test_attempt_repair_captures_emotional_anchor(
    isolated_runtime, monkeypatch,
) -> None:
    from core.runtime.db import get_self_repair_pattern
    from core.services import self_repair_engine as eng
    import core.services.emotional_memory_engine as em

    eng.register_pattern(
        pattern_id="p1", name="X", trigger_event_kind="k",
        action_type="control_daemon",
        action_params={"name": "mail_checker", "action": "restart"},
    )
    monkeypatch.setitem(eng._ACTION_HANDLERS, "control_daemon", lambda p: {"ok": True})

    captured = []
    monkeypatch.setattr(
        em,
        "capture_emotional_anchor",
        lambda **kwargs: captured.append(kwargs) or {"ok": True},
    )

    pattern = eng._decode_pattern(get_self_repair_pattern("p1"))
    eng._attempt_repair(pattern, {"id": 99, "kind": "k", "payload": {}})

    assert captured
    assert captured[0]["anchor_type"] == "self_repair_attempt"
    assert captured[0]["context_features"]["pattern_id"] == "p1"
    assert captured[0]["context_features"]["outcome"] == "executed"


def test_attempt_repair_publishes_emotional_precedent(
    isolated_runtime, monkeypatch,
) -> None:
    from core.runtime.db import get_self_repair_pattern
    from core.services import self_repair_engine as eng
    import core.services.emotional_memory_engine as em

    eng.register_pattern(
        pattern_id="p1", name="X", trigger_event_kind="k",
        action_type="control_daemon",
        action_params={"name": "mail_checker", "action": "restart"},
    )
    monkeypatch.setitem(eng._ACTION_HANDLERS, "control_daemon", lambda p: {"ok": True})
    monkeypatch.setattr(
        em,
        "find_similar_anchors",
        lambda **kwargs: [{"outcome_score": -1.0, "score": 0.8}],
    )
    monkeypatch.setattr(em, "capture_emotional_anchor", lambda **kwargs: None)
    published = []
    monkeypatch.setattr(
        eng.event_bus,
        "publish",
        lambda kind, payload=None: published.append((kind, payload)),
    )

    pattern = eng._decode_pattern(get_self_repair_pattern("p1"))
    eng._attempt_repair(pattern, {"id": 99, "kind": "k", "payload": {}})

    assert any(
        kind == "self_repair.emotional_precedent_found"
        for kind, _payload in published
    )


def test_attempt_repair_records_failed_on_handler_exception(
    isolated_runtime, monkeypatch,
) -> None:
    from core.runtime.db import list_recent_self_repair_attempts, get_self_repair_pattern
    from core.services import self_repair_engine as eng

    eng.register_pattern(
        pattern_id="p1", name="X", trigger_event_kind="k",
        action_type="control_daemon",
        action_params={"name": "mail_checker", "action": "restart"},
    )

    def boom(params):
        raise RuntimeError("backend on fire")
    monkeypatch.setitem(eng._ACTION_HANDLERS, "control_daemon", boom)

    notify_calls = []
    monkeypatch.setattr(eng, "_notify_owner_async", lambda msg: notify_calls.append(msg))

    pattern = eng._decode_pattern(get_self_repair_pattern("p1"))
    eng._attempt_repair(pattern, {"id": 1, "kind": "k", "payload": {}})

    attempts = list_recent_self_repair_attempts(pattern_id="p1")
    assert len(attempts) == 1
    assert attempts[0]["outcome"] == "failed"
    assert "on fire" in attempts[0]["error_summary"]
    assert len(notify_calls) == 1
    assert "Self-repair failed" in notify_calls[0]


def test_attempt_repair_skips_when_action_not_in_allowlist(
    isolated_runtime, monkeypatch,
) -> None:
    from core.runtime.db import (
        list_recent_self_repair_attempts, get_self_repair_pattern,
        insert_self_repair_pattern,
    )
    from core.services import self_repair_engine as eng

    insert_self_repair_pattern(
        pattern_id="p1", name="X", trigger_event_kind="k",
        action_type="ghost_action", source="manual",
    )

    notify_calls = []
    monkeypatch.setattr(eng, "_notify_owner_async", lambda msg: notify_calls.append(msg))

    pattern = eng._decode_pattern(get_self_repair_pattern("p1"))
    eng._attempt_repair(pattern, {"id": 1, "kind": "k", "payload": {}})

    attempts = list_recent_self_repair_attempts(pattern_id="p1")
    assert len(attempts) == 1
    assert attempts[0]["outcome"] == "failed"
    assert "unknown action_type" in attempts[0]["error_summary"]


def test_attempt_repair_skips_when_cooldown_blocks(
    isolated_runtime, monkeypatch,
) -> None:
    from core.runtime.db import (
        list_recent_self_repair_attempts, get_self_repair_pattern,
    )
    from core.services import self_repair_engine as eng

    eng.register_pattern(
        pattern_id="p1", name="X", trigger_event_kind="k",
        action_type="control_daemon",
        action_params={"name": "mail_checker", "action": "restart"},
    )
    monkeypatch.setattr(eng, "_check_cooldown", lambda p: "cooldown (test)")

    handler_called = []
    monkeypatch.setitem(
        eng._ACTION_HANDLERS, "control_daemon",
        lambda params: handler_called.append(params),
    )

    pattern = eng._decode_pattern(get_self_repair_pattern("p1"))
    eng._attempt_repair(pattern, {"id": 1, "kind": "k", "payload": {}})

    assert handler_called == []
    attempts = list_recent_self_repair_attempts(pattern_id="p1")
    assert attempts[0]["outcome"] == "rate_limited"


def test_record_failed_triggers_auto_disable_at_threshold(
    isolated_runtime, monkeypatch,
) -> None:
    from datetime import UTC, datetime, timedelta
    from core.runtime.db import (
        get_self_repair_pattern, insert_self_repair_attempt,
    )
    from core.services import self_repair_engine as eng

    eng.register_pattern(
        pattern_id="p1", name="X", trigger_event_kind="k",
        action_type="control_daemon",
        cooldown_seconds=0,
        max_attempts_per_window=10,
        auto_disable_after_escalations=3,
        auto_disable_window_hours=24,
    )
    now = datetime(2026, 5, 5, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(eng, "_now", lambda: now)

    for i in range(2):
        insert_self_repair_attempt(
            pattern_id="p1",
            attempted_at=(now - timedelta(hours=i + 1)).isoformat(),
            triggered_by_event_id=i, outcome="failed",
            error_summary="prior", elapsed_ms=5,
        )

    notify_calls = []
    monkeypatch.setattr(eng, "_notify_owner_async", lambda msg: notify_calls.append(msg))

    def boom(params):
        raise RuntimeError("third failure")
    monkeypatch.setitem(eng._ACTION_HANDLERS, "control_daemon", boom)

    pattern = eng._decode_pattern(get_self_repair_pattern("p1"))
    eng._attempt_repair(pattern, {"id": 99, "kind": "k", "payload": {}})

    after = get_self_repair_pattern("p1")
    assert after["enabled"] == 0
    assert after["last_outcome"] == "auto_disabled"
    assert any("auto-disabled" in m for m in notify_calls)


def test_engine_disabled_skips_all_processing(
    isolated_runtime, monkeypatch,
) -> None:
    from core.runtime.db import list_recent_self_repair_attempts
    from core.runtime import settings as settings_mod
    from core.services import self_repair_engine as eng

    eng.register_pattern(
        pattern_id="p1", name="X", trigger_event_kind="k",
        action_type="control_daemon",
        action_params={"name": "x", "action": "restart"},
    )

    original_load = settings_mod.load_settings
    def patched_load():
        s = original_load()
        s.self_repair_engine_enabled = False
        return s
    monkeypatch.setattr(settings_mod, "load_settings", patched_load)

    eng._process_event({"id": 1, "kind": "k", "payload": {}})
    assert list_recent_self_repair_attempts(pattern_id="p1") == []


def test_unknown_event_kind_skipped_silently(
    isolated_runtime, monkeypatch,
) -> None:
    from core.runtime.db import list_recent_self_repair_attempts
    from core.services import self_repair_engine as eng

    eng.register_pattern(
        pattern_id="p1", name="X", trigger_event_kind="kind.x",
        action_type="control_daemon",
        action_params={"name": "x", "action": "restart"},
    )

    monkeypatch.setitem(eng._ACTION_HANDLERS, "control_daemon", lambda p: {"ok": True})

    eng._process_event({"id": 1, "kind": "kind.y", "payload": {}})
    assert list_recent_self_repair_attempts(pattern_id="p1") == []


def test_process_event_runs_matching_pattern(isolated_runtime, monkeypatch) -> None:
    from core.runtime.db import list_recent_self_repair_attempts
    from core.services import self_repair_engine as eng

    eng.register_pattern(
        pattern_id="p1", name="X",
        trigger_event_kind="kind.x",
        trigger_match={"daemon": "mail_checker"},
        action_type="control_daemon",
        action_params={"name": "mail_checker", "action": "restart"},
    )
    monkeypatch.setitem(eng._ACTION_HANDLERS, "control_daemon", lambda p: {"ok": True})

    eng._process_event({
        "id": 99, "kind": "kind.x", "payload": {"daemon": "mail_checker"},
    })

    attempts = list_recent_self_repair_attempts(pattern_id="p1")
    assert len(attempts) == 1
    assert attempts[0]["outcome"] == "executed"


def test_process_emotional_gate_event_suggests_pattern_after_repetition(
    isolated_runtime, monkeypatch,
) -> None:
    from core.services import self_repair_engine as eng
    import core.services.emotional_memory_engine as em

    captured = []
    monkeypatch.setattr(
        em,
        "capture_emotional_anchor",
        lambda **kwargs: captured.append(kwargs) or {"ok": True},
    )
    monkeypatch.setattr(
        em,
        "find_similar_anchors",
        lambda **kwargs: [{"score": 0.9}, {"score": 0.8}, {"score": 0.7}],
    )
    published = []
    monkeypatch.setattr(
        eng.event_bus,
        "publish",
        lambda kind, payload=None: published.append((kind, payload)),
    )

    eng._process_emotional_gate_event({
        "id": 44,
        "kind": "runtime.emotional_gate",
        "payload": {
            "input_action": "restart_daemon",
            "decision": "verify_first",
            "reason": "fatigue high",
            "risk": "medium",
            "snapshot": {
                "primary_mood": "tired",
                "frustration": 0.2,
                "fatigue": 0.8,
                "confidence": 0.3,
            },
        },
    })

    assert captured
    assert captured[0]["anchor_type"] == "self_repair_emotional_gate"
    assert any(
        kind == "self_repair.emotional_gate_pattern_suggested"
        for kind, _payload in published
    )


def test_listener_starts_and_stops_cleanly(isolated_runtime) -> None:
    import time
    from core.services import self_repair_engine as eng

    eng.start_listener()
    assert eng._LISTENER_THREAD is not None
    assert eng._LISTENER_THREAD.is_alive()

    eng.stop_listener()
    for _ in range(30):
        if not eng._LISTENER_THREAD.is_alive():
            break
        time.sleep(0.1)
    assert not eng._LISTENER_THREAD.is_alive()
