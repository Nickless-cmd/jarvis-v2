"""Hvad der sker EFTER en `load_more_tools`-hentning — og hvorfor det kan slukkes.

Udskilt fra `visible_runs.py` 30/9-2026 (Boy Scout: filen var 7.550 linjer).

## Prisen der skal væk

DeepSeeks præfiks er `[system][tools][beskeder]`, og cachen matcher fra
begyndelsen: **en ændring koster alt fra ændringspunktet og frem.** Værktøjs-
arrayet ligger før hele samtalen, så én ny definition kasserer historikken.
Målt tre gange 30/9-2026, uafhængigt:

* mod DeepSeeks API: én ny definition bagerst = **8.704 tokens** tabt;
* i produktion: værktøjerne skiftede 59.643 → 61.120 tegn, hit **88,0 % → 17,9 %**;
* i produktion igen: **+419 tegn → 62.672 miss**, hit 97 % → 28,3 %.

To ting gjorde arrayet ustabilt efter en hentning:

1. **fletten** — definitionen blev lagt ind i næste rundes array;
2. **lås-udvidelsen** — navnet blev lagt i `session_tool_pin`, så det holdt ved
   til næste tur. Det var med vilje (2026-09-05): ét brud er bedre end at
   tvinge en ny hentning hver tur. Men med `call_loaded_tool` er begge
   unødvendige — skemaerne står allerede i hentningens RESULTAT, altså i
   beskederne, efter cache-grænsen, hvor de koster ~0.

## Hvorfor det kan slukkes uden genstart

Vi har ingen adoptions-måling endnu: hvis modellen ikke bruger dispatcheren,
kan et hentet værktøj **ikke kaldes** — DeepSeek afviser et værktøj der ikke er
deklareret, og det er målt mod deres API, ikke antaget.

Derfor `visible_tools_frozen` i settings.json. `load_settings()` læser filen ved
HVERT kald, så den virker uden genstart. Slå den fra, og fletten og lås-
udvidelsen er tilbage præcis som før.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def frosset() -> bool:
    """Skal værktøjsarrayet holdes helt stille efter en hentning?

    Fail-safe: enhver fejl → **nej**, altså den gamle adfærd. En killswitch der
    ikke kan læses må ikke ændre noget af sig selv.
    """
    try:
        from core.runtime.settings import load_settings
        return bool(load_settings().visible_tools_frozen)
    except Exception as exc:  # et ulaeseligt flag maa ikke aendre adfaerd
        logger.debug("visible_tools_frozen kunne ikke laeses: %s", exc)
        return False


def hentede_navne(tool_results: list[dict[str, Any]] | None) -> list[str]:
    """Navnene fra `load_more_tools`-resultater i denne runde, i rækkefølge."""
    ud: list[str] = []
    for sr in tool_results or []:
        try:
            if str(sr.get("tool_name") or "") != "load_more_tools":
                continue
            for n in (sr.get("result") or {}).get("added") or []:
                if n and str(n) not in ud:
                    ud.append(str(n))
        except Exception as exc:  # en enkelt uparsbar raekke stopper ikke resten
            logger.debug("hentede_navne: sprang et resultat over: %s", exc)
    return ud


def udvid_laasen(session_id: str, navne: list[str]) -> bool:
    """Læg de hentede navne i session-låsen — med mindre arrayet er frosset.

    Returnerer om låsen blev udvidet.
    """
    if not navne or not session_id:
        return False
    if frosset():
        return False
    try:
        from core.services.session_tool_pin import extend as _extend
        _extend(str(session_id), [str(n) for n in navne])
        return True
    except Exception as exc:  # laasen maa ikke braekke turen
        logger.debug("udvid_laasen fejlede: %s", exc)
        return False


def flet_ind(
    definitions: list[dict[str, Any]] | None,
    navne: list[str],
    alle: list[dict[str, Any]] | None,
) -> list[dict[str, Any]] | None:
    """Flet de hentede definitioner ind i rundens array — med mindre frosset.

    Uændret adfærd når den ikke er frosset: kun navne der ikke allerede står i
    arrayet tilføjes, og rækkefølgen er katalogets.
    """
    if definitions is None or not navne:
        return definitions
    if frosset():
        return definitions
    findes = {
        ((d.get("function") or {}).get("name") or d.get("name") or "")
        for d in definitions
    }
    soeges = set(navne)
    ud = list(definitions)
    for d in alle or []:
        n = (d.get("function") or {}).get("name") or d.get("name") or ""
        if n in soeges and n not in findes:
            ud.append(d)
            findes.add(n)
    return ud
