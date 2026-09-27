"""Vagt: hvilke store tabeller i `jarvis.db` har ingen aftale om oprydning?

## Hvorfor den findes

Oprydningen i `events_retention` virker — `events` holder præcis sine 14 dage,
og de syv tabeller på `_TELEMETRY_RETENTION` holder deres alder. Problemet er
ikke mekanismen, det er at politikken er syv håndskrevne navne der ikke følger
med skemaet.

Målt på CT105 27/9-2026: `cheap_lane_route_decisions` blev oprettet 18.
september og var ni dage senere **2.381 MB — 45 % af hele databasen**. Den kom
aldrig på listen, og intet sagde til. 6.000 rutebeslutninger om dagen à 48 KB,
fordi hver gemte alle 101 kandidat-slots med deres fulde kvote-tilstand.

En liste over hvad der skal ryddes op kan ikke selv opdage hvad der mangler på
den. Derfor vender denne modul spørgsmålet om: den ser på hvad der FAKTISK
fylder i databasen, og kræver at hver stor tabel er placeret i én af to
skuffer — enten har den en politik, eller også er den bevidst gemt for evigt
med en skreven grund. Alt andet rapporteres.

## De to skuffer

* **Har politik** — udledt af `events_retention._TELEMETRY_RETENTION`,
  `_VERSIONED_RETENTION` og `events` selv. Den liste er sandheden; her
  gentages den ikke.
* **Bevidst uden alder** (`_BEVIDST_UDEN_ALDER`) — tabeller der SKAL blive
  liggende. Grunden står i værdien og er ikke valgfri: en tom grund er en
  udeladelse forklædt som en beslutning.

«Har et DELETE et sted i koden» er med vilje IKKE en skuffe. `chat_messages`
slettes af rewind-funktionen, men det er ikke oprydning — det er en bruger der
fortryder. En tabel er kun dækket hvis nogen har besluttet hvor længe den
lever.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

logger = logging.getLogger(__name__)

#: En tabel skal være mindst SÅ stor før den overhovedet er værd at tale om.
#: 25 MB er valgt fordi den mindste tabel der allerede HAR en politik
#: (`daemon_output_log`) lå på 25 MB — grænsen ligger altså lige under det
#: niveau hvor nogen sidst syntes en politik var nødvendig.
_MIN_BYTES = 25_000_000

#: …eller så mange rækker. Begge veje tæller: en smal tabel med en halv million
#: rækker (`central_hypothesis_samples`: 503.619 rækker, 49 MB) er lige så
#: meget en ubesvaret beslutning som en fed en med få.
_MIN_RAEKKER = 100_000

#: Tabeller der bliver liggende for evigt — med grunden. Værdien er ikke
#: pynt: den er hele forskellen på en beslutning og en forglemmelse.
_BEVIDST_UDEN_ALDER: dict[str, str] = {
    "chat_messages":
        "Bjørns samtaler. Slettes kun når han beder om det, aldrig på alder.",
    "private_brain_records":
        "Jarvis' hukommelse. Har sin egen udtynding i memory_pruning_daemon, "
        "som vurderer indhold — ikke alder.",
    "emotional_memory_anchors":
        "Følelsesankre knytter sig til øjeblikke der ikke bliver mindre "
        "betydningsfulde af at være gamle.",
    "memory_embeddings":
        "Afledt af hukommelsen og slettes sammen med den række den hører til "
        "(db_embeddings). En alder her ville gøre gammel hukommelse usøgbar.",
    "chat_messages_fts_data":
        "FTS-skygge af chat_messages — følger sin tabel, har ingen egen alder.",
}


def har_politik() -> dict[str, str]:
    """Tabeller med en alders-politik, og hvor den står. Kilden er én."""
    ud: dict[str, str] = {}
    try:
        from core.services import events_retention as er
    except Exception as exc:                      # pragma: no cover - importfejl
        logger.debug("retention_coverage: kunne ikke læse politikken: %s", exc)
        return ud
    ud["events"] = "events_retention.prune_old_events (%d dage)" % er._retention_days()
    for tabel, _kol, dage in er._TELEMETRY_RETENTION:
        ud[tabel] = "events_retention._TELEMETRY_RETENTION (%d dage)" % dage
    for tabel, _kol, behold in er._VERSIONED_RETENTION:
        ud[tabel] = "events_retention._VERSIONED_RETENTION (%d versioner)" % behold
    ud.setdefault(
        "cheap_lane_redacted_payloads",
        "cheap_lane_payloads.purge_expired_payloads (expires_at)",
    )
    return ud


def _stoerrelser(conn: sqlite3.Connection) -> dict[str, int]:
    """Bytes pr. tabel via dbstat. Tom dict hvis dbstat ikke er bygget ind."""
    try:
        raekker = conn.execute(
            "SELECT name, SUM(pgsize) FROM dbstat GROUP BY name"
        ).fetchall()
    except sqlite3.Error as exc:
        logger.debug("retention_coverage: dbstat utilgængelig: %s", exc)
        return {}
    ud: dict[str, int] = {}
    for raekke in raekker:
        navn = raekke[0]
        ud[str(navn)] = int(raekke[1] or 0)
    return ud


def tabeller_uden_politik(
    *,
    conn: sqlite3.Connection | None = None,
    min_bytes: int = _MIN_BYTES,
    min_raekker: int = _MIN_RAEKKER,
) -> list[dict[str, Any]]:
    """De store tabeller der hverken har en politik eller en skreven grund.

    Størst først. Tom liste betyder at hver stor tabel er placeret — ikke at
    der ikke findes store tabeller.

    Uden dbstat (ikke bygget ind i alle SQLite-udgaver) falder den tilbage til
    kun at måle på rækketal. Den bliver altså mindre følsom, ikke tavs.
    """
    egen = conn is None
    if conn is None:
        from core.runtime.db_core import connect
        conn = connect()

    try:
        dakket = har_politik()
        stoerrelser = _stoerrelser(conn)
        navne = [
            str(r[0]) for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        ]
        fund: list[dict[str, Any]] = []
        for navn in navne:
            if navn in dakket or navn in _BEVIDST_UDEN_ALDER:
                continue
            bytes_ = int(stoerrelser.get(navn, 0))
            try:
                antal = int(conn.execute(
                    'SELECT COUNT(*) FROM "%s"' % navn.replace('"', '""')
                ).fetchone()[0])
            except sqlite3.Error as exc:
                # En COUNT kan fejle på en virtuel tabel hvis modulet bag den
                # ikke er indlæst, og på en tabel der bliver droppet mens vi
                # går listen igennem. Begge dele er «ikke en tabel man aftaler
                # en levetid for» — ikke en fejl der skal stoppe vagten.
                logger.debug("retention_coverage: sprang %s over: %s", navn, exc)
                continue
            if bytes_ < min_bytes and antal < min_raekker:
                continue
            fund.append({"tabel": navn, "bytes": bytes_, "raekker": antal})
        fund.sort(key=lambda f: (-f["bytes"], -f["raekker"]))
        return fund
    finally:
        if egen:
            try:
                conn.close()
            except Exception as exc:              # pragma: no cover
                # Vagten har allerede sit svar; en forbindelse der ikke vil
                # lukke må ikke koste det.
                logger.debug("retention_coverage: kunne ikke lukke: %s", exc)


def rapport(fund: list[dict[str, Any]]) -> str:
    """Én linje til loggen. Tom streng når der intet er at sige."""
    if not fund:
        return ""
    dele = [
        "%s (%.0f MB, %d rækker)" % (f["tabel"], f["bytes"] / 1e6, f["raekker"])
        for f in fund[:6]
    ]
    hale = "" if len(fund) <= 6 else " +%d mere" % (len(fund) - 6)
    return "tabeller uden aftalt oprydning: " + ", ".join(dele) + hale
