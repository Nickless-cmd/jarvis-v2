# core/services/notifikations_valg.py
"""Push-valg per slags (spec 2026-09-21).

`notification_preferences` har én kolonne pr. type (briefing, reminder, …) og
kan ikke baere en ny slags uden en ny kolonne hver gang. Valgene bor nu i
raekker. Kolonnerne bliver staaende indtil alle kaldesteder laeser den nye
tabel, og `notification_router` laeser raekker MED kolonnerne som fald-tilbage,
saa en halvvejs migreret base ikke taber nogens valg.
"""
from __future__ import annotations

import logging

from core.runtime.db import connect

_log = logging.getLogger(__name__)

GYLDIGE_KANALER = {"auto", "mobile", "desktop", "push", "ingen"}

#: Standard naar brugeren ikke har valgt. Kun det der HASTER pusher.
#: «auto» lader notification_router vaelge kanal efter enhed og stilletimer.
STANDARD: dict[str, str] = {
    "approval": "auto",
    "question": "auto",
    "run_failed": "auto",
    "run_done": "ingen",
    "briefing": "ingen",
    "reminder": "ingen",
    "reach_out": "ingen",
    "initiative": "ingen",
    "release": "ingen",
    "incident": "ingen",
    "quota": "ingen",
}

#: Kolonnenavn i notification_preferences -> slags i den nye tabel.
_GAMLE_KOLONNER = {
    "briefing": "briefing",
    "reminder": "reminder",
    "reach_out": "reach_out",
    "team_invite": "initiative",
    "wakeup": "initiative",
}


def kanal_for(user_id: str, slags: str) -> str:
    with connect() as conn:
        raekke = conn.execute(
            "SELECT kanal FROM notifikations_valg WHERE user_id=? AND slags=?",
            (user_id, slags)).fetchone()
    if raekke:
        return str(raekke[0])
    # STANDARD er feedens politik, ikke systemets. route_proactive_notification()
    # kaldes ogsaa med slags der aldrig hoerer til feeden (fx membrane_breach,
    # infra_security, keymaker_key_earned, moltbook_mention, central_flag) —
    # de staar ikke i STANDARD fordi de ikke er feedens bord, IKKE fordi de er
    # fravalgt. Fald-tilbage for dem skal vaere "auto", saa notification_router
    # falder igennem til sin egen resolve_channel() (gammel opfoersel), ikke
    # "ingen" som stopper leveringen i routerens tidlige udgang.
    return STANDARD.get(slags, "auto")


def saet(user_id: str, slags: str, kanal: str) -> None:
    if kanal not in GYLDIGE_KANALER:
        raise ValueError(f"ukendt kanal: {kanal}")
    with connect() as conn:
        conn.execute(
            "INSERT INTO notifikations_valg (user_id, slags, kanal) VALUES (?,?,?)"
            " ON CONFLICT(user_id, slags) DO UPDATE SET kanal=excluded.kanal",
            (user_id, slags, kanal))
        conn.commit()


def alle(user_id: str) -> dict[str, str]:
    """Alle slags med brugerens valg lagt oven paa standarden."""
    ud = dict(STANDARD)
    with connect() as conn:
        for slags, kanal in conn.execute(
                "SELECT slags, kanal FROM notifikations_valg WHERE user_id=?",
                (user_id,)).fetchall():
            ud[str(slags)] = str(kanal)
    return ud


def migrer_kolonner() -> int:
    """Baer de gamle kolonner over som raekker. Idempotent.

    `INSERT OR IGNORE`: har brugeren allerede valgt noget nyere for den slags,
    roeres det ikke. Ellers ville en genstart rulle et valg tilbage.
    """
    flyttet = 0
    with connect() as conn:
        try:
            raekker = conn.execute(
                "SELECT user_id, " + ", ".join(_GAMLE_KOLONNER) +
                " FROM notification_preferences").fetchall()
        except Exception:
            _log.warning("notification_preferences kunne ikke laeses; "
                         "ingen valg migreret", exc_info=True)
            return 0
        for raekke in raekker:
            user_id = str(raekke[0])
            for i, slags in enumerate(_GAMLE_KOLONNER.values(), start=1):
                vaerdi = raekke[i]
                if not vaerdi:
                    continue
                markoer = conn.execute(
                    "INSERT OR IGNORE INTO notifikations_valg (user_id, slags, kanal)"
                    " VALUES (?,?,?)", (user_id, slags, str(vaerdi)))
                flyttet += int(markoer.rowcount or 0)
        conn.commit()
    return flyttet
