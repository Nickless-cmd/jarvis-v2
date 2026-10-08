"""Protect private message payloads at the durable ledger boundary."""
from __future__ import annotations

import json
from typing import Any

from core.services import chat_crypto

_TEXT_FIELDS = ("content", "reasoning_content", "content_json")


def protect_event(session_id: str, event: dict[str, Any], *, conn=None) -> dict[str, Any]:
    if event.get("kind") != "message":
        return event
    payload = event.get("payload") or {}
    member = chat_crypto.medlem_for_raekke(
        user_id=str(payload.get("user_id") or ""),
        workspace_name=str(payload.get("workspace_name") or ""),
    ) or chat_crypto.medlem_for_session(session_id, conn=conn)
    if not member:
        return event
    protected = dict(payload)
    for field in _TEXT_FIELDS:
        value = protected.get(field)
        if value:
            source = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
            protected[field] = chat_crypto.krypter(source, member)
    return {**event, "payload": protected}


def reveal_event(session_id: str, event: dict[str, Any], *, conn=None) -> dict[str, Any]:
    if event.get("kind") != "message":
        return event
    payload = event.get("payload") or {}
    if not any(chat_crypto.er_krypteret(payload.get(field)) for field in _TEXT_FIELDS):
        return event
    member = chat_crypto.medlem_for_raekke(
        user_id=str(payload.get("user_id") or ""),
        workspace_name=str(payload.get("workspace_name") or ""),
    ) or chat_crypto.medlem_for_session(session_id, conn=conn)
    if not member:
        return event
    revealed = dict(payload)
    for field in _TEXT_FIELDS:
        value = revealed.get(field)
        if chat_crypto.er_krypteret(value):
            plain = chat_crypto.dekrypter(value, member)
            if field == "content_json":
                try:
                    plain = json.loads(plain)
                except (TypeError, ValueError):  # Legacy content_json may be plain text.
                    pass
            revealed[field] = plain
    return {**event, "payload": revealed}
