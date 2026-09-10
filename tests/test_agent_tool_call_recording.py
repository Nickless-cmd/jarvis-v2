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
    # Kommentarer strippes FOERST. Foerste udgave saa i et 900-tegns vindue,
    # og de kommentarer jeg selv tilfoejede skubbede `except` ud af det —
    # testen faldt over sin egen forklaring. (Tredje gang det moenster bider.)
    kode = "\n".join(ln for ln in kilde.splitlines()
                     if not ln.strip().startswith("#"))
    efter = kode[kode.index("create_agent_tool_call("):]
    assert "except Exception" in efter[:600], "bogfoeringen er ikke fail-safe"


def test_felterne_matcher_skemaet():
    """Foerste udgave sendte `result_json`; feltet hedder `result_preview`.
    En bogfoering med forkerte felter ville kaste, blive slugt af vagten, og
    tabellen ville forblive tom — koblet paa og blind."""
    from core.runtime.db_agent_runtime import create_agent_tool_call

    navne = set(inspect.signature(create_agent_tool_call).parameters)
    from core.services import agent_runtime_base as b
    kilde = inspect.getsource(b._run_agent_tool_loop)
    kode = "\n".join(ln for ln in kilde.splitlines()
                     if not ln.strip().startswith("#"))
    blok = kode[kode.index("create_agent_tool_call("):]
    blok = blok[:blok.index(")\n")]
    brugt = {ln.split("=")[0].strip() for ln in blok.splitlines()[1:]
             if "=" in ln and not ln.strip().startswith("#")}
    ukendte = {n for n in brugt if n and n not in navne}
    assert not ukendte, f"felter der ikke findes i skemaet: {ukendte}"


# ── run_id skal have en VAERDI, ikke bare et feltnavn ───────────────────
#
# Jarvis fandt det inden for en time: bogfoeringen laeste `agent["_run_id"]`,
# en noegle INGEN i kodebasen saetter — og `agent` er register-opslaget, som
# ikke har den kolonne. Hver raekke ville faa run_id="" og ikke kunne join'es
# til sin koersel. Tabellen fyldt, og stadig ubrugelig.
#
# Og min egen test fangede det ikke: den tjekkede at feltnavnene findes i
# skemaet, ikke at vaerdierne er der. FORM verificeret, SUBSTANS ikke — samme
# fejlklasse som `kontrolleret: 0 -> holder: True`, som jeg selv lukkede i dag.

def test_run_id_traades_ind_som_ARGUMENT():
    from core.services import agent_runtime_base as b

    par = inspect.signature(b._run_agent_tool_loop).parameters
    assert "run_id" in par, "loekken kan ikke modtage et run_id"
    kilde = inspect.getsource(b._run_agent_tool_loop)
    assert "run_id=str(run_id or" in kilde, (
        "bogfoeringen bruger stadig kun en noegle ingen saetter")


def test_kaldestedet_sender_det_rigtige_run_id():
    """`run_id` ligger klar to linjer over kaldet — det skulle bare traades ind."""
    from core.services import agent_runtime_spawn as sp

    kilde = inspect.getsource(sp._execute_agent_task_impl)
    i_kald = kilde.index("_run_agent_tool_loop(")
    blok = kilde[i_kald:i_kald + 240]
    assert "run_id=run_id" in blok, (
        "kaldestedet sender ikke koerslens id videre — raekkerne kan ikke "
        "join'es til den koersel de hoerer til")


def test_bogfoert_raekke_faar_et_IKKE_TOMT_run_id(isolated_runtime):
    """Adfaerd, ikke kildetekst: en bogfoert raekke skal kunne findes via sit
    run_id."""
    from core.runtime.db_agent_runtime import (
        create_agent_registry_entry, create_agent_run, create_agent_tool_call,
        list_agent_tool_calls,
    )

    create_agent_registry_entry(agent_id="a", role="r", goal="g")
    create_agent_run(run_id="r-42", agent_id="a", status="completed")
    create_agent_tool_call(tool_call_id="tc-1", run_id="r-42", agent_id="a",
                           tool_name="read_file", status="ok")

    raekker = list_agent_tool_calls(run_id="r-42")
    assert raekker, "kaldet kunne ikke findes via sit run_id"
    assert str(raekker[0]["run_id"]) == "r-42"
