from __future__ import annotations

import asyncio


class _Request:
    def __init__(self, host: str | None, headers: dict[str, str]):
        self.client = type("Client", (), {"host": host})() if host else None
        self.headers = headers


def test_internal_stream_rejects_non_loopback_forwarded_and_bad_tokens(monkeypatch) -> None:
    from apps.api.jarvis_api.routes import internal_run_stream as route

    monkeypatch.setattr(route, "internal_dispatch_token", lambda: "correct-token")

    cases = [
        (_Request("10.0.0.8", {route._INTERNAL_TOKEN_HEADER: "correct-token"}), 403),
        (_Request("127.0.0.1", {"x-forwarded-for": "8.8.8.8", route._INTERNAL_TOKEN_HEADER: "correct-token"}), 403),
        (_Request("127.0.0.1", {}), 401),
        (_Request("127.0.0.1", {route._INTERNAL_TOKEN_HEADER: "wrong"}), 401),
    ]
    for request, expected in cases:
        response = asyncio.run(route.internal_run_stream(request, "run-local", 0))
        assert response.status_code == expected


def test_internal_stream_only_serves_local_log(isolated_runtime, monkeypatch) -> None:
    from apps.api.jarvis_api.routes import internal_run_stream as route
    from core.services import run_event_log

    monkeypatch.setattr(route, "internal_dispatch_token", lambda: "correct-token")
    request = _Request(
        "127.0.0.1",
        {route._INTERNAL_TOKEN_HEADER: "correct-token"},
    )

    missing = asyncio.run(route.internal_run_stream(request, "run-remote", 0))
    assert missing.status_code == 404

    run_event_log.create("run-local", "session-local")
    run_event_log.append("run-local", 'event: message_stop\ndata: {"type":"message_stop"}\n\n')
    run_event_log.mark_done("run-local")
    response = asyncio.run(route.internal_run_stream(request, "run-local", 0))
    assert response.status_code == 200
    assert response.headers["x-run-id"] == "run-local"
