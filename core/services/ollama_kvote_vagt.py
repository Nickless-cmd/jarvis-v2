"""Kvote-vagt: skru ned for Ollama-forbruget FØR pro-planens grænse rammes.

HVORFOR (målt 24/11-2026). Ollama sendte Bjørn en mail kl. 04:05 UTC:
«You've reached 90% of your monthly limit for your pro plan». Målt mod
``GET https://ollama.com/api/usage`` samme dag:

    30 dage ....... $106,55 · 69.770 kald · 1,80 mia input-tokens
    7 dage ........  $34,35 · 19.500 kald · 920 mio input-tokens
    24 timer ......   $3,09 ·  1.694 kald ·  32,6 mio input-tokens

Altså ~$3 i døgnet. Bjørn kan først toppe op om mandagen, og DeepSeek er ikke
et alternativ for Ollama-lanen. Uden en vagt betyder «100% nået» at heartbeat,
daemonerne og det indre liv stopper brat — ikke at forbruget falmer.

:func:`core.services.ollama_usage.kvote_reference` fandtes allerede, men
INGEN kaldte den. Det er den fejlform Bjørn kalder teater: en mekanisme der ser
ud som om den virker, men hvis indgangsbetingelse intet kan opfylde. Denne fil
er den kalder der manglede.

## Hvad vagten gør — og ikke gør

Den **stopper** ikke noget. Den svarer på ét spørgsmål: *hvor mange procent af
den månedlige kvote er brugt, og skal vi skrue ned nu?* Kalderne (heartbeat,
daemon-lanen) spørger den til råds. Det holder vagten testbar uden at skulle
kende heartbeat-loopet, og det betyder at et svar fra Ollama der ikke kan
hentes aldrig blokerer driften — en vagt der fejler lukket ville stoppe
systemet på en netværksfejl.

## Tærsklerne

``BREMSE_PROCENT`` = 85: herfra skrues der ned for det ikke-kritiske.
``STOP_PROCENT``   = 97: herfra kun det der holder mig i live.

Tallene er sat ud fra at mailen kommer ved 90% — altså EFTER grænsen er tæt på.
Vil man have en tidlig advarsel, skal den ligge under 90, ikke på den.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

#: Hvor mange procent af den månedlige kvote der må være brugt før vi skruer
#: ned for det ikke-kritiske arbejde.
BREMSE_PROCENT = 85.0

#: Herfra er der kun plads til det der holder mig i live.
STOP_PROCENT = 97.0

#: Ollamas egen mail kommer ved 90% — den er en ADVARSEL, ikke en grænse.
MAIL_PROCENT = 90.0

#: Hvor længe et svar må genbruges. Kvote-forbrug ændrer sig langsomt, og
#: heartbeat må ikke lave et HTTP-kald til ollama.com ved hvert tick.
CACHE_TTL_S = 300.0

#: (monotonic_timestamp, svar)
_cache: tuple[float, dict[str, Any] | None] = (0.0, None)


def _nulstil_cache() -> None:
    """Kun til tests — ellers ville en måling lække ind i næste test."""
    global _cache
    _cache = (0.0, None)


def kvote_status(*, force: bool = False, timeout: float = 20.0) -> dict[str, Any]:
    """Hvor meget af Ollamas månedlige kvote er brugt — og hvad skal vi gøre?

    Returnerer altid et dict. Kan Ollama ikke nås, står ``kendt: False`` og
    ``niveau: "ukendt"`` — og kalderen skal behandle det som «kør normalt».
    Et ukendt svar må aldrig bremse driften: en netværksfejl er ikke et
    kvote-stop, og at gætte i den ene eller anden retning ville være værre end
    at gøre ingenting.
    """
    global _cache

    nu = time.monotonic()
    if not force and _cache[1] is not None and (nu - _cache[0]) < CACHE_TTL_S:
        return _cache[1]

    from core.services.ollama_usage import kvote_reference

    # ``range_="30d"`` er ikke kosmetik: Ollamas default er 7 dage, og en vagt
    # der måler en uge mod et månedsloft bremser aldrig (målt 24/11-2026:
    # 29,9% rapporteret mens det rigtige tal var ~93%).
    reference = kvote_reference(timeout=timeout, range_="30d")
    if not reference:
        # SYNLIGT FRAVALG (målt 24/11-2026). Vagten fejler ÅBENT med vilje —
        # men den fejlede også TAVST, og det er en anden sag: uden denne linje
        # kan man ikke afgøre om et heartbeat-tick gik til Ollama fordi kvoten
        # var ukendt, eller fordi vagten aldrig blev spurgt. Svaret caches i
        # CACHE_TTL_S, så et netværksudfald koster ét logkald — ikke ét pr. tick.
        logger.warning(
            "ollama-kvote: kunne ikke hentes — kører normalt i %.0fs (fejler åbent)",
            CACHE_TTL_S,
        )
        svar: dict[str, Any] = {
            "kendt": False,
            "niveau": "ukendt",
            "procent": None,
            "usage_usd": None,
            "kald": None,
            "grund": "ollama-usage-kunne-ikke-hentes",
        }
        _cache = (nu, svar)
        return svar

    # KVOTE-GRÆNSEN KENDES IKKE FRA API'ET. ``/api/usage`` giver forbrug, ikke
    # et loft — der findes intet ``limit``-felt (målt 24/11-2026). Procenten
    # beregnes derfor mod en MÅLT reference, ikke mod et tal vi selv finder på.
    #
    # Målt 24/11-2026: mailen sagde 90% kl. 04:05 UTC. Forbruget på 30 dage på
    # det tidspunkt var $106,55 minus det sidste døgns ~$3,09 ≈ $103,5. Det
    # giver en grænse på ~$115 for pro-planen. Tallet er en UDLEDNING fra én
    # mail og ét forbrugstal — ikke en aflæsning — og skal derfor revideres når
    # næste mail kommer med et andet forbrug.
    maaned_loft_usd = 115.0

    brugt = float(reference.get("usage_usd") or 0.0)
    # ``range=30d`` er den nærmeste vi kommer på «denne måned». Ollama nulstiller
    # ved abonnements-cyklussen, ikke ved månedsskiftet, så tallet er et
    # OVERESTIMAT i starten af en cyklus. Det er den sikre retning: vi bremser
    # hellere for tidligt end for sent.
    procent = (brugt / maaned_loft_usd) * 100.0 if maaned_loft_usd > 0 else 0.0

    if procent >= STOP_PROCENT:
        niveau = "stop"
    elif procent >= BREMSE_PROCENT:
        niveau = "bremse"
    elif procent >= MAIL_PROCENT:
        niveau = "advarsel"
    else:
        niveau = "normal"

    svar = {
        "kendt": True,
        "niveau": niveau,
        "procent": round(procent, 1),
        "usage_usd": round(brugt, 2),
        "maaned_loft_usd": maaned_loft_usd,
        "kald": int(reference.get("kald") or 0),
        "range": reference.get("range"),
        "fra": reference.get("fra"),
        "til": reference.get("til"),
    }
    # Log kun når der faktisk skal handles. Et normalt tick skriver intet, så
    # loggen bliver et bevis på bremsen — ikke en støjstrøm man filtrerer væk.
    if niveau in {"bremse", "stop"}:
        logger.info(
            "ollama-kvote: %s — %.1f%% af $%.0f brugt ($%.2f), ikke-kritisk arbejde "
            "skrues ned til cheap-lanen",
            niveau,
            procent,
            maaned_loft_usd,
            brugt,
        )
    _cache = (nu, svar)
    return svar


def skal_bremse() -> bool:
    """Skal det ikke-kritiske arbejde skrues ned nu?

    ``False`` når kvoten er ukendt — en vagt der fejler lukket stopper
    systemet på en netværksfejl, og det er en værre fejl end den den vogter.
    """
    return kvote_status().get("niveau") in {"bremse", "stop"}


def skal_stoppe() -> bool:
    """Er der kun plads til det der holder mig i live?"""
    return kvote_status().get("niveau") == "stop"
