"""Delivery only applies to a finished read-only research agent."""

from core.services.scout_inbox_delivery import record_scout_completion


def test_non_scout_is_not_registered(monkeypatch):
    from core.services import inbox_state

    called = []
    monkeypatch.setattr(inbox_state, "registrer_kilde", called.append)
    assert record_scout_completion({
        "agent_id": "agent-1", "role": "executor",
        "tool_policy": "read-only-runtime", "status": "completed",
        "context": {"user_id": "bjorn"},
        "latest_run": {"run_id": "run-1", "status": "completed"},
    }) is False
    assert called == []
