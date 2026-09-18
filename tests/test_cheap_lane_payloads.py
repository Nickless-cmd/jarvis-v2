from __future__ import annotations

from datetime import UTC, datetime, timedelta


def _invocation() -> str:
    from core.runtime.db_cheap_provider import record_cheap_provider_invocation

    row = record_cheap_provider_invocation(provider="groq", status="completed")
    return str(row["invocation_id"])


def test_redaction_removes_headers_keys_prefixes_and_keeps_safe_text():
    from core.services.cheap_lane_payloads import redact_payload

    result = redact_payload({
        "Authorization": "Bearer abcdefghijklmnopqrstuvwxyz",
        "api" + "_key": "jvs-secret-value-123456",
        "nested": {"cookie": "session=top-secret", "prompt": "hello"},
    })

    assert "abcdefghijklmnopqrstuvwxyz" not in result.text
    assert "jvs-secret" not in result.text
    assert "top-secret" not in result.text
    assert "hello" in result.text
    assert result.redacted_count == 3


def test_failed_redaction_stores_status_not_payload(isolated_runtime, monkeypatch):
    import core.services.cheap_lane_payloads as payloads
    from core.runtime.db_cheap_lane_control import get_cheap_lane_invocation_detail

    invocation_id = _invocation()
    monkeypatch.setattr(
        payloads, "redact_payload",
        lambda _value: (_ for _ in ()).throw(ValueError("bad")),
    )
    status = payloads.capture_invocation_payload(
        invocation_id=invocation_id, prompt={"x": 1}, response="ok"
    )
    detail = get_cheap_lane_invocation_detail(invocation_id)

    assert status == "redaction_failed"
    assert detail is not None
    assert detail["payload_status"] == "redaction_failed"
    assert detail["payload"]["prompt"] is None
    assert detail["payload"]["response"] is None


def test_capture_is_bounded_and_uses_configured_pattern(isolated_runtime, monkeypatch):
    import core.services.cheap_lane_payloads as payloads
    from core.runtime.db_cheap_lane_control import get_cheap_lane_invocation_detail

    invocation_id = _invocation()
    monkeypatch.setattr(payloads, "_configured_patterns", lambda: [r"customer-\d+"])
    status = payloads.capture_invocation_payload(
        invocation_id=invocation_id,
        prompt="customer-123 " + "x" * 80_000,
        response="done",
    )
    detail = get_cheap_lane_invocation_detail(invocation_id)

    assert status == "captured"
    assert detail is not None
    assert "customer-123" not in detail["payload"]["prompt"]
    assert len(detail["payload"]["prompt"].encode("utf-8")) <= 64 * 1024


def test_expired_payload_is_removed_without_invocation(isolated_runtime):
    from core.runtime.db_core import connect
    from core.runtime.db_cheap_lane_control import get_cheap_lane_invocation_detail
    from core.services.cheap_lane_payloads import (
        capture_invocation_payload,
        purge_expired_payloads,
    )

    invocation_id = _invocation()
    capture_invocation_payload(
        invocation_id=invocation_id, prompt="hello", response="world"
    )
    with connect() as conn:
        conn.execute(
            "UPDATE cheap_lane_redacted_payloads SET expires_at = ? WHERE invocation_id = ?",
            ((datetime.now(UTC) - timedelta(days=1)).isoformat(), invocation_id),
        )
        conn.commit()

    assert purge_expired_payloads(now=datetime.now(UTC)) == 1
    detail = get_cheap_lane_invocation_detail(invocation_id)
    assert detail is not None
    assert detail["payload"] is None
    assert detail["payload_status"] == "expired"
