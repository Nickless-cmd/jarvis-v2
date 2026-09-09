"""Hver shell-sti skal SIGE om den er indespaerret — Fase 3, K10.

«persistent and one-shot shell paths obey the same policy contract.»

Maalt 9/9-2026: kun ÉN af fire shell-indgange sagde noget som helst om
indespaerring. `bash` rapporterede paa begge sine grene; `bash_session_run`,
`operator_bash` og `operator_bash_session_run` rapporterede INTET — og alle
tre kan modellen kalde direkte, altsaa uden om det ene sted der rapporterede.

## Hvad dette modul goer, og hvad det ikke goer

Det AENDRER ingen politik. Den vedvarende shell bliver ikke indespaerret her,
og operator-kanalen bliver ikke lukket ned. Begge er Bjoerns vej udenom
systemet, og de staar urort.

Det der lukkes, er at de tier. Forskellen mellem «ikke indespaerret» og
«troede den var det» er hele forskellen paa en aaben doer og en man ikke vidste
var aaben — og en taendt sandkasse saa indtil nu ud som om den daekkede alle
shell-veje, mens tre af fire gik udenom uden at naevne det.
"""
from __future__ import annotations

from typing import Any

# Den vedvarende, delte shell: én proces holder cd/env i live paa tvaers af
# kald, saa en per-kommando-indespaerring ville skulle pakke en shell der
# allerede koerer. Det er en egenskab ved stien, ikke en fejl.
VEDVARENDE = ("vedvarende delt shell — kan ikke indespaerres pr. kommando; "
              "kun engangs-stien kan")

# Operator-kanalen udfoerer paa Bjoerns EGEN maskine over broen. Containerens
# bwrap siger intet om den; at rapportere «indespaerret» ville vaere forkert,
# og at tie ville vaere vaerre.
OPERATOR = ("koerer paa operatorens egen maskine over broen — containerens "
            "sandkasse gaelder ikke der")


def rapport(grund: str) -> dict[str, Any] | None:
    """Byg rapporten — eller None naar der ikke er noget at sige.

    Er sandkassen slukket, er «ikke indespaerret» ikke en oplysning; det er
    standarden. Rapporten findes for det tilfaelde hvor nogen TROR den er
    daekket.
    """
    try:
        from core.services.bash_sandbox import is_available, is_enabled
        if not is_enabled():
            return None
        return {"requested": True, "actual": False, "honored": False,
                "available": is_available(), "enabled": True, "reason": grund}
    except Exception:
        return None


def vedhaeft(svar: Any, grund: str) -> Any:
    """Saet rapporten paa et svar. Roerer intet andet, kaster aldrig."""
    try:
        if not isinstance(svar, dict) or "confinement" in svar:
            return svar
        r = rapport(grund)
        if r is not None:
            svar["confinement"] = r
    except Exception:
        pass
    return svar
