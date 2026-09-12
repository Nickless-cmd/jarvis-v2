"""Research-runnet synligt i session-ledgeren (spec Fase A4).

## Hvorfor

Et research-run lever i dag udelukkende i sin egen `research_*`-store. Det
overlever genstart, men det er ikke en del af *sessionens* historik: åbner man
ledgeren for at se hvad der skete i en samtale, er research-runnet usynligt.

Ledgeren giver genskabelighed — én nummereret, uforanderlig hændelsesrække pr.
session. Det er præcis hvad et run med flere workers og flere faser har brug for
at kunne forklares ud fra bagefter.

## Den ene regel: research må aldrig kunne vælte turen

Samme kontrakt som `shadow_ledger_writer`: skrivningen sker EFTER at runnet selv
har skrevet sin sandhed i `research_store`, og den **kaster aldrig**. Et run der
dør fordi det ikke kunne skrive en metadatalinje ville være et eksperiment der
er værre end det problem det løser.

## Hvorfor ikke den ejede vej

`append_session_events` kræver en lease. At tage leasen for at skrive en
metadata-hændelse ville betyde at research-skrivningen kunne konflikte med
chat-skrivningen om den samme session — og leasen er kort (300 s) mens et run
kan vare længere. Vi vælger derfor `append_unowned`, som koster én transaktion.

Prisen er at den AFVISER en session der er kanonisk i ledgeren (`ledger`-mode),
fordi der dér kræves et `SessionHandle` med lease. Det er ikke et hul: vi
springer over, tæller det, og lader runnet fortsætte. Et research-run er
metadata om en tur — ikke turen selv — og må ikke tage ejerskabet fra den.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

#: Tællere pr. proces. Ikke sandhed — et sted at kigge når noget ser skævt ud.
_taellere: dict[str, int] = {"skrevet": 0, "sprunget_over": 0, "fejl": 0}


def taellere() -> dict[str, int]:
    return dict(_taellere)


def _nulstil_for_tests() -> None:
    for k in _taellere:
        _taellere[k] = 0


def record_research_event(
    session_id: str,
    *,
    event_id: str,
    event: str,
    payload: dict | None = None,
) -> bool:
    """Skriv én research-hændelse i session-ledgeren. Kaster aldrig.

    `event_id` er både hændelsens identitet OG dens idempotens-nøgle: skrives
    det samme run igennem to gange (genstart, retry), bliver det til ÉN række.
    Kald derfor med et STABILT id — fx ``f"{run_id}:started"`` — ikke et uuid4.

    Returnerer om der blev skrevet. `False` betyder *ikke* at runnet fejlede;
    det betyder kun at metadatalinjen ikke landede (kanonisk session, eller en
    fejl der er logget og talt).
    """
    sid = str(session_id or "").strip()
    if not sid or not str(event_id or "").strip():
        _taellere["sprunget_over"] += 1
        return False
    try:
        from core.runtime.db_session_ledger import append_unowned, storage_mode

        if storage_mode(sid) == "ledger":
            # Kanonisk session: skrivning kræver et SessionHandle med lease.
            # Research-metadata må ikke tage ejerskabet fra turen.
            _taellere["sprunget_over"] += 1
            return False

        append_unowned(sid, events=[{
            "event_id": str(event_id),
            "kind": "research",
            "payload": {"event": str(event), **(payload or {})},
        }])
        _taellere["skrevet"] += 1
        return True
    except Exception:
        _taellere["fejl"] += 1
        logger.warning(
            "research_ledger: kunne ikke skrive %s for %s", event, sid, exc_info=True,
        )
        return False


def record_run_started(session_id: str, *, run_id: str, tier: str, query: str) -> bool:
    """Runnet er startet: tier og den oprindelige forespørgsel."""
    return record_research_event(
        session_id,
        event_id=f"{run_id}:started",
        event="research_started",
        payload={"research_run_id": run_id, "tier": tier, "query": str(query or "")[:500]},
    )


def record_run_completed(
    session_id: str,
    *,
    run_id: str,
    sources: int,
    quality: str,
    timed_out: bool,
    tool_calls: int | None = None,
) -> bool:
    """Runnet er slut: hvad det blev — kilder, kvalitetsdom, timeout, forbrug."""
    return record_research_event(
        session_id,
        event_id=f"{run_id}:completed",
        event="research_completed",
        payload={
            "research_run_id": run_id,
            "sources": int(sources),
            "quality": str(quality),
            "timed_out": bool(timed_out),
            "tool_calls": tool_calls,
        },
    )
