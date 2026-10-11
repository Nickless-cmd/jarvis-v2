from __future__ import annotations

import asyncio

import pytest

from core.services import live_job_events as hub


@pytest.fixture(autouse=True)
def _fresh_hub():
    hub.reset_for_tests()
    yield
    hub.reset_for_tests()


def _drain_nowait(queue: asyncio.Queue) -> list[hub.JobEvent]:
    items: list[hub.JobEvent] = []
    while True:
        try:
            items.append(queue.get_nowait())
        except asyncio.QueueEmpty:
            return items


def test_replay_returns_only_events_after_cursor():
    first = hub.publish(
        "job_started", job_key="tool:a", session_id="s1", source="tool", payload={}
    )
    second = hub.publish(
        "job_output", job_key="tool:a", session_id="s1", source="tool",
        payload={"seq": 1, "chunk": "a"},
    )

    sub = hub.subscribe(session_id="s1", after=first.cursor)

    assert [event.cursor for event in sub.initial_events] == [second.cursor]
    assert sub.needs_snapshot is False
    sub.close()


def test_expired_cursor_requires_a_fresh_snapshot():
    local = hub.LiveJobEventHub(replay_size=2)
    first = local.publish(
        "job_started", job_key="tool:a", session_id="s1", source="tool", payload={}
    )
    for seq in range(1, 4):
        local.publish(
            "job_output", job_key="tool:a", session_id="s1", source="tool",
            payload={"seq": seq, "chunk": str(seq)},
        )

    sub = local.subscribe(session_id="s1", after=first.cursor)

    assert sub.needs_snapshot is True
    assert sub.initial_events == []
    sub.close()


@pytest.mark.asyncio
async def test_mismatched_session_receives_no_event_but_global_event_does():
    sub = hub.subscribe(session_id="s2", after=None)
    hub.publish(
        "job_output", job_key="tool:a", session_id="s1", source="tool",
        payload={"seq": 1, "chunk": "secret"},
    )
    hub.publish(
        "source_status", job_key="operator", session_id="", source="operator",
        payload={"healthy": False},
    )
    await asyncio.sleep(0)

    delivered = _drain_nowait(sub.queue)
    assert [(event.event_type, event.session_id) for event in delivered] == [
        ("source_status", ""),
    ]
    sub.close()


@pytest.mark.asyncio
async def test_slow_subscriber_drops_output_but_keeps_finish():
    sub = hub.subscribe(session_id="s1", after=None, queue_size=2)
    for seq in range(1, 5):
        hub.publish(
            "job_output", job_key="tool:a", session_id="s1", source="tool",
            payload={"seq": seq, "chunk": str(seq)},
        )
    hub.publish(
        "job_finished", job_key="tool:a", session_id="s1", source="tool",
        payload={"status": "exited", "exit_code": 0},
    )
    await asyncio.sleep(0)

    delivered = _drain_nowait(sub.queue)
    assert delivered[-1].event_type == "job_finished"
    assert delivered[-1].payload["output_truncated"] is True
    assert len(delivered) <= 2
    sub.close()


def test_cursor_and_serialized_shape_are_stable():
    first = hub.publish(
        "job_started", job_key="tool:a", session_id="s1", source="tool",
        payload={"job": {"id": "a"}},
    )
    second = hub.publish(
        "job_finished", job_key="tool:a", session_id="s1", source="tool",
        payload={"status": "exited", "exit_code": 0},
    )

    assert second.cursor == first.cursor + 1
    assert second.as_dict() == {
        "cursor": second.cursor,
        "type": "job_finished",
        "job_key": "tool:a",
        "session_id": "s1",
        "source": "tool",
        "timestamp": second.timestamp,
        "payload": {"status": "exited", "exit_code": 0},
    }
