"""Kadence-beslutningsjournal — hvorfor en producer IKKE kørte.

Målt 4/11-2026: cadence-tikkets resultater levede kun i ``_last_tick_results``,
en liste der overskrives ved hvert tick. En producer der aldrig blev kørt
efterlod præcis ét spor: et manglende claim — fordi ``note_producer_ran`` kun
skrives i succesgrenen. Spørgsmålet «hvorfor kørte min selvmodel ikke i går?»
kunne derfor ikke besvares med data, kun med simulation, og simulationen brugte
hverken ``visible_grace`` eller den faktiske ``last_visible_at``.

Asymmetrien er den arkitektoniske pointe: en kørsel efterlader et varigt spor,
et FRAVALG efterlader ingen. En beslutning om ikke at handle er også en
beslutning, og den skal kunne efterprøves.

FORM — hvorfor ikke én række pr. producer pr. tick
--------------------------------------------------
121 producers × et tick hvert minut ville være ~174.000 rækker i døgnet, altså
endnu en historiktabel der vokser uden loft. Journalen gemmer derfor ÉN ÅBEN
post pr. producer og komprimerer gentagelser til en tæller:

  * samme (status, årsags-kode) som sidst → ``occurrences += 1`` og
    ``last_seen_at`` flyttes. Ingen ny række.
  * tilstandsskift → den åbne post LUKKES (``closed_at``) og en ny åbnes.
    Overgangen er det interessante, og den bevares som sin egen række.

Væksten er derfor antallet af tilstandsovergange, ikke antallet af ticks.

``reason`` fra ``_evaluate_producer`` er dynamisk formateret
(``cooldown:2m<2m`` ændrer sig hvert tick). Komprimering på den fulde streng
ville derfor aldrig ramme, så journalen udleder en stabil ``reason_code``
(``cooldown``, ``visible-grace``, ``dispatch-budget`` …) og beholder den
formaterede streng som ``reason_detail`` — øjebliksbilledet, ikke nøglen.

Selv-sikker: en journal må aldrig vælte cadencen der kalder den. Alle
skrive-/læse-fejl sluges og rapporteres som 0/[].
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any, Iterable

from core.runtime.db_core import connect

logger = logging.getLogger(__name__)

#: Lukkede poster ældre end dette slettes. Overgange er interessante i uger,
#: ikke i måneder — og en ulukket post slettes ALDRIG af retentionen, for så
#: ville «hvorfor kørte den ikke» blive ubesvarligt netop for de producers der
#: stadig ikke kører.
CLOSED_RETENTION_DAYS = 30

#: Hårdt rækkeloft som bagstopper oven på alders-retentionen. Samme beslutning
#: som ``api_request_log``: alders-retention kan ikke bounde en tabel hvis
#: tilstandene flapper hurtigere end de ældes.
MAX_ROWS = 50_000

_OPEN = ""

#: Stabile årsags-koder. ``reason`` er formateret med tal der ændrer sig hvert
#: tick, så nøglen skal være kategorien — ikke øjebliksbilledet.
#:
#: Kun ``blocked`` har brug for at blive splittet: «forælderen findes ikke» og
#: «forælderen er for gammel» er to forskellige diagnoser med samme status.
#: De øvrige statusser har præcis én reason-form, så de falder til
#: ``_STATUS_CODES``. Stod ``cooldown`` eller ``visible-too-recent`` her, ville
#: samme tilstand få to navne i journalen (``visible-grace`` fra status,
#: ``visible-too-recent`` fra prefix-listen), og komprimeringen ville splitte
#: en uændret tilstand i to rækker.
_REASON_CODE_PREFIXES = (
    "dependency-not-met",
    "dependency-stale",
    "dispatch-error",
)

_STATUS_CODES = {
    "ran": "dispatched",
    "deferred": "dispatch-budget",
    "cooling_down": "cooldown",
    "visible_grace": "visible-grace",
    "i_flugt": "in-flight",
    "blocked": "blocked",
    "error": "dispatch-error",
    "skipped": "skipped",
}


def reason_code_for(*, status: str, reason: str) -> str:
    """Udled den stabile årsags-kode af (status, formateret reason).

    ``deferred`` får sin egen kode frem for at arve ``cooldown``: forskellen
    mellem «den var ikke klar» og «den var klar, men budgettet slap op» er
    præcis den forskel et senere «hvorfor kørte den ikke?» skal kunne se.
    """
    st = str(status or "").strip()
    if st == "deferred":
        return "dispatch-budget"
    raa = str(reason or "").strip()
    for prefix in _REASON_CODE_PREFIXES:
        if raa.startswith(prefix):
            return prefix
    return _STATUS_CODES.get(st, st or "unknown")


def _ensure_cadence_decisions_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cadence_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producer TEXT NOT NULL,
            status TEXT NOT NULL,
            reason_code TEXT NOT NULL,
            reason_detail TEXT NOT NULL DEFAULT '',
            priority INTEGER NOT NULL DEFAULT 0,
            tick_id TEXT NOT NULL DEFAULT '',
            due_since TEXT NOT NULL DEFAULT '',
            last_visible_at TEXT NOT NULL DEFAULT '',
            dispatch_budget INTEGER NOT NULL DEFAULT 0,
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            occurrences INTEGER NOT NULL DEFAULT 1,
            closed_at TEXT NOT NULL DEFAULT ''
        )
        """
    )
    # Partial unik indeks: højst ÉN åben post pr. producer. Det er den der gør
    # komprimeringen entydig — uden den kunne to samtidige ticks åbne hver sin.
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_cadence_decisions_open "
        "ON cadence_decisions (producer) WHERE closed_at = ''"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_cadence_decisions_producer_seen "
        "ON cadence_decisions (producer, last_seen_at DESC)"
    )


def record_cadence_decisions(
    decisions: Iterable[dict[str, Any]],
    *,
    tick_id: str,
    dispatch_budget: int = 0,
    now: datetime | None = None,
) -> int:
    """Skriv ét tiks beslutninger. Returnerer antal rækker der blev berørt.

    Hver ``decision`` er ``{producer, status, reason, priority?, due_since?,
    last_visible_at?}``. Gentagne identiske beslutninger komprimeres ind i den
    åbne post; et tilstandsskift lukker den gamle og åbner en ny.
    """
    items = [d for d in decisions if str(d.get("producer") or "").strip()]
    if not items:
        return 0
    ts = (now or datetime.now(UTC)).isoformat()
    touched = 0
    try:
        with connect() as conn:
            _ensure_cadence_decisions_table(conn)
            for item in items:
                producer = str(item.get("producer") or "").strip()
                status = str(item.get("status") or "").strip() or "unknown"
                reason_detail = str(item.get("reason") or "")
                code = reason_code_for(status=status, reason=reason_detail)
                row = conn.execute(
                    "SELECT id, status, reason_code FROM cadence_decisions "
                    "WHERE producer = ? AND closed_at = ''",
                    (producer,),
                ).fetchone()
                if row is not None and row["status"] == status and row["reason_code"] == code:
                    conn.execute(
                        "UPDATE cadence_decisions SET "
                        "last_seen_at = ?, occurrences = occurrences + 1, "
                        "reason_detail = ?, tick_id = ?, dispatch_budget = ?, "
                        "priority = ?, due_since = ?, last_visible_at = ? "
                        "WHERE id = ?",
                        (
                            ts,
                            reason_detail,
                            str(tick_id or ""),
                            int(dispatch_budget or 0),
                            int(item.get("priority") or 0),
                            str(item.get("due_since") or ""),
                            str(item.get("last_visible_at") or ""),
                            int(row["id"]),
                        ),
                    )
                    touched += 1
                    continue
                if row is not None:
                    conn.execute(
                        "UPDATE cadence_decisions SET closed_at = ? WHERE id = ?",
                        (ts, int(row["id"])),
                    )
                conn.execute(
                    "INSERT INTO cadence_decisions "
                    "(producer, status, reason_code, reason_detail, priority, "
                    " tick_id, due_since, last_visible_at, dispatch_budget, "
                    " first_seen_at, last_seen_at, occurrences, closed_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)",
                    (
                        producer,
                        status,
                        code,
                        reason_detail,
                        int(item.get("priority") or 0),
                        str(tick_id or ""),
                        str(item.get("due_since") or ""),
                        str(item.get("last_visible_at") or ""),
                        int(dispatch_budget or 0),
                        ts,
                        ts,
                        _OPEN,
                    ),
                )
                touched += 1
            conn.commit()
        return touched
    except Exception as exc:
        # Journalen maa ikke vaelte cadencen der kalder den — men den maa
        # heller ikke doe tavst: en tavs journal er praecis den fejlform den
        # findes for at afsloere.
        logger.warning("kadence-journal: kunne ikke skrive beslutninger: %s", exc)
        return 0


def recent_cadence_decisions(
    *,
    producer: str = "",
    open_only: bool = False,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Læs journalen — nyeste først. Tom liste ved fejl (selv-sikker)."""
    try:
        clauses: list[str] = []
        params: list[Any] = []
        if producer:
            clauses.append("producer = ?")
            params.append(str(producer))
        if open_only:
            clauses.append("closed_at = ''")
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(max(int(limit), 1))
        with connect() as conn:
            _ensure_cadence_decisions_table(conn)
            rows = conn.execute(
                "SELECT producer, status, reason_code, reason_detail, priority, "
                "tick_id, due_since, last_visible_at, dispatch_budget, "
                "first_seen_at, last_seen_at, occurrences, closed_at "
                f"FROM cadence_decisions{where} ORDER BY last_seen_at DESC LIMIT ?",
                tuple(params),
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as exc:
        # Tom liste betyder ellers "ingen fravalg" — som er noget andet end
        # "journalen kunne ikke laeses".
        logger.warning("kadence-journal: kunne ikke laeses: %s", exc)
        return []


def prune_cadence_decisions(
    *,
    retention_days: int = CLOSED_RETENTION_DAYS,
    max_rows: int = MAX_ROWS,
    now: datetime | None = None,
) -> dict[str, int]:
    """Retention: slet GAMLE LUKKEDE poster, og håndhæv rækkeloftet.

    Åbne poster røres aldrig — de beskriver en tilstand der stadig gælder, og
    at slette dem ville gøre netop det spørgsmål ubesvarligt som journalen
    findes for at besvare.
    """
    out = {"expired": 0, "capped": 0}
    cutoff = ((now or datetime.now(UTC)) - timedelta(days=int(retention_days))).isoformat()
    try:
        with connect() as conn:
            _ensure_cadence_decisions_table(conn)
            cur = conn.execute(
                "DELETE FROM cadence_decisions WHERE closed_at <> '' AND closed_at < ?",
                (cutoff,),
            )
            out["expired"] = int(cur.rowcount or 0)
            total = int(
                conn.execute("SELECT COUNT(*) FROM cadence_decisions").fetchone()[0]
            )
            if total > int(max_rows):
                overskud = total - int(max_rows)
                # Ældste LUKKEDE først; åbne poster er fredede.
                cur = conn.execute(
                    "DELETE FROM cadence_decisions WHERE id IN ("
                    "  SELECT id FROM cadence_decisions WHERE closed_at <> '' "
                    "  ORDER BY last_seen_at ASC LIMIT ?)",
                    (overskud,),
                )
                out["capped"] = int(cur.rowcount or 0)
            conn.commit()
        return out
    except Exception as exc:
        logger.warning("kadence-journal: retention fejlede: %s", exc)
        return out
