"""Forgetting nudge — reminds Jarvis to consider transience during conversation.

Fase 2 i learning-to-forget. Modstykke til memory_consolidation_nudge:
den minder om at GEMME, denne minder om at OVERVEJE GLEMSEL.

Injecterer et kort signal i prompten der spørger:
- Er noget af det her forbigående? Markér det med lav importance.
- Er noget af det her vigtigt? Markér det med høj importance.

Polish 2026-05-08 (Claude review):
  - Var: fires every turn unconditionally
  - Nu: kun når samtalen ER substantiel (mindst 3 user-turns) eller
    Jarvis allerede har skrevet til brain i denne session. Korte
    chitchat-svar trigger ikke nudge — der er intet at huske/glemme.
"""
from __future__ import annotations

_NUDGE_TEXT = (
    "💡 Glemsels-nudge: Hvis noget i denne samtale er "
    "forbigående (en midlertidig besked, et hurtigt fix, "
    "snak der ikke skal gemmes), så kald `remember_this` "
    "med `importance=0.3` eller arkivér det bagefter. "
    "Omvendt: Hvis noget er vigtigt — markér med "
    "`importance=0.9`. Din pruning-daemon bruger "
    "importance til at afgøre hvad der overlever."
)

# Tærskel for hvornår nudge er relevant. Under denne grænse er samtalen
# typisk for kort/triviel til at have noget at markere.
_MIN_USER_TURNS_FOR_NUDGE = 3


def _conversation_is_substantial(session_id: str | None) -> bool:
    """Return True if there are enough user-turns OR brain-writes
    in this session to make the nudge relevant.

    Best-effort: if anything fails (no session_id, DB hiccup), default
    to False — better to silently skip than to inject noise.
    """
    if not session_id or not str(session_id).strip():
        return False
    try:
        from core.services.chat_sessions import recent_chat_session_messages
        history = recent_chat_session_messages(session_id, limit=20)
        user_turns = sum(1 for m in history if m.get("role") == "user")
        if user_turns >= _MIN_USER_TURNS_FOR_NUDGE:
            return True
    except Exception:
        return False

    # Alternative trigger: Jarvis already wrote to brain this session.
    # If he's actively memorising, the nudge to think about importance
    # IS relevant even on shorter conversations.
    try:
        from core.runtime.db import connect
        with connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM brain_index "
                "WHERE created_at >= datetime('now', '-30 minutes')"
            ).fetchone()
        if row and int(row["n"]) >= 1:
            return True
    except Exception:
        pass

    return False


def forgetting_nudge_section(session_id: str | None = None) -> str:
    """Return forgetting nudge text when the conversation is substantial.

    Returns empty string when the conversation is too brief or the
    session has no recent brain-writes — _awareness_add tolerates empty
    strings without injecting them.
    """
    if not _conversation_is_substantial(session_id):
        return ""
    return _NUDGE_TEXT
