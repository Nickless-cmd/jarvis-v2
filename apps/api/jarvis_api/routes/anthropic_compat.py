"""Anthropic Messages API compatible endpoint.

Exposes Jarvis as a model so Claude Desktop / Claude Code can connect
via ANTHROPIC_BASE_URL=http://<host>/anthropic. Routes per-user via
x-api-key. Mode 2: identity-injected, Claude Desktop's tools passed
through to the Ollama backend.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Iterator, Optional
from uuid import uuid4

import requests
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from apps.api.jarvis_api.middleware.anthropic_auth import (
    resolve_api_key,
    short_key_for_log,
)
from core.runtime.provider_router import resolve_provider_router_target
from core.runtime.settings import RuntimeSettings
from core.services.anthropic_identity import build_identity_prefix
from core.services.anthropic_sse_emitter import AnthropicSSEEmitter
from core.services.anthropic_translator import (
    build_non_streaming_response,
    drive_emitter_from_ollama_chunks,
    translate_request_to_ollama,
)

logger = logging.getLogger("uvicorn.error")
router = APIRouter()

_OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
_WORKSPACES_ROOT = Path(os.getenv("JARVIS_WORKSPACES_DIR")
                        or (Path.home() / ".jarvis-v2" / "workspaces"))


def _error_response(*, status: int, type_: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"type": "error", "error": {"type": type_, "message": message}},
    )


def _resolve_workspace_dir(workspace_name: str) -> Path:
    return _WORKSPACES_ROOT / workspace_name


def _resolve_backend_model(requested: Optional[str]) -> str:
    """Pick the Ollama model to use. 'jarvis' or empty → visible-lane default."""
    requested = (requested or "").strip()
    if not requested or requested.lower() == "jarvis":
        target = resolve_provider_router_target(lane="visible")
        return str(target.get("model") or "")
    # Allow explicit override (passthrough — only works if backend has the model)
    return requested


def _ollama_chat_non_stream(payload: dict) -> dict:
    """Call Ollama /api/chat with stream=False; return the single response dict."""
    body = dict(payload)
    body["stream"] = False
    r = requests.post(
        f"{_OLLAMA_BASE_URL}/api/chat",
        json=body,
        timeout=120,
    )
    r.raise_for_status()
    return r.json()


def _ollama_chat_stream(payload: dict) -> Iterator[dict]:
    """Call Ollama /api/chat with stream=True; yield chunks."""
    body = dict(payload)
    body["stream"] = True
    with requests.post(
        f"{_OLLAMA_BASE_URL}/api/chat",
        json=body,
        stream=True,
        timeout=120,
    ) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception as exc:
                logger.warning("anthropic_compat: bad ollama chunk: %s", exc)


def _book_usage(*, backend_model: str, response: dict) -> None:
    """Bogfør Ollamas token-forbrug i ``costs``-ledgeren.

    MÅLT 30/10-2026: denne sti kaldte Ollama og returnerede uden at røre
    ``costs``. Alt der kom ind ad ``/anthropic/v1/messages`` var derfor
    usynligt i hovedbogen — Ollama fakturerede det, men vi kunne hverken se
    hvad det kostede eller hvem der kaldte. Ollamas eget API viste 59.336 kald
    over 30 dage mod vores 161 i døgnet: dsh-harnesset løb igennem netop denne
    dør, og den var den eneste indgang i huset uden regnskab.

    Ollama returnerer ``prompt_eval_count``/``eval_count`` men INGEN cache-split
    (cache er en cloud-side størrelse). ``compute_cost_usd`` lægger derfor alt
    input som ``cache_miss`` — den forsigtige retning: vi overestimerer hellere
    end vi underestimerer.
    """
    try:
        prompt_tokens = int(response.get("prompt_eval_count") or 0)
        output_tokens = int(response.get("eval_count") or 0)
        if prompt_tokens <= 0 and output_tokens <= 0:
            return
        from core.costing.ledger import record_cost

        record_cost(
            lane="anthropic_compat",
            provider="ollama",
            model=backend_model,
            input_tokens=prompt_tokens,
            output_tokens=output_tokens,
        )
    except Exception:
        # En manglende regnskabs-række må ikke vælte svaret til kalderen —
        # men den må heller ikke forsvinde tavst.
        logger.warning(
            "anthropic_compat: kunne ikke bogfoere forbrug (model=%s)",
            backend_model,
            exc_info=True,
        )


def _tap_usage(chunks: Iterator[dict], *, backend_model: str) -> Iterator[dict]:
    """Videresend Ollama-chunks uændret, men bogfør forbruget fra ``done``-chunket.

    Stream-stien er den Claude Desktop faktisk bruger, så uden denne tap ville
    den vej stadig være usynlig selv om non-stream blev rettet.

    MÅLT 30/10-2026: bogføringen lå først EFTER ``for``-løkken. Det virkede i
    en isoleret test, men i drift bryder ``drive_emitter_from_ollama_chunks``
    ud af iterationen når den ser ``done`` — så generatorens hale kørte aldrig,
    og forbruget blev aldrig skrevet. En generator der ikke bliver udtømt,
    kører ikke sin hale. Derfor sker bogføringen nu i det øjeblik chunket
    passerer, før det yieldes videre.
    """
    for chunk in chunks:
        if isinstance(chunk, dict) and chunk.get("done"):
            _book_usage(backend_model=backend_model, response=chunk)
        yield chunk


@router.get("/anthropic/v1/models")
async def list_models() -> JSONResponse:
    return JSONResponse(content={
        "data": [{
            "id": "jarvis",
            "type": "model",
            "display_name": "Jarvis",
            "created_at": "2026-05-06T00:00:00Z",
        }],
        "has_more": False,
        "first_id": "jarvis",
        "last_id": "jarvis",
    })


@router.post("/anthropic/v1/messages", response_model=None)
async def messages(request: Request) -> JSONResponse | StreamingResponse:
    settings = RuntimeSettings()
    if not settings.anthropic_compat_enabled:
        return _error_response(
            status=503, type_="api_error",
            message="Anthropic-compat endpoint is disabled.",
        )

    api_key = request.headers.get("x-api-key", "")
    user_info = resolve_api_key(
        api_key,
        dev_mode_open=settings.anthropic_compat_dev_mode_open,
    )
    if user_info is None:
        logger.info("anthropic_compat: invalid key=%s", short_key_for_log(api_key))
        return _error_response(
            status=401, type_="authentication_error",
            message="Invalid API key. See state/anthropic_api_keys.json.",
        )

    user = user_info.get("user", "")
    workspace = user_info.get("workspace", "default")
    workspace_dir = _resolve_workspace_dir(workspace)
    logger.info(
        "anthropic_compat: request user=%s workspace=%s key=%s",
        user, workspace, short_key_for_log(api_key),
    )

    try:
        body = await request.json()
    except Exception:
        return _error_response(
            status=400, type_="invalid_request_error",
            message="Body must be valid JSON.",
        )

    if not body.get("messages"):
        return _error_response(
            status=400, type_="invalid_request_error",
            message="`messages` is required and cannot be empty.",
        )

    backend_model = _resolve_backend_model(body.get("model"))
    if not backend_model:
        return _error_response(
            status=500, type_="api_error",
            message="No backend model configured.",
        )

    identity_prefix = build_identity_prefix(workspace_dir)
    ollama_payload = translate_request_to_ollama(
        anthropic_body=body,
        identity_prefix=identity_prefix,
        backend_model=backend_model,
    )

    message_id = f"msg_{uuid4().hex[:24]}"
    requested_model_label = (body.get("model") or "jarvis").strip() or "jarvis"

    if bool(body.get("stream", False)):
        return StreamingResponse(
            _stream_response(
                payload=ollama_payload,
                message_id=message_id,
                model=requested_model_label,
                backend_model=backend_model,
            ),
            media_type="text/event-stream",
        )

    # Non-streaming
    try:
        response = _ollama_chat_non_stream(ollama_payload)
    except Exception as exc:
        logger.exception("anthropic_compat: ollama call failed")
        return _error_response(
            status=502, type_="api_error",
            message=f"Backend call failed: {exc}",
        )

    msg = response.get("message") or {}
    text = str(msg.get("content") or "")
    tool_calls = msg.get("tool_calls") or []
    _book_usage(backend_model=backend_model, response=response)
    return JSONResponse(content=build_non_streaming_response(
        message_id=message_id,
        model=requested_model_label,
        text=text,
        tool_calls=tool_calls,
    ))


def _stream_response(
    *, payload: dict, message_id: str, model: str, backend_model: str
) -> Iterator[str]:
    """Drive the AnthropicSSEEmitter from Ollama stream chunks."""
    emitter = AnthropicSSEEmitter(message_id=message_id, model=model)
    try:
        chunks = _tap_usage(
            _ollama_chat_stream(payload), backend_model=backend_model
        )
        yield from drive_emitter_from_ollama_chunks(emitter, chunks)
    except Exception as exc:
        logger.exception("anthropic_compat: stream failed")
        yield from emitter.error(str(exc))
