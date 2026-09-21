# core/services/notifikations_emittere.py
"""Hvor notifikationer foedes (spec 2026-09-21).

Ét sted der baade laegger raekken og — hvis brugerens valg siger det — sender
pushet. Uden det ville hver kilde skulle huske begge dele, og den ene ville
blive glemt.

Feeden er den PAALIDELIGE del; telefonen er den upaalidelige. Et push der
fejler maa aldrig tage raekken med sig.
"""
from __future__ import annotations

import logging

from core.services import notifikationer as _lager
from core.services import notifikations_valg as _valg

_log = logging.getLogger(__name__)


def _owner_id() -> str | None:
    """Ejeren. Systemraekker hoerer til ham — de handler om maskinen."""
    try:
        from core.runtime.db import connect
        with connect() as conn:
            raekke = conn.execute(
                "SELECT user_id FROM users WHERE role='owner' LIMIT 1").fetchone()
        return str(raekke[0]) if raekke else None
    except Exception:
        _log.warning("kunne ikke finde owner til en systemnotifikation", exc_info=True)
        return None


def _maaske_push(user_id: str, slags: str, titel: str, tekst: str) -> None:
    kanal = _valg.kanal_for(user_id, slags)
    if kanal == "ingen":
        return
    try:
        from core.services import notification_router
        notification_router.route_proactive_notification(
            user_id, slags, {"titel": titel, "tekst": tekst},
            importance="high" if slags in ("approval", "question") else "normal")
    except Exception:
        # Raekken staar allerede i feeden. Et brudt push maa ikke tage den med.
        _log.warning("push for %s til %s fejlede", slags, user_id, exc_info=True)


def _foed(*, user_id: str, slags: str, kilde: str, titel: str,
          tekst: str = "", ref: str | None = None,
          session_id: str | None = None) -> None:
    _lager.opret(user_id=user_id, slags=slags, kilde=kilde, titel=titel,
                 tekst=tekst, ref=ref, session_id=session_id)
    _maaske_push(user_id, slags, titel, tekst)


def paa_godkendelse(approval_id: str, *, user_id: str, session_id: str,
                    vaerktoej: str) -> None:
    _foed(user_id=user_id, slags="approval", kilde="approval", ref=approval_id,
          session_id=session_id, titel=f"Vil du tillade {vaerktoej}?")


def paa_koersel_fejlet(run_id: str, *, user_id: str, session_id: str,
                       titel: str) -> None:
    _foed(user_id=user_id, slags="run_failed", kilde="run", ref=run_id,
          session_id=session_id, titel=f"Noget gik galt i «{titel}»")


def paa_koersel_faerdig(run_id: str, *, user_id: str, session_id: str,
                        titel: str) -> None:
    _foed(user_id=user_id, slags="run_done", kilde="run", ref=run_id,
          session_id=session_id, titel=f"Svar klar i «{titel}»")


def fra_jarvis(user_id: str, slags: str, titel: str, tekst: str = "") -> None:
    """Det Jarvis selv sender. Har ingen ejer — raekken ER sandheden."""
    _foed(user_id=user_id, slags=slags, kilde="egen", titel=titel, tekst=tekst)


def system(slags: str, titel: str, tekst: str = "") -> None:
    uid = _owner_id()
    if not uid:
        return
    _foed(user_id=uid, slags=slags, kilde="egen", titel=titel, tekst=tekst)
