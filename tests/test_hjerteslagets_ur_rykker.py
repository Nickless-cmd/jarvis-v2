"""Hjerteslaget skal rykke sit eget ur.

24/9-2026: Jarvis havde ikke sendt et eneste autonomt run af sted i timevis, og
planlæggeren sagde `due=True` hvert 30. sekund uden at noget skete. Det lignede
et stoppet hjerte. Det var det modsatte.

`tick_with_phases` kører sense → reflect → act, udsender `heartbeat.phased_tick`
og returnerer en dict. Den skrev ALDRIG tilstanden. `next_tick_at` skrives kun
ét sted i hele kodebasen — `_record_heartbeat_outcome` — og den kaldes tre
steder, alle i `heartbeat_runtime`. `heartbeat_phases` kaldte den nul gange.

Planlæggeren blev 18/5-2026 ruttet om til `tick_with_phases`; uret blev efterladt
i den gamle sti. `next_tick_at` stod derfor stille, `due` blev ved med at være
sand, og planlæggeren fyrede et helt tik hver eneste gang den pollede.

Målt på CT105 med 15-minutters kadence konfigureret:

    sidste  30 min:   56 tik   (forventet  2)
    sidste  60 min:   83 tik   (forventet  4)
    sidste 240 min:  368 tik   (forventet 16)

Ét tik hvert ~32. sekund — planlæggerens poll-interval. 28 gange for hurtigt.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta


def test_et_faset_tik_rykker_next_tick_at(monkeypatch) -> None:
    """Kernen: efter et tik skal uret pege FREM, ellers er det straks forfaldent igen.

    Det er hele fejlen i én assertion. Stod `next_tick_at` stille, ville
    `_merge_runtime_state` regne `due = next_tick_at <= now` til sand ved hvert
    eneste poll, og planlæggeren ville fyre igen 30 sekunder senere. For evigt.
    """
    from core.services import heartbeat_phases as p

    skrevet: dict[str, object] = {}

    def _fang(**kw):
        skrevet.update(kw)

    monkeypatch.setattr("core.services.heartbeat_runtime.record_phased_tick",
                        lambda **kw: _fang(**kw))
    monkeypatch.setattr(p, "sense_phase", lambda **kw: {})
    monkeypatch.setattr(p, "reflect_phase", lambda s: {"activity_level": "idle"})
    monkeypatch.setattr(p, "act_phase",
                        lambda **kw: {"kind": "productive_idle", "summary": "intet at gøre"})

    p.tick_with_phases(name="default", trigger="scheduled")

    assert skrevet, (
        "det fasede tik skrev ikke uret — planlæggeren vil fyre igen ved næste "
        "poll, og hjertet løber løbsk"
    )
    assert skrevet.get("trigger") == "scheduled"
    assert (skrevet.get("result") or {}).get("started_at"), (
        "starttiden mangler i resultatet — uret kan ikke regne kadencen"
    )


def test_recorderen_saetter_uret_et_helt_interval_frem(monkeypatch) -> None:
    """`record_phased_tick` skal skrive et `next_tick_at` der ligger i FREMTIDEN.

    Uden det er rettelsen kosmetisk: en skrivning der sætter uret til nu, ville
    lade `due` være sand med det samme.
    """
    from core.services import heartbeat_runtime as h

    fanget: dict[str, object] = {}
    monkeypatch.setattr(h, "_record_heartbeat_outcome",
                        lambda **kw: fanget.update(kw) or {"tick_id": "t"})
    monkeypatch.setattr(h, "load_heartbeat_policy",
                        lambda name="default": {"enabled": True, "kill_switch": "enabled",
                                                "interval_minutes": 15,
                                                "budget_status": "bounded-internal-only"})
    monkeypatch.setattr(h, "ensure_default_workspace", lambda name="default": None)
    monkeypatch.setattr(h, "get_heartbeat_runtime_state", lambda: {"state_id": "default"})

    h.record_phased_tick(name="default", trigger="scheduled",
                         result={"phases": {"act": {"kind": "productive_idle"}}})

    assert fanget, "recorderen kaldte ikke den kanoniske skrivning"
    # `_record_heartbeat_outcome` regner selv next_tick_at ud fra finished_at;
    # det vi skal sikre er at den FÅR en frisk finished_at at regne fra.
    slut = datetime.fromisoformat(str(fanget["finished_at"]))
    assert abs((datetime.now(UTC) - slut).total_seconds()) < 60, (
        "finished_at er ikke nu — uret ville blive sat tilbage i tiden"
    )
    assert fanget["currently_ticking"] is False, (
        "tikket markeres som stadig kørende — næste tik ville blive sprunget over"
    )


def test_kun_EN_vej_skriver_uret() -> None:
    """`next_tick_at` må kun kunne skrives ét sted.

    Det var netop fordi skrivningen lå ét sted — og den fasede sti ikke gik
    derigennem — at fejlen kunne opstå. Kommer der en vej mere, skal nogen tage
    stilling til om begge rykker uret ens.
    """
    import inspect

    from core.runtime import db_heartbeat

    kilde = inspect.getsource(db_heartbeat)
    # Selve SQL-sætningen der rører kolonnen.
    assert kilde.count("next_tick_at = excluded.next_tick_at") == 1, (
        "der er nu mere end én vej til at skrive next_tick_at — hvilken af dem "
        "rykker uret, og gør de det ens?"
    )


def test_forfald_regnes_ud_fra_last_tick_at_ikke_fra_next_tick_at() -> None:
    """Pin den mekanik der gjorde fejlen til en løbsk løkke.

    `_merge_runtime_state` bruger IKKE den gemte `next_tick_at`. Når der er et
    `last_tick_at`, regner den `next = last_tick_at + interval` forfra hver
    gang. Hele kadencen hænger altså i ét felt — og det felt skrives kun af
    `_record_heartbeat_outcome`, som den fasede sti aldrig kaldte.

    Derfor stod `last_tick_at` på CT105 stille på 14:10, `next` blev regnet til
    14:25, og fra 14:25 og frem var svaret «forfalden» ved hvert eneste poll.

    (Min første udgave af denne test skrev et fremtidigt `next_tick_at` og
    forventede `due=False`. Den fejlede — fordi feltet bliver ignoreret. Testen
    havde en forkert model af koden, og ville have pinnet den forkerte model.)
    """
    from core.services.heartbeat_runtime import (
        _merge_runtime_state, load_heartbeat_policy,
    )

    politik = dict(load_heartbeat_policy(name="default"))
    politik.update(enabled=True, kill_switch="enabled", interval_minutes=15)

    def _tilstand(minutter_siden_sidste_tik: int, gemt_next: str = "") -> dict:
        return _merge_runtime_state(
            policy=politik,
            persisted={
                "last_tick_at": (datetime.now(UTC)
                                 - timedelta(minutes=minutter_siden_sidste_tik)).isoformat(),
                "next_tick_at": gemt_next,
            },
            now=datetime.now(UTC),
        )

    # Et gammelt tik → forfalden.
    assert _tilstand(20)["due"] is True
    assert _tilstand(20)["schedule_state"] == "due"

    # Et FRISKT tik → ikke forfalden. Det er præcis det rettelsen opnår.
    assert _tilstand(1)["due"] is False
    assert _tilstand(1)["schedule_state"] == "scheduled"

    # Og den gemte `next_tick_at` betyder ingenting — selv en langt fremtidig
    # værdi redder ikke et gammelt `last_tick_at`.
    langt_ude = (datetime.now(UTC) + timedelta(hours=5)).isoformat()
    assert _tilstand(20, gemt_next=langt_ude)["due"] is True, (
        "den gemte next_tick_at blev pludselig brugt — så gælder hele "
        "analysen af fejlen ikke længere"
    )
