"""Er dét vaerktoej faktisk bestilt? — afgjort af en lille lokal model.

Ordmatchen (``tool_lexical_match``) finder HVILKET vaerktoej en besked minder
om. Den kan ikke afgoere OM beskeden overhovedet er en bestilling, og det er
dér nudgen faldt: maalt 7/9-2026 paa 400 aegte beskeder var 26 af 32 bud
forkerte, og de forkerte var samme slags hver gang — Bjoern taler om systemet.

    «Du koere vision i denne session»        -> hf_vision_analyze
    «Hvor mange vision tools har du?»        -> hf_vision_analyze
    «Du har osse look_around tool»           -> look_around
    «Hahahaha det er en gate der blokker»    -> skill_gate

To leksikalske forsoeg paa at lukke det slog fejl, begge maalt: den
data-udledte stopordsliste fjernede «claude»-stoejen men ikke «vision», og
imperativ-gaten (``tool_router._clarity_signal``, +17,1 % mod grundsandhed)
lod alle ni vision-bud passere — «check lige priserne paa flash vision» ER en
befaling og stadig ikke en bestilling af billedanalyse.

Skellet kraever forstaaelse af saetningen. Maalt paa de 35 aegte bud mod
haandmaerkede labels:

    kun ordmatch      6 rigtige af 32 bud     17 % praecision
    + denne gate      5 rigtige af  5 bud    100 % praecision, 26 af 26 forkerte afvist

## Hvorfor lokalt og ikke cheap lane

Ikke kvalitet — **fejlretning**. Sektionen bygges inde i prompt-samlingen. En
udbyder der er nede har to gange leveret sin kvotefejl videre som indhold
(``provider_error_in_self_anchor``, explore-fundet der var en fejlbesked). En
lokal model der er nede leverer ingenting, og det er det rigtige svar her.

Modellen ligger i forvejen residens i CT105's VRAM (qwen3:4b, 5,37 GB, ~0,19 s
pr. kald) paa et kort med 0 % udnyttelse.

## Hard deadline, og hvorfor den er saa stram

Ollama-kald KOEER 28-91 s naar ollama er optaget — det er dokumenteret som
selve cut-off-roden i ``prompt_contract._timed_result``. Maalt kald er 0,19 s,
saa ``_TIMEOUT_S`` giver otte gange luft og fejler LUKKET: ingen dom, ingen
nudge. Stoej er vaerre end ingen nudge, saa tvivl skal koste buddet — ikke
turen.
"""

from __future__ import annotations

import hashlib
import logging

from core.services.local_small_model import MODEL, spoerg_et_ord

logger = logging.getLogger(__name__)

__all__ = ["MODEL", "er_bestilt"]

_TIMEOUT_S = 1.5
_CACHE_TTL_S = 900

# Eksemplerne er MED VILJE hentet uden for de bud gaten blev maalt paa
# (kalender/gmail, som ikke optraeder i saettet). Foerste udgave brugte de
# faktiske fejl som eksempler og scorede 100 % — paa sig selv. Med rene
# eksempler holder tallet: 5 af 5 rigtige, 26 af 26 forkerte afvist.
_SKABELON = (
    "Vaerktoej: {navn}\n"
    "Hvad det goer: {beskrivelse}\n\n"
    "Nedenfor staar en besked fra brugeren til sin assistent.\n"
    "Ville assistenten skulle KALDE netop dette vaerktoej for at goere det "
    "brugeren beder om?\n\n"
    "Svar NEJ hvis brugeren blot naevner, omtaler eller spoerger TIL emnet, "
    "eller beder om at faa noget BYGGET frem for brugt.\n"
    "Svar JA hvis brugeren beder om en handling som netop dette vaerktoej "
    "udfoerer.\n\n"
    "Svar med ét ord: JA eller NEJ.\n\n"
    "Eksempler:\n"
    "«findes der et vaerktoej til kalenderen?» + calendar_list_events -> NEJ "
    "(spoerger om det findes)\n"
    "«laeg et moede ind i morgen kl. 10» + calendar_create_event -> JA "
    "(beder om handlingen)\n"
    "«gmail-integrationen driller vist» + gmail_send -> NEJ (kommenterer)\n"
    "«send den til Michelle» + gmail_send -> JA (beder om handlingen)"
)


def _cache_noegle(besked: str, navn: str) -> str:
    fingeraftryk = hashlib.sha1(  # noqa: S324 - cache-noegle, ikke sikkerhed
        f"{navn}\x00{besked}".encode()
    ).hexdigest()[:16]
    return f"local_intent_gate:{fingeraftryk}"


def er_bestilt(besked: str, navn: str, beskrivelse: str = "") -> bool:
    """Beder brugeren om noget hvor ``navn`` ville blive kaldt?

    Returnerer ``False`` ved enhver tvivl — modellen svarer nej, den svarer
    uforstaaeligt, den er nede, eller den er for langsom. Kaster aldrig.
    """
    besked = (besked or "").strip()
    navn = (navn or "").strip()
    if not besked or not navn:
        return False

    noegle = _cache_noegle(besked, navn)
    try:
        from core.services import shared_cache
        cachet = shared_cache.get(noegle)
        if cachet is not None:
            return bool(cachet)
    except Exception as exc:
        logger.debug("local_intent_gate: cache utilgaengelig: %s", exc)

    ord_ = spoerg_et_ord(
        _SKABELON.format(navn=navn, beskrivelse=(beskrivelse or "")[:150]),
        besked,
        timeout_s=_TIMEOUT_S,
    )
    # Kun et rent «JA» er et ja. ``spoerg_et_ord`` giver foerste HELE ord, saa
    # «JAVEL» og «JANUAR» falder her — gaten fejler lukket og skal vaere striks.
    # Ingen dom (modellen nede eller for langsom) er ogsaa et nej.
    dom = ord_ == "JA"
    try:
        from core.services import shared_cache
        shared_cache.set(noegle, dom, ttl_seconds=_CACHE_TTL_S)
    except Exception as exc:
        logger.debug("local_intent_gate: kunne ikke cache dom: %s", exc)
    return dom
