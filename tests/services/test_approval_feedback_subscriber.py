from __future__ import annotations

import importlib
import time


def _load_modules():
    bus = importlib.import_module("core.eventbus.bus")
    subscriber = importlib.import_module("core.services.approval_feedback_subscriber")
    runtime = importlib.import_module("core.services.tool_intent_approval_runtime")
    db = importlib.import_module("core.runtime.db")
    return bus, subscriber, runtime, db


def test_subscriber_logs_approved_event(isolated_runtime) -> None:
    bus, subscriber, _, db = _load_modules()
    subscriber.start_approval_feedback_subscriber()
    try:
        bus.event_bus.publish(
            "approvals.tool_intent_resolved",
            {
                "intent_key": "tool-intent::abc",
                "approval_state": "approved",
                "approval_source": "mc",
                "resolved_at": "2026-04-17T10:00:00+00:00",
                "resolution_reason": "Approved in test",
                "resolution_message": "Looks good",
                "session_id": "test-session",
                "tool_name": "repo-inspector",
            },
        )
        deadline = time.time() + 2.0
        rows = []
        while time.time() < deadline:
            rows = db.list_approval_feedback(limit=5)
            if rows:
                break
            time.sleep(0.05)
        assert rows
        assert rows[0]["approval_state"] == "approved"
        assert rows[0]["tool_name"] == "repo-inspector"
    finally:
        subscriber.stop_approval_feedback_subscriber()


def test_subscriber_ignores_unrelated_events(isolated_runtime) -> None:
    bus, subscriber, _, db = _load_modules()
    subscriber.start_approval_feedback_subscriber()
    try:
        bus.event_bus.publish("runtime.started", {"component": "api"})
        time.sleep(0.2)
        assert db.list_approval_feedback(limit=5) == []
    finally:
        subscriber.stop_approval_feedback_subscriber()


def test_emission_does_not_break_resolve_on_eventbus_failure(
    isolated_runtime, monkeypatch
) -> None:
    _, _, runtime, db = _load_modules()
    intent_surface = {
        "intent_state": "active",
        "approval_required": True,
        "intent_type": "inspect-repo-status",
        "intent_target": "workspace",
        "approval_scope": "repo-read",
        "tool_name": "repo-inspector",
    }
    intent_key = runtime.tool_intent_approval_key(intent_surface)
    db.create_tool_intent_approval_request(
        intent_key=intent_key,
        intent_type="inspect-repo-status",
        intent_target="workspace",
        approval_scope="repo-read",
        approval_required=True,
        approval_reason="Need approval",
        requested_at="2026-04-17T10:00:00+00:00",
        expires_at="2026-04-17T10:15:00+00:00",
    )
    monkeypatch.setattr(runtime.event_bus, "publish", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))

    resolved = runtime.resolve_tool_intent_approval(
        intent_surface,
        approval_state="approved",
        approval_source="mc",
        resolution_reason="Approved despite eventbus failure",
        resolution_message="ok",
        session_id="mc-test",
    )

    assert resolved["approval_state"] == "approved"
    stored = db.get_tool_intent_approval_request(intent_key)
    assert stored is not None
    assert stored["approval_state"] == "approved"
