"""`explore` skal kunne findes under den tur der foedte den — Fase 5.

«child identity is durable before work starts» og «`explore` appears under its
parent in Mission Control».

MAALT paa produktionen 10/9-2026, og de to foerste maalinger var FORKERTE:

  1. «explore registrerer ikke noget barn» — nej: jeg soegte paa
     `run_id LIKE '%explore%'`, og explore-runs baerer ikke ordet i deres id.
  2. «de 189 i registret er raads-medlemmer» — kun de 93 er. De oevrige 96 er
     raadloese `researcher`-agenter med aegte explore-maal.

Det RIGTIGE billede: 96 boern, alle med et run, alle registreret FOER runnet
(96 af 96). Identiteten er altsaa durabel og i rigtig raekkefoelge.

Hullet var herkomsten: `parent_agent_id` var konstanten «jarvis» for alle 96,
og `context_json` indeholdt kun `{"spawn_depth": 0}`. Ingen forbindelse til den
TUR der foedte barnet — saa intet kunne vise dem under den.
"""
from __future__ import annotations

import pytest

from core.tools import simple_tools_explore as E


@pytest.fixture
def fanget(monkeypatch):
    """Fang hvad der sendes til spawn'et, uden at koere en agent."""
    set_af: list[dict] = []

    def _spawn(**kw):
        set_af.append(kw)
        return {"agent_id": "a1", "provider": "p", "model": "m",
                "output_summary": "fandt noget"}

    import core.tools.simple_tools_native as N
    monkeypatch.setattr(N, "_explore_spawn", _spawn)
    monkeypatch.setattr(E, "_explore_svar", lambda r: ("fandt noget", ""))
    return set_af


def test_herkomsten_foelger_med_paa_runtime_stien(isolated_runtime, fanget):
    E._exec_explore({"query": "hvor er X", "target": "runtime",
                     "_runtime_session_id": "s-42", "_runtime_turn_id": "run-7"})
    ctx = fanget[0]["context"]
    assert ctx["parent_session_id"] == "s-42"
    assert ctx["parent_run_id"] == "run-7"


def test_herkomsten_foelger_med_paa_workstation_stien(isolated_runtime, fanget,
                                                      monkeypatch):
    monkeypatch.setattr(E, "_execution_context",
                        lambda a: ("workstation", {"workspace_root": "/w"}, ""))
    E._exec_explore({"query": "hvor er X",
                     "_runtime_session_id": "s-42", "_runtime_turn_id": "run-7"})
    ctx = fanget[0]["context"]
    assert ctx["parent_run_id"] == "run-7"
    assert ctx["workspace_root"] == "/w", "den eksisterende kontekst gik tabt"


def test_uden_herkomst_sendes_der_ingen_tomme_felter(isolated_runtime, fanget):
    """Et internt kald uden runtime-noegler skal ikke give
    `parent_run_id: ""` — et tomt felt er vaerre end intet, for det ligner en
    forbindelse der ikke findes."""
    E._exec_explore({"query": "hvor er X", "target": "runtime"})
    ctx = fanget[0].get("context") or {}
    assert "parent_run_id" not in ctx and "parent_session_id" not in ctx


def test_delvis_herkomst_tages_med(isolated_runtime, fanget):
    E._exec_explore({"query": "x", "target": "runtime",
                     "_runtime_session_id": "s-42"})
    ctx = fanget[0]["context"]
    assert ctx["parent_session_id"] == "s-42" and "parent_run_id" not in ctx


def test_execution_target_bevares(isolated_runtime, fanget):
    """Konteksten blev foer brugt til at fortaelle agenten hvor den koerer.
    Herkomsten maa ikke skubbe det ud."""
    E._exec_explore({"query": "x", "target": "runtime",
                     "_runtime_turn_id": "run-7"})
    assert fanget[0]["context"]["execution_target"] == "runtime"
