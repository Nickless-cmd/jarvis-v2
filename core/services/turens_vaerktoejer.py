"""Ét værktøjssæt for HELE turen — begge trin ser det samme.

En tur har to trin. Første pas læser brugerens besked og beslutter hvad der
skal gøres; de agentiske runder udfører det. De fik hvert sit sæt:

    første pas:        `copilot_tool_pruning.select_tools_for_visible`  (48)
    agentiske runder:  `tool_router.select_tools` + `session_tool_pin`  (~119)

Og sættene var **ikke indlejrede**. Målt 30/9-2026: 77 værktøjer kunne kun
kaldes i runderne, og 6 kun i første pas — heriblandt `read_tool_result`, som
læser resultater fra andre værktøjer og manglede netop i de runder hvor
resultater læses.

Målt samtidig: **95 % af alle ture har mere end én runde** (median 9,
gennemsnit 13,2). Den lille første kasse sparer derfor noget på 5 % af turene
og tvinger en omvej i de øvrige 95 %, hvor det store array alligevel sendes fra
runde 1. Forenet sender vi ét array pr. tur i stedet for to, og prosa-turene
rammer samme varme præfiks som resten.

## Retningen er hele pointen

Foreningen går mod **routerens** sæt, ikke mod de 48. Omvendt ville første pas
sætte session-låsen til sine 48, og så fik de agentiske runder også kun 48 i
stedet for ~119 — en tavs kapabilitets-nedskæring, og præcis den forkerte vej.

## Hvorfor det ligger her og ikke i pruneren

`select_tools_for_visible` er en REN funktion af sine argumenter, og det er
værd at bevare: cache-warmeren kalder den, og den skal kunne testes uden en
router og en database. Lagde man foreningen derind, blev et DB-opslag skjult
inde i en «pruning»-funktion — og to eksisterende tests faldt på præcis det.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _navn(d: dict[str, Any]) -> str:
    return str((d.get("function") or d).get("name") or "")


def vaerktoejer_for_turen(
    alle: list[dict[str, Any]],
    *,
    user_message: str,
    session_id: str | None,
) -> list[dict[str, Any]]:
    """Værktøjerne for DENNE tur — samme sæt i begge trin.

    Uden en session (fx cache-warmeren) er svaret prunerens eget valg, præcis
    som før. Self-sikker: enhver fejl → prunerens valg, så en fejlet forening
    aldrig koster turen dens værktøjer.

    Killswitch `visible_tools_unified` læses ved HVERT kald, så den virker uden
    genstart.
    """
    from core.tools.copilot_tool_pruning import select_tools_for_visible

    eget = select_tools_for_visible(alle, user_message=user_message, session_id=session_id)
    if not session_id:
        return eget
    try:
        from core.runtime.settings import load_settings
        if not load_settings().visible_tools_unified:
            return eget
        from core.services.session_tool_pin import resolve as _pin_resolve
        from core.services.tool_router import select_tools as _router
        valg = _router(user_message=user_message, session_id=str(session_id), lane="visible")
        kandidater = (list(valg.selected_names) if not valg.fallback_used
                      else [_navn(d) for d in eget])
        navne, _kilde = _pin_resolve(str(session_id), kandidater)
        saet = set(navne)
        # `call_loaded_tool` har ingen definition i katalogets liste; pruneren
        # injicerer den. Tag den med herfra, ellers tabes dispatcheren.
        fra_eget = {_navn(d): d for d in eget}
        ud = [d for d in alle if _navn(d) in saet]
        for n in saet - {_navn(d) for d in ud}:
            if n in fra_eget:
                ud.append(fra_eget[n])
        return ud or eget
    except Exception as exc:  # en forening maa aldrig koste turen dens vaerktoejer
        logger.debug("forenet vaerktoejssaet fejlede, bruger foerste pas: %s", exc)
        return eget
