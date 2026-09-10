"""Vaerktoejskald skal BOGFOERES — ellers laeses tomheden som en maaling.

MAALT 10/9-2026: `agent_tool_calls` havde NUL raekker paa tvaers af 935
agent-koersler, og `create_agent_tool_call` havde ingen kaldere. Tabellen
fandtes; ingen fyldte den.

Konsekvensen var ikke bare manglende observabilitet. Jarvis testede
`explore` mod Bjoerns maskine, fik et selvsikkert forkert svar, gik i tabellen
og konkluderede at MODELLEN ikke kunne kalde vaerktoejer — «tool-kald: 0».

Men tallet er nul for enhver model, altid. Han maalte fravaeret af en maaling
og laeste det som et resultat. Det er samme fejlklasse som `holder=True` ved
nul kontrollerede paastande, bare i data i stedet for i en dom.
"""
from __future__ import annotations

import inspect


def test_loekken_bogfoerer_hvert_kald():
    from core.services import agent_runtime_base as b

    kilde = inspect.getsource(b._run_agent_tool_loop)
    assert "create_agent_tool_call(" in kilde, (
        "vaerktoejskald bogfoeres stadig ikke — tabellen forbliver tom, og "
        "enhver model ser ud til ikke at kunne kalde vaerktoejer")
    i_exec = kilde.index("_execute_agent_tool_call(")
    i_bog = kilde.index("create_agent_tool_call(")
    assert i_exec < i_bog, "bogfoeringen sker foer kaldet er udfoert"


def test_bogfoeringen_kan_ikke_vaelte_barnets_tur():
    """En observation maa aldrig kunne stoppe det den observerer."""
    from core.services import agent_runtime_base as b

    kilde = inspect.getsource(b._run_agent_tool_loop)
    efter = kilde[kilde.index("create_agent_tool_call("):]
    assert "except Exception" in efter[:900], (
        "bogfoeringen er ikke fail-safe")


def test_felterne_matcher_skemaet():
    """Foerste udgave sendte `result_json`; feltet hedder `result_preview`.
    En bogfoering med forkerte felter ville kaste, blive slugt af vagten, og
    tabellen ville forblive tom — koblet paa og blind."""
    from core.runtime.db_agent_runtime import create_agent_tool_call

    navne = set(inspect.signature(create_agent_tool_call).parameters)
    from core.services import agent_runtime_base as b
    kilde = inspect.getsource(b._run_agent_tool_loop)
    blok = kilde[kilde.index("create_agent_tool_call("):]
    blok = blok[:blok.index(")\n")]
    brugt = {ln.split("=")[0].strip() for ln in blok.splitlines()[1:] if "=" in ln}
    ukendte = {n for n in brugt if n and n not in navne}
    assert not ukendte, f"felter der ikke findes i skemaet: {ukendte}"
