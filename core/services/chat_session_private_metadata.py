"""Encrypt message-derived session metadata for registered non-owner users."""
from __future__ import annotations

from core.services import chat_crypto
from core.runtime.db import connect


def encrypt_session_text(
    text: str, session_id: str, *, user_id: str = "", workspace_name: str = "",
) -> str:
    if not text or chat_crypto.er_krypteret(text) or not chat_crypto.kryptering_slaaet_til():
        return text
    member = chat_crypto.medlem_for_raekke(
        user_id=user_id, workspace_name=workspace_name,
    ) or chat_crypto.medlem_for_session(session_id)
    if not member:
        from core.identity.workspace_context import current_role
        if current_role() in {"member", "partner", "guest"}:
            raise RuntimeError("authenticated member key could not be resolved")
    return chat_crypto.krypter(text, member) if member else text


def decrypt_session_text(text: str, session_id: str) -> str:
    if not chat_crypto.er_krypteret(text):
        return text
    member = chat_crypto.medlem_for_session(session_id)
    if not member:
        from core.identity.workspace_context import current_user_id
        uid = current_user_id() or ""
        member = chat_crypto.medlem_for_raekke(user_id=uid)
    return chat_crypto.dekrypter(text, member) if member else text


def search_member_sessions(query: str, user_id: str, limit: int) -> list[dict[str, object]]:
    """Search ciphertext-backed member sessions after an indexed user scope."""
    from core.services.chat_sessions import _make_snippet

    with connect() as conn:
        sessions = conn.execute(
            "SELECT s.session_id, s.title, s.updated_at FROM chat_sessions s "
            "WHERE EXISTS (SELECT 1 FROM chat_messages m WHERE m.session_id=s.session_id "
            "AND m.user_id=?) ORDER BY s.updated_at DESC LIMIT 500",
            (user_id,),
        ).fetchall()
        found = []
        for session in sessions:
            sid = str(session[0])
            member = chat_crypto.medlem_for_session(sid, conn=conn)
            def readable(value: str) -> str:
                return chat_crypto.dekrypter(value, member) if member and chat_crypto.er_krypteret(value) else value
            title = readable(str(session[1]))
            snippet = title if query.casefold() in title.casefold() else ""
            if not snippet:
                rows = conn.execute(
                    "SELECT content FROM chat_messages WHERE session_id=? "
                    "AND role IN ('user','assistant') ORDER BY id DESC LIMIT 10000",
                    (sid,),
                )
                for row in rows:
                    content = readable(str(row[0]))
                    if query.casefold() in content.casefold():
                        snippet = content
                        break
            if snippet:
                found.append({"session_id": sid, "title": title,
                              "snippet": _make_snippet(snippet, query),
                              "updated_at": session[2]})
                if len(found) >= limit:
                    break
    return found
