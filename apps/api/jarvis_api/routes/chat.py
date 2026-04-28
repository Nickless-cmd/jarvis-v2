from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.services.chat_sessions import (
    append_chat_message,
    create_chat_session,
    delete_chat_session,
    get_chat_session,
    list_chat_sessions,
    rename_chat_session,
)
from core.services.visible_runs import (
    cancel_visible_run,
    resolve_pending_approval,
    start_visible_run,
)

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatStreamRequest(BaseModel):
    message: str = ""
    session_id: str = ""
    attachment_ids: list[str] = []
    approval_mode: str = "ask"  # "ask" | "trust"
    # Thinking mode for reasoning-capable models (deepseek-v4-flash et al.).
    # "fast" = no thinking (intuitive answer)
    # "think" = default thinking (balanced)
    # "deep" = max reasoning effort (slowest, hardest problems)
    # Ignored for models that don't support thinking parameters.
    thinking_mode: str = "think"


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
    print(
        f"[chat/stream] session={session_id[:20]} "
        f"attachment_ids={list(request.attachment_ids or [])} "
        f"message_len={len(request.message)}",
        flush=True,
    )

    # Build attachment context block and prepend to message.
    # Be explicit about HOW to look at the file — without a directive, the
    # model reads "[Attached files: ...]" as flavour text and claims it cannot
    # see images, even though the path is right there and analyze_image is
    # available.
    effective_message = request.message
    if request.attachment_ids:
        from apps.api.jarvis_api.routes.attachments import get_attachment

        # Use pre-formatted blocks where the path is the prominent line and
        # the model is directed to copy it verbatim. Earlier formats put the
        # path in a parenthetical, which the model truncated at the first space
        # in the filename — producing image_path='Skærmbillede fra ...' with
        # no leading directory.
        image_lines: list[str] = []
        other_lines: list[str] = []
        for aid in request.attachment_ids:
            meta = get_attachment(aid)
            if not meta:
                continue
            if meta.mime_type.startswith("image/"):
                image_lines.append(
                    f"To see the image '{meta.filename}', call:\n"
                    f"  analyze_image(image_path={meta.server_path!r})\n"
                    f"Use that exact absolute path verbatim — do not abbreviate it."
                )
            else:
                other_lines.append(
                    f"To read the file '{meta.filename}', call:\n"
                    f"  read_file(path={meta.server_path!r})"
                )

        prefix_parts: list[str] = []
        if image_lines:
            prefix_parts.append(
                "[The user attached image(s) to this message. You CAN see "
                "images by using the analyze_image tool. Do NOT claim you "
                "cannot see images — the tool exists and works.]\n\n"
                + "\n\n".join(image_lines)
            )
        if other_lines:
            prefix_parts.append(
                "[The user attached file(s):]\n\n" + "\n\n".join(other_lines)
            )
        if prefix_parts:
            effective_message = "\n\n".join(prefix_parts) + "\n\n---\n\n" + request.message

    append_chat_message(session_id=session_id, role="user", content=effective_message)
    from core.services.notification_bridge import pin_session
    pin_session(session_id)
    return StreamingResponse(
        start_visible_run(
            message=effective_message,
            session_id=session_id,
            approval_mode=request.approval_mode,
            thinking_mode=request.thinking_mode,
        ),
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


@router.post("/runs/{run_id}/steer")
async def chat_steer_run(run_id: str, body: dict) -> dict:
    """Mid-flight steer: inject a user message into a running visible-run.
    The agentic loop picks it up at the next round boundary."""
    from core.services.visible_runs import append_visible_run_steer
    content = str((body or {}).get("content") or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="content required")
    ok = append_visible_run_steer(run_id, content)
    if not ok:
        raise HTTPException(status_code=404, detail="Visible run not active")
    return {"ok": True, "run_id": run_id, "queued": True}
