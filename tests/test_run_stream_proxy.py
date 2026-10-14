from __future__ import annotations

import asyncio


def test_local_proxy_stream_replays_from_global_cursor() -> None:
    from core.services import run_event_log
    from core.services.run_stream_proxy import local_frame_generator

    run_event_log._RUNS.clear()
    run_event_log._ALIASER.clear()
    run_event_log._ALIASER_OMVENDT.clear()
    run_event_log.create("proxy-run", "proxy-session")
    run_event_log.append("proxy-run", 'event: ping\ndata: {"type":"ping"}\n\n')
    run_event_log.append(
        "proxy-run",
        'event: message_stop\ndata: {"type":"message_stop"}\n\n',
    )
    run_event_log.mark_done("proxy-run")

    async def collect() -> list[str]:
        return [frame async for frame in local_frame_generator("proxy-run", 0)]

    assert asyncio.run(collect()) == [
        'event: message_stop\ndata: {"type":"message_stop"}\n\n'
    ]

