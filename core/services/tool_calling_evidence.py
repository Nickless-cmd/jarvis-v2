"""Hvilke modeller KALDER faktisk vaerktoejer — maalt, ikke antaget.

`egnede_modeller` har en `follows`-port, men «foelger instruktioner» er ikke
det samme som «kan udsende et gyldigt vaerktoejskald». En model kan adlyde
praecist i prosa og stadig fabrikere svaret paa en opgave der KRAEVER at den
laeser en fil.

MAALT 10/9-2026 over 935 agent-koersler — 62 af dem (6,6 %) kaldte et
vaerktoej:

    copilot-free/gpt-4.1                     43 koersler, 32 med kald (74 %)
    nvidia/nemotron-3-ultra-550b-a55b        87 koersler,  4 med kald (4,6 %)
    groq/llama-3.3-70b-versatile            172 koersler,  0
    ollamafreeapi/deepseek-r1:latest        169 koersler,  0
    cloudflare/@cf/meta/llama-4-scout       167 koersler,  0
    ollamafreeapi/llama3.2:latest           167 koersler,  0

TO TING GJORDE DENNE MAALING MULIG, og de er begge dagens laere.

Foerst troede jeg der ingen data var: `agent_tool_calls` har nul raekker, fordi
`create_agent_tool_call` aldrig havde en kalder. Men tallet laa i
`agent_runs.output_payload_json.tool_calls` — loekkens EGEN taelling af
faktisk udfoerte kald, i den raekke jeg selv kiggede paa. Jarvis fandt det.
«Tomt lager» er ikke «ingen maaling».

Og hans egen slutning gik for langt den anden vej: «modellen kan ikke kalde
vaerktoejer» holdt ikke — nemotron goer det i 4,6 % af tilfaeldene. To
observationer er et spor. 172 koersler uden ét eneste kald er en dom.

DERFOR KRAEVES DER EN MAENGDE FOER VI DOEMMER. En model der har koert to
gange uden kald siger ingenting; en der har koert 167 gange uden ét siger
noget. Og en UMAALT model spaerres aldrig — vi ved ikke at den ikke kan.
"""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

#: Under saa mange koersler doemmer vi ikke. To observationer er et spor.
MIN_KOERSLER = 25

#: Har den kaldt i under saa stor en andel af sine koersler, regnes den som
#: uegnet til opgaver DER KRAEVER vaerktoejer. Sat lavt med vilje: vi vil ramme
#: «aldrig», ikke «sjaeldent».
MIN_ANDEL = 0.02


#: Kort proces-cache. MAALT 10/9: ét fuldt scan koster 15,9 ms ved 935
#: koersler, og porten kaldes ÉN GANG PR. KANDIDAT i rotationen — fire kald
#: blev til 30 ms. Det er lidt i dag, men det vokser med historikken, og
#: `agent_runs` bliver kun laengere. (Jarvis pegede paa loekken.)
#:
#: 60 sekunder er rigeligt: en models evne til at kalde vaerktoejer aendrer sig
#: ikke fra minut til minut, og en frisk observation naar frem ved naeste
#: vindue frem for aldrig.
_CACHE_SEKUNDER = 60.0
_cache: dict[str, dict[str, Any]] | None = None
_cache_tid: float = 0.0
_cache_min: int = -1
#: Cachen noegles ogsaa paa DATABASE-STIEN. Uden det ville en proces der
#: skifter runtime-hjem — praecis hvad testene goer — laese et svar fra et
#: ANDET hus og tro det var sit eget. Jeg har lige brugt dagen paa at vise at
#: seks suite-fejl skyldtes forurening; en cache uden denne noegle ville vaere
#: en ny kilde til samme slags.
_cache_db: str = ""


def _db_noegle() -> str:
    try:
        from core.runtime import db_core
        return str(db_core.DB_PATH)
    except Exception:
        return ""


def _nulstil_cache_for_tests() -> None:
    global _cache, _cache_tid, _cache_min, _cache_db
    _cache, _cache_tid, _cache_min, _cache_db = None, 0.0, -1, ""


def tool_calling_record(*, min_koersler: int = MIN_KOERSLER) -> dict[str, dict[str, Any]]:
    """(provider, model) -> {koersler, med_kald, andel, dom}.

    `dom` er "kan" / "kan-ikke" / "umaalt". Den sidste er ikke en mistanke —
    den betyder at vi ikke har grundlag, og saa spaerrer vi ikke.
    """
    global _cache, _cache_tid, _cache_min, _cache_db
    import time as _t
    _db = _db_noegle()
    if (_cache is not None and _cache_min == int(min_koersler)
            and _cache_db == _db
            and (_t.monotonic() - _cache_tid) < _CACHE_SEKUNDER):
        return _cache

    ud: dict[str, dict[str, Any]] = {}
    try:
        from core.runtime.db_core import connect
        with connect() as conn:
            raekker = conn.execute(
                "SELECT provider, model, output_payload_json FROM agent_runs "
                "WHERE provider != ''"
            ).fetchall()
    except Exception:
        logger.warning("kunne ikke laese vaerktoejs-historikken", exc_info=True)
        return ud

    for r in raekker:
        n = f"{r['provider']}/{r['model']}"
        p = ud.setdefault(n, {"provider": str(r["provider"]),
                              "model": str(r["model"]),
                              "koersler": 0, "med_kald": 0})
        p["koersler"] += 1
        try:
            if int((json.loads(r["output_payload_json"] or "{}") or {}).get("tool_calls") or 0):
                p["med_kald"] += 1
        except Exception:
            pass

    for p in ud.values():
        p["andel"] = p["med_kald"] / max(p["koersler"], 1)
        if p["koersler"] < int(min_koersler):
            p["dom"] = "umaalt"
        elif p["andel"] < MIN_ANDEL:
            p["dom"] = "kan-ikke"
        else:
            p["dom"] = "kan"
    # Kun et VELLYKKET scan caches. En fejlet laesning maa ikke fastfryse et
    # tomt svar i et minut — da er det bedre at proeve igen med det samme.
    if raekker:
        _cache, _cache_tid, _cache_min, _cache_db = (
            ud, _t.monotonic(), int(min_koersler), _db)
    return ud


def kan_kalde_vaerktoejer(provider: str, model: str) -> bool:
    """Skal denne model faa en opgave der KRAEVER vaerktoejer?

    Fail-OPEN: kan historikken ikke laeses, eller er modellen umaalt, svarer
    vi ja. En port der spaerrer paa manglende viden ville lukke enhver ny
    model ude — og det er ikke det den er til for.
    """
    n = f"{str(provider or '')}/{str(model or '')}"
    try:
        return tool_calling_record().get(n, {}).get("dom") != "kan-ikke"
    except Exception:
        logger.warning("vaerktoejs-porten kunne ikke afgoere %s — lader den gaa",
                       n, exc_info=True)
        return True
