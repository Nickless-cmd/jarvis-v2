from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from core.services.run_stream_locator import RunStreamLocation


def _location(**changes) -> RunStreamLocation:
    values = {
        "run_id": "run-123",
        "session_id": "session-123",
        "lifecycle": "running",
        "producer_process": "runtime",
        "local_available": False,
        "journal_status": "running",
    }
    values.update(changes)
    return RunStreamLocation(**values)


def test_running_remote_stream_failure_is_503_not_404_or_200(monkeypatch) -> None:
    from apps.api.jarvis_api.routes import chat_run_streams as routes

    monkeypatch.setattr(routes, "locate_run", lambda _run_id: _location())
    monkeypatch.setattr(routes, "kraev_adgang", lambda _session_id: None)

    async def _failed_proxy(*_args, **_kwargs):
        raise routes.stream_error(503, "stream_unavailable", retry_after=1)

    monkeypatch.setattr(routes, "proxy_owner_stream", _failed_proxy)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(routes.chat_run_subscribe("run-123"))
    assert exc.value.status_code == 503
    assert exc.value.detail["code"] == "stream_unavailable"


@pytest.mark.parametrize(
    ("location", "status", "code"),
    [
        (_location(lifecycle="terminal", producer_process="unknown"), 410, "stream_pruned"),
        (_location(lifecycle="unknown", session_id="", producer_process="unknown"), 404, "run_unknown"),
    ],
)
def test_subscribe_distinguishes_terminal_pruned_and_unknown(
    monkeypatch,
    location: RunStreamLocation,
    status: int,
    code: str,
) -> None:
    from apps.api.jarvis_api.routes import chat_run_streams as routes

    monkeypatch.setattr(routes, "locate_run", lambda _run_id: location)
    monkeypatch.setattr(routes, "kraev_adgang", lambda _session_id: None)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(routes.chat_run_subscribe(location.run_id))
    assert exc.value.status_code == status
    assert exc.value.detail["code"] == code


def test_session_live_remote_running_never_returns_204(monkeypatch) -> None:
    from apps.api.jarvis_api.routes import chat_run_streams as routes

    monkeypatch.setattr(routes, "live_run_for_session", lambda _sid: _location())
    monkeypatch.setattr(routes, "kraev_adgang", lambda _session_id: None)

    async def _failed_proxy(*_args, **_kwargs):
        raise routes.stream_error(503, "stream_unavailable", retry_after=1)

    monkeypatch.setattr(routes, "proxy_owner_stream", _failed_proxy)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(routes.chat_session_live("session-123"))
    assert exc.value.status_code == 503
