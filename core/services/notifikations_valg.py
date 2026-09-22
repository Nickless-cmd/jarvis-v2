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
#:
#: K4 (2026-09-22): `briefing`, `reminder`, `reach_out` og `initiative` STOD
#: her foer med "ingen" — men de fire navne er IKKE kun feedens. `reach_out`
#: er allerede `notification_type` for proactivity_bridge.py,
#: autonomous_outreach_daemon.py, action_router.py og central_moltbook.py
#: (via broen), som intet har med denne feed at goere. `kanal_for()` kaldes
#: FOR ALLE proaktive kilder (se route_proactive_notification), saa en
#: "ingen" her slukkede tavst for et eksisterende, ufeed-relateret system —
#: efterproevet: REACH_OUT/BRIEFING gav begge {'delivered': False, 'channel':
#: 'fravalgt'}.
#:
#: `reach_out` er siden (opgave "routeren-foeder", 2026-09-22) flyttet TILBAGE
#: i STANDARD — se begrundelsen ved selve STANDARD nedenfor: routeren foder nu
#: altid en feed-raekke uanset kanal_for()s svar, saa "ingen" ikke laengere
#: kan betyde total tavshed. `briefing`, `reminder` og `initiative` staar
#: STADIG udenfor: der findes ingen afsender for dem NOGEN steder i repoet
#: (grep for "briefing"|"reminder"|"initiative" som notification_type giver
#: kun urelaterede traef) — de er navne fra den gamle
#: notification_preferences-tabel, ikke rigtige haendelser. En STANDARD-vaerdi
#: for en slags der aldrig fødes ville vaere ren fiktion.
#:
#: `wakeup` er IKKE et af de fire — den er (i modsaetning til `reach_out`)
#: ikke `notification_type` for noget andet, eksisterende system; grep over
#: `route_proactive_notification`-kaldene finder ingen anden kilde end denne
#: feed der bruger "wakeup". Den kan derfor sikkert have en standard her.
#: Valgt "ingen": en planlagt opfoelgning er en TING JARVIS SELV satte for
#: at huske noget — den blokerer ikke en koersel og venter ikke paa svar
#: (modsat `approval`/`question`), saa den behoever ikke afbryde telefonen.
#: Den staar stadig i feeden; brugeren kan altid skrue op i indstillingerne.
#:
#: Opgave "routeren-foeder" (2026-09-22): `notification_router.
#: route_proactive_notification()` laegger nu SELV en feed-raekke for enhver
#: slags den leverer — ogsaa naar `kanal_for()` her siger "ingen" (raekken
#: skrives i routerens ydre wrapper, EFTER selve leverings-forsoeget, uanset
#: dets udfald). K4s aegte problem var ALDRIG at "ingen" betoed "ingen push"
#: — det var at "ingen" dengang betoed "INGENTING SKER", fordi routeren ikke
#: havde nogen anden vej for reach_out/briefing. Den vej findes nu (feeden),
#: saa "ingen" er igen kun en push-praeference, praecis som for run_done/
#: release/incident/quota ovenfor — og `reach_out` kan derfor sikkert have en
#: standard igen. De fem oevrige (central_flag, membrane_breach,
#: infra_security, keymaker_key_earned, moltbook_mention) har ALDRIG vaeret i
#: K4s undtagelse — de faldt bare til "auto" som enhver anden ukendt slags.
#: De faar nu en bevidst standard i stedet for den implicitte.
STANDARD: dict[str, str] = {
    "approval": "auto",
    "question": "auto",
    "run_failed": "auto",
    "run_done": "ingen",
    "release": "ingen",
    "incident": "ingen",
    "quota": "ingen",
    "wakeup": "ingen",
    "reach_out": "auto",             # Jarvis tager selv initiativ — som en besked fra et menneske
    "central_flag": "ingen",         # Centralens egen overvaagning — informativt, sjaeldent akut
    "membrane_breach": "auto",       # altid importance=critical: brud paa den beskyttede kerne
    "infra_security": "auto",        # altid importance=high: vaert/net i fare
    "keymaker_key_earned": "ingen",  # "en mulighed, ikke et brud" (central_keymaker.py)
    "moltbook_mention": "ingen",     # social omtale, ikke tidskritisk
}

#: Kolonnenavn i notification_preferences -> slags i den nye tabel.
#:
#: V8 (2026-09-22): `team_invite` og `wakeup` mappede FOER begge til
#: `initiative`. `migrer_kolonner()`s `INSERT OR IGNORE` rammer det unikke
#: indeks paa (user_id, slags), saa kun den FOERSTE af de to blev skrevet —
#: efterproevet: `wakeup='push'` forsvandt naar `team_invite` ogsaa havde et
#: valg. Specen (docs/superpowers/specs/2026-09-21-notifikations-feed-
#: design.md) lover udtrykkeligt at alle fem kolonner baeres over uden tab.
#: `wakeup` faar derfor sin egen slags i stedet for at dele `team_invite`s.
_GAMLE_KOLONNER = {
    "briefing": "briefing",
    "reminder": "reminder",
    "reach_out": "reach_out",
    "team_invite": "initiative",
    "wakeup": "wakeup",
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

    V8 (2026-09-22): de gamle kolonner valideredes ikke mod `GYLDIGE_KANALER`
    — de kan lovligt indeholde `discord`/`telegram`
    (`notification_router.VALID_CHANNELS`), som feedens egen kanal-vaelger
    ikke kender. En ukendt vaerdi klemmes derfor ned til "auto" i stedet for
    at blive skrevet uaendret over i den nye tabel.
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
                vaerdi = str(raekke[i] or "")
                if not vaerdi:
                    continue
                if vaerdi not in GYLDIGE_KANALER:
                    _log.warning(
                        "migrering: ukendt kanal %r for %s (bruger %s) — "
                        "klemt til 'auto'", vaerdi, slags, user_id)
                    vaerdi = "auto"
                markoer = conn.execute(
                    "INSERT OR IGNORE INTO notifikations_valg (user_id, slags, kanal)"
                    " VALUES (?,?,?)", (user_id, slags, vaerdi))
                flyttet += int(markoer.rowcount or 0)
        conn.commit()
    return flyttet
