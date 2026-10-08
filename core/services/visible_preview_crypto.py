"""Encrypt durable previews for visible member runs."""
from __future__ import annotations

from core.services import chat_crypto


def member_for_run(run) -> str | None:
    member = chat_crypto.medlem_for_raekke(user_id=str(getattr(run, "user_id", "") or ""))
    if member:
        return member
    member = chat_crypto.medlem_for_session(str(getattr(run, "session_id", "") or ""))
    if not member:
        from core.identity.workspace_context import current_role
        if current_role() in {"member", "partner", "guest"}:
            raise RuntimeError("authenticated member key could not be resolved")
    return member


def protect_preview(text: str | None, member: str | None) -> str | None:
    return chat_crypto.krypter(text, member) if text and member else text


def reveal_preview(text: str | None, user_id: str | None) -> str | None:
    if not text or not chat_crypto.er_krypteret(text) or not user_id:
        return text
    member = chat_crypto.medlem_for_raekke(user_id=user_id)
    return chat_crypto.dekrypter(text, member) if member else text
