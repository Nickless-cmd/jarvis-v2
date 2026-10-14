from __future__ import annotations


def test_recall_observability_drops_content_fields(monkeypatch) -> None:
    from core.services import recall_observability

    captured = {}
    monkeypatch.setattr(
        "core.eventbus.bus.event_bus.publish",
        lambda kind, payload: captured.update({"kind": kind, "payload": payload}),
    )
    recall_observability.emit_recall_outcome(
        path="recall", result_count=1, query="private", user_id="private-user",
    )
    assert captured == {
        "kind": "memory.recall",
        "payload": {"path": "recall", "result_count": 1},
    }
