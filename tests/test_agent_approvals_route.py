"""F4c: API til at afgoere agent-approvals - kun et menneske, totrin ved godkendelse, ejer-scoped."""
from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

import core.identity.users as users
import core.identity.workspace_context as wc
from apps.api.jarvis_api.routes import agent_approvals as R
from core.services import totp_verifier as tv

O = "bjorn"


@pytest.fixture
def rt(isolated_runtime, monkeypatch):
    import core.runtime.db_agent_approvals as appr
    import core.runtime.db_agent_contract as c
    import core.services.agent_contract_service as svc
    from core.runtime.db_agent_runtime import create_agent_registry_entry

    seed = tv.generate_seed()
    monkeypatch.setattr(users, "get_totp_seed", lambda discord_id: seed)
    tv._ATTEMPTS.clear()
    monkeypatch.setattr("core.identity.owner_resolver.owner_user_id", lambda: "platform-ejer")
    started = []
    monkeypatch.setattr(svc, "_run_in_background", lambda fn: started.append(fn))

    def som(uid=O):
        monkeypatch.setattr(wc, "current_user_id", lambda: uid)

    som()

    class H:
        appr_, c_, svc_, seed_, started_ = appr, c, svc, seed, started
        som_ = staticmethod(som)

        def req(self, name="a1", owner=O, session="s1", cmd="ls"):
            create_agent_registry_entry(agent_id=name, role="executor", goal="g")
            c.bind_agent_owner(agent_id=name, owner_user_id=owner, owner_session_id=session)
            acc = c.accept_assignment(agent_id=name, owner_user_id=owner, origin_session_id=session, goal="g",
                                      parent_agent_id="jarvis", parent_run_id="pr")
            return appr.request(owner_user_id=owner, origin_session_id=session, assignment_id=acc["assignment_id"],
                                tool_name="bash", arguments={"command": cmd})

        def decide(self, r, decision="approve", kode=None, digest=None, **kw):
            body = R.DecisionRequest(decision=decision, digest=digest if digest is not None else r["args_digest"],
                                     kode=tv.generate_code(self.seed_) if kode is None else kode, **kw)
            return asyncio.run(R.decide(r["approval_id"], body))

    return H()


def test_listing_requires_login_and_shows_only_own_approvals_without_raw_arguments(rt):
    mine = rt.req("a1")
    rt.req("a2", owner="anden", session="sx")
    out = asyncio.run(R.list_approvals(status="pending", session=""))
    assert [a["approval_id"] for a in out["approvals"]] == [mine["approval_id"]]
    assert "arguments_json" not in out["approvals"][0] and out["approvals"][0]["safe_view"].startswith("bash(")
    rt.som_("")
    with pytest.raises(HTTPException) as e:
        asyncio.run(R.list_approvals())
    assert e.value.status_code == 401


def test_the_owner_approves_with_the_right_code_and_the_child_is_resumed(rt):
    r = rt.req()
    out = rt.decide(r)
    assert out["status"] == "ok" and out["approval"]["status"] == "approved" and out["approval"]["decided_by"] == O
    assert rt.appr_.get(approval_id=r["approval_id"])["status"] == "approved"


@pytest.mark.parametrize("kode,status", [("000000", 403), ("", 403)])
def test_approving_needs_the_two_step_code_when_one_is_set_up(rt, kode, status):
    r = rt.req()
    with pytest.raises(HTTPException) as e:
        rt.decide(r, kode=kode)
    assert e.value.status_code == status and rt.appr_.get(approval_id=r["approval_id"])["status"] == "pending"


def test_denying_never_needs_the_code(rt):
    r = rt.req()
    out = rt.decide(r, "deny", kode="")
    assert out["approval"]["status"] == "denied"


def test_without_a_configured_code_the_login_alone_is_enough_but_it_is_logged(rt, monkeypatch, caplog):
    monkeypatch.setattr(users, "get_totp_seed", lambda discord_id: None)
    r = rt.req()
    with caplog.at_level("WARNING"):
        out = rt.decide(r, kode="")
    assert out["approval"]["status"] == "approved" and any("UDEN totrinskode" in m for m in caplog.messages)


def test_not_logged_in_decides_nothing(rt):
    r = rt.req()
    rt.som_("")
    with pytest.raises(HTTPException) as e:
        rt.decide(r)
    assert e.value.status_code == 401 and rt.appr_.get(approval_id=r["approval_id"])["status"] == "pending"


def test_another_user_cannot_decide_even_with_a_valid_code(rt):
    r = rt.req()
    rt.som_("anden")
    with pytest.raises(HTTPException) as e:
        rt.decide(r)
    assert e.value.status_code == 403 and rt.appr_.get(approval_id=r["approval_id"])["status"] == "pending"


def test_the_platform_owner_can_decide_a_members_approval(rt):
    r = rt.req(owner="medlem", session="sm")
    rt.som_("platform-ejer")
    assert rt.decide(r, "deny")["approval"]["status"] == "denied"


@pytest.mark.parametrize("case,status", [("digest", 404), ("ukendt", 404), ("dobbelt", 409)])
def test_errors_map_to_http_status_codes(rt, case, status):
    r = rt.req()
    with pytest.raises(HTTPException) as e:
        if case == "digest":
            rt.decide(r, digest="0" * 64)
        elif case == "ukendt":
            asyncio.run(R.decide("appr-findes-ikke", R.DecisionRequest(decision="deny", digest="x")))
        else:
            rt.decide(r, "deny")
            rt.decide(r, "deny")
    assert e.value.status_code == status


def test_an_expired_approval_answers_410(rt):
    r = rt.req()
    c = rt.c_._conn()
    c.execute("UPDATE agent_approvals SET expires_at='2000-01-01T00:00:00Z' WHERE approval_id=?", (r["approval_id"],))
    c.commit()
    with pytest.raises(HTTPException) as e:
        rt.decide(r, "deny")
    assert e.value.status_code == 410


def test_the_request_body_cannot_claim_a_different_actor_kind(rt):
    """actor_kind er ikke et felt i anmodningen - den saettes af ruten ud fra login."""
    assert "actor_kind" not in R.DecisionRequest.model_fields
    r = rt.req()
    body = R.DecisionRequest.model_validate({"decision": "deny", "digest": r["args_digest"], "actor_kind": "agent"})
    assert asyncio.run(R.decide(r["approval_id"], body))["approval"]["status"] == "denied"


def test_the_routes_are_mounted_in_the_app():
    from apps.api.jarvis_api.app import app

    paths = {getattr(r, "path", "") for r in app.routes}
    assert {"/agents/approvals", "/agents/approvals/{approval_id}/decision"} <= paths
