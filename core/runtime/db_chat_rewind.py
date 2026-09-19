"""Spol en samtale tilbage — og fortryd det, indtil næste besked.

Claude Desktops kontrakt (cc-desktop-chatview.md §8), ordret: «Brings back the
messages this rewind removed. Your files stay as they are. Undo works until
you send your next message.» Tre ting i én sætning, og alle tre gælder her:

1. **Beskederne kommer tilbage.** De SLETTES ikke — de flyttes til
   `chat_messages_rewound` med et rewind-id. Fortryd flytter dem tilbage med
   SAMME id: `chat_messages.id` er AUTOINCREMENT, så et id genbruges aldrig, og
   `message_id` er unik. FTS-triggerne på chat_messages holder søgeindekset i
   takt i begge retninger.
2. **Filerne røres ikke.** Intet her kigger på disk. Heller ikke hukommelse
   eller journal: hvad Jarvis allerede har gemt fra de beskeder, bliver stående.
3. **Fortryd lukker ved næste besked.** Er der kommet en ny besked i samtalen
   siden tilbagespolingen, afvises fortryd — de to tidslinjer kan ikke flettes.
   Arkivet bliver liggende; intet skæres væk (Bjørns regel).

Fordi beskederne FLYTTES og ikke markeres, ser alt der læser chat_messages —
prompt-bygning, komprimering, søgning, eksport — dem automatisk ikke længere.
En markering ville kræve et filter i hver eneste læser, og ét glemt sted ville
lade en «fjernet» besked lække tilbage i prompten.

Punktet er en BRUGER-besked: den og alt efter den fjernes, og dens tekst gives
tilbage, så klienten kan lægge den i skrivefeltet («Cancel and edit message»).
En kørsel der er i gang, kan ikke spoles tilbage under sig.
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from core.runtime.db import connect

logger = logging.getLogger(__name__)

__all__ = ["spol_tilbage", "fortryd", "RewindFejl"]

ARKIV = "chat_messages_rewound"


class RewindFejl(Exception):
    """En tilbagespoling eller fortrydelse der ikke kan lade sig gøre — med en
    forklaring til brugeren og en HTTP-agtig kode (404/409)."""

    def __init__(self, besked: str, kode: int = 409) -> None:
        super().__init__(besked)
        self.kode = kode


def _kolonner(conn, tabel: str) -> list[str]:
    return [str(r[1]) for r in conn.execute(f"PRAGMA table_info({tabel})").fetchall()]


def _sikr_arkiv(conn) -> list[str]:
    """Arkivet har chat_messages' kolonner plus rewind_id/rewound_at.

    chat_messages får kolonner dovent (git_sha, content_json …), så arkivet
    følger med ved hvert kald i stedet for at blive frosset ved oprettelsen.
    Returnerer chat_messages' kolonner — dem der flyttes.
    """
    kilde = _kolonner(conn, "chat_messages")
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS {ARKIV} ("
        "rewind_id TEXT NOT NULL, rewound_at TEXT NOT NULL, id INTEGER NOT NULL, "
        "session_id TEXT NOT NULL)"
    )
    har = set(_kolonner(conn, ARKIV))
    for k in kilde:
        if k not in har:
            conn.execute(f"ALTER TABLE {ARKIV} ADD COLUMN {k}")
    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{ARKIV}_rewind ON {ARKIV}(rewind_id, id)")
    return kilde


def _koerer(session_id: str) -> bool:
    """Kører der et svar i samtalen lige nu? Samme kilder som /chat/active-runs."""
    try:
        from core.runtime.settings import load_settings
        if load_settings().server_authoritative_runs:
            import core.services.run_event_log as rel
            return any(rel.session_for_run(r) == session_id for r in rel.live_run_ids())
    except Exception:
        logger.debug("chat_rewind: run_event_log kunne ikke spørges", exc_info=True)
    try:
        from core.services.run_follow import session_is_live
        return bool(session_is_live(session_id))
    except Exception:
        return False


def spol_tilbage(session_id: str, message_id: str) -> dict[str, Any]:
    """Fjern `message_id` (en bruger-besked) og alt efter den fra samtalen.

    Returnerer {rewind_id, fjernet, tekst}: `tekst` er den fjernede beskeds
    indhold, til skrivefeltet.
    """
    sid = str(session_id or "").strip()
    mid = str(message_id or "").strip()
    if not sid or not mid:
        raise RewindFejl("session_id og message_id skal gives", 400)
    if _koerer(sid):
        raise RewindFejl("Jarvis svarer stadig — stop svaret før du spoler tilbage")
    with connect() as conn:
        raekke = conn.execute(
            "SELECT id, role, content FROM chat_messages WHERE session_id = ? AND message_id = ?",
            (sid, mid),
        ).fetchone()
        if not raekke:
            raise RewindFejl("Beskeden findes ikke i samtalen", 404)
        fra_id, rolle, tekst = int(raekke[0]), str(raekke[1]), str(raekke[2] or "")
        if rolle != "user":
            raise RewindFejl("Der kan kun spoles tilbage til en af dine egne beskeder", 400)
        kolonner = _sikr_arkiv(conn)
        rid = f"rw-{uuid.uuid4().hex[:12]}"
        nu = datetime.now(UTC).isoformat()
        liste = ", ".join(kolonner)
        conn.execute(
            f"INSERT INTO {ARKIV} (rewind_id, rewound_at, {liste}) "
            f"SELECT ?, ?, {liste} FROM chat_messages WHERE session_id = ? AND id >= ?",
            (rid, nu, sid, fra_id),
        )
        fjernet = conn.execute(
            "DELETE FROM chat_messages WHERE session_id = ? AND id >= ?", (sid, fra_id),
        ).rowcount
    logger.info("chat_rewind: %s spolet tilbage fra %s — %d beskeder arkiveret som %s",
                sid, mid, fjernet, rid)
    return {"status": "ok", "rewind_id": rid, "fjernet": int(fjernet), "tekst": tekst}


def fortryd(session_id: str, rewind_id: str) -> dict[str, Any]:
    """Læg beskederne fra en tilbagespoling tilbage — hvis der ikke er skrevet siden."""
    sid = str(session_id or "").strip()
    rid = str(rewind_id or "").strip()
    with connect() as conn:
        kolonner = _sikr_arkiv(conn)
        foerste = conn.execute(
            f"SELECT MIN(id) FROM {ARKIV} WHERE rewind_id = ? AND session_id = ?", (rid, sid),
        ).fetchone()
        if not foerste or foerste[0] is None:
            raise RewindFejl("Tilbagespolingen findes ikke (eller er allerede fortrudt)", 404)
        nyere = conn.execute(
            "SELECT COUNT(*) FROM chat_messages WHERE session_id = ? AND id > ?",
            (sid, int(foerste[0])),
        ).fetchone()[0]
        if nyere:
            raise RewindFejl("Der er skrevet i samtalen siden — fortryd lukkede ved næste besked")
        liste = ", ".join(kolonner)
        conn.execute(
            f"INSERT INTO chat_messages ({liste}) SELECT {liste} FROM {ARKIV} "
            f"WHERE rewind_id = ? AND session_id = ? ORDER BY id",
            (rid, sid),
        )
        genskabt = conn.execute(
            f"DELETE FROM {ARKIV} WHERE rewind_id = ? AND session_id = ?", (rid, sid),
        ).rowcount
    logger.info("chat_rewind: %s fortrudt — %d beskeder tilbage i %s", rid, genskabt, sid)
    return {"status": "ok", "genskabt": int(genskabt)}
