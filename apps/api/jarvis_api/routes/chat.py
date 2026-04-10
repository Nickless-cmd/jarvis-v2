from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from apps.api.jarvis_api.services.chat_sessions import (
    append_chat_message,
    create_chat_session,
    delete_chat_session,
    get_chat_session,
    list_chat_sessions,
    rename_chat_session,
)
from apps.api.jarvis_api.services.visible_runs import (
    cancel_visible_run,
    resolve_pending_approval,
    start_visible_run,
)

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatStreamRequest(BaseModel):
    message: str = ""
    session_id: str = ""


class ChatSessionCreateRequest(BaseModel):
    title: str = "New chat"


class ChatSessionRenameRequest(BaseModel):
    title: str


@router.get("/sessions")
async def chat_sessions() -> dict:
    return {"items": list_chat_sessions()}


@router.post("/sessions")
async def chat_create_session(request: ChatSessionCreateRequest) -> dict:
    return {"session": create_chat_session(title=request.title)}


@router.get("/sessions/{session_id}")
async def chat_session(session_id: str) -> dict:
    session = get_chat_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"session": session}


@router.put("/sessions/{session_id}/rename")
async def chat_rename_session(session_id: str, request: ChatSessionRenameRequest) -> dict:
    session = rename_chat_session(session_id, title=request.title)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"session": session}


@router.delete("/sessions/{session_id}")
async def chat_delete_session(session_id: str) -> dict:
    if not delete_chat_session(session_id):
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"ok": True, "session_id": session_id}


@router.post("/stream")
async def chat_stream(request: ChatStreamRequest) -> StreamingResponse:
    session_id = request.session_id.strip()
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id must be a non-empty string")
    if get_chat_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    append_chat_message(session_id=session_id, role="user", content=request.message)
    from apps.api.jarvis_api.services.notification_bridge import pin_session
    pin_session(session_id)
    return StreamingResponse(
        start_visible_run(message=request.message, session_id=session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/approvals/{approval_id}/approve")
async def chat_approve_tool(approval_id: str) -> dict:
    result = resolve_pending_approval(approval_id, approved=True)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("error", "Not found"))
    return result


@router.post("/approvals/{approval_id}/deny")
async def chat_deny_tool(approval_id: str) -> dict:
    result = resolve_pending_approval(approval_id, approved=False)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("error", "Not found"))
    return result


@router.post("/runs/{run_id}/cancel")
async def chat_cancel_run(run_id: str) -> dict:
    if not cancel_visible_run(run_id):
        raise HTTPException(status_code=404, detail="Visible run not active")
    return {
        "ok": True,
        "run_id": run_id,
        "status": "cancelled",
    }
