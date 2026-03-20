from __future__ import annotations

import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.eventbus.bus import event_bus

router = APIRouter()


@router.websocket("/ws")
async def websocket_stream(ws: WebSocket) -> None:
    await ws.accept()
    last_seen_id = 0
    try:
        while True:
            items = event_bus.recent(limit=20)
            items_sorted = sorted(items, key=lambda x: x["id"])
            fresh = [item for item in items_sorted if item["id"] > last_seen_id]
            for item in fresh:
                await ws.send_json(item)
                last_seen_id = max(last_seen_id, item["id"])
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        return
