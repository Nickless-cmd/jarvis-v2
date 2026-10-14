"""Hvilken SAMTALE hører et job til? — én definition, tre ure.

Målt 14/10-2026 (Bjørn: «tingene skal vække den aktive session de er bestilt
i»): recurring-, scheduled- og heartbeat-urene startede alle et run i en
``auto-{origin}-{dato}``-silo, fordi ingen af dem bar den samtale jobbet blev
bestilt i. 367 recurring-runs skrev deres svar i en session ingen læser.

Bindingen kan ikke gættes bagefter: den skal skrives NED da jobbet blev
bestilt. Dette modul er det ene sted der læser den aktive kontekst og afgør
hvad der må bindes — tre kopier ville drive fra hinanden, og den ene ville
stille mangle ``auto-``-reglen nedenfor.
"""
from __future__ import annotations


def er_auto_session(session_id: str) -> bool:
    """Er dette en autonom silo (``auto-*``) og ikke en rigtig samtale?"""
    return str(session_id or "").strip().startswith("auto-")


def bind_session(session_id: str = "") -> str:
    """Den samtale et job blev bestilt i — eller ``''`` hvis ingen.

    Eksplicit ``session_id`` vinder. Ellers læses den aktive kontekst
    (``workspace_context.current_session_id``), som middleware og gateway
    sætter for hver request.

    En ``auto-*``-session bindes ALDRIG. Et autonomt run der opretter et job
    ville ellers binde det til sin egen silo — og vi ville genskabe præcis det
    problem bindingen findes for at fjerne (målt 14/10-2026: 367
    recurring-runs i ``auto-recurring``).

    Kaster aldrig: en fejl i kontekst-opslaget giver ``''`` — jobbet oprettes
    uden binding frem for slet ikke at blive oprettet.
    """
    sid = str(session_id or "").strip()
    if not sid:
        try:
            from core.identity.workspace_context import current_session_id

            sid = str(current_session_id() or "").strip()
        except Exception:
            sid = ""
    if er_auto_session(sid):
        return ""
    return sid
