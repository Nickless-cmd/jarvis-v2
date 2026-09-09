"""Skygge for godkendelses-broen: ville den have sagt det samme?

Samme mønster som ledger- og afregnings-skyggen, af samme grund: en kontrakt
er ikke bevist ved at bestå sine egne tests. Den er bevist når den siger det
SAMME som den kode der har kørt i produktion.

## Hvorfor netop her skal det være en skygge

Det her er den vej hvert eneste godkendte værktøjskald går igennem. En fejl
her betyder enten at en godkendt handling ikke sker, eller — værre — at en
handling sker som ingen godkendte. Ingen af delene må opdages i drift.

Så broen kører ved siden af: den registrerer, beslutter og forsøger at
overtage, men dens svar **afgør ingenting**. Uenigheder logges med begge sider,
så de kan afgøres frem for at gættes.

## Den ene ting skyggen kan opdage som tests ikke kan

Om digesten er STABIL gennem den virkelige vej. Argumenterne rejser fra
værktøjets svar, gennem en dict i hukommelsen, gennem delt tilstand mellem
processer, og tilbage. Bliver de undervejs til noget der ikke er byte-lig med
sig selv — en JSON-tur, en tilføjet `_runtime`-nøgle, en ændret rækkefølge —
så vil broen afvise et kald som brugeren faktisk godkendte.

Det er præcis den slags der ser rigtigt ud i en test der bygger sit eget input.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_taellere: dict[str, int] = {"registreret": 0, "besluttet": 0, "enige": 0,
                             "uenige": 0, "fejl": 0, "sprunget_over": 0}

CACHE_NOEGLE = "approval:bridge:shadow:taellere"
_CACHE_TTL = 7 * 24 * 3600.0


def taellere() -> dict[str, int]:
    return dict(_taellere)


def _nulstil_for_tests() -> None:
    for k in _taellere:
        _taellere[k] = 0


def taellere_fra_cache() -> dict[str, int] | None:
    """Læs tællerne fra en anden proces — se `settlement_shadow` for hvorfor
    en log alene ikke rækker."""
    try:
        from core.services import shared_cache
        v = shared_cache.get(CACHE_NOEGLE)
    except Exception:
        return None
    return v if isinstance(v, dict) else None


def _gem() -> None:
    try:
        from core.services import shared_cache
        shared_cache.set(CACHE_NOEGLE, taellere(), ttl_seconds=_CACHE_TTL)
    except Exception:
        pass


def live() -> bool:
    """Eksplicit opt-in. Husets `is_enabled` er fail-open og ville tænde en
    måling ingen har besluttet — se `settlement_shadow`."""
    try:
        from core.services.central_switches import _key, shared_cache
        v = shared_cache.get(_key("approval", "bridge_shadow"))
    except Exception:
        return False
    return isinstance(v, dict) and v.get("enabled") is True


def note_requested(approval_id: str, *, tool_name: str, arguments: dict[str, Any] | None,
                   run_id: str = "", session_id: str = "") -> None:
    """Godkendelsen er bedt om. Registrér den i broen — ændrer intet."""
    if not live():
        _taellere["sprunget_over"] += 1
        return
    try:
        from core.runtime.db_approval_bridge import request
        request(approval_id, tool_name=tool_name, arguments=arguments,
                run_id=run_id, session_id=session_id)
        _taellere["registreret"] += 1
        _gem()
    except Exception:
        _taellere["fejl"] += 1
        logger.warning("approval-bridge-shadow: kunne ikke registrere %s",
                       approval_id, exc_info=True)


def note_decided(approval_id: str, *, approved: bool) -> None:
    """Mennesket har klikket."""
    if not live():
        return
    try:
        from core.runtime.db_approval_bridge import decide
        decide(approval_id, approved=approved)
        _taellere["besluttet"] += 1
        _gem()
    except Exception:
        _taellere["fejl"] += 1
        logger.warning("approval-bridge-shadow: kunne ikke beslutte %s",
                       approval_id, exc_info=True)


def note_claim(approval_id: str, *, tool_name: str, arguments: dict[str, Any] | None,
               legacy_allowed: bool) -> None:
    """Ville broen have tilladt det samme som den kørende kode?

    `legacy_allowed` er hvad der FAKTISK skete. Broens svar afgør ingenting.
    """
    if not live():
        return
    try:
        from core.runtime.db_approval_bridge import ApprovalRefused, claim, state

        # En godkendelse der blev OPRETTET før skyggen blev tændt, har ingen
        # post i broen. Uden dette tjek ville overtagelsen fejle med «ukendt
        # godkendelse» og tælle som en uenighed — en uenighed skyggen SELV
        # havde skabt.
        #
        # Det er ikke en detalje: de første målinger efter en tænding ville
        # være lutter falske uenigheder, og så lærer man at ignorere signalet
        # præcis når det begynder at virke.
        if state(approval_id) is None:
            _taellere["sprunget_over"] += 1
            _gem()
            return

        try:
            claim(approval_id, tool_name=tool_name, arguments=arguments)
            bro_tillod, grund = True, ""
        except ApprovalRefused as e:
            bro_tillod, grund = False, str(e)

        if bro_tillod == legacy_allowed:
            _taellere["enige"] += 1
        else:
            _taellere["uenige"] += 1
            # BEGGE sider og grunden — så uenigheden kan afgøres.
            logger.warning(
                "approval-bridge-shadow UENIGE id=%s tool=%s gammel=%s bro=%s grund=%r",
                approval_id, tool_name, legacy_allowed, bro_tillod, grund[:200])
        _gem()
    except Exception:
        _taellere["fejl"] += 1
        logger.warning("approval-bridge-shadow: kunne ikke sammenligne %s",
                       approval_id, exc_info=True)


def note_settled(approval_id: str, *, ok: bool) -> None:
    """Luk den post skyggen selv aabnede.

    Set paa CT105 efter foerste taending: seks overtagelser stod som
    `dispatching` og blev aldrig lukket. Det er ikke kosmetik — `dispatching`
    BETYDER «udfaldet er ukendt», og `expire_stale` roerer den aldrig netop
    derfor. Uden denne lukning ville hver eneste skygge-maaling se ud som et
    nedbrud, og saa er tilstanden ubrugelig praecis naar broen skal haandhaeve.
    """
    if not live():
        return
    try:
        from core.runtime.db_approval_bridge import settle, state
        if state(approval_id) is None:
            return
        settle(approval_id, ok=ok)
    except Exception:
        _taellere["fejl"] += 1
        logger.warning("approval-bridge-shadow: kunne ikke lukke %s",
                       approval_id, exc_info=True)
