from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from apps.api.jarvis_api.services.visible_runs import cancel_visible_run, start_visible_run

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatStreamRequest(BaseModel):
    message: str = ""


@router.post("/stream")
async def chat_stream(request: ChatStreamRequest) -> StreamingResponse:
    return StreamingResponse(
        start_visible_run(message=request.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/runs/{run_id}/cancel")
async def chat_cancel_run(run_id: str) -> dict:
    if not cancel_visible_run(run_id):
        raise HTTPException(status_code=404, detail="Visible run not active")
    return {
        "ok": True,
        "run_id": run_id,
        "status": "cancelled",
    }
