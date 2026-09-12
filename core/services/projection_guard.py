"""Vagten der gør et skifte til hovedbogen fortrydeligt.

En udskiftning består af TO dele, ikke én: projektionen der folder hændelser
til kompatibilitets-rækker, og vagten der nægter det direkte skrivested når
sessionen er i `ledger`. Uden vagten flytter et skifte ikke sandheden — det
FORDOBLER den: nogle rækker foldet fra hovedbogen, andre skrevet udenom, og
ingen måde at se hvilke der er hvilke.

Vagten lå indtil 12/9-2026 i `projection_chat_messages` og blev kaldt fra
`chat_sessions`. Da `projection_drift` blev gjort genbrugelig til flere
projektioner, fulgte vagten ikke med — så `projection_tool_router` kunne
foldes, men dens direkte skrivested i `tool_router.py` var uvogtet. Flippede
man en session dér, ville projektionen skrive rækker med udledt `decision_id`
og skrivestedet rækker med `decision_id = NULL`; det fulde unikke indeks
tillader netop NULL, så resultatet var to rækker pr. beslutning — og routerens
egne statistikker (`COUNT`, `AVG(tokens_saved_estimate)`, `AVG(elapsed_ms)`)
ville dobbelttælle fra første skifte.

Derfor bor den her nu, hvor den kan nås af alle projektioner.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class DirekteSkrivningAfvist(RuntimeError):
    """En ledger-session fik et direkte skrive-forsøg uden om projektoren."""


def guard_direct_write(session_id: str, *, projektion: str, tabel: str, conn=None) -> None:
    """Afvis direkte skrivninger til `tabel` for en ledger-session.

    Tilstanden læses fra databasen hver gang, ikke fra en cache i processen:
    et skifte sker i den ene proces og skal ses i den anden med det samme.

    **Fail-open, og det er et valg.** Kan tilstanden ikke læses, tillades
    skrivningen — en utilgængelig tilstands-kolonne må ikke gøre en samtale
    skrivebeskyttet. Til gengæld logges det, så en vagt der er holdt op med at
    virke ikke gør det i tavshed.

    `conn` SKAL gives når kalderen allerede har en forbindelse åben:
    forbindelserne er poolede, så et nyt `with connect()` ville være den samme
    forbindelse og committe kalderens transaktion for tidligt.
    """
    try:
        from core.runtime.db_session_ledger import storage_mode
        mode = storage_mode(session_id, conn=conn)
    except Exception:
        logger.warning("%s: kunne ikke laese storage_mode", projektion, exc_info=True)
        return
    if mode == "ledger":
        raise DirekteSkrivningAfvist(
            f"session {session_id!r} er i ledger-tilstand: {tabel}-rækker skrives "
            "af projektoren, ikke direkte. Skriv hændelsen til hovedbogen i stedet."
        )
