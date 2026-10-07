"""Den streamede syntese, skrubbet — ét sted.

Boy Scout-udskillelse fra `visible_runs.py` (7.648 linjer), 3/10-2026.

## Hvorfor netop denne enhed

Jarvis gjorde syntesen streamet samme dag, så den ikke længere kommer som et
blink. Det gjorde den rigtige ting, men de to kaldesteder blev næsten identiske
— og da jeg rettede den manglende skrubning, fordoblede jeg dubletten: samme
skrubber, samme `foed`, samme `skyl`, samme `_sse`-form, to steder.

To kopier af en skrubning driver fra hinanden. Det var præcis sådan fejlen
opstod i første omgang: tre skrub-steder blev til ét, fordi ingen af dem var
den samme kode.

## Hvorfor en strøm ikke kan skrubbes bagefter

En intern markør kan være **delt over to deltaer**. `fjern_interne_markoerer`
på den færdige tekst renser det persisterede, men brugeren har allerede set den
halve markør. `StroemSkrubber` holder en lille hale tilbage indtil den kan
afgøre om den er del af en markør — og derfor SKAL den skylles til sidst,
ellers forsvinder det sidste stykke svar.

Målt da fejlen stod: det eneste tilbageværende skrub ramte `followup_text`,
altså det persisterede. Interne markører nåede skærmen live og forsvandt
bagefter fra tråden — en asymmetri der ikke kan genfindes i historikken.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SyntesStykke:
    """Ét renset stykke på vej til skærmen."""
    tekst: str


@dataclass(slots=True)
class SyntesFacit:
    """Den færdige, skrubbede tekst. Kommer sidst, præcis én gang."""
    tekst: str


async def skrubbet_syntese(
    stroem: AsyncIterator[Any],
    *,
    delta_klasse: type,
) -> AsyncIterator[SyntesStykke | SyntesFacit]:
    """Kør en syntese-strøm igennem `StroemSkrubber` og giv rensede stykker.

    Kalderen får `SyntesStykke` for hvert stykke der må vises, og til sidst
    præcis ét `SyntesFacit` med den fulde, skrubbede tekst til persistering.

    `delta_klasse` injiceres frem for at importeres, så denne fil ikke skal
    kende `visible_post_tool_synthesis` — og så testene kan sende deres egen
    uden at mocke et modul.

    Halen skylles i et `finally`: afbrydes strømmen (cutoff, en exception fra
    udbyderen), ville det tilbageholdte stykke ellers forsvinde sammen med
    resten. Det er den samme fejlform som en `StroemSkrubber` uden `skyl()`,
    bare udløst af en fejl i stedet for af en glemsel.
    """
    from core.services import visible_text_scrub as _vts

    skrub = _vts.StroemSkrubber()
    facit = ""
    try:
        async for begivenhed in stroem:
            if isinstance(begivenhed, delta_klasse):
                rent = skrub.foed(getattr(begivenhed, "text", "") or "")
                if rent:
                    yield SyntesStykke(rent)
            else:
                # Den afsluttende begivenhed bærer hele teksten. Den skrubbes
                # med funktionen — her ER teksten færdig, så en delt markør
                # findes ikke længere.
                facit = _vts.fjern_interne_markoerer(
                    getattr(begivenhed, "text", "") or "")
    finally:
        try:
            rest = skrub.skyl()
        except Exception as exc:  # noqa: BLE001
            # En skrubber der kaster i skylningen maa ikke tage svaret med.
            logger.warning("visible_synthesis_stream: skyl() fejlede: %s", exc)
            rest = ""
        if rest:
            yield SyntesStykke(rest)
        yield SyntesFacit(facit)


__all__ = ["SyntesFacit", "SyntesStykke", "skrubbet_syntese"]
