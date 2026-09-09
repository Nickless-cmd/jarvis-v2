"""Skygge for skema-kontrakten — ville den have afvist noget den ikke burde?

Samme moenster som ledger-, afregnings- og godkendelses-skyggen, af samme
grund: en kontrakt er ikke bevist ved at bestaa sine egne tests.

## Hvorfor netop denne skal maales foer den haandhaever

Maalingen paa 20.170 aegte kald fandt begge fejl-retninger paa én gang.

Hullet: `write_memory_topic` kaldt 17 gange uden `title` og med `content` i
stedet for `body` — vaerktoejet skrev tomme filer og svarede `confirmed:
true`. 14 af 100 kuraterede hukommelsesfiler ligger paa 0 bytes.

Faren: `recall_memories` kaldt med `modalities: ["somatic"]`, som skemaets
enum ikke tillader — og som gav 10 rigtige resultater, fordi koden accepterer
enhver streng. Dér er SKEMAET forkert.

Historiske tal kan kun sige noget om historien. Skyggen siger hvad der sker
NU, paa de kald der faktisk koeres, foer noget bliver afvist for alvor.
"""
from __future__ import annotations

import collections
import logging
from typing import Any

logger = logging.getLogger(__name__)

_taellere: dict[str, int] = {"maalt": 0, "rene": 0, "haarde": 0, "bloede": 0,
                             "ukendt_vaerktoej": 0, "fejl": 0}
_pr_vaerktoej: collections.Counter = collections.Counter()

CACHE_NOEGLE = "tools:contract:shadow:taellere"
_CACHE_TTL = 7 * 24 * 3600.0


def taellere() -> dict[str, int]:
    return dict(_taellere)


def pr_vaerktoej() -> dict[str, int]:
    return dict(_pr_vaerktoej)


def _nulstil_for_tests() -> None:
    for k in _taellere:
        _taellere[k] = 0
    _pr_vaerktoej.clear()
    _sidst_gemt.clear()
    try:
        from core.services import shared_cache
        shared_cache.delete(CACHE_NOEGLE)
    except Exception:
        pass


def taellere_fra_cache() -> dict[str, Any] | None:
    try:
        from core.services import shared_cache
        v = shared_cache.get(CACHE_NOEGLE)
    except Exception:
        return None
    return v if isinstance(v, dict) else None


_sidst_gemt: dict[str, int] = {}


def _gem() -> None:
    """Deltaer, ikke totaler — se `shadow_counters` for hvorfor."""
    from core.services.shadow_counters import flet
    flet(CACHE_NOEGLE, taellere(), _sidst_gemt,
         ekstra={"_top": dict(_pr_vaerktoej.most_common(20))}, ttl=_CACHE_TTL)


def live() -> bool:
    """Eksplicit opt-in. Husets `is_enabled` er fail-open og ville taende en
    maaling ingen har besluttet."""
    try:
        from core.services.central_switches import _key, shared_cache
        v = shared_cache.get(_key("tools", "contract_shadow"))
    except Exception:
        return False
    return isinstance(v, dict) and v.get("enabled") is True


def haandhaever() -> bool:
    """Skal HAARDE brud faktisk afvise kaldet?

    Adskilt fra `live()` med vilje: skyggen skal kunne maale i dagevis uden at
    haandhaeve, og haandhaevelsen skal kunne slaas fra uden at maalingen stopper.
    """
    try:
        from core.services.central_switches import _key, shared_cache
        v = shared_cache.get(_key("tools", "contract_enforce"))
    except Exception:
        return False
    return isinstance(v, dict) and v.get("enabled") is True


def observe(tool_name: str, arguments: dict[str, Any] | None) -> list:
    """Maal ét kald. Returnerer bruddene — men afgoer intet selv.

    Kaster aldrig: en maaling der kan vaelte et vaerktoejskald er ikke en
    maaling, den er en ny fejlkilde.
    """
    if not live():
        return []
    try:
        from core.tools.tool_schema_contract import kendt, violations

        _taellere["maalt"] += 1
        if not kendt(tool_name):
            _taellere["ukendt_vaerktoej"] += 1
            _gem()
            return []

        brud = violations(tool_name, arguments)
        if not brud:
            _taellere["rene"] += 1
            _gem()
            return []

        h = [b for b in brud if b.haard]
        if h:
            _taellere["haarde"] += 1
            _pr_vaerktoej[f"{tool_name}/haard"] += 1
            # BEGGE sider: hvad manglede, og hvad kaldet faktisk havde med.
            logger.warning(
                "tool-contract-shadow HAARD tool=%s mangler=%s havde=%s",
                tool_name, [b.besked for b in h[:4]],
                sorted(str(k) for k in (arguments or {}) if not str(k).startswith("_")))
        else:
            _taellere["bloede"] += 1
            _pr_vaerktoej[f"{tool_name}/{brud[0].art}"] += 1
            logger.info("tool-contract-shadow bloed tool=%s art=%s %s",
                        tool_name, brud[0].art, brud[0].besked[:160])
        _gem()
        return brud
    except Exception:
        _taellere["fejl"] += 1
        logger.warning("tool-contract-shadow: kunne ikke maale %s", tool_name,
                       exc_info=True)
        return []
