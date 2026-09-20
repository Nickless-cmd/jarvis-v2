"""Samtalens tilladelses-niveau — én sandhed, på serveren (Bjørn 20/9-2026).

    ask   — Jarvis spørger før et værktøj muterer noget (godkendelses-kort)
    trust — fuld adgang: værktøjerne kører uden at spørge

## Hvorfor den bor her

Desk havde sit valg i `localStorage` (`composerPrefs.PERM_KEY`) og telefonen
sit eget i SecureStore, pr. samtale. Ingen af dem delte med den anden, og
serveren havde intet sted at slå op. Resultatet — målt 20/9-2026:

  * Desk stod på «fuld adgang», telefonen på «spørg først».
  * Turen blev startet fra den ene klient, så runnet fik DENS mode.
  * Den anden klients ikon viste stadig sit eget gamle valg.
  * Og runnet ventede i virkeligheden på et kort som den anden klient
    hverken ventede eller så — indtil kortet udløb.

`start_or_attach_user_run` kaster `approval_mode` væk i attach-grenen, og
`trust_all` låses ved run-start (`visible_runs.py`). Så to klienter med hvert
sit valg kunne ikke forhandle — de kunne kun være uenige, i det stille.

Kilden flyttes derfor ét skridt op: klienterne SKRIVER deres valg til
samtalen, og begge LÆSER derfra. Så findes der kun én sandhed at vise.

## Hvorfor den ikke ligger i `get_chat_session`

Den funktion er udfaset (`scripts/verify_history_reads.py`): den henter hele
historikken for at levere ét metadata-felt. Denne fil læser ÉN kolonne, i
samme stil som `session_view.py`, og koster ikke en besked-gennemløb.

Kolonnen lægges på `chat_sessions` med samme dovne migration som
`pinned`/`archived`/`transcript_view`. En ukendt værdi falder tilbage til
`ask` — den sikre vej — frem for at fejle åbent.
"""
from __future__ import annotations

import logging
from typing import Final

from core.runtime.db import connect

logger = logging.getLogger(__name__)

__all__ = ["GYLDIGE", "STANDARD", "hent_permission", "saet_permission"]

GYLDIGE: Final[frozenset[str]] = frozenset({"ask", "trust"})
#: `ask` er standarden overalt: her, i `visible_runs` og i mobilens
#: `spoergFoerst`. En tvivl skal koste et spørgsmål, ikke en mutation.
STANDARD: Final[str] = "ask"


def _sikr_kolonne(conn) -> None:
    try:
        conn.execute(
            "ALTER TABLE chat_sessions ADD COLUMN approval_mode TEXT NOT NULL DEFAULT 'ask'"
        )
    except Exception:
        pass  # findes allerede


def hent_permission(session_id: str) -> str:
    """Samtalens niveau; `ask` for en ukendt samtale eller værdi."""
    sid = str(session_id or "").strip()
    if not sid:
        return STANDARD
    try:
        with connect() as conn:
            _sikr_kolonne(conn)
            r = conn.execute(
                "SELECT approval_mode FROM chat_sessions WHERE session_id = ?", (sid,),
            ).fetchone()
    except Exception:
        logger.debug("session_permission: kunne ikke læse %s", sid, exc_info=True)
        return STANDARD
    v = str(r[0]) if r and r[0] else STANDARD
    return v if v in GYLDIGE else STANDARD


def saet_permission(session_id: str, mode: str) -> dict[str, object]:
    sid = str(session_id or "").strip()
    m = str(mode or "").strip().lower()
    if not sid:
        return {"status": "error", "error": "session_id mangler"}
    if m not in GYLDIGE:
        return {"status": "error", "error": f"ukendt niveau: {m!r} (ask, trust)"}
    with connect() as conn:
        _sikr_kolonne(conn)
        cur = conn.execute(
            "UPDATE chat_sessions SET approval_mode = ? WHERE session_id = ?", (m, sid),
        )
        if cur.rowcount != 1:
            return {"status": "error", "error": f"ukendt samtale: {sid}"}
    return {"status": "ok", "id": sid, "approval_mode": m}
