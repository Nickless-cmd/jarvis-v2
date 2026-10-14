from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from core.services.run_stream_locator import RunStreamLocation


def _location(**changes) -> RunStreamLocation:
    values = {
        "run_id": "run-foreign",
        "session_id": "session-foreign",
        "lifecycle": "running",
        "producer_process": "api",
        "local_available": True,
        "journal_status": "running",
    }
    values.update(changes)
    return RunStreamLocation(**values)


def test_subscribe_checks_session_access_before_stream_lookup(monkeypatch) -> None:
    from apps.api.jarvis_api.routes import chat_run_streams as routes

    monkeypatch.setattr(routes, "locate_run", lambda _run_id: _location())

    def _deny(_session_id: str) -> None:
        raise HTTPException(status_code=403, detail="forbidden")

    monkeypatch.setattr(routes, "kraev_adgang", _deny)
    monkeypatch.setattr(
        routes,
        "local_frame_generator",
        lambda *_args, **_kwargs: pytest.fail("stream was read before authorization"),
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(routes.chat_run_subscribe("run-foreign"))
    assert exc.value.status_code == 403


def test_active_runs_omits_foreign_journal_session(monkeypatch) -> None:
    from apps.api.jarvis_api.routes import chat_run_streams as routes

    monkeypatch.setattr(
        routes,
        "active_locations",
        lambda **_kwargs: [
            _location(run_id="run-allowed", session_id="session-allowed"),
            _location(run_id="run-foreign", session_id="session-foreign"),
        ],
    )
    monkeypatch.setattr(
        "core.identity.session_access.maa_tilgaa_session",
        lambda session_id: session_id == "session-allowed",
    )
    monkeypatch.setattr(
        "core.runtime.settings.load_settings",
        lambda: type("Settings", (), {"server_authoritative_runs": True})(),
    )

    payload = routes.chat_active_runs()

    assert payload["session_ids"] == ["session-allowed"]
    assert [item["run_id"] for item in payload["sessions"]] == ["run-allowed"]
