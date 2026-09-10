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

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _opsloegere(context: Any) -> tuple[Any, Any, str]:
    """Vaelg den maskine paastanden skal efterproeves PAA.

    Et barn med `execution_target=workstation` laeser filer paa Bjoerns
    maskine over broen. Uden opslags-funktioner opløste vi mod CONTAINEREN og
    fandt en fil der LIGNEDE den agenten laeste — begge maskiner har
    `/media/projects/jarvis-v2`. Samme sti, forskellig maskine; i dag var de
    identiske, saa det gik ved et tilfaelde.

    Vi falder IKKE tilbage til containeren naar broen ikke svarer. Det er
    netop den forkerte maskine, og et vaern der spoerger den forkerte maskine
    er vaerre end et der siger «jeg kunne ikke afgoere det».
    """
    ctx: dict[str, Any] = {}
    if isinstance(context, str) and context.strip():
        try:
            ctx = json.loads(context) or {}
        except Exception:
            ctx = {}
    elif isinstance(context, dict):
        ctx = dict(context)
    if str(ctx.get("execution_target") or "").strip().lower() != "workstation":
        return None, None, "container"
    bruger = str(ctx.get("user_id") or "").strip()
    if not bruger:
        return None, None, "uden-bro"
    try:
        # ÉT sted ejer bro-ruten (se `_bro_kontrol`). En kopi her ville vaere
        # den femte udgave af samme spoergsmaal.
        from core.tools.simple_tools_explore import _bro_kontrol
        findes, linje = _bro_kontrol({
            "_runtime_user_id": bruger,
            "_runtime_session_id": str(ctx.get("session_id") or ""),
        })
    except Exception:
        logger.debug("kunne ikke bygge bro-opsloegere", exc_info=True)
        return None, None, "uden-bro"
    return findes, linje, "workstation"


def tjek_rapport(text: str, *, agent_id: str = "", role: str = "",
                 run_id: str = "", context: Any = None) -> dict[str, Any]:
    """Efterproev en barne-rapports filstier og linjenumre. Kaster ALDRIG.

    Returnerer `{"kontrolleret": n, "holder": bool, "fejl": [...]}` — samme
    form som `tjek_paastande`, saa den kan gemmes raat paa runnet.
    """
    # `ikke-spurgt`: uden tekst — eller hvis vaernet selv faldt — spurgte vi
    # ingen maskine. At skrive «container» ville vaere en lille loegn i netop
    # den post der skal sige hvem der blev spurgt.
    tom = {"kontrolleret": 0, "holder": True, "fejl": [],
           "bevis": "intet-bevis", "kontrolleret_mod": "ikke-spurgt"}
    try:
        if not str(text or "").strip():
            return tom
        from core.services.explore_claim_check import tjek_paastande
        _findes, _linje, _mod = _opsloegere(context)
        if _mod == "uden-bro":
            # Barnet laeste paa Bjoerns maskine; vi kan ikke naa den. At slaa
            # op i containeren ville give et tal om den FORKERTE maskine — og
            # netop dét er fejlen. Saa vi doemmer ikke.
            #
            # `holder: None`, ikke True. «Vi kunne ikke doemme» og «vi doemte
            # og det holdt» maa ikke dele boolean — huset har allerede ordet
            # fra `process_identity.lever()`, hvor None betyder at kalderen
            # skal lade vaere. Uden efterproevelige paastande er `True` stadig
            # rigtigt: dér blev der intet PAASTAAET. Her blev der paastaaet
            # noget vi ikke kunne naa. (Jarvis' indvending.)
            return {**tom, "kontrolleret_mod": "uden-bro", "holder": None}
        dom = tjek_paastande(str(text), findes_fn=_findes, linje_fn=_linje)
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

    # `holder: True` med `kontrolleret: 0` laeser som «bestaaet». Uden `bevis`
    # kan raekken ikke skelne «vi efterproevede alt» fra «vi doemte intet» —
    # samme sammenblanding som vaerktoejet selv havde.
    #
    # Og `kontrolleret_mod` siger HVILKEN maskine der blev spurgt. To tal der
    # svarer paa hvert sit spoergsmaal er til at leve med, hvis de siger hvad
    # de er.
    return {"kontrolleret": kontrolleret, "holder": holder, "fejl": fejl[:8],
            "bevis": str(dom.get("bevis") or "intet-bevis"),
            "indhold_bekraeftet": int(dom.get("indhold_bekraeftet") or 0),
            "kontrolleret_mod": _mod}
