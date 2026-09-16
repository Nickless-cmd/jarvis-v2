"""Den lette agent-liste — den der kan filtreres uden tolvhundrede opslag."""
from __future__ import annotations

import pytest

from core.services import agent_pool_surface as S


def _agent(aid: str, *, rolle="researcher", status="completed", goal="noget"):
    from core.runtime.db_agent_runtime import create_agent_registry_entry
    create_agent_registry_entry(agent_id=aid, kind="subagent", role=rolle,
                                goal=goal, status=status)


def _koersel(aid: str, *, status="completed", pris=0.01, ind=100, ud=50):
    from core.runtime.db_agent_runtime import create_agent_run, update_agent_run
    r = create_agent_run(run_id=f"run-{aid}-{status}", agent_id=aid, status=status)
    update_agent_run(str(r["run_id"]), status=status, cost_usd=pris,
                     input_tokens=ind, output_tokens=ud)


@pytest.fixture
def pulje(isolated_runtime):
    _agent("agent-1", rolle="researcher", goal="find noget om broen")
    _agent("agent-2", rolle="critic", status="active")
    _agent("agent-3", rolle="researcher", status="failed")
    _koersel("agent-1", status="completed")
    _koersel("agent-3", status="failed", pris=0.02)
    return True


def test_listen_giver_koerselstal_uden_at_berige_hver_agent(pulje):
    ud = S.agent_liste()
    a1 = next(a for a in ud["agenter"] if a["agent_id"] == "agent-1")
    assert a1["koersler"] == 1 and a1["pris_usd"] == 0.01 and a1["tokens"] == 150
    assert a1["seneste_udfald"] == "completed"


def test_filter_paa_status(pulje):
    assert {a["agent_id"] for a in S.agent_liste(status="failed")["agenter"]} == {"agent-3"}


def test_aktive_er_ET_filter_ikke_en_status(pulje):
    """«aktive» daekker seks statusser. Uden det skulle man kende dem alle."""
    ud = S.agent_liste(status="aktive")
    assert {a["agent_id"] for a in ud["agenter"]} == {"agent-2"}
    assert ud["agenter"][0]["er_aktiv"] is True


def test_filter_paa_rolle_og_soegning(pulje):
    assert S.agent_liste(rolle="critic")["i_alt"] == 1
    assert {a["agent_id"] for a in S.agent_liste(soeg="broen")["agenter"]} == {"agent-1"}


def test_loftet_er_ikke_facit(pulje):
    ud = S.agent_liste(limit=1)
    assert ud["vist"] == 1 and ud["i_alt"] == 3          # limit-faelden
    anden = S.agent_liste(limit=1, offset=1)
    assert anden["agenter"][0]["agent_id"] != ud["agenter"][0]["agent_id"]


def test_opsummeringen_taeller_status_rolle_og_vindue(pulje):
    o = S.pool_opsummering(timer=24)
    assert o["agenter_i_alt"] == 3
    assert o["pr_status"]["failed"] == 1 and o["aktive_nu"] == 1
    assert o["vindue"]["koersler"] == 2 and o["vindue"]["fejlede"] == 1
    assert o["vindue"]["fejlrate"] == 0.5
    assert o["graenser"]["samtidige"] >= 1


def test_ingen_koersler_giver_INGEN_fejlrate(isolated_runtime):
    assert S.pool_opsummering(timer=1)["vindue"]["fejlrate"] is None


def test_seneste_arbejde_kommer_fra_koerslerne(pulje):
    k = S.seneste_arbejde(limit=5)["koersler"]
    assert len(k) == 2 and {x["status"] for x in k} == {"completed", "failed"}
    assert all("role" in x for x in k)      # rollen foelger med fra registret
