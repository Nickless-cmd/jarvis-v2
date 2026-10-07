"""core/services/peak_varsel_daemon.py

Varsel 15 minutter før DeepSeeks myldretid åbner — man-fre, kun dagvinduet.

DeepSeek fakturerer det DOBBELTE i myldretiden. Bjørn 30/9-2026: «lad os lave
et eller andet der minder os om peak hours lige før». Badgen i prompt-halen
(``core/services/peak_hours.py``) klarer «mens vi er i det» — men et badge
findes kun NÅR en tur sker. Kører der ingen tur kl. 07:45, sker der ingenting.
Derfor denne: en notifikation uden for turen.

HVORFOR EN DAEMON OG IKKE EN ``recurring_task``
    ``recurring_tasks`` fyrer via ``start_autonomous_run()`` — altså en HEL
    LLM-tur for at sende ét push. Her er nul tokens: daemonen kalder den
    kanoniske router direkte, som lægger feed-rækken og sender pushet.

HVORFOR ÅBNINGEN BEREGNES OG IKKE ER ET FAST KLOKKESLET
    Vinduet er defineret i UTC (``MYLDRE_VINDUER``), men quiet hours regnes i
    dansk lokal tid. Om sommeren åbner dagvinduet 08:00 dansk — et 15-min
    varsel lander 07:45, uden for quiet hours (23:00-07:00). Om vinteren åbner
    det 07:00 dansk, så varslet lander 06:45 — MIDT i quiet hours. Et fast
    klokkeslet ville derfor blive parkeret i quiet-hours-køen og leveret
    FOR SENT, når vinduet allerede var åbnet. Det er samme DST-fælde som
    badgen blev bidt af, og løsningen er den samme: regn i UTC, oversæt kun
    til visning. Varslet sendes desuden med ``importance="critical"``, som
    med vilje omgår quiet hours — det er tidskritisk, og et varsel der kommer
    for sent er ikke et varsel.

KUN DAGVINDUET
    Myldretiden er to vinduer: UTC 01-04 og 06-10. Det første er 03-04 dansk —
    midt om natten. Der er ingen at minde, så daemonen ser kun dagvinduet
    (``DAG_VINDUE_FRA_UTC``). Nat-vinduet gælder stadig for prisen.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Final
from zoneinfo import ZoneInfo

from core.runtime.db import get_runtime_state_value, set_runtime_state_value
from core.services.llm_pricing import MYLDRE_VINDUER
from core.services.peak_hours import (
    VARSEL_MINUTTER,
    naeste_vindue_start,
    som_utc,
)

_log = logging.getLogger(__name__)

#: `VARSEL_MINUTTER` importeres fra `peak_hours` — se begrundelsen der. Her
#: stod indtil 1/10-2026 en EGEN konstant med samme navn og en anden vaerdi,
#: saa badgen og notifikationen ikke kunne vaere enige.

#: Dagvinduet er det der åbner kl. 06 UTC (08 dansk om sommeren, 07 om vinteren).
#: Nat-vinduet (01-04 UTC) har ingen at minde.
DAG_VINDUE_FRA_UTC: Final[int] = 6

#: ``runtime_state_kv``-nøglen der husker hvilket vindue vi sidst varslede om.
_KV_KEY: Final[str] = "peak_varsel_sidst_vindue"

_DANSK = ZoneInfo("Europe/Copenhagen")


def _vindue_slut(aabning: datetime) -> datetime:
    """Vinduets sluttid, læst fra ``MYLDRE_VINDUER`` — ikke et gæt på 4 timer."""
    for fra, til in MYLDRE_VINDUER:
        if fra == aabning.hour:
            return aabning + timedelta(hours=til - fra)
    return aabning + timedelta(hours=4)


def _allerede_varslet(aabning: datetime) -> bool:
    """Har vi allerede sendt varsel for netop dette vindue?"""
    gemt = get_runtime_state_value(_KV_KEY, "")
    return str(gemt or "").strip() == aabning.isoformat()


def _marker_varslet(aabning: datetime) -> None:
    set_runtime_state_value(_KV_KEY, aabning.isoformat())


def _varsel_tekst(aabning: datetime) -> tuple[str, str]:
    """(titel, body) til både feed-rækken og pushet."""
    aabner = aabning.astimezone(_DANSK)
    lukker = _vindue_slut(aabning).astimezone(_DANSK)
    titel = f"⏳ Myldretid om {VARSEL_MINUTTER} min"
    body = (
        f"DeepSeek koster 2× fra kl. {aabner:%H:%M} dansk.\n"
        "Tungt arbejde der kan klares nu, bør klares nu — "
        f"ellers vent til {lukker:%H:%M}."
    )
    return titel, body


def tick_peak_varsel_daemon(now: datetime | str | None = None) -> dict:
    """Ét tick. Sender højst ét varsel pr. vindue. Aldrig i weekenden.

    Returnerer en lille dict til ``record_daemon_tick`` — den skal kunne ses
    i Centralen uden at skulle grave i logs.
    """
    nu = som_utc(now)

    # Weekend: der er ingen myldretid. Tjekkes FØRST, for `naeste_vindue_start`
    # springer weekenden over og ville ellers fyre lørdag morgen for mandag.
    if nu.weekday() >= 5:
        return {"fired": False, "reason": "weekend"}

    aabning = naeste_vindue_start(nu)
    if aabning is None:
        return {"fired": False, "reason": "intet-vindue"}

    if aabning.hour != DAG_VINDUE_FRA_UTC:
        return {"fired": False, "reason": "ikke-dagvinduet",
                "aabning": aabning.isoformat()}

    minutter_til = (aabning - nu).total_seconds() / 60.0
    if minutter_til > VARSEL_MINUTTER:
        return {"fired": False, "reason": "for-tidligt",
                "minutter_til": round(minutter_til)}

    if _allerede_varslet(aabning):
        return {"fired": False, "reason": "allerede-varslet",
                "aabning": aabning.isoformat()}

    titel, body = _varsel_tekst(aabning)
    levering = _send_varsel(titel, body)
    # Markøren sættes OGSÅ når leveringen fejler: et forsøg pr. vindue. Ellers
    # ville et vedvarende transportproblem give ét push hvert femte minut.
    _marker_varslet(aabning)

    return {"fired": True, "minutter_til": round(minutter_til),
            "aabning": aabning.isoformat(), "delivery": levering}


def _send_varsel(titel: str, body: str) -> dict:
    """Send gennem den kanoniske router — feed-række + mobil push i ét kald."""
    from core.identity.owner_resolver import get_owner_discord_id
    from core.services.notification_router import route_proactive_notification

    uid = (get_owner_discord_id() or "").strip()
    if not uid:
        _log.warning("peak_varsel: ingen owner-uid — kan ikke sende varsel")
        return {"delivered": False, "channel": "no-owner"}

    # `critical` omgår quiet hours med vilje: om vinteren lander varslet 06:45
    # dansk, inde i quiet hours (23:00-07:00), og ville ellers blive køet til
    # 07:00 — præcis når vinduet åbner, altså for sent.
    return route_proactive_notification(
        uid,
        "reminder",
        {"title": titel, "body": body},
        importance="critical",
    )
