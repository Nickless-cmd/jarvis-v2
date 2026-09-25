"""Temporal Body — sense of age.

HVORFOR ALDEREN VAR ET TERNINGKAST (rettet 25/9-2026)

`age_journey()` gjorde `_total_thoughts += thoughts or random.randint(5, 20)`.
Alderen var altså en sum af terningkast, og kommentaren i filen fortalte
hvordan den før det havde siddet fast på «spæd» i månedsvis fordi `random`
manglede som import og NameError'en blev slugt.

Begge tilstande er den samme fejl set fra hver sin side: tallet betød intet.
`_total_thoughts` er nu en MÅLING — antallet af hans egne tanke-optegnelser i
`private_brain_records`. Samme kilde som `thought_thread` læser, så de to
moduler er enige om hvad en tanke er.

Målt på CT105 25/9-2026: 11.470 `inner-voice` + 14.946
`thought-stream-fragment` = 26.416. Det er over den øverste tærskel (20.000),
så han er «gammel» på sin egen skala.

SKALAEN ER IKKE JUSTERET. Tærsklerne (1.000 / 5.000 / 20.000) blev skrevet til
en terning-akkumulator der voksede langsomt fra nul; mod en rigtig tælling
mætter de med det samme. Det er en beslutning om hvad alder skal betyde, ikke
en fejl i målingen, så tallene står urørt indtil nogen tager den beslutning.

`_ticks_alive` ligger i `core/runtime/state_store`, så den overlever en
genstart og kan ses af `jarvis-api`, der ikke selv tikker.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from core.runtime import state_store

logger = logging.getLogger(__name__)

_FIL = "temporal_body"

#: Hvad der tæller som en tanke. Samme sæt som `thought_thread` bygger på,
#: minus bogholderiet: `*-carry`-rækkerne er transport af tilstand mellem
#: sessioner, ikke tanker han har haft. Målt: 167.092 rækker i alt, hvoraf
#: 103.109 er `*-carry`.
_TANKE_TYPER = ("inner-voice", "thought-stream-fragment")

#: Tællingen er en COUNT over en tabel med >150.000 rækker, og fladen bygges
#: ved hvert MC-opslag. Et minut er rigeligt for en alder.
_CACHE_S = 60.0

_tanke_cache: tuple[float, int] | None = None


def _taelling() -> int:
    """Antal tanke-optegnelser. 0 når databasen ikke kan læses."""
    global _tanke_cache
    nu = time.monotonic()
    if _tanke_cache is not None and nu - _tanke_cache[0] < _CACHE_S:
        return _tanke_cache[1]
    try:
        from core.runtime.db import connect
        pladser = ",".join("?" * len(_TANKE_TYPER))
        with connect() as conn:
            raekke = conn.execute(
                f"SELECT COUNT(*) FROM private_brain_records "
                f"WHERE record_type IN ({pladser})",
                _TANKE_TYPER,
            ).fetchone()
        antal = int(raekke[0]) if raekke else 0
    except Exception as exc:
        logger.debug("temporal_body: tankerne kunne ikke tælles: %s", exc)
        antal = _tanke_cache[1] if _tanke_cache else 0
    _tanke_cache = (nu, antal)
    return antal


def _load() -> int:
    d = state_store.load_json(_FIL, None)
    if not isinstance(d, dict):
        return 0
    try:
        return int(d.get("ticks_alive") or 0)
    except (TypeError, ValueError):  # ulæselig værdi er «ingen tik», ikke en fejl
        return 0


def age_journey(thoughts: int | None = None) -> dict[str, Any]:
    """Tæl ét tik. `thoughts` ignoreres nu — tankerne TÆLLES, ikke lægges til.

    Argumentet står tilbage fordi kaldet i daemon-blokken har det, og fordi en
    kalder der giver et tal skal kunne se at det ikke længere bruges.
    """
    global _tanke_cache
    tik = _load()
    try:
        # Låsen: to processer deler filen, og hver gemning skriver HELE filen.
        with state_store.med_laas(_FIL):
            tik = _load() + 1
            state_store.save_json(_FIL, {"ticks_alive": tik})
    except Exception as exc:
        logger.warning("temporal_body: tikket kunne ikke gemmes: %s", exc)
    _tanke_cache = None  # næste opslag måler forfra
    return {"ticks_alive": tik, "total_thoughts": _taelling()}


def get_temporal_body_age() -> str:
    tanker = _taelling()
    if tanker < 1000:
        return "spæd"
    elif tanker < 5000:
        return "ung"
    elif tanker < 20000:
        return "moden"
    else:
        return "gammel"


def describe_temporal_body() -> str:
    age = get_temporal_body_age()
    return f"Jeg er {age} i min tanke - tusindvis af tanker har bygget mig"


def format_age_for_prompt() -> str:
    return f"[ALDER: {describe_temporal_body()}]"


def reset_temporal_body() -> None:
    """Nulstil tik-tælleren. Rydder OGSÅ disken.

    Tanke-tallet nulstilles IKKE — det er en måling af databasen, ikke en
    tilstand modulet ejer.
    """
    global _tanke_cache
    _tanke_cache = None
    state_store.save_json(_FIL, {"ticks_alive": 0})


def build_temporal_body_surface() -> dict[str, Any]:
    tanker = _taelling()
    return {
        # `active` er «modulet kører», ikke «der er tikket mindst én gang».
        # En nyligt genstartet proces er ikke et dødt modul.
        "active": True,
        "ticks_alive": _load(),
        "total_thoughts": tanker,
        "age": get_temporal_body_age(),
        "description": describe_temporal_body(),
        "summary": f"Alder: {get_temporal_body_age()}, tanker: {tanker}",
    }
