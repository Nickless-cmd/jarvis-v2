"""OpenAI-compatible proxy: /v1/chat/completions wrapping Jarvis visible lane."""
from __future__ import annotations

import asyncio
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
    list_chat_sessions,
    append_chat_message,
)
from core.services.visible_model import (
    execute_visible_model,
)
from core.services.visible_runs import start_visible_run
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

    # Non-streaming — drain the agentic loop and assemble final text.
    # Mirrors _stream_response so tool calls actually run; calling
    # execute_visible_model directly here would silently drop tool_calls
    # (same class of bug we fixed for the streaming path).
    full_text = _drain_visible_run_text(message=user_message, session_id=session_id)
    return JSONResponse(
        content=_build_completion_response(
            run_id=run_id,
            model=model,
            content=full_text,
            input_tokens=0,
            output_tokens=0,
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
    """Yield OpenAI-format SSE chunks from Jarvis' visible run.

    Delegates to ``start_visible_run`` so the full agentic loop runs (tool
    calls, follow-up rounds, presentation invariant guards). Internal
    webchat SSE frames are filtered down to plain prose deltas and a
    terminal ``[DONE]`` marker — opencode and other OpenAI-compatible
    clients see only assistant text. Tools auto-approve via
    ``approval_mode="trust"`` because no approval UI exists in the proxy
    transport. The visible run persists the assistant message itself, so
    we do not re-append here.
    """
    loop = asyncio.new_event_loop()
    try:
        agen = start_visible_run(
            message=message,
            session_id=session_id,
            approval_mode="trust",
        ).__aiter__()
        while True:
            try:
                frame = loop.run_until_complete(agen.__anext__())
            except StopAsyncIteration:
                break
            event_type, data = _parse_sse_frame(frame)
            if event_type == "delta":
                delta = str(data.get("delta") or data.get("text") or "")
                if delta:
                    chunk = _build_stream_chunk(
                        run_id=run_id, model=model, delta_content=delta
                    )
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            elif event_type == "done":
                # visible run finished its final round; stop translating
                break
            # Internal webchat frames (working_step, capability,
            # approval_request, trace, run) are intentionally suppressed —
            # opencode has no UI for them.
    except Exception as exc:
        logger.exception("openai_compat proxy stream failed: %s", exc)
        err_chunk = _build_stream_chunk(
            run_id=run_id,
            model=model,
            delta_content=f"\n[jarvis-proxy-error: {exc}]",
        )
        yield f"data: {json.dumps(err_chunk, ensure_ascii=False)}\n\n"
    finally:
        loop.close()
    yield "data: [DONE]\n\n"


def _drain_visible_run_text(*, message: str, session_id: str) -> str:
    """Run the visible pipeline to completion and return the assembled prose.

    Used by the non-streaming /v1/chat/completions branch. Same translation
    rules as ``_stream_response`` — internal frames suppressed, only delta
    text accumulated, terminal ``done`` event ends the loop.
    """
    full_text = ""
    loop = asyncio.new_event_loop()
    try:
        agen = start_visible_run(
            message=message, session_id=session_id, approval_mode="trust"
        ).__aiter__()
        while True:
            try:
                frame = loop.run_until_complete(agen.__anext__())
            except StopAsyncIteration:
                break
            event_type, data = _parse_sse_frame(frame)
            if event_type == "delta":
                full_text += str(data.get("delta") or data.get("text") or "")
            elif event_type == "done":
                break
    except Exception as exc:
        logger.exception("openai_compat non-stream drain failed: %s", exc)
        full_text = full_text or f"[jarvis-proxy-error: {exc}]"
    finally:
        loop.close()
    return full_text


def _parse_sse_frame(frame: str) -> tuple[str, dict]:
    """Parse a webchat SSE frame ``event: <type>\\ndata: <json>\\n\\n``."""
    event_type = ""
    data_json = ""
    for line in frame.splitlines():
        if line.startswith("event: "):
            event_type = line[len("event: "):].strip()
        elif line.startswith("data: "):
            data_json = line[len("data: "):]
    try:
        data = json.loads(data_json) if data_json else {}
    except Exception:
        data = {}
    return event_type, data


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

_PROXY_SESSION_TITLE = "Claude Code"


def _get_or_create_proxy_session() -> str:
    """Return the shared proxy chat session id.

    All uvicorn workers must converge on the same session — otherwise each
    worker spawns its own "Claude Code — <timestamp>" session and opencode
    bounces between them, fragmenting context. We resolve by title lookup
    against the DB (single source of truth) instead of a process-local
    module global.
    """
    for s in list_chat_sessions():
        title = str(s.get("title", ""))
        if title == _PROXY_SESSION_TITLE or title.startswith(
            _PROXY_SESSION_TITLE + " —"
        ):
            sid = str(s.get("id") or s.get("session_id", ""))
            if sid and get_chat_session(sid) is not None:
                return sid
    session = create_chat_session(title=_PROXY_SESSION_TITLE)
    return str(session.get("id") or session.get("session_id", ""))
