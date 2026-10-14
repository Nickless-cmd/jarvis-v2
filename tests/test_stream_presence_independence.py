from __future__ import annotations

import asyncio


async def _subscribe_once(routes, workspace_context, channel: str) -> str:
    from core.services import run_event_log

    token = workspace_context.set_context(
        workspace_name="bjorn",
        user_id="owner-user",
        role="owner",
        channel=channel,
    )
    try:
        response = await routes.chat_run_subscribe("run-presence-independent", 0)
        iterator = response.body_iterator
        first = await iterator.__anext__()
        assert run_event_log._RUNS["run-presence-independent"]["subscribers"] == 1
        chunks = [first.decode() if isinstance(first, bytes) else first]
        async for chunk in iterator:
            chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)
        assert run_event_log._RUNS["run-presence-independent"]["subscribers"] == 0
        return "".join(chunks)
    finally:
        workspace_context.reset_context(token)


def test_notification_destination_does_not_own_or_authorize_stream(
    isolated_runtime,
    monkeypatch,
) -> None:
    from apps.api.jarvis_api.routes import chat_run_streams as routes
    from core.identity import workspace_context
    from core.services import device_presence
    from core.services import in_flight_runs
    from core.services import notification_router
    from core.services import run_event_log

    clock = {"now": 0.0}
    monkeypatch.setattr(device_presence, "_now", lambda: clock["now"])
    device_presence.reset()
    device_presence.record_ping(
        "owner-user",
        "desk",
        "desktop",
        foreground=True,
        awake=True,
        network="home",
        interaction=True,
    )
    clock["now"] = 20.0  # desk er stale (>12 s)
    device_presence.record_ping(
        "owner-user",
        "mobile",
        "mobile",
        foreground=True,
        awake=True,
        network="away",
        interaction=True,
    )
    notification_router.set_preferences("owner-user", **{"global": "mobile"})
    assert notification_router.resolve_channel(
        notification_router.get_preferences("owner-user"), "wakeup"
    ) == "mobile"

    monkeypatch.setattr("core.services.central_xproc.process_role", lambda: "api")
    in_flight_runs.mark_started(
        run_id="run-presence-independent",
        session_id="session-presence-independent",
        user_message="independence proof",
        kind="autonomous",
    )
    run_event_log.create("run-presence-independent", "session-presence-independent")
    run_event_log.append(
        "run-presence-independent",
        'event: message_stop\ndata: {"type":"message_stop"}\n\n',
    )
    run_event_log.mark_done("run-presence-independent")
    journal_before = dict(in_flight_runs.get_record("run-presence-independent") or {})

    desk_stream = asyncio.run(_subscribe_once(routes, workspace_context, "jarvisx-electron"))
    mobile_stream = asyncio.run(_subscribe_once(routes, workspace_context, "mobile"))

    assert desk_stream == mobile_stream
    assert "message_stop" in desk_stream
    assert in_flight_runs.get_record("run-presence-independent") == journal_before
    assert journal_before["producer_process"] == "api"
