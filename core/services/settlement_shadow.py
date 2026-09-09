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

## Tavshed er tvetydig, så den siges højt

En måling der kun logger ved uenighed, kan ikke skelne «alt passer» fra
«fyrede aldrig». Derfor siges tællerne højt hver 20. observation — så nul
uenigheder kan aflæses som et resultat frem for et fravær.

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


def _puls() -> None:
    """Sig tællerne højt ved FØRSTE observation og derefter periodisk.

    Den første er den vigtigste: den er beviset for at koblingen overhovedet
    fyrer. Uden den skal man vente på den 20. for at vide om målingen er i
    live — og indtil da er tavshed stadig tvetydig.
    """
    n = _taellere["enige"] + _taellere["uenige"]
    if n == 1 or (n and n % PULS_HVER == 0):
        logger.info("settlement-shadow puls: %s", taellere())


def observe(*, run_id: str, legacy_status: str, legacy_error: str | None,
            text: str, emitted_prefix: str, cancelled: bool,
            transport_error: bool = False, tool_dispatched: bool = False) -> None:
    """Sammenlign den kørende beslutning med den nye kontrakts. Kaster aldrig."""
    if not live():
        _taellere["sprunget_over"] += 1
        return
    try:
        from core.services import outcome_projector as O
        from core.services import stream_settlement as S

        terminal = (S.CANCELLED if cancelled
                    else S.TRANSPORT_ERROR if transport_error else S.OK)
        forsoeg = S.Attempt(
            terminal=terminal,
            text_blocks=((text,) if text else ()),
            emitted_prefix=str(emitted_prefix or ""),
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
        # BEGGE svar og de kendsgerninger der førte til dem — så uenigheden kan
        # afgøres frem for at skulle gættes.
        logger.warning(
            "settlement-shadow UENIGE run=%s gammel=%s(→%s) ny=%s regel=%r "
            "tekst=%d praefiks=%d cancelled=%s transport=%s tool=%s fejl=%r",
            run_id, legacy_status, forventet, ny.outcome, ny.rule,
            len(text or ""), len(emitted_prefix or ""), cancelled,
            transport_error, tool_dispatched, (legacy_error or "")[:120],
        )
    except Exception:
        _taellere["fejl"] += 1
        logger.warning("settlement-shadow fejlede for run=%s", run_id, exc_info=True)
