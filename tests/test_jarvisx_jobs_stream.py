from __future__ import annotations

import json

from fastapi import HTTPException
import pytest

from apps.api.jarvis_api.routes import jarvisx_processes as routes
from core.services import live_job_events


class _Pump:
    def __init__(self):
        self.added = 0
        self.removed = 0

    def add_subscriber(self):
        self.added += 1

    def remove_subscriber(self):
        self.removed += 1


@pytest.fixture
def client(monkeypatch):
    live_job_events.reset_for_tests()
    monkeypatch.setattr(routes, "_require_owner", lambda: None)
    monkeypatch.setattr(routes, "_jobs_snapshot", lambda **_kwargs: {
        "jobs": [{"id": "worker", "kilde": "supervisor"}],
        "bridge_ok": True,
        "uspecificeret": 0,
    })
    pump = _Pump()
    monkeypatch.setattr(routes, "_job_source_pump", lambda _uid: pump)
    return pump


def _publish(event_type="job_output", *, session_id=""):
    return live_job_events.publish(
        event_type, job_key="job-1", session_id=session_id,
        source="tool", payload={"chunk": "x"},
    )


async def _first_frame(*, session_id="", after=None, last_event_id=None):
    response = await routes.stream_background_jobs(
        session_id=session_id, after=after, last_event_id=last_event_id,
    )
    try:
        chunk = await anext(response.body_iterator)
    finally:
        await response.body_iterator.aclose()
    frame: dict[str, str] = {}
    for line in chunk.strip().splitlines():
        key, value = line.split(":", 1)
        frame[key] = value.strip()
    return frame


@pytest.mark.asyncio
async def test_stream_starts_with_snapshot_and_cursor(client):
    frame = await _first_frame(session_id="s1")
    assert frame["event"] == "snapshot"
    data = json.loads(frame["data"])
    assert data["jobs"][0]["id"] == "worker"
    assert data["bridge_ok"] is True
    assert data["cursor"] == int(frame["id"])


@pytest.mark.asyncio
async def test_after_cursor_replays_only_missed_events(client):
    first = _publish("job_started")
    second = _publish("job_output")
    frame = await _first_frame(after=first.cursor)
    assert frame["event"] == "job_output"
    assert frame["id"] == str(second.cursor)


@pytest.mark.asyncio
async def test_last_event_id_is_used_when_after_is_absent(client):
    first = _publish("job_started")
    second = _publish("job_output")
    frame = await _first_frame(last_event_id=str(first.cursor))
    assert frame["id"] == str(second.cursor)


@pytest.mark.asyncio
async def test_session_filter_hides_other_conversation(client):
    _publish("job_output", session_id="s-other")
    frame = await _first_frame(session_id="s-current")
    assert frame["event"] == "snapshot"
    assert "s-other" not in frame["data"]


@pytest.mark.asyncio
async def test_unauthenticated_stream_is_rejected(monkeypatch):
    live_job_events.reset_for_tests()

    def deny():
        raise HTTPException(status_code=403, detail="owner required")

    monkeypatch.setattr(routes, "_require_owner", deny)
    with pytest.raises(HTTPException) as caught:
        await routes.stream_background_jobs(
            session_id="", after=None, last_event_id=None,
        )
    assert caught.value.status_code == 403
