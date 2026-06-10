"""POST /chat/stream/v2 — Anthropic-style SSE protokol.

Wrapper omkring eksisterende start_visible_run() der oversætter den
gamle protokol til Anthropic-style v2-protokol via translate_to_v2().

Spec: docs/superpowers/specs/2026-06-10-chat-stream-v2-design.md
Translator: core/services/visible_runs_sse_v2.py
Event-dataclasses: apps/api/jarvis_api/sse_v2_events.py

Bemærk: /chat/stream (legacy) eksisterer uændret. v2 er additiv for at
understøtte den nye jarvis-desk app der bygges sideløbende.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from apps.api.jarvis_api.routes.chat import ChatStreamRequest
from core.runtime.settings import load_settings
from core.services.chat_sessions import append_chat_message, get_chat_session
from core.services.visible_runs import start_visible_run
from core.services.visible_runs_sse_v2 import translate_to_v2

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/stream/v2")
async def chat_stream_v2(request: ChatStreamRequest) -> StreamingResponse:
    """Anthropic-style streaming alternative til /chat/stream.

    Konsumerer samme request-format, men producerer Anthropic-protokol:
    message_start → content_block_start(text) → content_block_delta(text_delta)*
    → content_block_stop → message_delta → message_stop, med ping
    hver 5 sek og system_event-wrappede Jarvis-specifikke events.
    """
    session_id = request.session_id.strip()
    if not session_id:
        raise HTTPException(
            status_code=400, detail="session_id must be a non-empty string"
        )
    if get_chat_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    if not (request.message or "").strip():
        raise HTTPException(
            status_code=400,
            detail="message must not be empty or whitespace-only",
        )

    print(
        f"[chat/stream/v2] session={session_id[:20]} "
        f"message_len={len(request.message)}",
        flush=True,
    )

    from core.identity.workspace_context import current_user_id
    _uid = current_user_id() or None
    append_chat_message(
        session_id=session_id,
        role="user",
        content=request.message,
        user_id=_uid,
    )

    # Load model/provider/lane settings så vi kan inkludere dem i
    # message_start metadata (klienten skal bruge dem til at display'e
    # "kører på X-model" + til debugging).
    settings = load_settings()

    legacy_iter = start_visible_run(
        message=request.message,
        session_id=session_id,
        approval_mode=request.approval_mode,
        thinking_mode=request.thinking_mode,
        force_user_id=_uid,
    )

    v2_stream = translate_to_v2(
        legacy_iter,
        run_id="",  # plukkes fra første legacy event
        model=settings.visible_model_name,
        provider=settings.visible_model_provider,
        lane=settings.primary_model_lane,
        session_id=session_id,
        ping_interval_s=5.0,
    )

    return StreamingResponse(
        v2_stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Stream-Protocol": "v2-anthropic",
        },
    )
