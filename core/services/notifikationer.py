# core/services/notifikationer.py
"""Notifikations-feedens lager (spec docs/superpowers/specs/2026-09-21-...).

Raekken PEGER paa sin ejer gennem `kilde` + `ref`; den kopierer ham ikke.
Hydreringen (notifikationer_hydrering.py) slaar op hos ejeren ved laesning, og
det er DEN der lukker en raekke hvis ejeren er faerdig. Dette modul kender kun
tabellen.

Feeden er en to-do-liste: `klaret` sat = vaek fra fladen. Raekken slettes ikke
med det samme, for uden den ville en gen-udsendt haendelse kunne genaabne noget
der lige er klaret. `ryd_gamle()` fjerner dem efter en uge.
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from core.runtime.db import connect

_log = logging.getLogger(__name__)

#: Systemraekker hoerer til ejeren — de handler om maskinen, ikke om en samtale.
SYSTEM_SLAGS = {"release", "incident", "quota"}


def _nu() -> str:
    return datetime.now(UTC).isoformat()


def opret(*, user_id: str, slags: str, kilde: str, titel: str,
          tekst: str = "", ref: str | None = None,
          session_id: str | None = None) -> str:
    """Laeg en notifikation. Returnerer id.

    Findes samme (slags, ref) i forvejen — ogsaa en KLARET — returneres den
    eksisterende raekkes id uden at skrive. Det er hele grunden til at klarede
    raekker bliver liggende.
    """
    with connect() as conn:
        if ref is not None:
            fundet = conn.execute(
                "SELECT id FROM notifikationer WHERE slags=? AND ref=?",
                (slags, ref)).fetchone()
            if fundet:
                return str(fundet[0])
        nid = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO notifikationer"
            " (id, user_id, slags, kilde, ref, session_id, titel, tekst, oprettet)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (nid, user_id, slags, kilde, ref, session_id, titel, tekst, _nu()))
        conn.commit()
        return nid


def aabne(user_id: str, *, er_owner: bool) -> list[dict[str, Any]]:
    """Aabne raekker for denne bruger. RAA — se hydreringen for den rigtige feed.

    Owner ser sine egne raekker. Systemraekker faar `user_id` = owner ved
    oprettelse, saa de er allerede med. Owner ser IKKE andre brugeres
    personlige raekker: deres indhold er krypteret og ikke ment til ejeren.
    `er_owner` er derfor ikke et filter i dag, men staar i signaturen fordi
    kaldestedet SKAL tage stilling, og fordi en fremtidig systemraekke uden
    ejer ville skulle bruge den.
    """
    del er_owner  # se docstring
    with connect() as conn:
        raekker = conn.execute(
            "SELECT id, user_id, slags, kilde, ref, session_id, titel, tekst,"
            " oprettet, klaret, udfald"
            " FROM notifikationer WHERE user_id=? AND klaret IS NULL"
            " ORDER BY oprettet DESC",
            (user_id,)).fetchall()
    kolonner = ("id", "user_id", "slags", "kilde", "ref", "session_id",
                "titel", "tekst", "oprettet", "klaret", "udfald")
    return [dict(zip(kolonner, r)) for r in raekker]


def luk(notif_id: str, udfald: str) -> None:
    """Klaret — vaek fra fladen. Raekken bliver liggende til `ryd_gamle`."""
    with connect() as conn:
        conn.execute(
            "UPDATE notifikationer SET klaret=?, udfald=? WHERE id=? AND klaret IS NULL",
            (_nu(), udfald, notif_id))
        conn.commit()


def ryd_gamle(dage: int = 7) -> int:
    """Fjern KLAREDE raekker aeldre end `dage`. Returnerer antal fjernede."""
    graense = (datetime.now(UTC) - timedelta(days=dage)).isoformat()
    with connect() as conn:
        markoer = conn.execute(
            "DELETE FROM notifikationer WHERE klaret IS NOT NULL AND klaret < ?",
            (graense,))
        conn.commit()
        return int(markoer.rowcount or 0)
