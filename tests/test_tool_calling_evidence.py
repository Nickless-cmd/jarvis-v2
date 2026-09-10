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
