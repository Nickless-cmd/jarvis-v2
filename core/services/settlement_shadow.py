"""Skygge-sammenligning: er den nye afregning enig med den kørende kode?

Fase 2's kobling. Den følger samme mønster som ledger-skyggen, af samme grund:
en ny kontrakt er ikke bevist ved at bestå sine egne tests. Den er bevist når
den siger det SAMME som den kode der har kørt i produktion — på virkelige
kørsler, ikke på fikstur.

## Den ændrer ingenting

`observe()` sammenligner og logger. Den rører ikke runnet, kaster aldrig, og
har ingen returværdi nogen handler på. Går den i stykker, sker der intet andet
end at målingen udebliver.

Det er ikke forsigtighed for forsigtighedens skyld: dette sidder på den
synlige svarvej. En måling der kan vælte et svar, er ikke en måling værd at
have.

## Afbryderen, og hvorfor den IKKE bruger husets `is_enabled`

`central_switches.is_enabled()` er **fail-OPEN**: den svarer `True` når nøglen
ikke findes, og `True` hvis cachen fejler. Det er rigtigt for en gate der
beskytter en funktion — en cache-nedbrud må ikke slukke for systemet.

Her ville det være forkert. Dette er en MÅLING på den synlige svarvej, og en
måling der tænder sig selv fordi ingen har sat en nøgle, er ikke noget nogen
har besluttet. Derfor kræves et EKSPLICIT `enabled: true`; alt andet — nøglen
mangler, cachen fejler, værdien har en anden form — regnes som slukket.

## Tavshed er tvetydig, så tællerne er AFLÆSELIGE UDEFRA

En måling der kun logger ved uenighed, kan ikke skelne «alt passer» fra
«fyrede aldrig».

Loggen alene løste det ikke: et pulsslag hver 20. observation betyder at den
sidst loggede værdi er forældet indtil den 20. — og en aflæser kan ikke se
forskel på «tælleren står på 1» og «tælleren stod på 1 sidst nogen sagde det».
Jeg byggede den fælde to gange i træk i dag.

Derfor skrives tællerne til `shared_cache`, som er sqlite-baseret og altså
læsbar fra ENHVER proces. Så er tallet et svar, ikke et ekko. Skrivningen er
best-effort og koster én lille skrivning pr. kørsel — ikke pr. delta.

## Hvad uenighed betyder

Ikke nødvendigvis at den nye kode tager fejl. Det kan lige så godt være at den
gamle gør, eller at de to beskriver forskellige ting. Derfor logges BEGGE svar
plus de kendsgerninger der førte til dem — så en uenighed kan afgøres frem for
at skulle gættes.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_taellere: dict[str, int] = {"enige": 0, "uenige": 0, "fejl": 0, "sprunget_over": 0}


def taellere() -> dict[str, int]:
    return dict(_taellere)


def _nulstil_for_tests() -> None:
    for k in _taellere:
        _taellere[k] = 0


def live() -> bool:
    """Er skygge-sammenligningen tændt? Slukket ved enhver tvivl.

    Læser den rå værdi frem for `is_enabled()`, som er fail-open og ville
    svare `True` for en nøgle ingen har sat.
    """
    try:
        from core.services.central_switches import _key, shared_cache
        v = shared_cache.get(_key("settlement", "shadow"))
    except Exception:
        return False
    return isinstance(v, dict) and v.get("enabled") is True


#: Den kørende kodes status → den nye kontrakts udfald.
_KORT = {
    "completed": "completed",
    "failed": "failed",
    "interrupted": "interrupted",
    # Den gamle kode skelner mellem «cancelled» og «interrupted»; den nye har
    # ét ord for begge, fordi forskellen er HVORFOR turen stoppede, ikke
    # hvordan den endte. Kortlægges her frem for at kalde det en uenighed.
    "cancelled": "interrupted",
}


#: Hvor ofte enigheden siges højt. Tavshed er ellers TVETYDIG: den kan betyde
#: «alt passer» eller «målingen fyrede aldrig», og de to skal kunne skelnes.
PULS_HVER = 20


#: Nøglen tællerne kan læses på — fra en hvilken som helst proces.
CACHE_NOEGLE = "settlement:shadow:taellere"
_CACHE_TTL = 7 * 24 * 3600.0


def _puls() -> None:
    """Gør tællerne aflæselige udefra, og sig dem højt med jævne mellemrum."""
    try:
        from core.services import shared_cache
        shared_cache.set(CACHE_NOEGLE, taellere(), ttl_seconds=_CACHE_TTL)
    except Exception:
        pass
    n = _taellere["enige"] + _taellere["uenige"]
    if n == 1 or (n and n % PULS_HVER == 0):
        logger.info("settlement-shadow puls: %s", taellere())


def taellere_fra_cache() -> dict[str, int] | None:
    """Læs tællerne UDEN at være den proces der skrev dem."""
    try:
        from core.services import shared_cache
        v = shared_cache.get(CACHE_NOEGLE)
    except Exception:
        return None
    return v if isinstance(v, dict) else None


def observe(*, run_id: str, legacy_status: str, legacy_error: str | None,
            text: str, emitted_prefix: str = "", cancelled: bool = False,
            transport_error: bool = False, tool_dispatched: bool = False) -> None:
    """Sammenlign den kørende beslutning med den nye kontrakts. Kaster aldrig."""
    if not live():
        _taellere["sprunget_over"] += 1
        return
    try:
        from core.services import outcome_projector as O
        from core.services import stream_settlement as S

        # `interrupted` er også en afbrydelse, ikke et almindeligt udfald.
        # Den gamle kode bruger `cancelled` for et brugerklik og `interrupted`
        # for et run der døde midt i flugten (GeneratorExit, CancelledError).
        # Begge er «turen blev stoppet», og at kalde den sidste `OK` ville få
        # klassifikatoren til at se et tomt svar hvor der var en afbrydelse.
        terminal = (S.CANCELLED if (cancelled or str(legacy_status) == "interrupted")
                    else S.TRANSPORT_ERROR if transport_error else S.OK)
        # Præfikset måles fra den SERVER-EJEDE buffer, ikke fra kalderens
        # variabel: spec en siger at bytes en klient så, men som ikke er i den
        # buffer, er en transport-fejl — ikke en alternativ historik.
        # Falder tilbage til det kalderen gav, hvis loggen ikke kan læses.
        praefiks = str(emitted_prefix or "")
        try:
            from core.services.emitted_prefix import emitted_prefix as _maalt
            p = _maalt(run_id)
            if not p.problem:
                praefiks = p.text
        except Exception:
            logger.warning("settlement-shadow: kunne ikke maale praefikset",
                           exc_info=True)

        forsoeg = S.Attempt(
            terminal=terminal,
            text_blocks=((text,) if text else ()),
            emitted_prefix=praefiks,
            tool_dispatched=bool(tool_dispatched),
            message_committed=bool(text),
        )
        ny = O.project([S.classify(forsoeg)])
        forventet = _KORT.get(str(legacy_status), str(legacy_status))

        if ny.outcome == forventet:
            _taellere["enige"] += 1
            _puls()
            return

        _taellere["uenige"] += 1
        _puls()
        # BEGGE svar og de kendsgerninger der førte til dem — så uenigheden kan
        # afgøres frem for at skulle gættes.
        logger.warning(
            "settlement-shadow UENIGE run=%s gammel=%s(→%s) ny=%s regel=%r "
            "tekst=%d praefiks=%d cancelled=%s transport=%s tool=%s fejl=%r",
            run_id, legacy_status, forventet, ny.outcome, ny.rule,
            len(text or ""), len(praefiks), cancelled,
            transport_error, tool_dispatched, (legacy_error or "")[:120],
        )
    except Exception:
        _taellere["fejl"] += 1
        logger.warning("settlement-shadow fejlede for run=%s", run_id, exc_info=True)
