"""Tidsstyring for Rutiner — én scheduler for ALLE brugere.

## Hullet den lukker

Frem til 25/10-2026 havde en Rutine med ``trigger_kind='schedule'`` ingen
eksekvering bag sig. ``schedule`` blev kun *valideret* i API-routen, og
``RoutineTriggerAdapters`` krævede både et migreret legacy-link OG
``JARVIS_ROUTINES_CUTOVER``. En nyoprettet rutine — Michelles ugentlige
madopskrifter — var derfor korrekt oprettet, synlig i hendes app og manuelt
kørbar, men fyrede aldrig af sig selv. Den så færdig ud og gjorde ingenting.

## Hvordan den fyrer sikkert

Scheduleren læser aktive rutiner på tværs af ALLE ejere, beregner den seneste
forekomst der er passeret, og lægger et run i kø med en idempotency-nøgle pr.
forekomst (``schedule:<ISO>``). ``create_run`` afviser en gentagelse, så det er
sikkert at polle hvert minut — også når to workers ser samme forekomst.

Ejerskabet bæres af rutinen selv: ``create_run`` kopierer ``owner_user_id`` fra
rutine-rækken. Intet her rører den globale ejer — det var netop fejlen i
``fire_session_id``, som ville have fyret Michelles opgave i Bjørns samtale.

## Formater (målt i den levende database, ikke gættet)

- ``{"interval_minutes": N}``      — hvert N. minut fra rutinens oprettelse
- ``{"time": "07:00", "weekday": "monday"}`` — ugentlig
- ``{"time": "07:00"}``            — daglig
- ``{"run_at": "<ISO>", "weekdays": [..]}`` — engangs (migrationsformat)

Et ukendt format fyrer ikke. Det er med vilje: en rutine der aldrig kører er
synlig i sin køliste, mens en der kører på et gæt er usynlig.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, time, timedelta
from typing import Any, Mapping

from core.runtime import db_routines

logger = logging.getLogger(__name__)

_UGEDAGE: dict[str, int] = {
    "monday": 1, "tuesday": 2, "wednesday": 3, "thursday": 4,
    "friday": 5, "saturday": 6, "sunday": 7,
    "mandag": 1, "tirsdag": 2, "onsdag": 3, "torsdag": 4,
    "fredag": 5, "lørdag": 6, "søndag": 7,
}

#: Hvor sent en passeret forekomst stadig må fyre. Maskinen kan have været
#: nede; en ugentlig rutine skal kunne indhente inden for et døgn, men ikke
#: fyre en forekomst fra sidste måned.
_VINDUE = timedelta(hours=24)


def _til_dt(vaerdi: object) -> datetime | None:
    tekst = str(vaerdi or "").strip()
    if not tekst:
        return None
    try:
        dt = datetime.fromisoformat(tekst.replace("Z", "+00:00"))
    except (ValueError, TypeError):  # uparsebar tidsstempel = ingen forekomst, ikke en fejl
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _seneste_forekomst(
    config: Mapping[str, Any], *, anchor: datetime, now: datetime,
) -> datetime | None:
    """Den seneste planlagte forekomst der ligger på eller før ``now``."""
    try:
        interval = int(config.get("interval_minutes") or 0)
    except (TypeError, ValueError):  # ikke-numerisk interval = ingen interval-plan
        interval = 0
    if interval > 0:
        if now < anchor:
            return None
        forloebet = (now - anchor).total_seconds()
        if forloebet < interval * 60:
            return None
        antal = int(forloebet // (interval * 60))
        return anchor + timedelta(minutes=interval * antal)

    run_at = _til_dt(config.get("run_at"))
    if run_at is not None:
        return run_at if run_at <= now else None

    tid = str(config.get("time") or "").strip()
    if not tid:
        return None
    try:
        dele = tid.split(":")
    except (AttributeError, TypeError):  # ikke en streng = ingen klokketid
        return None
    try:
        klokken = time(int(dele[0]), int(dele[1]) if len(dele) > 1 else 0)
    except (ValueError, TypeError, IndexError):  # ugyldig klokketid = ingen plan
        return None

    ugedag = str(config.get("weekday") or "").strip().lower()
    maalt_dag = _UGEDAGE.get(ugedag)
    if ugedag and maalt_dag is None:
        # Ukendt ugedagsnavn: hellere intet run end et run på den forkerte dag.
        return None

    # Otte dage tilbage dækker «i dag» plus en hel uge — nok til at finde den
    # seneste forekomst uanset ugedag.
    for dage in range(0, 8):
        dag = (now - timedelta(days=dage)).date()
        if maalt_dag is not None and dag.isoweekday() != maalt_dag:
            continue
        kandidat = datetime.combine(dag, klokken, tzinfo=UTC)
        if kandidat <= now:
            return kandidat
    return None


def _service():
    from core.services.routine_service import RoutineService
    from core.services.routine_types import RoutinePrincipal

    return RoutineService(
        RoutinePrincipal("routine-scheduler", role="system", actor_kind="system")
    )


def fire_due(*, now: datetime | None = None) -> list[str]:
    """Læg et run i kø for hver rutine hvis forekomst er passeret.

    Returnerer id'erne på de rutiner der fik et NYT run. Kaster aldrig: én
    brækket rutine må ikke stoppe de andre brugeres kø.
    """
    nu = now or datetime.now(UTC)
    if nu.tzinfo is None:
        nu = nu.replace(tzinfo=UTC)
    fyrede: list[str] = []
    service = None
    for row in db_routines.list_schedulable_routines():
        routine_id = str(row.get("routine_id") or "")
        ejer = str(row.get("owner_user_id") or "")
        if not routine_id or not ejer:
            continue
        try:
            # En rutine med en oprindelig kilde tidsstyres AF den kilde:
            # `recurring_tasks`/`scheduled_tasks` fyrer den gennem
            # `RoutineTriggerAdapters`. Uden dette led ville den få to runs af
            # samme forekomst — målt 25/10-2026 havde 198 rutiner et sådant
            # link, og cutover var slukket.
            if db_routines.routine_has_legacy_link(routine_id):
                continue
            privat = db_routines.get_routine(routine_id, decrypt_for=ejer)
            if not privat:
                continue
            anchor = _til_dt(row.get("created_at")) or nu
            forekomst = _seneste_forekomst(
                dict(privat.get("trigger_config") or {}), anchor=anchor, now=nu,
            )
            if forekomst is None or (nu - forekomst) > _VINDUE:
                continue
            key = f"schedule:{forekomst.isoformat()}"
            if db_routines.run_exists_for_trigger(
                routine_id=routine_id, idempotency_key=key,
            ):
                continue
            if service is None:
                service = _service()
            service.enqueue_run(routine_id, trigger_key=key)
            fyrede.append(routine_id)
            logger.info(
                "routine_scheduler: %s fyrede forekomst %s (ejer=%s)",
                routine_id, forekomst.isoformat(), ejer,
            )
        except Exception as exc:  # noqa: BLE001 — én rutine må ikke vælte resten
            logger.warning(
                "routine_scheduler: kunne ikke fyre %s: %s",
                routine_id, type(exc).__name__,
            )
    return fyrede
