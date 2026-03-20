from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatStreamRequest(BaseModel):
    message: str = ""


@router.post("/stream")
async def chat_stream(request: ChatStreamRequest) -> StreamingResponse:
    return StreamingResponse(
        _event_stream(message=request.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


async def _event_stream(message: str) -> AsyncIterator[str]:
    safe_message = (message or "").strip() or "Tom synlig forespoergsel"
    chunks = [
        {
            "type": "status",
            "message": "visible-chat-stream-open",
        },
        {
            "type": "delta",
            "message": "Jarvis visible lane er klar. ",
        },
        {
            "type": "delta",
            "message": f"Streamingfundament modtog: {safe_message}. ",
        },
        {
            "type": "delta",
            "message": "Modelkoersel og reel svarlogik kobles paa i senere faser.",
        },
        {
            "type": "done",
        },
    ]

    for item in chunks:
        yield _sse("message", item)
        await asyncio.sleep(0.05)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
