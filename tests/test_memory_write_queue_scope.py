from __future__ import annotations

from core.identity.workspace_context import user_context


def test_sensory_queue_payload_carries_member_user(monkeypatch) -> None:
    from core.services import memory_write_queue as queue

    captured: dict[str, object] = {}
    monkeypatch.setattr(queue, "enqueue_write", lambda kind, payload, **kw: captured.update(payload) or "q1")
    monkeypatch.setattr("core.services.memory_write_queue.enqueue_write", queue.enqueue_write)
    from core.tools.sensory_tools import _exec_record_sensory_memory

    with user_context(discord_id="member-1"):
        result = _exec_record_sensory_memory(
            {"modality": "visual", "content": "et tydeligt indtryk"}
        )

    assert result["status"] == "ok"
    assert captured["user_id"] == "member-1"


def test_queue_processor_binds_payload_user(monkeypatch) -> None:
    from core.identity.workspace_context import current_user_id
    from core.services import memory_write_queue as queue

    seen: list[str] = []
    monkeypatch.setattr(
        queue,
        "_process_sensory",
        lambda payload, retry: (seen.append(current_user_id()) or True, ""),
    )

    ok, _ = queue._process_item(
        "sensory",
        {"modality": "visual", "content": "indtryk", "user_id": "member-1"},
        0,
    )

    assert ok is True
    assert seen == ["member-1"]


def test_queue_processor_rejects_legacy_unscoped_payload() -> None:
    from core.services import memory_write_queue as queue

    ok, error = queue._process_item("sensory", {"content": "legacy"}, 0)

    assert ok is False
    assert "user" in error.lower()


def test_member_cannot_enqueue_owner_brain_write(monkeypatch) -> None:
    from core.services import memory_write_queue as queue

    monkeypatch.setattr("core.identity.owner_resolver.owner_user_id", lambda: "owner-1")
    with user_context(discord_id="member-1"):
        queue_id = queue.enqueue_write(
            "brain", {"kind": "insight", "title": "x", "content": "private"}
        )

    assert queue_id == ""
