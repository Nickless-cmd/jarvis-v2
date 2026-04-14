from __future__ import annotations

import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.eventbus.bus import event_bus

router = APIRouter()
logger = logging.getLogger("uvicorn.error")

# Ping interval keeps the websocket alive during quiet periods.
# Many browsers / reverse-proxies drop idle connections after 30-60 s.
_PING_INTERVAL_S = 25
_EVENT_POLL_INTERVAL_S = 0.5
_EVENT_BATCH_SIZE = 100


@router.websocket("/ws")
async def websocket_stream(ws: WebSocket) -> None:
    client = getattr(ws, "client", None)
    client_label = f"{getattr(client, 'host', 'unknown')}:{getattr(client, 'port', 'unknown')}"
    await ws.accept()
    items = sorted(event_bus.recent(limit=20), key=lambda x: x["id"])
    last_seen_id = 0
    logger.info(
        "mission-control websocket connected client=%s backlog=%s",
        client_label,
        len(items),
    )

    for item in items:
        await ws.send_json(item)
        last_seen_id = max(last_seen_id, item["id"])

    async def _forward_events() -> None:
        """Poll persisted events so delivery works across multiple API workers."""
        nonlocal last_seen_id
        while True:
            items = await asyncio.to_thread(
                event_bus.recent_since_id,
                last_seen_id,
                limit=_EVENT_BATCH_SIZE,
            )
            if not items:
                await asyncio.sleep(_EVENT_POLL_INTERVAL_S)
                continue
            for item in items:
                if item["id"] <= last_seen_id:
                    continue
                await ws.send_json(item)
                last_seen_id = item["id"]
                logger.debug(
                    "mission-control websocket forwarded event client=%s event_id=%s family=%s kind=%s",
                    client_label,
                    item.get("id"),
                    item.get("family"),
                    item.get("kind"),
                )

    async def _keepalive_ping() -> None:
        """Send periodic websocket pings so idle connections are not dropped."""
        while True:
            await asyncio.sleep(_PING_INTERVAL_S)
            try:
                await ws.send_json({"type": "ping"})
            except Exception:
                return

    try:
        # Run event forwarding and keepalive in parallel.
        # When either task ends (disconnect / error), cancel the other.
        async with asyncio.TaskGroup() as tg:
            tg.create_task(_forward_events())
            tg.create_task(_keepalive_ping())
    except* WebSocketDisconnect:
        logger.info(
            "mission-control websocket disconnected client=%s last_seen_id=%s",
            client_label,
            last_seen_id,
        )
    except* Exception as eg:
        for exc in eg.exceptions:
            if not isinstance(exc, WebSocketDisconnect):
                logger.warning(
                    "mission-control websocket error client=%s error=%s",
                    client_label,
                    exc,
                )
    finally:
        logger.info(
            "mission-control websocket cleanup client=%s last_seen_id=%s",
            client_label,
            last_seen_id,
        )
