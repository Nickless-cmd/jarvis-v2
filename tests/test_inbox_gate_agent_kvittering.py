"""Inbox-værn: `bash` låses til fejlede agent-kørsler er kvitteret.

Rigtig sqlite og den ÆGTE kvittering (`agent_contract_projection.acknowledge`),
så beviset for at betingelsen kan opfyldes ikke er en fake.
"""
from __future__ import annotations

import pytest

from core.services.inbox_gate import evaluer_inbox_mutation

A, B, S = "bjorn", "anden", "sess-1"


@pytest.fixture
def agenter(isolated_runtime, monkeypatch):
    import core.runtime.db_agent_contract as c
    from core.eventbus.bus import event_bus
    from core.runtime.db_agent_runtime import create_agent_registry_entry

    monkeypatch.setattr(event_bus, "publish", lambda *a, **k: None)

    class H:
        c_ = c

        def opret(self, navn, status="failed", owner=A):
            create_agent_registry_entry(agent_id=navn, role="r", goal="g")
            c.bind_agent_owner(agent_id=navn, owner_user_id=owner, owner_session_id=S)
            asg = c.accept_assignment(agent_id=navn, owner_user_id=owner, origin_session_id=S,
                                      goal="g", parent_agent_id="jarvis", parent_run_id="pr")
            c.commit_terminal_outcome(assignment_id=asg["assignment_id"], status=status,
                                      summary="s")
            return asg["assignment_id"]

    return H()


def _bash(bruger=A, navn="bash", kommando="ls"):
    return evaluer_inbox_mutation(bruger, navn, {"command": kommando}, tur="t1")


def test_gate_fyrer_ved_ukvitteret_failed_og_navngiver_id_og_handling(agenter):
    aid = agenter.opret("a1")
    r = _bash()
    assert r["blokeret"] is True
    assert aid in r["poster"]
    assert aid in r["varsel"]
    assert "/acknowledge" in r["varsel"]


def test_gate_laaser_ogsaa_en_laeseagtig_bash_kommando(agenter):
    agenter.opret("a1")
    assert _bash(kommando="ls")["blokeret"] is True


def test_kvittering_aabner_gaten(agenter):
    from core.services import agent_contract_projection as proj
    aid = agenter.opret("a1")
    assert _bash()["blokeret"] is True
    assert proj.acknowledge(A, aid)["acknowledged"] is True
    assert _bash()["blokeret"] is False


def test_kun_den_ukvitterede_bliver_i_beskeden(agenter):
    from core.services import agent_contract_projection as proj
    a1, a2 = agenter.opret("a1"), agenter.opret("a2")
    proj.acknowledge(A, a1)
    r = _bash()
    assert r["poster"] == [a2]
    assert a1 not in r["varsel"]


def test_completed_med_accepted_resultat_blokerer_og_kvittering_aabner(agenter):
    from core.services import agent_contract_projection as proj
    aid = agenter.opret("a1", status="completed")
    ds = agenter.c_._conn().execute(
        "SELECT delivery_status FROM agent_result_outbox WHERE assignment_id=?",
        (aid,)).fetchone()["delivery_status"]
    assert ds == "accepted"
    r = _bash()
    assert r["blokeret"] is True and aid in r["varsel"]
    assert proj.acknowledge(A, aid)["acknowledged"] is True
    assert _bash()["blokeret"] is False


def test_failed_uden_kvittering_blokerer_stadig(agenter):
    agenter.opret("a1", status="failed")
    assert _bash()["blokeret"] is True


def test_en_andens_failed_assignment_laaser_ikke(agenter):
    agenter.opret("a1", owner=B)
    assert _bash(bruger=A)["blokeret"] is False


@pytest.mark.parametrize("navn", ["bash_session_run", "bash_session_open",
                                  "operator_bash_session_run"])
def test_bash_session_rammes_ikke(agenter, navn):
    agenter.opret("a1")
    r = evaluer_inbox_mutation(A, navn, {"command": "rm -rf x"}, tur="t1")
    assert r["blokeret"] is False
    assert r["grund"] == "bagdoer"


def test_db_fejl_standser_og_logger_grunden(agenter, monkeypatch, caplog):
    import core.services.inbox_gate as g

    def _boom(_):
        raise RuntimeError("db nede")
    monkeypatch.setattr(g, "_ukvitterede_fejlede_agenter", _boom)
    with caplog.at_level("WARNING"):
        r = _bash()
    assert r["blokeret"] is True
    assert "fail-closed" in r["grund"]
    assert "db nede" in caplog.text
    # flugtvejen er stadig åben
    assert evaluer_inbox_mutation(A, "bash_session_run", {"command": "x"})["blokeret"] is False


def test_en_agent_koersel_laases_ikke_af_sin_ejers_ukvitterede_resultater(agenter, monkeypatch):
    """Gaten hører til ejerens tur. En worker kan ikke kvittere — og bærer ejerens id.

    Uden undtagelsen ville en færdig agents ukvitterede resultat låse dens endnu
    kørende søskende midt i arbejdet. Patchen rammer den ÆGTE detektor
    (`er_i_agent_koersel`), ikke gaten, så testen beviser at den bliver spurgt.
    """
    import core.runtime.db_agent_lease as lease

    agenter.opret("a1")
    monkeypatch.setattr(lease, "er_i_agent_koersel", lambda: True)

    assert _bash()["blokeret"] is False


def test_uden_for_en_agent_koersel_laaser_det_samme_resultat_stadig(agenter, monkeypatch):
    """Modstykket: undtagelsen må ikke gøre gaten tandløs for ejeren selv."""
    import core.runtime.db_agent_lease as lease

    agenter.opret("a1")
    monkeypatch.setattr(lease, "er_i_agent_koersel", lambda: False)

    assert _bash()["blokeret"] is True
