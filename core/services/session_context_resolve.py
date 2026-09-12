"""Hvilken samtale kører vi i? — ét sted, frem for én kopi pr. værktøj.

Der er TO ContextVars der kan bære svaret, fordi der er to veje ind:
`visible_run_context` sættes af den synlige run-løkke, og `chat_sessions`'
egen sættes af chat-maskineriet. Ingen af dem er sat i alle tilfælde, og
rækkefølgen betyder noget — den synlige løkke er tættere på det brugeren
kigger på.

Resolveren har eksisteret siden staged_edits blev bygget, men lå som en
privat funktion i ét værktøjsmodul. Næste værktøj der havde brug for den
ville have skrevet sin egen, og så ville de to kunne blive uenige om
rækkefølgen uden at nogen opdagede det.
"""
from __future__ import annotations


def aktiv_session_id(standard: str = "") -> str:
    """Sessionens id, eller `standard` hvis ingen kilde kender den.

    Self-safe hele vejen: en manglende ContextVar må aldrig kunne vælte det
    værktøj der spurgte.
    """
    try:
        from core.services.visible_run_context import current_session_id
        sid = (current_session_id() or "").strip()
        if sid:
            return sid
    except Exception:
        pass
    try:
        from core.services.chat_sessions import current_session_id_ctx
        sid = (current_session_id_ctx() or "").strip()
        if sid:
            return sid
    except Exception:
        pass
    try:
        from core.identity.workspace_context import current_session_id as _wc
        sid = (_wc() or "").strip()
        if sid:
            return sid
    except Exception:
        pass
    return standard
