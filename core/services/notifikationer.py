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
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from core.runtime.db import connect

_log = logging.getLogger(__name__)


def _udsend(slags_haendelse: str, nid: str, user_id: str, slags: str) -> None:
    """Live-vejen til klokken. Fejler den, skal FEEDEN stadig virke — men den
    skal siges hoejt, ikke sluges: en tavs bus er praecis den fejl der har
    ramt dette repo fem gange."""
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(f"notifikation.{slags_haendelse}",
                          {"id": nid, "user_id": user_id, "slags": slags})
    except Exception:
        _log.warning("notifikation.%s kunne ikke udsendes for %s",
                     slags_haendelse, nid, exc_info=True)


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

    Kaploebssikker (2026-09-21): to samtidige kald med samme (slags, ref) saa
    tidligere begge et "findes ikke" foer nogen af dem havde naaet at skrive
    (SELECT foer INSERT, uden faelles transaktion) — det unikke indeks
    `ux_notif_ref` fangede saa kun den ene, og den anden fik en raa
    sqlite3.IntegrityError. Vi lader derfor DATABASEN afgoere det i stedet
    for at spoerge foerst: indsaet, og fang fejlen fra det unikke indeks.
    Det kraever ingen laas paa tvaers af forbindelser og virker uanset hvem
    af de to der vinder kaploebet.
    """
    nid = str(uuid.uuid4())
    with connect() as conn:
        try:
            conn.execute(
                "INSERT INTO notifikationer"
                " (id, user_id, slags, kilde, ref, session_id, titel, tekst, oprettet)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (nid, user_id, slags, kilde, ref, session_id, titel, tekst, _nu()))
        except sqlite3.IntegrityError:
            # GREN "fandtes i forvejen": vores INSERT tabte kaploebet (eller
            # raekken laa der bare i forvejen, klaret eller ej). Dette er
            # IKKE en ny raekke — en senere haendelses-udsendelse for
            # "notifikation oprettet" maa derfor ALDRIG fyre herfra.
            conn.rollback()
            if ref is None:
                # Uden ref rammer intet unikt indeks — skulle ikke kunne
                # ske. Fail loud i stedet for at gaette paa hvad der skete.
                raise
            fundet = conn.execute(
                "SELECT id FROM notifikationer WHERE slags=? AND ref=?",
                (slags, ref)).fetchone()
            if fundet is None:
                raise
            return str(fundet[0])
        else:
            # GREN "ny raekke": vores INSERT vandt (eller var alene om det).
            # Det er HER en senere haendelses-udsendelse skal sidde.
            conn.commit()
    _udsend("ny", nid, user_id, slags)
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
        markoer = conn.execute(
            "UPDATE notifikationer SET klaret=?, udfald=? WHERE id=? AND klaret IS NULL",
            (_nu(), udfald, notif_id))
        conn.commit()
        raekke = None
        if markoer.rowcount:
            # Kun naar VI lukkede raekken skal haendelsen fyre — ellers ville
            # et gentaget kald paa en allerede-klaret raekke faa klokken til
            # at blinke igen for noget gammelt (samme faelde som i opret()).
            raekke = conn.execute(
                "SELECT user_id, slags FROM notifikationer WHERE id=?", (notif_id,)).fetchone()
    if raekke:
        _udsend("klaret", notif_id, str(raekke[0]), str(raekke[1]))


def genaabn(slags: str, ref: str) -> bool:
    """Genaabn en LUKKET raekke for (slags, ref). Returnerer True hvis en
    raekke faktisk blev genaabnet.

    V1 (2026-09-22): `opret()`s dedup paa `ux_notif_ref` daekker ogsaa
    KLAREDE raekker — bevidst, saa en gen-udsendt haendelse ikke kan genaabne
    noget en anden kanal allerede har afgjort. Men intet reviderede en raekke
    der blev lukket FORKERT (fx af hydreringen der racede en async
    DB-skrivning, V2). Kaldes derfor kun fra `afstem_godkendelser`, som
    SPØRGER ejeren direkte foer den genaabner — modsat en gen-udsendt
    haendelse er det sikkert, fordi det ikke er en gaetning.
    """
    with connect() as conn:
        markoer = conn.execute(
            "UPDATE notifikationer SET klaret=NULL, udfald=NULL"
            " WHERE slags=? AND ref=? AND klaret IS NOT NULL",
            (slags, ref))
        conn.commit()
        raekke = None
        if markoer.rowcount:
            raekke = conn.execute(
                "SELECT id, user_id FROM notifikationer WHERE slags=? AND ref=?",
                (slags, ref)).fetchone()
    if raekke:
        _udsend("genaabnet", str(raekke[0]), str(raekke[1]), slags)
    return bool(markoer.rowcount)


def ryd_gamle(dage: int = 7) -> int:
    """Fjern KLAREDE raekker aeldre end `dage`. Returnerer antal fjernede."""
    graense = (datetime.now(UTC) - timedelta(days=dage)).isoformat()
    with connect() as conn:
        markoer = conn.execute(
            "DELETE FROM notifikationer WHERE klaret IS NOT NULL AND klaret < ?",
            (graense,))
        conn.commit()
        return int(markoer.rowcount or 0)
