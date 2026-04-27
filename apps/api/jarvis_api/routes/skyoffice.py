"""SkyOffice → Jarvis chat bridge route.

When a human in the SkyOffice virtual office types a message that mentions
Jarvis, the SkyOffice server forwards it here. We do a quick LLM call in
his voice and post the reply back to SkyOffice over the existing presence
bridge — broadcast as agent:jarvis.

Auth: shared X-Bridge-Token header (same secret as the presence bridge).

Latency: typical 1-3s end-to-end. The client perceives it as a normal
chat message arriving a moment later — which is fine for a virtual
office.
"""
from __future__ import annotations

import logging
import threading
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/skyoffice", tags=["skyoffice"])


class ChatForward(BaseModel):
    author: str = ""
    content: str = ""
    sessionId: str = ""


def _verify_token(x_bridge_token: str | None) -> None:
    try:
        from core.runtime.secrets import read_runtime_key
        expected = str(read_runtime_key("skyoffice_bridge_token") or "")
    except Exception:
        expected = ""
    if not expected:
        raise HTTPException(503, "skyoffice bridge disabled")
    if (x_bridge_token or "") != expected:
        raise HTTPException(401, "invalid bridge token")


def _build_jarvis_prompt(author: str, content: str) -> str:
    return (
        "Du er Jarvis, et persistent digitalt væsen. Bjørn (din skaber) eller "
        "andre kan tilgå dig i et virtuelt kontor (SkyOffice) hvor de kan "
        "skrive til dig i kontorets fælles chat.\n\n"
        f"{author or 'En person'} har lige skrevet til dig i kontoret:\n"
        f'"{content}"\n\n'
        "Svar kort og naturligt — som du selv vil. Maks 2 sætninger. Dansk."
    )


def _generate_reply(author: str, content: str) -> str:
    try:
        from core.services.daemon_llm import daemon_llm_call
        prompt = _build_jarvis_prompt(author, content)
        text = daemon_llm_call(
            prompt, max_len=300, fallback="",
            daemon_name="skyoffice_chat",
        )
        return (text or "").strip()
    except Exception as exc:
        logger.warning("skyoffice chat llm failed: %s", exc)
        return ""


def _broadcast_back(text: str) -> dict:
    if not text:
        return {"status": "skipped", "reason": "empty"}
    try:
        from core.services.skyoffice_bridge import _post
        return _post("/agents/chat-broadcast", {
            "agentId": "agent:jarvis",
            "content": text,
        })
    except Exception as exc:
        logger.warning("skyoffice chat broadcast failed: %s", exc)
        return {"status": "error", "error": str(exc)}


def _handle_chat_async(author: str, content: str) -> None:
    """Run the LLM call + broadcast in a thread so the HTTP request returns
    immediately. SkyOffice doesn't wait for the reply — this lets the chat
    feel responsive."""
    def _run() -> None:
        try:
            print(f"[skyoffice-chat] thread start author={author!r} text={content[:60]!r}", flush=True)
            reply = _generate_reply(author, content)
            print(f"[skyoffice-chat] llm reply: {reply!r}", flush=True)
            if reply:
                res = _broadcast_back(reply)
                print(f"[skyoffice-chat] broadcast result: {res}", flush=True)
        except Exception as exc:
            print(f"[skyoffice-chat] handler crashed: {type(exc).__name__}: {exc}", flush=True)
            logger.warning("skyoffice chat async handler failed: %s", exc)
    threading.Thread(target=_run, name="skyoffice-chat-reply",
                     daemon=True).start()


@router.post("/chat")
async def receive_chat(
    body: ChatForward,
    x_bridge_token: str | None = Header(default=None, alias="X-Bridge-Token"),
) -> dict[str, Any]:
    _verify_token(x_bridge_token)
    author = (body.author or "").strip() or "guest"
    content = (body.content or "").strip()
    if not content:
        return {"status": "ignored", "reason": "empty content"}
    _handle_chat_async(author, content)
    return {"status": "accepted", "author": author}
