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
