"""Dedikeret vækker-tråd: fyr forfaldne vækninger inden for sekunder (12/11-2026).

## Hvorfor

Vækninger blev fyret af jobbet `wakeup_dispatch`, som `periodic_jobs_scheduler`
køsætter hvert 60. sekund — og den hænger selv på heartbeatens ~30 s-poll og
jobkøen. Målt på CT105: dagens vækninger fyrede 3-59 s efter planlagt tid (median
32 s). En kortere kadence i `_SCHEDULE` ændrer intet, fordi opløsningen er pollens.

## Hvad tråden gør

Hvert `INTERVAL_S` sekund spørger den `self_wakeup.forfaldne_ider()` (ét billigt
JSON-læs) og kalder `dispatch_due_wakeups()` KUN når noget er forfaldent. Jobbet i
`_SCHEDULE` bliver som sikkerhedsnet — dispatcheren er idempotent
(`dispatched`-flaget og `_dispatch_lock`), så de to kan ikke aflevere det samme.

## Tråden må ikke kunne spamme

Kan en post ikke afsluttes (fx fejler `marker_dispatch`), står den ved at være
forfalden, og tråden ville aflevere den hvert 5. sekund (nudge-push inklusive). Ser
den samme mængde forfaldne id'er `MAKS_GENTAGELSER` gange i træk, bakker den af til
`BAKKE_AF_S`. En ny post nulstiller tælleren.

Kun runtime-processen starter den (`runtime_services_enabled`): det er dér
dispatcheren og indbakke-vækkeren bor.
"""
from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

#: Hvor ofte tråden kigger efter noget forfaldent.
INTERVAL_S = 5.0
#: Hvor mange gange i træk den samme mængde må ses før tråden bakker af.
MAKS_GENTAGELSER = 3
#: Ventetid når tråden bakker af.
BAKKE_AF_S = 60.0

_traad: threading.Thread | None = None
_stop = threading.Event()
_laas = threading.Lock()


@dataclass(frozen=True)
class Tik:
    """Resultatet af ét tik: hvor længe der ventes, og hvad næste tik skal huske."""

    naeste_ventetid_s: float
    tilstand: tuple[frozenset[str], int]


def tik(
    forfaldne: Callable[[], set[str]],
    dispatch: Callable[[], object],
    *,
    forrige: tuple[frozenset[str], int],
) -> Tik:
    """Ét tik, uden tråd og ur — så det kan testes direkte."""
    ider = frozenset(forfaldne())
    if not ider:
        return Tik(INTERVAL_S, (frozenset(), 0))
    sidste_ider, gentagelser = forrige
    gentagelser = gentagelser + 1 if ider == sidste_ider else 1
    try:
        dispatch()
    except Exception:  # noqa: BLE001 — en fejlet dispatch må ikke dræbe tråden
        logger.warning("wakeup_ticker: dispatch fejlede", exc_info=True)
    venter = BAKKE_AF_S if gentagelser > MAKS_GENTAGELSER else INTERVAL_S
    if venter == BAKKE_AF_S:
        logger.warning(
            "wakeup_ticker: samme %d vækning(er) forfaldne %d gange i træk — bakker af %ds",
            len(ider), gentagelser, int(BAKKE_AF_S),
        )
    return Tik(venter, (ider, gentagelser))


def _loop() -> None:
    from core.services.self_wakeup import forfaldne_ider
    from core.services.wakeup_dispatcher import dispatch_due_wakeups

    tilstand: tuple[frozenset[str], int] = (frozenset(), 0)
    while not _stop.is_set():
        res = tik(forfaldne_ider, dispatch_due_wakeups, forrige=tilstand)
        tilstand = res.tilstand
        _stop.wait(res.naeste_ventetid_s)


def start_wakeup_ticker() -> bool:
    """Start tråden. Idempotent: kører den allerede, returneres `True` uden en ny."""
    global _traad
    with _laas:
        if _traad is not None and _traad.is_alive():
            return True
        _stop.clear()
        _traad = threading.Thread(target=_loop, name="wakeup-ticker", daemon=True)
        _traad.start()
    logger.info("wakeup_ticker: startet (interval %.0fs)", INTERVAL_S)
    return True


def stop_wakeup_ticker() -> None:
    global _traad
    _stop.set()
    with _laas:
        traad, _traad = _traad, None
    if traad is not None and traad.is_alive():
        traad.join(timeout=2.0)
