"""Jarvis' EGEN godkendelses-vej for sine agenters vaerktoejskald (14/10-2026).

``decide`` kraever ``actor_kind == "human"`` - og DET KRAV STAAR. Denne fil pinner den ANDEN
vej, og hvorfor den ikke er en udhuling af den foerste:

En agent Jarvis selv har startet er hans UDDELEGERING, ikke hans egen handling. Hans eget
vaerktoejskald maa han afgoere selv; en aendring af HUSETS kode maa han ikke. Graensen ligger i
lageret som to krav - ``parent_agent_id == "jarvis"`` og ``kind == "tool_call"`` - og hvert krav
pinnes for sig, saa en fremtidig aendring ikke kan udvide vejen i det stille.

Det vigtigste i filen er de NEGATIVE tests: de maaler at vejen ikke er bredere end dens grund.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def rt(isolated_runtime, monkeypatch):
    import core.runtime.db_agent_approvals as appr
    import core.runtime.db_agent_contract as c
    import core.services.agent_contract_service as svc
    from core.runtime.db_agent_runtime import create_agent_registry_entry

    started = []
    monkeypatch.setattr(svc, "_run_in_background", lambda fn: started.append(fn))

    class H:
        appr_, c_, svc_, started_ = appr, c, svc, started

        def req(self, name="a1", owner="bjorn", session="s1", parent="jarvis", kind="tool_call",
                cmd="ls"):
            create_agent_registry_entry(agent_id=name, role="executor", goal="g")
            c.bind_agent_owner(agent_id=name, owner_user_id=owner, owner_session_id=session)
            acc = c.accept_assignment(agent_id=name, owner_user_id=owner, origin_session_id=session,
                                      goal="g", parent_agent_id=parent, parent_run_id="pr")
            return appr.request(owner_user_id=owner, origin_session_id=session,
                                assignment_id=acc["assignment_id"], tool_name="bash",
                                arguments={"command": cmd}, kind=kind,
                                requested_by="jarvis" if kind == "integration" else "agent")

        def som_jarvis(self, r, decision="approve", digest=None):
            return self.svc_.decide_approval_as_parent(
                approval_id=r["approval_id"], decision=decision,
                digest=digest if digest is not None else r["args_digest"])

    return H()


def test_jarvis_kan_afgoere_sin_EGEN_agents_vaerktoejskald(rt):
    """Grunden til at vejen findes: uddelegeringen skal ikke gaa i staa bag en totrinskode."""
    r = rt.req()
    out = rt.som_jarvis(r)
    assert out["status"] == "ok"
    assert out["approval"]["status"] == "approved"
    assert out["approval"]["decided_by"] == "jarvis", "afgoerelsen skal staa som Jarvis', ikke som en bruger"


def test_jarvis_kan_AFVISE_og_postens_status_er_endelig(rt):
    r = rt.req()
    out = rt.som_jarvis(r, decision="deny")
    assert out["status"] == "ok" and out["approval"]["status"] == "denied"


# ── Graensen: de to krav, hver for sig ──────────────────────────────────────────────────────

def test_en_INTEGRATION_kan_jarvis_IKKE_afgoere(rt):
    """En aendring af husets kode er ikke agentens handling. Den kraever stadig Bjorns haand.

    Det er praecis den graense ``test_jarvis_cannot_approve_his_own_integration_request`` vogter
    fra den anden side; her maales den gennem den NYE vej.
    """
    r = rt.req(kind="integration")
    out = rt.som_jarvis(r)
    assert (out["status"], out["code"]) == ("error", "POLICY_DENIED")
    assert rt.appr_.get(approval_id=r["approval_id"])["status"] == "pending", "posten maa staa urørt"


def test_en_FREMMED_agents_anmodning_kan_jarvis_IKKE_afgoere(rt):
    """Kun agenter HAN startede. En legacy-agent uden parent falder udenfor."""
    r = rt.req(parent="")
    out = rt.som_jarvis(r)
    assert (out["status"], out["code"]) == ("error", "POLICY_DENIED")


def test_den_gamle_vej_afviser_STADIG_actor_kind_jarvis(rt):
    """Vaernet mod selv-godkendelse staar uændret. Den nye vej er en SEPARAT funktion -
    ``decide`` kan ikke lokkes til at acceptere en ikke-menneskelig aktør ved at faa en streng."""
    r = rt.req()
    with pytest.raises(rt.c_.ContractError) as e:
        rt.appr_.decide(approval_id=r["approval_id"], decision="approve", actor_user_id="bjorn",
                        actor_kind="jarvis", digest=r["args_digest"])
    assert e.value.code == "POLICY_DENIED"
    assert rt.appr_.get(approval_id=r["approval_id"])["status"] == "pending"


def test_digest_skal_passe_ellers_afvises_den(rt):
    """Afgoerelsen bindes til netop dette kald - er argumenterne aendret, kraeves en ny approval."""
    r = rt.req()
    out = rt.som_jarvis(r, digest="deadbeef")
    assert (out["status"], out["code"]) == ("error", "INVALID_SCOPE")
    assert rt.appr_.get(approval_id=r["approval_id"])["status"] == "pending"


def test_en_udloebet_post_kan_ikke_afgoeres(rt):
    r = rt.req()
    c = rt.c_._conn()
    c.execute("UPDATE agent_approvals SET expires_at='2000-01-01T00:00:00Z' WHERE approval_id=?",
              (r["approval_id"],))
    c.commit()
    out = rt.som_jarvis(r)
    assert (out["status"], out["code"]) == ("error", "EXPIRED")


def test_afgoerelsen_skrives_i_revisionssporet(rt):
    """Hvem afgjorde hvad - og at det var Jarvis selv, ikke et menneske."""
    r = rt.req()
    rt.som_jarvis(r)
    spor = rt.appr_.audit_trail(approval_id=r["approval_id"])
    assert any(e["event"] == "approved" and e["actor"] == "parent:jarvis" for e in spor)
