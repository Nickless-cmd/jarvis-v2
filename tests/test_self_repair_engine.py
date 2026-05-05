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
