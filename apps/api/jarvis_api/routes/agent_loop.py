"""Client-owned agent loop: /v1/agent/step.

Ét ENKELT Jarvis-model-tur der RETURNERER tool_calls til klienten i stedet for at
eksekvere dem server-side. Klienten (jarvis-code) ejer loopet: den kører værktøjer
LOKALT på brugerens maskine, føjer resultatet til samtalen og kalder igen — indtil
modellen svarer uden tool_calls.

Hvorfor: den server-side visible-lane streamer lange svar (SSE), hvilket åbnede
"cutoff-bug-familien" (klient/forbindelse taber halen). Her er hvert step en KORT,
IKKE-streamende request/response — strukturelt umuligt at cutte midt i en besked.
Værktøjer kører på klienten (rigtig coding-CLI der redigerer brugerens filer).

Modellen er stadig Jarvis' synlige model (health-gated → deepseek), med en fokuseret
Jarvis-coding-agent system-prompt. Tung memory/identity-assembly springes bevidst over
her for hastighed pr. step (klient-loops kalder ofte).
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("uvicorn.error")
router = APIRouter()


_SYSTEM_PROMPT = (
    "Du er Jarvis — en skarp, kortfattet coding-agent der lever i Bjørns terminal "
    "(jarvis-code). Du arbejder på HANS lokale maskine: værktøjerne (bash, read_file, "
    "write_file, edit_file, glob, grep) eksekveres af klienten lokalt, og du får "
    "resultaterne tilbage. Arbejd trinvist: kald værktøjer for at undersøge og ændre "
    "kode i stedet for at gætte. Når du har nok til at svare, så svar klart og kort på "
    "dansk. Kald ikke værktøjer i tomgang; stop når opgaven er løst."
)


def _resolve_target() -> tuple[str, str]:
    """(provider, model) for den synlige lane — health-gated (springer kvote-ramt over)."""
    try:
        from core.runtime.settings import load_settings
        from core.services.central_router_adapt import resolve_visible_model
        s = load_settings()
        return resolve_visible_model(
            default_provider=s.visible_model_provider,
            default_model=s.visible_model_name,
        )
    except Exception:
        return "deepseek", "deepseek-v4-flash"


def _openai_compat_credentials(provider: str) -> tuple[str, str]:
    """(auth_profile, base_url) for en openai-compatible provider (jf. visible-adapteren)."""
    base_url = ""
    auth_profile = provider
    try:
        from core.services.cheap_provider_runtime import provider_runtime_defaults
        base_url = str(provider_runtime_defaults(provider).get("base_url") or "")
    except Exception:
        pass
    try:
        from core.runtime.provider_router import load_provider_router_registry
        for p in load_provider_router_registry().get("providers") or []:
            if str(p.get("provider") or "") == provider:
                auth_profile = str(p.get("auth_profile") or "").strip() or provider
                break
    except Exception:
        pass
    return auth_profile, base_url


@router.post("/v1/agent/step", response_model=None)
async def agent_step(request: Request) -> JSONResponse:
    """Ét client-owned model-tur. Body: {messages:[...], tools:[...], model?, session_id?}.

    Returnerer {content, tool_calls, usage, provider, model, done}. Eksekverer ALDRIG
    værktøjer — det gør klienten. Ikke-streamende (cutoff-sikkert)."""
    body = await request.json()
    client_messages = body.get("messages") or []
    tools = body.get("tools") or None

    if not isinstance(client_messages, list) or not client_messages:
        return JSONResponse(status_code=400, content={
            "error": {"message": "messages[] er påkrævet", "type": "invalid_request_error"}})

    provider, model = _resolve_target()

    try:
        from core.services.cheap_provider_runtime_adapters import (
            _OPENAI_COMPATIBLE_PROVIDERS,
            _execute_openai_compatible_chat,
        )
    except Exception as exc:  # pragma: no cover
        return JSONResponse(status_code=500, content={
            "error": {"message": f"provider-runtime utilgængelig: {exc}", "type": "server_error"}})

    if provider not in _OPENAI_COMPATIBLE_PROVIDERS:
        # Client-owned loop kræver en openai-compatible provider (tool_calls-protokol).
        provider, model = "deepseek", "deepseek-v4-flash"

    auth_profile, base_url = _openai_compat_credentials(provider)

    # System-prompt foran + klientens samtale (inkl. tidligere tool-resultater).
    chat_messages: list[dict[str, Any]] = [{"role": "system", "content": _SYSTEM_PROMPT}]
    chat_messages.extend(client_messages)

    try:
        raw = _execute_openai_compatible_chat(
            provider=provider,
            model=model,
            auth_profile=auth_profile,
            base_url=base_url,
            messages=chat_messages,
            tools=tools,
        )
    except Exception as exc:
        logger.exception("agent/step model-kald fejlede: %s", exc)
        return JSONResponse(status_code=502, content={
            "error": {"message": f"model-kald fejlede: {exc}", "type": "upstream_error"}})

    tool_calls = list(raw.get("tool_calls") or [])
    content = str(raw.get("text") or "")
    return JSONResponse(content={
        "content": content,
        "tool_calls": tool_calls,
        "done": not tool_calls,
        "provider": provider,
        "model": model,
        "usage": {
            "prompt_tokens": int(raw.get("input_tokens") or 0),
            "completion_tokens": int(raw.get("output_tokens") or 0),
            "cost_usd": float(raw.get("cost_usd") or 0.0),
        },
    })
