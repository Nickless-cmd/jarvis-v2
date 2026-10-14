"""F4c: API til at afgoere agent-approvals - kun et menneske, ejer-scoped, session-bundet.

TOTP-PORTEN ER VAEK (14/10-2026). Denne fil pinnede indtil i dag at en godkendelse kraevede en
totrinskode. Det var en fejl: Bjoerns egen spec (``2026-06-14-totp-override-security-design.md``
§6.1) siger at TOTP kraeves i en FREMMED session, og at ejeren i sin EGEN desk-session har fri
adgang fordi «sessionen er allerede kryptografisk bundet til owner». Agent-godkendelser sker i
hans egen session. Det der nu pinnes i stedet er de to ting der FAKTISK baerer sikkerheden:
token-identiteten (kun et menneske, kun ejeren) og session-bindingen.
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

import core.identity.workspace_context as wc
from apps.api.jarvis_api.routes import agent_approvals as R

EJER = "bjorn"


@pytest.fixture
def rt(isolated_runtime, monkeypatch):
    import core.runtime.db_agent_approvals as appr
    import core.runtime.db_agent_contract as c
    import core.services.agent_contract_service as svc
    from core.runtime.db_agent_runtime import create_agent_registry_entry

    monkeypatch.setattr("core.identity.owner_resolver.owner_user_id", lambda: "platform-ejer")
    started = []
    monkeypatch.setattr(svc, "_run_in_background", lambda fn: started.append(fn))

    def som(uid=EJER):
        monkeypatch.setattr(wc, "current_user_id", lambda: uid)

    som()

    class H:
        appr_, c_, svc_, started_ = appr, c, svc, started
        som_ = staticmethod(som)

        def req(self, name="a1", owner=EJER, session="s1", cmd="ls"):
            create_agent_registry_entry(agent_id=name, role="executor", goal="g")
            c.bind_agent_owner(agent_id=name, owner_user_id=owner, owner_session_id=session)
            acc = c.accept_assignment(agent_id=name, owner_user_id=owner, origin_session_id=session, goal="g",
                                      parent_agent_id="jarvis", parent_run_id="pr")
            return appr.request(owner_user_id=owner, origin_session_id=session, assignment_id=acc["assignment_id"],
                                tool_name="bash", arguments={"command": cmd})

        def decide(self, r, decision="approve", digest=None, session="s1", **kw):
            body = R.DecisionRequest(decision=decision, digest=digest if digest is not None else r["args_digest"],
                                     session=session, **kw)
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


def test_the_owner_approves_and_the_child_is_resumed(rt):
    """Ingen kode - login + session er nok. Det er hele aendringen."""
    r = rt.req()
    out = rt.decide(r)
    assert out["status"] == "ok" and out["approval"]["status"] == "approved" and out["approval"]["decided_by"] == EJER
    assert rt.appr_.get(approval_id=r["approval_id"])["status"] == "approved"


def test_approving_needs_NO_two_step_code(rt):
    """Porten er væk. En tom kode (og et felt der ikke findes) maa ikke blokere."""
    r = rt.req()
    assert "kode" not in R.DecisionRequest.model_fields, "TOTP-feltet er tilbage i anmodningen"
    out = rt.decide(r)
    assert out["approval"]["status"] == "approved"


def test_denying_works_without_a_code(rt):
    r = rt.req()
    out = rt.decide(r, "deny")
    assert out["approval"]["status"] == "denied"


def test_a_decision_from_ANOTHER_session_is_refused(rt):
    """Session-bindingen: en godkendelse der svarer paa noget i EN session maa ikke trykkes fra en ANDEN."""
    r = rt.req(session="s1")
    with pytest.raises(HTTPException) as e:
        rt.decide(r, session="s2")
    assert e.value.status_code == 403
    assert rt.appr_.get(approval_id=r["approval_id"])["status"] == "pending", "afvisningen efterlod en afgjort post"


def test_an_empty_session_still_works_the_token_carries_the_identity(rt):
    """En klient der ikke oplyser sin session er ikke laast ude - identiteten baeres da af token'en."""
    r = rt.req(session="s1")
    assert rt.decide(r, session="")["approval"]["status"] == "approved"


def test_not_logged_in_decides_nothing(rt):
    r = rt.req()
    rt.som_("")
    with pytest.raises(HTTPException) as e:
        rt.decide(r)
    assert e.value.status_code == 401 and rt.appr_.get(approval_id=r["approval_id"])["status"] == "pending"


def test_another_user_cannot_decide_even_with_the_right_session(rt):
    r = rt.req()
    rt.som_("anden")
    with pytest.raises(HTTPException) as e:
        rt.decide(r)
    assert e.value.status_code == 403 and rt.appr_.get(approval_id=r["approval_id"])["status"] == "pending"


def test_the_platform_owner_can_decide_a_members_approval(rt):
    r = rt.req(owner="medlem", session="sm")
    rt.som_("platform-ejer")
    assert rt.decide(r, "deny", session="sm")["approval"]["status"] == "denied"


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
