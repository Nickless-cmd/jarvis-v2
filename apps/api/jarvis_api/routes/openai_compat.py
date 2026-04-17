"""OpenAI-compatible proxy: /v1/chat/completions wrapping Jarvis visible lane."""
from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime
from typing import Iterator
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from core.services.chat_sessions import (
    create_chat_session,
    get_chat_session,
    append_chat_message,
)
from core.services.visible_model import (
    stream_visible_model,
    execute_visible_model,
    VisibleModelDelta,
    VisibleModelStreamDone,
    VisibleModelToolCalls,
)
from core.eventbus.bus import event_bus
from core.runtime.provider_router import resolve_provider_router_target

logger = logging.getLogger("uvicorn.error")
router = APIRouter()


@router.get("/v1/models")
async def list_models() -> JSONResponse:
    """OpenAI-compatible model list — exposes Jarvis as a single model."""
    return JSONResponse(content={
        "object": "list",
        "data": [
            {
                "id": "jarvis",
                "object": "model",
                "created": 1700000000,
                "owned_by": "jarvis",
            }
        ],
    })


@router.post("/v1/chat/completions", response_model=None)
async def chat_completions(request: Request) -> JSONResponse | StreamingResponse:
    """OpenAI-compatible chat completion endpoint wrapping Jarvis' visible lane."""
    body = await request.json()
    model_param = str(body.get("model", "")).strip()
    messages = body.get("messages", [])
    stream = bool(body.get("stream", False))

    # Extract user message (last user role message)
    user_message = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_message = str(msg.get("content", ""))
            break

    if not user_message:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "message": "No user message found in messages array",
                    "type": "invalid_request_error",
                }
            },
        )

    # Resolve provider and model
    provider, model = _resolve_model_provider(model_param)

    # Session handling
    session_id = request.headers.get("X-Jarvis-Session", "").strip()
    if not session_id:
        session_id = _get_or_create_proxy_session()

    # Persist user message
    append_chat_message(session_id=session_id, role="user", content=user_message)

    event_bus.publish(
        "channel.proxy_request_received",
        {
            "provider": provider,
            "model": model,
            "stream": stream,
            "session_id": session_id,
        },
    )

    run_id = f"jarvis-proxy-{uuid4().hex[:12]}"

    if stream:
        return StreamingResponse(
            _stream_response(
                run_id=run_id,
                message=user_message,
                provider=provider,
                model=model,
                session_id=session_id,
            ),
            media_type="text/event-stream",
        )

    # Non-streaming
    result = execute_visible_model(
        message=user_message,
        provider=provider,
        model=model,
        session_id=session_id,
    )
    append_chat_message(session_id=session_id, role="assistant", content=result.text)
    return JSONResponse(
        content=_build_completion_response(
            run_id=run_id,
            model=model,
            content=result.text,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )
    )


def _stream_response(
    *,
    run_id: str,
    message: str,
    provider: str,
    model: str,
    session_id: str,
) -> Iterator[str]:
    """Yield OpenAI-format SSE chunks from Jarvis' visible model stream."""
    full_text = ""
    for event in stream_visible_model(
        message=message,
        provider=provider,
        model=model,
        session_id=session_id,
    ):
        if isinstance(event, VisibleModelDelta):
            full_text += event.delta
            chunk = _build_stream_chunk(
                run_id=run_id,
                model=model,
                delta_content=event.delta,
            )
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        elif isinstance(event, VisibleModelStreamDone):
            if full_text.strip():
                append_chat_message(
                    session_id=session_id, role="assistant", content=full_text
                )
            yield "data: [DONE]\n\n"
            return

    # Fallback if stream ends without done event
    if full_text.strip():
        append_chat_message(
            session_id=session_id, role="assistant", content=full_text
        )
    yield "data: [DONE]\n\n"


# ---------------------------------------------------------------------------
# Model routing
# ---------------------------------------------------------------------------


def _resolve_model_provider(model_param: str) -> tuple[str, str]:
    """Map a model parameter to (provider, model) tuple.

    Rules:
    - "jarvis" or empty -> visible lane default
    - Contains ":cloud" or known Ollama tag -> ollama
    - Starts with "gpt-" or "o1-" or "o3-" -> openai
    - Starts with "copilot/" -> github-copilot (strip prefix)
    - Otherwise -> visible lane default provider with given model
    """
    model = model_param.strip()

    if not model or model == "jarvis":
        target = resolve_provider_router_target(lane="visible")
        return str(target.get("provider", "")), str(target.get("model", ""))

    if model.startswith("copilot/"):
        return "github-copilot", model.removeprefix("copilot/")

    if model.startswith(("gpt-", "o1-", "o3-")):
        return "openai", model

    if ":" in model:
        return "ollama", model

    # Unknown model — use default provider
    target = resolve_provider_router_target(lane="visible")
    return str(target.get("provider", "")), model


# ---------------------------------------------------------------------------
# Response formatting
# ---------------------------------------------------------------------------


def _build_completion_response(
    *,
    run_id: str,
    model: str,
    content: str,
    input_tokens: int,
    output_tokens: int,
) -> dict:
    """Build a standard OpenAI chat.completion response."""
    return {
        "id": run_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        },
    }


def _build_stream_chunk(
    *,
    run_id: str,
    model: str,
    delta_content: str,
) -> dict:
    """Build a standard OpenAI chat.completion.chunk for streaming."""
    return {
        "id": run_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {"content": delta_content},
                "finish_reason": None,
            }
        ],
    }


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

_PROXY_SESSION_ID: str | None = None


def _get_or_create_proxy_session() -> str:
    """Return or create a persistent proxy chat session."""
    global _PROXY_SESSION_ID
    if _PROXY_SESSION_ID:
        session = get_chat_session(_PROXY_SESSION_ID)
        if session is not None:
            return _PROXY_SESSION_ID

    title = f"Claude Code — {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')}"
    session = create_chat_session(title=title)
    _PROXY_SESSION_ID = str(session.get("id") or session.get("session_id", ""))
    return _PROXY_SESSION_ID
