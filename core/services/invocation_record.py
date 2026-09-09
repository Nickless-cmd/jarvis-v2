"""Durabel invokations-tilstand for kald ingen bliver spurgt om.

Fase 3, K3: «`prepared` commits before dispatch».

## Hvorfor kun NOGLE kald

MÅLT 9/9-2026: 1.086 værktøjskald i døgnet. De to mest kaldte er `operator_bash`
og `bash` — tilsammen 60% — og langt de fleste af dem er LÆSNINGER. En
DB-skrivning pr. `ls` ville være nøjagtig den samme fejl som en tråd pr.
følelses-signal, som kostede lås-strid på brugerens egen besked tidligere i dag.

Så: kun kald der faktisk ÆNDRER noget.

Godkendelses-krævende kald har allerede en post gennem broen. Det der manglede
var mellemklassen — auto-godkendte kald der stadig skriver, som en
workspace-fil. De havde ingen post overhovedet, og et nedbrud dér efterlod en
ægte ukendt tilstand: skete skrivningen, eller gjorde den ikke?

## Den må aldrig kunne vælte kaldet den beskriver

Registreringen er observabilitet. Fejler den, sker skrivningen alligevel — men
det siges højt, for en durabel tilstand der stille holder op med at blive
skrevet, er værre end ingen: man tror man kan rekonstruere, og man kan ikke.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_taellere: dict[str, int] = {"forberedt": 0, "afsendt": 0, "afsluttet": 0, "fejl": 0}


def taellere() -> dict[str, int]:
    return dict(_taellere)


def _nulstil_for_tests() -> None:
    for k in _taellere:
        _taellere[k] = 0
    _mislykkede.clear()


@contextmanager
def recorded(tool_name: str, arguments: dict[str, Any] | None, *,
             run_id: str = "", session_id: str = ""):
    """Omslut et MUTERENDE kald med prepared → dispatching → completed/failed.

    Bruges som:

        with recorded("write_file", args):
            skriv_filen()

    Et nedbrud undervejs efterlader tilstanden `dispatching`, hvilket betyder
    «udfaldet er ukendt» — til forskel fra `prepared`, som betyder «det skete
    aldrig». Dét er hele grunden til at posten findes.
    """
    iid = f"inv-{uuid4().hex}"
    forberedt = False

    # K7: gentager dette kald noget der allerede efterlod et UKENDT udfald?
    # Her SIGES det kun. Registreringen maa aldrig blokere et kald — men den
    # maa heller ikke tie om at skrivningen maaske sker for anden gang.
    try:
        from core.services.retry_admissibility import advar_hvis_gentagelse
        advar_hvis_gentagelse(tool_name, arguments)
    except Exception:
        pass
    try:
        from core.runtime.db_approval_bridge import claim, prepare
        prepare(iid, tool_name=tool_name, arguments=arguments,
                run_id=run_id, session_id=session_id)
        _taellere["forberedt"] += 1
        claim(iid, tool_name=tool_name, arguments=arguments)
        _taellere["afsendt"] += 1
        forberedt = True
    except Exception:
        # Kaldet fortsætter. Men ikke tavst: en durabel tilstand der stille
        # holder op med at blive skrevet, er værre end ingen.
        _taellere["fejl"] += 1
        logger.warning("invocation_record: kunne ikke registrere %s — kaldet "
                       "koerer alligevel, men uden durabel tilstand", tool_name,
                       exc_info=True)

    try:
        yield iid
    except Exception:
        if forberedt:
            _afslut(iid, ok=False)
        raise
    else:
        if forberedt and iid not in _mislykkede:
            _afslut(iid, ok=True)
        _mislykkede.discard(iid)


_mislykkede: set[str] = set()


def markaer_mislykket(iid: str) -> None:
    """Sig at kaldet fejlede UDEN at kaste.

    Værktøjer over bro-grænsen returnerer en fejl-dict frem for at kaste. Uden
    dette ville et mislykket operator-kald blive afsluttet som `completed`, og
    så beskriver posten ikke det den er til for.
    """
    if not iid:
        return
    _mislykkede.add(iid)
    _afslut(iid, ok=False)


def _afslut(iid: str, *, ok: bool) -> None:
    try:
        from core.runtime.db_approval_bridge import settle
        settle(iid, ok=ok)
        _taellere["afsluttet"] += 1
    except Exception:
        _taellere["fejl"] += 1
        logger.warning("invocation_record: kunne ikke afslutte %s — tilstanden "
                       "staar som 'dispatching' (udfald ukendt)", iid, exc_info=True)
