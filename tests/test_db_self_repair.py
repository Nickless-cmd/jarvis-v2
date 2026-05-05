from __future__ import annotations


def test_insert_and_get_pattern(isolated_runtime) -> None:
    from core.runtime.db import (
        insert_self_repair_pattern,
        get_self_repair_pattern,
    )

    insert_self_repair_pattern(
        pattern_id="p1",
        name="Restart mail_checker",
        trigger_event_kind="process_watcher.matched",
        trigger_match_json='{"watch_id": "mail_checker_overdue"}',
        action_type="control_daemon",
        action_params_json='{"name": "mail_checker", "action": "restart"}',
        cooldown_seconds=300,
        max_attempts_per_window=3,
        window_seconds=3600,
        auto_disable_after_escalations=3,
        auto_disable_window_hours=24,
        source="manual",
    )
    row = get_self_repair_pattern("p1")
    assert row is not None
    assert row["name"] == "Restart mail_checker"
    assert row["trigger_event_kind"] == "process_watcher.matched"
    assert row["enabled"] == 1
    assert row["total_executed"] == 0


def test_list_patterns_filters_enabled_and_kind(isolated_runtime) -> None:
    from core.runtime.db import (
        insert_self_repair_pattern,
        list_self_repair_patterns,
        update_self_repair_pattern,
    )

    insert_self_repair_pattern(
        pattern_id="a", name="A", trigger_event_kind="kind.x",
        action_type="control_daemon", source="manual",
    )
    insert_self_repair_pattern(
        pattern_id="b", name="B", trigger_event_kind="kind.x",
        action_type="control_daemon", source="manual",
    )
    insert_self_repair_pattern(
        pattern_id="c", name="C", trigger_event_kind="kind.y",
        action_type="control_daemon", source="manual",
    )
    update_self_repair_pattern("b", enabled=False)

    only_enabled = list_self_repair_patterns(enabled=True)
    ids = sorted(r["pattern_id"] for r in only_enabled)
    assert ids == ["a", "c"]

    only_x = list_self_repair_patterns(trigger_event_kind="kind.x")
    ids_x = sorted(r["pattern_id"] for r in only_x)
    assert ids_x == ["a", "b"]


def test_update_pattern_partial_fields(isolated_runtime) -> None:
    from core.runtime.db import (
        insert_self_repair_pattern,
        update_self_repair_pattern,
        get_self_repair_pattern,
    )

    insert_self_repair_pattern(
        pattern_id="p1", name="orig", trigger_event_kind="x",
        action_type="control_daemon", source="manual",
    )
    update_self_repair_pattern("p1", enabled=False, last_outcome="executed")
    row = get_self_repair_pattern("p1")
    assert row["enabled"] == 0
    assert row["last_outcome"] == "executed"
    assert row["name"] == "orig"


def test_update_pattern_with_increment_fields(isolated_runtime) -> None:
    from core.runtime.db import (
        insert_self_repair_pattern,
        update_self_repair_pattern,
        get_self_repair_pattern,
    )

    insert_self_repair_pattern(
        pattern_id="p1", name="x", trigger_event_kind="k",
        action_type="control_daemon", source="manual",
    )
    update_self_repair_pattern("p1", total_executed_increment=1)
    update_self_repair_pattern("p1", total_executed_increment=2)
    row = get_self_repair_pattern("p1")
    assert row["total_executed"] == 3


def test_insert_and_count_attempts(isolated_runtime) -> None:
    from core.runtime.db import (
        insert_self_repair_pattern,
        insert_self_repair_attempt,
        count_recent_attempts,
    )

    insert_self_repair_pattern(
        pattern_id="p1", name="x", trigger_event_kind="k",
        action_type="control_daemon", source="manual",
    )
    insert_self_repair_attempt(
        pattern_id="p1",
        attempted_at="2026-05-05T10:00:00+00:00",
        triggered_by_event_id=42,
        outcome="executed",
        error_summary=None,
        elapsed_ms=15,
    )
    insert_self_repair_attempt(
        pattern_id="p1",
        attempted_at="2026-05-05T10:01:00+00:00",
        triggered_by_event_id=43,
        outcome="failed",
        error_summary="boom",
        elapsed_ms=22,
    )
    insert_self_repair_attempt(
        pattern_id="p1",
        attempted_at="2026-05-05T10:02:00+00:00",
        triggered_by_event_id=44,
        outcome="rate_limited",
        error_summary="cooldown",
        elapsed_ms=0,
    )

    total = count_recent_attempts(
        pattern_id="p1", since_iso="2026-05-05T09:55:00+00:00",
    )
    assert total == 3

    executed = count_recent_attempts(
        pattern_id="p1",
        since_iso="2026-05-05T09:55:00+00:00",
        outcome="executed",
    )
    assert executed == 1

    later = count_recent_attempts(
        pattern_id="p1", since_iso="2026-05-05T10:01:30+00:00",
    )
    assert later == 1


def test_delete_pattern(isolated_runtime) -> None:
    from core.runtime.db import (
        insert_self_repair_pattern,
        delete_self_repair_pattern,
        get_self_repair_pattern,
    )

    insert_self_repair_pattern(
        pattern_id="p1", name="x", trigger_event_kind="k",
        action_type="control_daemon", source="manual",
    )
    assert delete_self_repair_pattern("p1") is True
    assert get_self_repair_pattern("p1") is None
    assert delete_self_repair_pattern("nonexistent") is False
