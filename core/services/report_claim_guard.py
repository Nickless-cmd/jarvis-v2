"""Efterproev det et barn PAASTAAR — Fase 6.

Raadet foreslog det selv. `architecture-fixer` skrev at subagent-runtime'en kan
tvinge kilde-citater og afvise rapporter uden verificerbare referencer, og at
det er «loesbart ved seamen, ikke en iboende skaebne».

## Hvad der allerede fandtes, og hvad der manglede

`explore_claim_check.tjek_paastande` slaar filstier og linjenumre op i kilden
og siger om de holder. Modulnavnet er explore-specifikt; funktionen er det
ikke. Den var bare kun koblet paa `explore`.

Derfor kunne et hvilket som helst ANDET barn levere en rapport med opdigtede
filstier uden at nogen saa det. De tre raadsmedlemmer der selv skrev
«commit-hash a3f7c6d8 findes ikke i repoet» gjorde det af egen drift — ikke
fordi runtime'en bad dem om det.

## Hvorfor den RAPPORTERER og ikke afviser

Modulet doemmer ikke et svar det ikke kan efterproeve: uden efterproevelige
paastande er dommen «holder». At afvise paa FRAVAER af referencer ville ramme
enhver ren prosa-rapport — og de fleste raadspositioner er prosa.

Det der er farligt, er en paastand der kan efterproeves og er FALSK. Den siges
nu hoejt og gemmes paa runnet, saa den kan ses bagefter i stedet for at blive
troet.

Afvisning er naeste skridt, og den skal hvile paa tal fra denne rapportering —
ikke paa en formodning om hvor tit det sker.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def tjek_rapport(text: str, *, agent_id: str = "", role: str = "",
                 run_id: str = "") -> dict[str, Any]:
    """Efterproev en barne-rapports filstier og linjenumre. Kaster ALDRIG.

    Returnerer `{"kontrolleret": n, "holder": bool, "fejl": [...]}` — samme
    form som `tjek_paastande`, saa den kan gemmes raat paa runnet.
    """
    tom = {"kontrolleret": 0, "holder": True, "fejl": []}
    try:
        if not str(text or "").strip():
            return tom
        from core.services.explore_claim_check import tjek_paastande
        dom = tjek_paastande(str(text))
    except Exception:
        logger.debug("report_claim_guard: kunne ikke efterproeve %s",
                     agent_id, exc_info=True)
        return tom

    kontrolleret = int(dom.get("kontrolleret") or 0)
    fejl = [str(f) for f in (dom.get("fejl") or [])]
    holder = bool(dom.get("holder", True))

    if kontrolleret and not holder:
        # DET er signalet. En rapport der citerer noget der ikke findes, er
        # ikke en daarlig rapport — den er en opdigtet en.
        logger.warning(
            "barne-rapport med FALSKE referencer: agent=%s role=%s run=%s "
            "kontrolleret=%d fejl=%s",
            agent_id or "?", role or "?", run_id or "?", kontrolleret, fejl[:4])
        try:
            from core.services.central_core import central
            central().observe({
                "cluster": "agents", "nerve": "child_report_unverifiable",
                "agent_id": str(agent_id or ""), "role": str(role or ""),
                "run_id": str(run_id or ""),
                "kontrolleret": kontrolleret, "fejl": fejl[:4],
            })
        except Exception:
            pass

    return {"kontrolleret": kontrolleret, "holder": holder, "fejl": fejl[:8]}
