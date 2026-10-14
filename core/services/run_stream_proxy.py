"""Local replay and authenticated cross-process proxying for run streams."""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from core.services.run_stream_locator import RunStreamLocation

logger = logging.getLogger(__name__)

_INTERNAL_RUN_STREAM_PATH = "/api/internal/run-stream/{run_id}"


def stream_error(
    status: int,
    code: str,
    retry_after: int | None = None,
    *,
    run_id: str = "",
) -> HTTPException:
    headers = {"Retry-After": str(retry_after)} if retry_after is not None else None
    return HTTPException(
        status_code=status,
        detail={"code": code, "run_id": str(run_id or "")},
        headers=headers,
    )


async def local_frame_generator(run_id: str, from_idx: int) -> AsyncIterator[str]:
    """Replay and follow one process-local authoritative frame log."""
    from apps.api.jarvis_api.sse_v2_events import Ping
    from core.services import run_event_log as relay

    session_id = relay.session_for_run(run_id) or ""
    idx = max(0, int(from_idx))
    saw_stop = False
    empty = 0
    last_emit = time.monotonic()
    relay.subscriber_opened(run_id)
    logger.info("run-stream attach run=%s from_idx=%d", run_id, idx)
    try:
        while True:
            frames, done, next_idx = relay.read_from(run_id, idx)
            if frames and next_idx > idx and any(relay.er_gap_frame(f) for f in frames):
                logger.info("run-stream replay-gap run=%s from_idx=%d next_idx=%d", run_id, idx, next_idx)
            idx = next_idx
            for frame in frames:
                if "message_stop" in frame:
                    saw_stop = True
                yield frame
                last_emit = time.monotonic()
            if done:
                if not saw_stop:
                    yield relay.synthetic_terminal_frame(
                        run_id,
                        session_id,
                        reason="run_done_no_stop",
                    )
                relay.mark_consumed(run_id)
                logger.info("run-stream terminal run=%s offset=%d", run_id, idx)
                break
            if frames:
                empty = 0
            else:
                empty += 1
                if (time.monotonic() - last_emit) >= 5.0:
                    # Keepalive is deliberately not stored and does not change idx.
                    yield Ping().to_sse_line()
                    last_emit = time.monotonic()
                if empty > 300 and relay.is_open(run_id):
                    empty = 0
                elif empty > 300:
                    yield relay.synthetic_terminal_frame(
                        run_id,
                        session_id,
                        reason="run_subscribe_idle",
                    )
                    break
            await asyncio.sleep(0.08)
    finally:
        relay.subscriber_closed(run_id)
        logger.info("run-stream detach run=%s offset=%d", run_id, idx)


async def proxy_owner_stream(
    location: RunStreamLocation,
    from_idx: int,
) -> StreamingResponse:
    """Open the owner process before committing a public 200 response."""
    import httpx

    from core.services.jarvisx_bridge import (
        _INTERNAL_TOKEN_HEADER,
        _port_for_process,
        internal_dispatch_token,
    )

    token = internal_dispatch_token()
    if not token:
        raise stream_error(
            503, "stream_unavailable", retry_after=1, run_id=location.run_id
        )
    port = _port_for_process(location.producer_process)
    url = f"http://127.0.0.1:{port}" + _INTERNAL_RUN_STREAM_PATH.format(
        run_id=location.run_id
    )
    client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=2.0))
    upstream_context = client.stream(
        "GET",
        url,
        params={"from_idx": max(0, int(from_idx))},
        headers={_INTERNAL_TOKEN_HEADER: token},
    )
    try:
        upstream = await upstream_context.__aenter__()
    except Exception as exc:
        await client.aclose()
        logger.warning(
            "run-stream proxy-failure run=%s owner=%s error=%s",
            location.run_id,
            location.producer_process,
            type(exc).__name__,
        )
        raise stream_error(
            503, "stream_unavailable", retry_after=1, run_id=location.run_id
        ) from exc

    content_type = upstream.headers.get("content-type", "").lower()
    if upstream.status_code != 200 or "text/event-stream" not in content_type:
        await upstream_context.__aexit__(None, None, None)
        await client.aclose()
        logger.warning(
            "run-stream proxy-rejected run=%s owner=%s status=%d content_type=%s",
            location.run_id,
            location.producer_process,
            upstream.status_code,
            content_type[:80],
        )
        raise stream_error(
            503, "stream_unavailable", retry_after=1, run_id=location.run_id
        )

    async def _bytes() -> AsyncIterator[bytes]:
        try:
            async for chunk in upstream.aiter_raw():
                yield chunk
        finally:
            await upstream_context.__aexit__(None, None, None)
            await client.aclose()

    logger.info(
        "run-stream proxy-attach run=%s owner=%s from_idx=%d",
        location.run_id,
        location.producer_process,
        max(0, int(from_idx)),
    )
    return StreamingResponse(
        _bytes(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Run-Id": location.run_id,
        },
    )
