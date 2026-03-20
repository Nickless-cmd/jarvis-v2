from __future__ import annotations

import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.eventbus.bus import event_bus

router = APIRouter()


@router.websocket("/ws")
async def websocket_stream(ws: WebSocket) -> None:
    await ws.accept()
    subscriber = event_bus.subscribe()
    items = sorted(event_bus.recent(limit=20), key=lambda x: x["id"])
    last_seen_id = 0

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
    except WebSocketDisconnect:
        return
    finally:
        event_bus.unsubscribe(subscriber)
