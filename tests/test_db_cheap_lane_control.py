from __future__ import annotations

from datetime import UTC, datetime


def _record(**overrides):
    from core.runtime.db_cheap_provider import record_cheap_provider_invocation

    values = {
        "provider": "groq",
        "model": "llama",
        "status": "completed",
    }
    values.update(overrides)
    return record_cheap_provider_invocation(**values)


def test_extended_invocation_defaults_preserve_old_callers(isolated_runtime):
    from core.runtime.db_cheap_lane_control import get_cheap_lane_invocation_detail

    row = _record()
    detail = get_cheap_lane_invocation_detail(str(row["invocation_id"]))

    assert detail is not None
    assert detail["correlation_id"]
    assert detail["attempt"] == 1
    assert detail["route_decision_id"] == ""
    assert detail["cache_hit_tokens"] == 0
    assert detail["payload_status"] == "not_captured"


def test_extended_invocation_persists_observability_fields(isolated_runtime):
    from core.runtime.db_cheap_lane_control import get_cheap_lane_invocation_detail

    row = _record(
        invocation_id="inv-1",
        correlation_id="corr-1",
        daemon="dream",
        task_kind="background",
        egress="proxy-a",
        error_class="rate_limit",
        payload_status="captured",
        cache_hit_tokens=12,
        cache_miss_tokens=3,
        attempt=2,
        retry_parent_id="inv-0",
        fallback_parent_id="inv-x",
        route_decision_id="route-1",
    )
    detail = get_cheap_lane_invocation_detail(str(row["invocation_id"]))

    assert detail is not None
    assert detail["correlation_id"] == "corr-1"
    assert detail["daemon"] == "dream"
    assert detail["attempt"] == 2
    assert detail["cache_hit_tokens"] == 12
    assert detail["fallback_parent_id"] == "inv-x"


def test_route_trace_and_audit_are_durable(isolated_runtime):
    from core.runtime.db_cheap_lane_control import (
        finalize_cheap_lane_audit,
        get_route_decision,
        list_cheap_lane_audit,
        record_cheap_lane_audit,
        record_route_decision,
    )

    trace_id = record_route_decision(
        correlation_id="corr-1",
        task_kind="background",
        daemon="dream",
        candidates=[
            {"slot_id": "groq::m::default", "eligible": True, "weight": 0.8}
        ],
        selected_slot_id="groq::m::default",
        selection_reason="healthy-headroom",
    )
    audit_id = record_cheap_lane_audit(
        actor="owner",
        action="slot.pause",
        target="groq::m::default",
        reason="maintenance",
        before={"paused": False},
        after={},
        result="pending",
    )
    finalize_cheap_lane_audit(
        audit_id, after={"paused": True}, result="ok"
    )

    trace = get_route_decision(trace_id)
    audits = list_cheap_lane_audit(limit=10)
    assert trace is not None
    assert trace["selected_slot_id"] == "groq::m::default"
    assert trace["candidates"][0]["weight"] == 0.8
    assert audits["items"][0]["audit_id"] == audit_id
    assert audits["items"][0]["after"] == {"paused": True}
    assert audits["items"][0]["result"] == "ok"


def test_quota_observation_and_redacted_payload_join_detail(isolated_runtime):
    from core.runtime.db_cheap_lane_control import (
        get_cheap_lane_invocation_detail,
        list_quota_observations,
        record_quota_observation,
        record_redacted_payload,
    )

    _record(invocation_id="inv-payload", correlation_id="corr-payload")
    record_quota_observation(
        provider="groq",
        auth_profile="default",
        period="month",
        unit="tokens",
        limit=1_000_000,
        remaining=750_000,
        reset_at="2026-10-01T00:00:00+00:00",
        observed_at="2026-09-18T10:00:00+00:00",
    )
    record_redacted_payload(
        invocation_id="inv-payload",
        prompt="hello",
        response="world",
        status="captured",
        expires_at="2026-09-25T10:00:00+00:00",
    )

    observations = list_quota_observations(provider="groq", auth_profile="default")
    detail = get_cheap_lane_invocation_detail("inv-payload")
    assert observations[0]["remaining"] == 750_000
    assert detail is not None
    assert detail["payload"]["prompt"] == "hello"
    assert detail["payload"]["response"] == "world"


def test_invocation_log_filters_and_cursor_are_stable(isolated_runtime):
    from core.runtime.db import connect
    from core.runtime.db_cheap_lane_control import list_cheap_lane_invocations

    first = _record(invocation_id="inv-a", provider="groq", status="failed")
    second = _record(invocation_id="inv-b", provider="gemini", status="completed")
    with connect() as conn:
        conn.execute(
            "UPDATE cheap_provider_invocations SET created_at = ? WHERE invocation_id = ?",
            ("2026-09-18T09:00:00+00:00", first["invocation_id"]),
        )
        conn.execute(
            "UPDATE cheap_provider_invocations SET created_at = ? WHERE invocation_id = ?",
            ("2026-09-18T10:00:00+00:00", second["invocation_id"]),
        )
        conn.commit()

    page_one = list_cheap_lane_invocations(
        since="2026-09-18T00:00:00+00:00", limit=1
    )
    page_two = list_cheap_lane_invocations(
        since="2026-09-18T00:00:00+00:00",
        limit=1,
        cursor=str(page_one["next_cursor"]),
    )
    failed = list_cheap_lane_invocations(
        since="2026-09-18T00:00:00+00:00", provider="groq", status="failed"
    )

    assert [row["invocation_id"] for row in page_one["items"]] == ["inv-b"]
    assert [row["invocation_id"] for row in page_two["items"]] == ["inv-a"]
    assert page_two["next_cursor"] is None
    assert [row["invocation_id"] for row in failed["items"]] == ["inv-a"]


def test_invalid_cursor_is_rejected(isolated_runtime):
    from core.runtime.db_cheap_lane_control import list_cheap_lane_invocations

    _record()
    try:
        list_cheap_lane_invocations(
            since=datetime(2026, 1, 1, tzinfo=UTC).isoformat(), cursor="not-a-cursor"
        )
    except ValueError as exc:
        assert "cursor" in str(exc).lower()
    else:
        raise AssertionError("invalid cursor was accepted")
