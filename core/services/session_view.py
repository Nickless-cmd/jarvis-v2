"""Samtalens visningstilstand — Claude Desktops tre (cc-desktop-chatview.md §1).

    normal   — værktøjsrunder foldet, tænkning som én linje
    thinking — «a one-line recap of Claude's thinking above each tool group»
    verbose  — alt åbent: hvert kald for sig

Tilstanden bor på SERVEREN, pr. samtale, fordi den er en del af samtalens
kontrakt og ikke kun et tegne-valg: i «thinking» laver kørslen et
tænke-resumé pr. værktøjsgruppe (`core.services.tanke_resume`), og det koster
et modelkald. Claude Desktop sender den med ved start
(`thinkingSummariesWanted`); her slår kørslen den op pr. runde, så et skift
midt i et svar gælder fra næste runde.

Lagret som kolonnen `transcript_view` på `chat_sessions` — samme dovne
migration som `pinned`/`archived`. En ukendt værdi falder tilbage til
`normal` (deres `Dt()`-validering) frem for at fejle.
"""
from __future__ import annotations

import logging
from typing import Final

from core.runtime.db import connect

logger = logging.getLogger(__name__)

__all__ = ["GYLDIGE", "STANDARD", "hent_visning", "saet_visning", "vil_have_tanke_resume"]

GYLDIGE: Final[frozenset[str]] = frozenset({"normal", "thinking", "verbose"})
STANDARD: Final[str] = "normal"


def _sikr_kolonne(conn) -> None:
    try:
        conn.execute("ALTER TABLE chat_sessions ADD COLUMN transcript_view TEXT NOT NULL DEFAULT 'normal'")
    except Exception:
        pass  # findes allerede


def hent_visning(session_id: str) -> str:
    """Samtalens tilstand; `normal` for en ukendt samtale eller værdi."""
    sid = str(session_id or "").strip()
    if not sid:
        return STANDARD
    try:
        with connect() as conn:
            _sikr_kolonne(conn)
            r = conn.execute(
                "SELECT transcript_view FROM chat_sessions WHERE session_id = ?", (sid,),
            ).fetchone()
    except Exception:
        logger.debug("session_view: kunne ikke læse %s", sid, exc_info=True)
        return STANDARD
    v = str(r[0]) if r and r[0] else STANDARD
    return v if v in GYLDIGE else STANDARD


def saet_visning(session_id: str, visning: str) -> dict[str, object]:
    sid = str(session_id or "").strip()
    v = str(visning or "").strip()
    if not sid:
        return {"status": "error", "error": "session_id mangler"}
    if v not in GYLDIGE:
        return {"status": "error", "error": f"ukendt visning: {v!r} (normal, thinking, verbose)"}
    with connect() as conn:
        _sikr_kolonne(conn)
        cur = conn.execute(
            "UPDATE chat_sessions SET transcript_view = ? WHERE session_id = ?", (v, sid),
        )
        if cur.rowcount != 1:
            return {"status": "error", "error": f"ukendt samtale: {sid}"}
    return {"status": "ok", "id": sid, "view": v}


def vil_have_tanke_resume(session_id: str | None) -> bool:
    """Skal kørslen lave tænke-resuméer for denne samtale? Kaster aldrig."""
    try:
        return hent_visning(str(session_id or "")) == "thinking"
    except Exception:
        return False
