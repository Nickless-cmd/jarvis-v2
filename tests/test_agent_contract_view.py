"""G: Desks laese-/styrings-rute - ejeren kommer fra login, aldrig fra anmodningen; felter pinnet mod svaret."""
from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

import core.identity.workspace_context as wc
from apps.api.jarvis_api.routes import agent_contract_view as R

A, B, S1 = "bjorn", "anden", "sess-1"


@pytest.fixture
def rt(isolated_runtime, monkeypatch):
    import core.runtime.db_agent_artifacts as art
    import core.runtime.db_agent_contract as c
    import core.services.agent_contract_service as svc
    from core.runtime.db_agent_runtime import create_agent_registry_entry
    from core.services import in_flight_runs as ifr

    ifr._mutate(lambda r: r.clear())
    monkeypatch.setattr("core.identity.owner_resolver.owner_user_id", lambda: "platform-ejer")
    monkeypatch.setattr(svc, "_run_in_background", lambda fn: None)

    def som(uid):
        monkeypatch.setattr(wc, "current_user_id", lambda: uid)

    som(A)

    class H:
        c_, art_, svc_ = c, art, svc
        som_ = staticmethod(som)

        def agent(self, name, owner=A, session=S1, run="running"):
            create_agent_registry_entry(agent_id=name, role="researcher", goal="find X")
            c.bind_agent_owner(agent_id=name, owner_user_id=owner, owner_session_id=session)
            acc = c.accept_assignment(agent_id=name, owner_user_id=owner, origin_session_id=session, goal="find X",
                                      parent_agent_id="jarvis", parent_run_id="pr")
            cn = c._conn()
            cn.execute("UPDATE agent_runs SET status=? WHERE run_id=?", (run, acc["run_id"]))
            cn.execute("UPDATE agent_assignments SET status='active' WHERE assignment_id=?", (acc["assignment_id"],))
            cn.commit()
            return acc

        def call(self, fn, *a, **kw):
            return asyncio.run(fn(*a, **kw))

        def http(self, fn, *a, **kw):
            with pytest.raises(HTTPException) as e:
                asyncio.run(fn(*a, **kw))
            return e.value.status_code

    yield H()
    ifr._mutate(lambda r: r.clear())


def test_every_endpoint_needs_a_login(rt):
    rt.som_("")
    calls = [(R.overview, ()), (R.agent, ("a1",)), (R.artifact, ("a1", "r", "final.txt")),
             (R.message, ("a1", R.MessageBody(content="x"))), (R.followup, ("a1", R.FollowupBody(goal="x"))),
             (R.stop, ("a1",)), (R.close, ("a1",)), (R.feed, ()), (R.read, ("agent", "x")),
             (R.acknowledge, ("x",))]
    for fn, args in calls:
        assert rt.http(fn, *args) == 401, fn.__name__


def test_no_request_model_can_carry_an_owner_or_session(rt):
    for model in (R.MessageBody, R.FollowupBody, R.StopBody):
        assert not ({"owner_user_id", "user_id", "owner", "session", "origin_session_id", "actor_kind"}
                    & set(model.model_fields))
    r = R.MessageBody.model_validate({"content": "hej", "owner_user_id": B})          # ekstra felt ignoreres
    assert r.model_dump() == {"content": "hej"}


def test_dispatch_checks_authenticated_session_before_service_call(rt, monkeypatch):
    from core.services import chat_sessions

    seen = []
    monkeypatch.setattr(chat_sessions, "get_session_owner", lambda sid: B if sid == "foreign" else A)
    monkeypatch.setattr(rt.svc_, "dispatch_agent",
                        lambda **kw: seen.append(kw) or {"status": "accepted", "agent_id": "a"})
    assert rt.http(R.dispatch, R.DispatchBody(session_id="foreign", goal="work")) == 404
    assert seen == []
    out = rt.call(R.dispatch, R.DispatchBody(session_id=S1, goal="work"))
    assert out["status"] == "accepted"
    assert seen[0]["owner_user_id"] == A and seen[0]["origin_session_id"] == S1


def test_overview_response_shape_is_pinned_to_the_fields_the_client_reads(rt):
    rt.agent("a1")
    out = rt.call(R.overview)
    assert set(out) == {"status", "capability", "agents", "counts", "groups", "contract_version"}
    assert set(out["counts"]) == {"active", "queued", "waiting", "blocked", "attention", "open"}
    assert set(out["capability"]) == {"enabled", "reason", "contract_version"}
    assert set(out["agents"][0]) == {
        "agent_id", "parent_agent_id", "role", "goal", "council_id", "children", "lifecycle_status", "target",
        "assignment_id", "assignment_status", "origin_session_id", "run_id", "run_status", "attempts", "bucket",
        "attention", "reason", "error", "started_at", "finished_at", "duration_s", "updated_at", "heartbeat",
        "tokens", "cost_usd", "route", "last_message", "summary", "pending_approvals", "model_claim", "read",
        "acknowledged"}
    d = rt.call(R.agent, "a1")
    assert set(d) == {"status", "agent", "assignments", "runs", "messages", "tool_calls", "approvals", "artifacts",
                      "children", "capability", "contract_version"}


def test_feed_response_shape_is_pinned(rt):
    rt.agent("a1")
    out = rt.call(R.feed)
    assert set(out) == {"status", "cards", "counts", "contract_version"}
    assert set(out["counts"]) == {"venter", "svar", "aktiv", "unread"}
    assert set(out["cards"][0]) == {
        "ref_kind", "ref_id", "section", "bucket", "agent_id", "assignment_id", "origin_session_id", "title",
        "reason", "summary", "error", "updated_at", "created_at", "state", "can_acknowledge"}
    assert set(out["cards"][0]["state"]) == {"read", "acknowledged", "model_claim", "assignment_status"}


def test_another_owners_agent_artifact_and_controls_are_404_not_403(rt):
    rt.svc_.set_capability(True, role="owner")
    acc = rt.agent("a1", owner=A)
    rt.art_.write_artifact(agent_id="a1", run_id=acc["run_id"], name="final.txt", data="x",
                           assignment_id=acc["assignment_id"], owner_user_id=A)
    assert rt.call(R.artifact, "a1", acc["run_id"], "final.txt")["content"] == "x"
    rt.som_(B)
    assert rt.http(R.agent, "a1") == 404
    assert rt.http(R.artifact, "a1", acc["run_id"], "final.txt") == 404
    assert rt.http(R.artifact, "a1", acc["run_id"], "final.txt", session=S1) == 404
    assert rt.http(R.message, "a1", R.MessageBody(content="hej")) == 404
    assert rt.http(R.followup, "a1", R.FollowupBody(goal="nyt")) == 404
    assert rt.http(R.stop, "a1") == 404
    assert rt.http(R.close, "a1") == 404
    assert rt.http(R.acknowledge, acc["assignment_id"]) == 404
    assert rt.http(R.read, "agent", acc["assignment_id"]) == 404
    assert rt.call(R.overview)["agents"] == [] and rt.call(R.feed)["cards"] == []
    reg = rt.c_._conn().execute("SELECT status, lifecycle_status FROM agent_registry WHERE agent_id='a1'").fetchone()
    assert (reg["status"], reg["lifecycle_status"]) == ("planned", "available")


def test_message_and_stop_return_accept_receipts_not_confirmation(rt):
    rt.svc_.set_capability(True, role="owner")
    rt.agent("a1")
    m = rt.call(R.message, "a1", R.MessageBody(content="hej"))
    assert m["receipt"] == {"kind": "message", "accepted": True, "confirmed": False, "code": "",
                            "state": "accepted", "delivered": False}
    s = rt.call(R.stop, "a1", R.StopBody(note="nok"))
    assert s["status"] == "stop_requested" and s["receipt"]["confirmed"] is False


def test_the_engine_being_off_never_blocks_control_of_accepted_work(rt):
    rt.agent("a1")
    for fn, body in ((R.message, R.MessageBody(content="hej")),):
        try:
            rt.call(fn, "a1", body)
        except HTTPException as e:
            assert e.status_code != 403, "kill switchen maa kun blokere NYT arbejde (spec 12.4)"
    assert rt.call(R.overview)["capability"]["enabled"] is False                     # laesning virker stadig


def test_the_routes_are_mounted_in_the_app():
    from apps.api.jarvis_api.app import app

    paths = {getattr(r, "path", "") for r in app.routes}
    assert {"/agents/contract/overview", "/agents/contract/feed", "/agents/contract/agents/{agent_id}",
            "/agents/contract/agents/{agent_id}/stop", "/agents/contract/agents/{agent_id}/message",
            "/agents/contract/assignments/{assignment_id}/acknowledge",
            "/agents/contract/agents/{agent_id}/artifacts/{run_id}/{name}"} <= paths


# --- Desk-fixturen: feltnavne pinnet i BEGGE ender ------------------------------------------------------------

import json  # noqa: E402
import os  # noqa: E402
from pathlib import Path  # noqa: E402

FIXTURE = Path(__file__).resolve().parents[1] / "apps/jarvis-desk/src/lib/__fixtures__/agentContract.json"

#: Stier hvor nøglerne læses af Desk. Fixturen indeholder rigtige svar fra ruterne ovenfor.
_PATHS = ["overview", "overview.counts", "overview.capability", "overview.agents.0", "overview.agents.0.route",
          "overview.agents.0.heartbeat", "overview.agents.0.last_message", "overview.agents.1.error", "overview.groups.0",
          "detail", "detail.agent", "detail.assignments.0", "detail.assignments.0.outcome", "detail.assignments.0.routes.0",
          "detail.runs.0", "detail.messages.0", "detail.tool_calls.0", "detail.approvals.0", "detail.artifacts.0",
          "feed", "feed.counts", "feed.cards.0", "feed.cards.0.state", "feed.approval_card.approval",
          "message", "message.receipt", "stop", "stop.receipt", "artifact"]


def _scrub(x):
    """Fixturen bærer feltnavne, ikke værdier: lange hex-strenge (digests, checksummer) nulstilles, så de hverken
    driver fra kørsel til kørsel eller ligner en hemmelighed for detect-secrets."""
    import re
    if isinstance(x, dict):
        return {k: _scrub(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_scrub(v) for v in x]
    if isinstance(x, str) and re.fullmatch(r"[0-9a-f]{32,}", x):
        return "0" * len(x)
    return x


def _at(obj, path):
    for part in path.split("."):
        obj = obj[int(part)] if isinstance(obj, list) else obj[part]
    return obj


def _live_payloads(rt):
    import core.runtime.db_agent_approvals as appr
    from core.runtime import db_agent_route
    from core.runtime.db_agent_runtime import create_agent_message, create_agent_registry_entry, create_agent_run

    rt.svc_.set_capability(True, role="owner")
    acc = rt.agent("agent-a", run="running")
    create_agent_registry_entry(agent_id="agent-kid", role="researcher", goal="del-opgave", parent_agent_id="agent-a",
                                council_id="raad-1")
    rt.c_.bind_agent_owner(agent_id="agent-kid", owner_user_id=A, owner_session_id=S1)
    kid = rt.c_.accept_assignment(agent_id="agent-kid", owner_user_id=A, origin_session_id=S1, goal="del-opgave",
                                  parent_agent_id="agent-a", parent_run_id="pr")
    cn = rt.c_._conn()            # ÉN forbindelse: et nyt _conn()-kald ruller en aaben transaktion tilbage
    cn.execute("UPDATE agent_runs SET status='failed', input_tokens=10, output_tokens=5, cost_usd=0.001, "
               "started_at='2026-10-07T10:00:00Z' WHERE run_id=?", (kid["run_id"],))
    cn.execute("UPDATE agent_registry SET council_id='raad-1' WHERE agent_id='agent-a'")
    cn.commit()
    rt.c_.commit_terminal_outcome(assignment_id=kid["assignment_id"], status="failed", summary="gik galt",
                                  error_code="AGENT_FAILED", error_phase="model")
    db_agent_route.record_decision(assignment_id=acc["assignment_id"], agent_id="agent-a", owner_user_id=A,
                                   decision={"route_source": "agent_pool", "provider": "p", "model": "m"}, attempt=1)
    import core.runtime.db_agent_lease as lease
    lease.acquire(assignment_id=acc["assignment_id"], holder="w1")
    create_agent_message(message_id="m1", thread_id="t", agent_id="agent-a", direction="agent->jarvis",
                         role="assistant", kind="result", content="halvvejs")
    c = rt.c_._conn()
    c.execute("INSERT INTO agent_tool_calls (tool_call_id, run_id, agent_id, tool_name, status, started_at, created_at) "
              "VALUES ('tc1', ?, 'agent-a', 'read_file', 'completed', '2026-10-07T10:00:01Z', '2026-10-07T10:00:01Z')",
              (acc["run_id"],))
    c.commit()
    rt.art_.write_artifact(agent_id="agent-a", run_id=acc["run_id"], name="final.txt", data="svar",
                           assignment_id=acc["assignment_id"], owner_user_id=A)
    appr.request(owner_user_id=A, origin_session_id=S1, assignment_id=acc["assignment_id"], tool_name="bash",
                 arguments={"command": "make"}, run_id=acc["run_id"])
    overview = rt.call(R.overview, scope="all")
    overview["agents"].sort(key=lambda r: r["agent_id"])           # agent-a foerst, agent-kid (fejl) som nr. 2
    feed = rt.call(R.feed)
    card_approval = next(c for c in feed["cards"] if c["ref_kind"] == "approval")
    feed["cards"].sort(key=lambda c: (c["ref_kind"] != "agent", c["agent_id"]))
    feed["approval_card"] = card_approval
    return {
        "overview": overview, "detail": rt.call(R.agent, "agent-a"), "feed": feed,
        "message": rt.call(R.message, "agent-a", R.MessageBody(content="hej")),
        "stop": rt.call(R.stop, "agent-a"),
        "artifact": rt.call(R.artifact, "agent-a", acc["run_id"], "final.txt"),
    }


def test_the_committed_desk_fixture_pins_the_same_field_names_as_the_real_routes(rt):
    live = _live_payloads(rt)
    if os.environ.get("REGEN_DESK_FIXTURE") == "1":
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE.write_text(json.dumps(_scrub(live), ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    stored = json.loads(FIXTURE.read_text())
    for path in _PATHS:
        assert sorted(_at(stored, path)) == sorted(_at(live, path)), path
