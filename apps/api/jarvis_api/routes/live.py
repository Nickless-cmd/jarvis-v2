from __future__ import annotations

import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.eventbus.bus import event_bus

router = APIRouter()
logger = logging.getLogger("uvicorn.error")


@router.websocket("/ws")
async def websocket_stream(ws: WebSocket) -> None:
    client = getattr(ws, "client", None)
    await ws.accept()
    subscriber = event_bus.subscribe()
    items = sorted(event_bus.recent(limit=20), key=lambda x: x["id"])
    last_seen_id = 0
    logger.info(
        "mission-control websocket connected client=%s backlog=%s",
        f"{getattr(client, 'host', 'unknown')}:{getattr(client, 'port', 'unknown')}",
        len(items),
    )

    for item in items:
        await ws.send_json(item)
        last_seen_id = max(last_seen_id, item["id"])

    try:
        while True:
            item = await asyncio.to_thread(subscriber.get)
            if item is None or item["id"] <= last_seen_id:
                continue
            await ws.send_json(item)
            last_seen_id = item["id"]
            logger.debug(
                "mission-control websocket forwarded event client=%s event_id=%s family=%s kind=%s",
                f"{getattr(client, 'host', 'unknown')}:{getattr(client, 'port', 'unknown')}",
                item.get("id"),
                item.get("family"),
                item.get("kind"),
            )
    except WebSocketDisconnect:
        logger.info(
            "mission-control websocket disconnected client=%s last_seen_id=%s",
            f"{getattr(client, 'host', 'unknown')}:{getattr(client, 'port', 'unknown')}",
            last_seen_id,
        )
        return
    finally:
        event_bus.unsubscribe(subscriber)
