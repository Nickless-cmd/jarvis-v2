"""F1: agent-contract-v1 service - rigtig sqlite, falsk model, baggrundsstart under kontrol."""
from __future__ import annotations

import pytest

O, S, R = "bjorn", "sess-1", "visible-p"


@pytest.fixture
def sv(isolated_runtime, monkeypatch):
    import core.runtime.db_agent_contract as c
    import core.services.agent_contract_service as svc
    from core.services import agent_runtime_spawn as M

    class H:
        k, svc_ = c, svc
        started: list = []

        def on(self):
            svc.set_capability(True, role="owner")

        def run_all(self):
            fns, self.started[:] = list(self.started), []
            for f in fns:
                f()

        def d(self, **kw):
            base = dict(owner_user_id=O, origin_session_id=S, goal="find X", parent_run_id=R)
            base.update(kw)
            return svc.dispatch_agent(**base)

        def rows(self, table):
            return c._conn().execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    h = H()
    h.started = []
    monkeypatch.setattr(svc, "_run_in_background", lambda fn: h.started.append(fn))

    class _F:
        def execute_with_role_or_fallback(self, **kw):
            return {"text": "klart: X i y.py", "input_tokens": 3, "output_tokens": 2,
                    "status": "completed"}

    monkeypatch.setattr(M, "agent_tools_enabled", lambda: False)
    monkeypatch.setattr(M, "_facade", lambda: _F())
    from core.services import in_flight_runs as ifr
    ifr._mutate(lambda r: r.clear())   # afskaermningen deles af hele sessionen
    yield h
    ifr._mutate(lambda r: r.clear())


# --- kapabilitet -------------------------------------------------------------------

def test_capability_starts_off_and_only_the_owner_can_turn_it_on(sv):
    svc = sv.svc_
    assert svc.capability_enabled() is False
    assert svc.capability_status()["enabled"] is False and svc.capability_status()["reason"]
    assert svc.set_capability(True, role="member") is False
    assert svc.capability_enabled() is False
    assert svc.set_capability(True, role="owner") is True
    assert svc.set_capability(False, role="member") is False       # kill switch: alle maa
    assert svc.capability_enabled() is False


def test_capability_read_failure_is_closed(sv, monkeypatch):
    import core.runtime.db_core as core

    sv.on()
    monkeypatch.setattr(core, "get_runtime_state_bool",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("db")))
    assert sv.svc_.capability_enabled() is False


def test_every_operation_is_refused_when_off_and_creates_nothing(sv):
    svc = sv.svc_
    base = dict(owner_user_id=O, origin_session_id=S)
    outs = [svc.dispatch_agent(goal="x", **base),
            svc.followup_agent(agent_id="a", goal="x", **base),
            svc.send_message(agent_id="a", content="x", **base),
            svc.interrupt_agent(agent_id="a", **base),
            svc.close_agent(agent_id="a", **base),
            svc.wait_agents(assignment_ids=["a"], **base)]
    assert [(o["status"], o["code"]) for o in outs] == [("error", "POLICY_DENIED")] * 6
    assert (sv.rows("agent_registry"), sv.rows("agent_assignments"), sv.started) == (0, 0, [])


# --- dispatch --------------------------------------------------------------------------

def test_dispatch_returns_ids_before_the_agent_has_run_then_completes(sv):
    sv.on()
    out = sv.d()
    assert out["status"] == "accepted" and out["assignment_status"] == "queued"
    assert out["agent_id"].startswith("agent-") and out["assignment_id"].startswith("asg-")
    assert out["run_id"] and out["replayed"] is False and out["contract_version"] == "agent-contract-v1"
    assert len(sv.started) == 1                      # planlagt, ikke koert: accept != gennemfoerelse
    assert sv.k.list_pending_results(owner_user_id=O, origin_session_id=S) == []
    sv.run_all()
    a = sv.k.get_assignment(assignment_id=out["assignment_id"], owner_user_id=O)
    assert a["status"] == "completed"
    (m,) = sv.k.list_pending_results(owner_user_id=O, origin_session_id=S)
    assert m["parent_run_id"] == R and m["last_run_id"] == out["run_id"]


@pytest.mark.parametrize("kw,code", [
    ({"goal": "  "}, "INVALID_SCOPE"),
    ({"owner_user_id": ""}, "INVALID_SCOPE"),
    ({"origin_session_id": ""}, "INVALID_SCOPE"),
    ({"target": "client:laptop"}, "CLIENT_OFFLINE"),
    ({"target": "mars"}, "INVALID_SCOPE"),
])
def test_rejected_dispatch_leaves_no_agent_assignment_or_execution(sv, kw, code):
    sv.on()
    out = sv.d(**kw)
    assert (out["status"], out["code"], out["phase"]) == ("error", code, "admission")
    assert (sv.rows("agent_registry"), sv.rows("agent_assignments"), sv.rows("agent_runs"),
            sv.started) == (0, 0, 0, [])


def test_idempotent_dispatch_replays_and_conflict_is_refused(sv):
    sv.on()
    first = sv.d(idempotency_key="k1")
    again = sv.d(idempotency_key="k1")
    assert again["replayed"] is True and again["assignment_id"] == first["assignment_id"]
    assert (sv.rows("agent_registry"), sv.rows("agent_assignments"), len(sv.started)) == (1, 1, 1)
    clash = sv.d(idempotency_key="k1", goal="noget helt andet")
    assert clash["code"] == "IDEMPOTENCY_CONFLICT"
    assert (sv.rows("agent_registry"), sv.rows("agent_assignments")) == (1, 1)
    # samme noegle i en ANDEN session er en anden dispatch
    other = sv.d(idempotency_key="k1", origin_session_id="sess-2")
    assert other["replayed"] is False and sv.rows("agent_assignments") == 2


def test_capacity_per_parent_blocks_the_seventh_child_without_creating_it(sv):
    sv.on()
    for i in range(6):
        assert sv.d(goal=f"opgave {i}")["status"] == "accepted"
    out = sv.d(goal="den syvende")
    assert (out["status"], out["code"]) == ("error", "CAPACITY")
    assert sv.rows("agent_registry") == 6 and sv.rows("agent_assignments") == 6


# --- followup / message -----------------------------------------------------------------

def test_followup_gives_the_same_agent_a_new_assignment_and_run(sv):
    sv.on()
    first = sv.d()
    sv.run_all()
    fu = sv.svc_.followup_agent(owner_user_id=O, origin_session_id=S, agent_id=first["agent_id"],
                                goal="nu y", parent_run_id=R)
    assert fu["status"] == "accepted" and fu["agent_id"] == first["agent_id"]
    assert fu["assignment_id"] != first["assignment_id"] and fu["run_id"] != first["run_id"]
    sv.run_all()
    assert sv.k.get_assignment(assignment_id=fu["assignment_id"], owner_user_id=O)["status"] == "completed"
    assert sv.rows("agent_registry") == 1 and len(sv.k.list_pending_results(
        owner_user_id=O, origin_session_id=S)) == 2


def test_followup_while_busy_other_owner_and_closed_agent_are_refused(sv):
    sv.on()
    first = sv.d()
    svc = sv.svc_
    busy = svc.followup_agent(owner_user_id=O, origin_session_id=S, agent_id=first["agent_id"], goal="x")
    assert busy["code"] == "CAPACITY"
    foreign = svc.followup_agent(owner_user_id="anden", origin_session_id=S,
                                 agent_id=first["agent_id"], goal="x")
    assert foreign["code"] == "INVALID_SCOPE"
    sv.run_all()
    svc.close_agent(owner_user_id=O, origin_session_id=S, agent_id=first["agent_id"])
    closed = svc.followup_agent(owner_user_id=O, origin_session_id=S, agent_id=first["agent_id"], goal="x")
    assert closed["code"] == "POLICY_DENIED"
    assert sv.rows("agent_assignments") == 1


def test_message_to_busy_agent_is_stored_with_honest_delivery(sv):
    sv.on()
    first = sv.d()
    out = sv.svc_.send_message(owner_user_id=O, origin_session_id=S, agent_id=first["agent_id"],
                               content="husk edge-casen")
    assert out["status"] == "accepted" and out["delivery"] == "accepted"
    assert out["message_id"] and out["assignment_id"] == first["assignment_id"]
    assert sv.rows("agent_assignments") == 1
    row = sv.k._conn().execute("SELECT * FROM agent_messages WHERE message_id=?",
                               (out["message_id"],)).fetchone()
    assert (row["direction"], row["kind"]) == ("jarvis->agent", "parent-message")
    assert "husk edge-casen" in row["content"]


def test_message_to_idle_agent_triggers_a_new_assignment(sv):
    sv.on()
    first = sv.d()
    sv.run_all()
    out = sv.svc_.send_message(owner_user_id=O, origin_session_id=S, agent_id=first["agent_id"],
                               content="en ting mere")
    assert out["status"] == "accepted" and out["triggered_assignment"] is True
    assert out["assignment_id"] != first["assignment_id"] and sv.rows("agent_assignments") == 2


def test_message_to_foreign_or_unknown_agent_is_refused(sv):
    sv.on()
    first = sv.d()
    for owner, aid in (("anden", first["agent_id"]), (O, "findes-ikke")):
        out = sv.svc_.send_message(owner_user_id=owner, origin_session_id=S, agent_id=aid, content="x")
        assert (out["status"], out["code"]) == ("error", "INVALID_SCOPE")


# --- interrupt / close ------------------------------------------------------------------

def test_interrupt_requests_a_stop_and_settles_the_assignment_as_cancelled(sv):
    sv.on()
    first = sv.d()
    out = sv.svc_.interrupt_agent(owner_user_id=O, origin_session_id=S, agent_id=first["agent_id"])
    assert out["status"] == "stop_requested" and out["assignment_id"] == first["assignment_id"]
    a = sv.k.get_assignment(assignment_id=first["assignment_id"], owner_user_id=O)
    assert a["status"] == "cancelled"
    (m,) = sv.k.list_pending_results(owner_user_id=O, origin_session_id=S)
    assert '"CANCELLED"' in m["payload_json"]
    again = sv.svc_.interrupt_agent(owner_user_id=O, origin_session_id=S, agent_id=first["agent_id"])
    assert again["status"] == "noop"
    foreign = sv.svc_.interrupt_agent(owner_user_id="anden", origin_session_id=S, agent_id=first["agent_id"])
    assert foreign["code"] == "INVALID_SCOPE"


def test_close_is_graceful_busy_agent_stays_closing_until_it_finishes(sv):
    sv.on()
    first = sv.d()
    out = sv.svc_.close_agent(owner_user_id=O, origin_session_id=S, agent_id=first["agent_id"])
    assert out["lifecycle_status"] == "closing"
    assert sv.k.get_assignment(assignment_id=first["assignment_id"], owner_user_id=O)["status"] == "queued"
    sv.run_all()
    assert sv.svc_.settle_closing(first["agent_id"], O) == "closed"
    idle = sv.d(goal="anden")
    sv.run_all()
    assert sv.svc_.close_agent(owner_user_id=O, origin_session_id=S,
                               agent_id=idle["agent_id"])["lifecycle_status"] == "closed"


# --- list / wait ------------------------------------------------------------------------

def test_list_agents_shows_only_the_owners_with_unprocessed_counts(sv):
    sv.on()
    a = sv.d()
    sv.d(goal="b", origin_session_id="sess-2")
    sv.run_all()
    mine = sv.svc_.list_agents(owner_user_id=O)
    assert mine["count"] == 2 and {r["assignment_status"] for r in mine["agents"]} == {"completed"}
    assert all(r["unprocessed"] == 1 for r in mine["agents"])
    one = sv.svc_.list_agents(owner_user_id=O, origin_session_id=S)
    assert [r["agent_id"] for r in one["agents"]] == [a["agent_id"]]
    assert sv.svc_.list_agents(owner_user_id="anden")["count"] == 0
    assert sv.svc_.list_agents(owner_user_id="")["code"] == "INVALID_SCOPE"


def test_wait_reports_state_registers_a_wake_contract_and_refuses_foreign_ids(sv):
    sv.on()
    a, b = sv.d(goal="a"), sv.d(goal="b")
    ids = [a["assignment_id"], b["assignment_id"]]
    svc = sv.svc_
    pending = svc.wait_agents(owner_user_id=O, origin_session_id=S, assignment_ids=ids)
    assert pending["satisfied"] is False and not any(v["terminal"] for v in pending["assignments"])
    reg = svc.wait_agents(owner_user_id=O, origin_session_id=S, assignment_ids=ids,
                          wake_if_run_ends=True, parent_run_id=R)
    assert reg["wait_contract"]["status"] == "registered"
    sv.run_all()
    done = svc.wait_agents(owner_user_id=O, origin_session_id=S, assignment_ids=ids)
    assert done["satisfied"] is True
    first = svc.wait_agents(owner_user_id=O, origin_session_id=S, assignment_ids=ids,
                            condition="first_terminal")
    assert first["satisfied"] is True
    foreign = svc.wait_agents(owner_user_id="anden", origin_session_id=S, assignment_ids=ids)
    assert foreign["code"] == "INVALID_SCOPE"
    bad = svc.wait_agents(owner_user_id=O, origin_session_id=S, assignment_ids=ids, condition="nej")
    assert bad["code"] == "INVALID_SCOPE"


def test_wait_with_timeout_returns_unsatisfied_when_nothing_finishes(sv, monkeypatch):
    sv.on()
    a = sv.d()
    monkeypatch.setattr(sv.svc_, "_POLL_SECONDS", 0.01)
    out = sv.svc_.wait_agents(owner_user_id=O, origin_session_id=S,
                              assignment_ids=[a["assignment_id"]], timeout_seconds=0.05)
    assert out["satisfied"] is False and "wait_contract" not in out


def test_wait_can_return_the_full_output_through_the_owner_checked_artifact(sv, monkeypatch):
    sv.on()
    long = "x" * 30000

    class _F:
        def execute_with_role_or_fallback(self, **kw):
            return {"text": long, "input_tokens": 1, "output_tokens": 1, "status": "completed"}

    from core.services import agent_runtime_spawn as M
    monkeypatch.setattr(M, "_facade", lambda: _F())
    a = sv.d()
    sv.run_all()
    ids = [a["assignment_id"]]
    svc = sv.svc_
    plain = svc.wait_agents(owner_user_id=O, origin_session_id=S, assignment_ids=ids)
    assert "output" not in plain["assignments"][0]
    full = svc.wait_agents(owner_user_id=O, origin_session_id=S, assignment_ids=ids, include_output=True)
    o = full["assignments"][0]["output"]
    assert (o["status"], len(o["content"]), o["truncated"], o["size"]) == ("ok", 20000, True, 30000)
    assert full["assignments"][0]["result_ref"].endswith("/result.json")
    page2 = svc.wait_agents(owner_user_id=O, origin_session_id=S, assignment_ids=ids,
                            include_output=True, output_offset=20000)
    assert len(page2["assignments"][0]["output"]["content"]) == 10000
    assert page2["assignments"][0]["output"]["truncated"] is False


def test_output_is_reported_precisely_when_the_artifact_is_gone(sv):
    import os

    sv.on()
    a = sv.d()
    sv.run_all()
    rec = sv.k._conn().execute("SELECT path FROM agent_artifacts WHERE name='final.txt'").fetchone()
    os.unlink(rec["path"])
    out = sv.svc_.wait_agents(owner_user_id=O, origin_session_id=S,
                              assignment_ids=[a["assignment_id"]], include_output=True)
    assert out["assignments"][0]["output"]["status"] == "MISSING"


def test_output_of_a_running_assignment_is_not_attached(sv):
    sv.on()
    a = sv.d()
    out = sv.svc_.wait_agents(owner_user_id=O, origin_session_id=S,
                              assignment_ids=[a["assignment_id"]], include_output=True)
    assert "output" not in out["assignments"][0]
