"""Hvilke modeller KALDER vaerktoejer — maalt, ikke antaget.

`egnede_modeller` havde en `follows`-port, men «foelger instruktioner» er ikke
«kan udsende et gyldigt vaerktoejskald». En model kan adlyde praecist i prosa
og stadig fabrikere svaret paa en opgave der KRAEVER at den laeser en fil.

MAALT 10/9-2026 over 935 agent-koersler — 62 (6,6 %) kaldte et vaerktoej:

    copilot-free/gpt-4.1                43 koersler, 32 med kald (74 %)
    nvidia/nemotron-3-ultra-550b        87 koersler,  4 med kald (4,6 %)
    groq/llama-3.3-70b-versatile       172 koersler,  0
    ollamafreeapi/deepseek-r1:latest   169 koersler,  0
    cloudflare/llama-4-scout           167 koersler,  0
    ollamafreeapi/llama3.2:latest      167 koersler,  0

TO FEJL GJORDE MAALINGEN MULIG, og de var hinandens spejlbillede:

  * Jeg saa at `agent_tool_calls` var tom og sluttede at der INGEN data var.
    Tallet laa i `agent_runs.output_payload_json.tool_calls` — i den raekke
    jeg selv kiggede paa.
  * Jarvis saa det samme nul og sluttede at MODELLEN ikke kan kalde
    vaerktoejer. Nemotron goer det i 4,6 % af tilfaeldene.

To observationer er et spor. 172 koersler uden ét eneste kald er en dom.
"""
from __future__ import annotations

import json

from core.services.tool_calling_evidence import (
    MIN_KOERSLER,
    kan_kalde_vaerktoejer,
    tool_calling_record,
)


def _koersel(db, provider, model, *, kald: int, n: int = 1):
    for i in range(n):
        db.create_agent_run(
            run_id=f"r-{provider}-{model}-{kald}-{i}", agent_id="a",
            provider=provider, model=model, status="completed",
            output_payload_json=json.dumps({"tool_calls": kald}),
        )


def test_en_model_der_ALDRIG_kalder_doemmes(isolated_runtime):
    import core.runtime.db_agent_runtime as db
    db.create_agent_registry_entry(agent_id="a", role="r", goal="g")
    _koersel(db, "p", "aldrig", kald=0, n=MIN_KOERSLER + 5)

    r = tool_calling_record()["p/aldrig"]
    assert r["dom"] == "kan-ikke"
    assert kan_kalde_vaerktoejer("p", "aldrig") is False


def test_en_model_der_SOMMETIDER_kalder_slipper_igennem(isolated_runtime):
    """Jarvis' generalisering gik for langt: nemotron kalder i 4,6 % af
    tilfaeldene. «Sjaeldent» er ikke «aldrig», og porten skal ramme «aldrig»."""
    import core.runtime.db_agent_runtime as db
    db.create_agent_registry_entry(agent_id="a", role="r", goal="g")
    _koersel(db, "p", "sommetider", kald=0, n=MIN_KOERSLER)
    _koersel(db, "p", "sommetider", kald=2, n=3)

    assert tool_calling_record()["p/sommetider"]["dom"] == "kan"
    assert kan_kalde_vaerktoejer("p", "sommetider") is True


def test_faa_koersler_doemmer_IKKE(isolated_runtime):
    """To observationer er et spor, ikke en dom. En model der har koert to
    gange uden kald siger ingenting."""
    import core.runtime.db_agent_runtime as db
    db.create_agent_registry_entry(agent_id="a", role="r", goal="g")
    _koersel(db, "p", "ny", kald=0, n=2)

    assert tool_calling_record()["p/ny"]["dom"] == "umaalt"
    assert kan_kalde_vaerktoejer("p", "ny") is True, (
        "en umaalt model blev spaerret — porten ville lukke enhver ny model ude")


def test_en_ukendt_model_spaerres_ikke(isolated_runtime):
    assert kan_kalde_vaerktoejer("findes", "ikke") is True


def test_porten_fejler_AABENT(isolated_runtime, monkeypatch):
    """Kan historikken ikke laeses, spaerrer vi ikke. En port der lukker paa
    manglende viden ville lukke alt ude naar databasen er nede."""
    import core.services.tool_calling_evidence as t
    monkeypatch.setattr(t, "tool_calling_record",
                        lambda **kw: (_ for _ in ()).throw(RuntimeError("db")))
    assert t.kan_kalde_vaerktoejer("p", "m") is True


def test_explore_kraever_vaerktoejer_af_sine_modeller():
    """Koblingen. Explore LAESER filer — en model der aldrig kalder dem,
    fabrikerer svaret i stedet."""
    import inspect

    from core.tools import simple_tools_explore as e

    assert "kraever_vaerktoejer=True" in inspect.getsource(e._exec_explore)


# ── porten kaldes ÉN GANG PR. KANDIDAT — scannet maa ikke gentages ──────
#
# Jarvis pegede paa loekken: `kan_kalde_vaerktoejer` kaldes inde i
# `for post in poster`, og hvert kald re-laeste HELE `agent_runs` med
# JSON-parse pr. raekke. MAALT: ét scan 15,9 ms ved 935 koersler, fire kald
# 30 ms. Lidt i dag — men det vokser med historikken, og tabellen bliver kun
# laengere.

def test_gentagne_kald_scanner_ikke_igen(isolated_runtime):
    import core.runtime.db_agent_runtime as db
    import core.services.tool_calling_evidence as t

    t._nulstil_cache_for_tests()
    db.create_agent_registry_entry(agent_id="a", role="r", goal="g")
    _koersel(db, "p", "m", kald=0, n=MIN_KOERSLER + 1)

    scan = {"n": 0}
    aegte = t.tool_calling_record

    t._nulstil_cache_for_tests()
    t.tool_calling_record()                       # varmer cachen
    from core.runtime import db_core
    aegte_connect = db_core.connect

    def _taeller(*a, **kw):
        scan["n"] += 1
        return aegte_connect(*a, **kw)

    db_core.connect = _taeller
    try:
        for _ in range(5):
            t.kan_kalde_vaerktoejer("p", "m")
    finally:
        db_core.connect = aegte_connect
    assert scan["n"] == 0, f"scannede {scan['n']} gange trods cache"
    del aegte


def test_en_FEJLET_laesning_caches_ikke(isolated_runtime, monkeypatch):
    """Ellers ville ét daarligt oejeblik fastfryse et tomt svar i et minut —
    og porten ville lade alt igennem imens, uden at nogen saa det."""
    import core.services.tool_calling_evidence as t

    t._nulstil_cache_for_tests()
    monkeypatch.setattr("core.runtime.db_core.connect",
                        lambda: (_ for _ in ()).throw(RuntimeError("db nede")))
    assert t.tool_calling_record() == {}
    assert t._cache is None, "en fejlet laesning blev cachet"


def test_cachen_udloeber(isolated_runtime):
    """En frisk observation skal naa frem ved naeste vindue — ikke aldrig."""
    import core.services.tool_calling_evidence as t

    assert t._CACHE_SEKUNDER <= 300, (
        "cachen holder for laenge til at ny evidens naar frem i praksis")


def test_cachen_noegles_paa_DATABASEN_ikke_kun_paa_tiden(isolated_runtime):
    """Uden DB-noeglen ville en proces der skifter runtime-hjem — praecis hvad
    testene goer — laese et svar fra et ANDET hus og tro det var sit eget.

    Det er samme fejlklasse som de seks suite-fejl der viste sig at vaere
    forurening: en delt tilstand der overlever en graense den ikke burde."""
    import core.services.tool_calling_evidence as t

    assert "_cache_db" in t.tool_calling_record.__globals__, (
        "cachen har ingen database-noegle")
    import inspect
    kilde = inspect.getsource(t.tool_calling_record)
    assert "_cache_db == _db" in kilde, (
        "cachen sammenligner ikke databasen — svaret kan komme fra et andet hus")
