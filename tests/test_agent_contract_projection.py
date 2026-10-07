"""G: Desks DB-projektion af agentkontrakten - ejergraense, status, taellere, feed, handlinger.

Rigtig sqlite (isolated_runtime) og seedede kontrakt-raekker; service-handlingerne observeres paa DB og
paa de eksisterende service-funktioner, ikke paa et opfundet svar.
"""
from __future__ import annotations

import json

import pytest

A, B, S1, S2 = "bjorn", "anden", "sess-1", "sess-2"


@pytest.fixture
def pj(isolated_runtime, monkeypatch):
    import core.runtime.db_agent_approvals as appr
    import core.runtime.db_agent_artifacts as art
    import core.runtime.db_agent_contract as c
    import core.runtime.db_agent_lease as lease
    import core.services.agent_contract_projection as proj
    import core.services.agent_contract_service as svc
    from core.runtime.db_agent_runtime import create_agent_message, create_agent_registry_entry
    from core.services import in_flight_runs as ifr

    ifr._mutate(lambda r: r.clear())
    monkeypatch.setattr("core.identity.owner_resolver.owner_user_id", lambda: "platform-ejer")
    started: list = []
    monkeypatch.setattr(svc, "_run_in_background", lambda fn: started.append(fn))

    class H:
        proj_, c_, svc_, appr_, art_, lease_ = proj, c, svc, appr, art, lease
        started_ = started

        def on(self):
            svc.set_capability(True, role="owner")

        def agent(self, name, *, owner=A, session=S1, role="researcher", goal="find X", run="running",
                  council="", parent="", terminal=None, summary="", err=("", ""), tokens=(0, 0), cost=0.0):
            create_agent_registry_entry(agent_id=name, role=role, goal=goal, council_id=council,
                                        parent_agent_id=parent)
            c.bind_agent_owner(agent_id=name, owner_user_id=owner, owner_session_id=session)
            acc = c.accept_assignment(agent_id=name, owner_user_id=owner, origin_session_id=session, goal=goal,
                                      parent_agent_id=parent or "jarvis", parent_run_id="pr")
            conn = c._conn()
            conn.execute("UPDATE agent_runs SET status=?, input_tokens=?, output_tokens=?, cost_usd=?, "
                         "started_at='2026-10-07T10:00:00Z' WHERE run_id=?",
                         (run, tokens[0], tokens[1], cost, acc["run_id"]))
            if run in ("running", "outcome_unknown", "waiting_for_approval", "waiting_for_budget",
                       "waiting_for_client"):
                conn.execute("UPDATE agent_assignments SET status=? WHERE assignment_id=?",
                             ("active" if run == "running" else "waiting", acc["assignment_id"]))
            conn.commit()
            if terminal:
                c.commit_terminal_outcome(assignment_id=acc["assignment_id"], status=terminal, summary=summary,
                                          error_code=err[0], error_phase=err[1])
            return acc

        def msg(self, name, text, direction="agent->jarvis", kind="result"):
            create_agent_message(message_id=f"m-{name}-{abs(hash(text)) % 99999}", thread_id=f"t-{name}",
                                 agent_id=name, direction=direction, role="assistant", kind=kind, content=text)

        def row(self, out, name):
            return next(r for r in out["agents"] if r["agent_id"] == name)

    yield H()
    ifr._mutate(lambda r: r.clear())


# --- klassifikation (ren funktion, tabel) -----------------------------------------------------------------

@pytest.mark.parametrize("a,r,bucket", [
    ("queued", "queued", "queued"), ("active", "running", "active"),
    ("waiting", "waiting_for_approval", "waiting_for_approval"),
    ("waiting", "waiting_for_budget", "waiting_for_budget"),
    ("waiting", "waiting_for_client", "waiting_for_client"),
    ("waiting", "outcome_unknown", "outcome_unknown"),
    ("outcome_unknown", "running", "outcome_unknown"),          # uanset hvor tilstanden skrives
    ("active", "failed", "retry_pending"), ("active", "completed", "settling"),
    ("completed", "completed", "done"), ("failed", "failed", "failed"),
    ("timed_out", "failed", "timed_out"), ("cancelled", "cancelled", "cancelled"),
    ("active", "noget-nyt", "unknown"), ("waiting", "", "unknown"),
])
def test_classify_reads_assignment_and_latest_run_status_never_text(pj, a, r, bucket):
    assert pj.proj_.classify(a, r) == bucket


# --- ejergraensen -------------------------------------------------------------------------------------------

def test_an_owner_sees_only_their_own_agents_never_a_foreign_or_legacy_one(pj):
    pj.agent("mine", owner=A)
    pj.agent("theirs", owner=B, session="sx")
    from core.runtime.db_agent_runtime import create_agent_registry_entry
    create_agent_registry_entry(agent_id="legacy", role="r", goal="gammel")        # legacy_unscoped
    out_a = pj.proj_.overview(A, scope="all")
    out_b = pj.proj_.overview(B, scope="all")
    assert [r["agent_id"] for r in out_a["agents"]] == ["mine"]
    assert [r["agent_id"] for r in out_b["agents"]] == ["theirs"]
    for bad in ("", "   ", "legacy_unscoped"):
        out = pj.proj_.overview(bad)
        assert (out["status"], out["code"]) == ("error", "INVALID_SCOPE") and "agents" not in out
    assert pj.proj_.agent_detail(A, "theirs") is None and pj.proj_.agent_detail(A, "legacy") is None
    assert pj.proj_.agent_detail(B, "mine") is None
    assert pj.proj_.agent_detail(A, "mine")["agent"]["agent_id"] == "mine"


def test_a_foreign_session_filter_does_not_widen_access_for_a_resumed_session(pj):
    pj.agent("a1", owner=A, session=S1)
    # ejeren genoptager i en ANDEN session: oprindelsessessionen aendres ikke, og en anden ejer faar intet
    assert [r["agent_id"] for r in pj.proj_.overview(A, scope="all", session_id=S1)["agents"]] == ["a1"]
    assert pj.proj_.overview(A, scope="all", session_id=S2)["agents"] == []
    assert pj.proj_.overview(B, scope="all", session_id=S1)["agents"] == []


# --- taellere og panel --------------------------------------------------------------------------------------

def test_active_count_is_separate_from_attention_and_success_leaves_the_panel(pj):
    pj.agent("run1")                                                       # active
    pj.agent("run2", run="queued")
    pj.agent("wapp", run="waiting_for_approval")
    pj.agent("unk", run="outcome_unknown")
    pj.agent("wcli", run="waiting_for_client")
    pj.agent("bad", run="failed", terminal="failed", err=("AGENT_FAILED", "model"))
    pj.agent("tmo", run="failed", terminal="timed_out", err=("TIMED_OUT", "budget"))
    pj.agent("stp", run="cancelled", terminal="cancelled", err=("CANCELLED", "recovery"))
    pj.agent("ok", run="completed", terminal="completed", summary="alt fint")
    out = pj.proj_.overview(A)
    assert sorted(r["agent_id"] for r in out["agents"]) == sorted(
        ["run1", "run2", "wapp", "unk", "wcli", "bad", "tmo", "stp"])                 # succes forsvinder
    assert out["counts"] == {"active": 1, "queued": 1, "waiting": 2, "blocked": 1, "attention": 5, "open": 5}
    assert {r["agent_id"] for r in out["agents"] if r["attention"]} == {"wapp", "unk", "bad", "tmo", "stp"}
    assert pj.row(out, "unk")["bucket"] == "outcome_unknown"
    assert pj.row(out, "unk")["reason"].startswith("Udfaldet er ukendt")
    assert pj.row(out, "bad")["error"] == {"phase": "model", "code": "AGENT_FAILED", "reason": ""}
    assert pj.proj_.overview(A, scope="all")["agents"].__len__() == 9              # hele traeet har den med


def test_failure_stays_until_acknowledged_open_work_can_never_be_acknowledged_away(pj):
    bad = pj.agent("bad", run="failed", terminal="failed", err=("AGENT_FAILED", "model"))
    unk = pj.agent("unk", run="outcome_unknown")
    pj.agent("ok", run="completed", terminal="completed")
    assert pj.proj_.acknowledge(B, bad["assignment_id"])["code"] == "INVALID_SCOPE"      # en anden ejer
    assert pj.proj_.overview(A)["counts"]["attention"] == 2
    r = pj.proj_.acknowledge(A, unk["assignment_id"])
    assert (r["status"], r["code"]) == ("error", "INVALID_TRANSITION")                  # uafklaret skrivning
    assert pj.proj_.overview(A)["counts"]["attention"] == 2
    assert pj.proj_.acknowledge(A, bad["assignment_id"])["acknowledged"] is True
    out = pj.proj_.overview(A)
    assert [r["agent_id"] for r in out["agents"]] == ["unk"] and out["counts"]["attention"] == 1
    assert pj.proj_.acknowledge(A, bad["assignment_id"])["acknowledged"] is True          # idempotent


def test_a_council_is_a_grouping_of_ordinary_runs_with_member_status_and_synthesis(pj):
    pj.agent("m1", council="c1", role="member", run="completed", terminal="completed")
    pj.agent("m2", council="c1", role="member", run="failed", terminal="failed", err=("AGENT_FAILED", "model"))
    pj.agent("syn", council="c1", role="synthesis", run="running")
    g, = pj.proj_.overview(A, scope="all")["groups"]
    assert g["council_id"] == "c1" and g["synthesis"] == {"agent_id": "syn", "bucket": "active"}
    assert sorted(g["members"], key=lambda m: m["agent_id"]) == [
        {"agent_id": "m1", "role": "member", "bucket": "done"},
        {"agent_id": "m2", "role": "member", "bucket": "failed"}]
    assert (g["counts"]["active"], g["counts"]["attention"]) == (1, 1)


# --- inspector -----------------------------------------------------------------------------------------------

def test_detail_carries_route_cost_heartbeat_artifacts_approvals_without_raw_arguments_or_paths(pj):
    acc = pj.agent("a1", parent="", tokens=(100, 20), cost=0.0123)
    pj.agent("kid", parent="a1")
    from core.runtime import db_agent_route
    db_agent_route.record_decision(assignment_id=acc["assignment_id"], agent_id="a1", owner_user_id=A,
                                   decision={"route_source": "agent_pool", "provider": "copilot-premium",
                                             "model": "claude-sonnet-5"}, attempt=1)
    tok = pj.lease_.acquire(assignment_id=acc["assignment_id"], holder="w1")
    assert tok == 1
    pj.art_.write_artifact(agent_id="a1", run_id=acc["run_id"], name="final.txt", data="fuldt svar",
                           assignment_id=acc["assignment_id"], owner_user_id=A)
    r = pj.appr_.request(owner_user_id=A, origin_session_id=S1, assignment_id=acc["assignment_id"],
                         tool_name="bash", arguments={"command": "rm -rf build", "_runtime_x": 1}, run_id=acc["run_id"])
    d = pj.proj_.agent_detail(A, "a1")
    ag = d["agent"]
    assert ag["route"] == {"route_source": "agent_pool", "provider": "copilot-premium", "model": "claude-sonnet-5"}
    assert (ag["tokens"], ag["cost_usd"], ag["heartbeat"]["state"]) == (120, 0.0123, "ok")
    assert d["children"] == ["kid"] and ag["children"] == 1
    assert [(a["name"], a["size"]) for a in d["artifacts"]] == [("final.txt", len("fuldt svar"))]
    ap, = d["approvals"]
    assert ap["approval_id"] == r["approval_id"] and ap["args_digest"] == r["args_digest"]
    blob = json.dumps(d)
    assert "arguments_json" not in blob and "_runtime_x" not in blob and "agent-artifacts" not in blob
    assert d["assignments"][0]["routes"][0]["route_source"] == "agent_pool"


def test_cost_is_unknown_not_zero_when_no_run_reported_usage(pj):
    pj.agent("a1")
    assert pj.row(pj.proj_.overview(A), "a1")["cost_usd"] is None
    pj.agent("a2", tokens=(5, 5), cost=0.0)
    assert pj.row(pj.proj_.overview(A), "a2")["cost_usd"] == 0.0


def test_an_expired_lease_shows_as_such_it_is_not_read_as_alive(pj):
    acc = pj.agent("a1")
    from datetime import UTC, datetime, timedelta
    pj.lease_.acquire(assignment_id=acc["assignment_id"], holder="w", now=datetime.now(UTC) - timedelta(hours=1))
    assert pj.row(pj.proj_.overview(A), "a1")["heartbeat"]["state"] == "expired"


# --- artefakter ------------------------------------------------------------------------------------------------

def test_full_output_needs_owner_agent_and_the_origin_session(pj):
    acc = pj.agent("a1")
    pj.art_.write_artifact(agent_id="a1", run_id=acc["run_id"], name="final.txt", data="hemmeligt svar",
                           assignment_id=acc["assignment_id"], owner_user_id=A)
    ok = pj.proj_.read_artifact(A, "a1", acc["run_id"], "final.txt")
    assert (ok["status"], ok["content"]) == ("ok", "hemmeligt svar")
    assert pj.proj_.read_artifact(A, "a1", acc["run_id"], "final.txt", session_id=S1)["status"] == "ok"
    nf = {"status": "NOT_FOUND", "ref": f"{acc['run_id']}/final.txt"}
    assert pj.proj_.read_artifact(B, "a1", acc["run_id"], "final.txt") == nf              # anden ejer
    assert pj.proj_.read_artifact(B, "a1", acc["run_id"], "final.txt", session_id=S1) == nf  # ...ogsaa m. session
    assert pj.proj_.read_artifact(A, "a1", acc["run_id"], "final.txt", session_id=S2) == nf  # forkert session
    assert pj.proj_.read_artifact(A, "andet", acc["run_id"], "final.txt") == nf           # forkert agent
    assert pj.proj_.read_artifact("legacy_unscoped", "a1", acc["run_id"], "final.txt") == nf
    assert pj.proj_.read_artifact("", "a1", acc["run_id"], "final.txt") == nf


# --- feed ------------------------------------------------------------------------------------------------------

def test_feed_has_one_card_per_assignment_success_under_svar_trouble_under_venter(pj):
    pj.agent("ok", run="completed", terminal="completed", summary="Fundet i y.py")
    pj.agent("bad", run="failed", terminal="failed", err=("AGENT_FAILED", "model"))
    pj.agent("unk", run="outcome_unknown")
    pj.agent("go")
    w = pj.agent("wapp", run="waiting_for_approval")
    r = pj.appr_.request(owner_user_id=A, origin_session_id=S1, assignment_id=w["assignment_id"], tool_name="bash",
                         arguments={"command": "make"}, run_id=w["run_id"])
    pj.agent("fremmed", owner=B, session="sx", run="failed", terminal="failed")
    out = pj.proj_.feed(A)
    by = {(c["ref_kind"], c["agent_id"]): c for c in out["cards"]}
    assert len(out["cards"]) == 6 and len({(c["ref_kind"], c["ref_id"]) for c in out["cards"]}) == 6
    assert by[("agent", "ok")]["section"] == "svar" and by[("agent", "ok")]["summary"] == "Fundet i y.py"
    for n in ("bad", "unk", "wapp"):
        assert by[("agent", n)]["section"] == "venter"
    assert by[("agent", "go")]["section"] == "aktiv"
    ap = by[("approval", "wapp")]
    assert ap["section"] == "venter" and ap["ref_id"] == r["approval_id"] and ap["origin_session_id"] == S1
    assert ap["approval"]["digest"] == r["args_digest"] and ap["summary"].startswith("bash(")
    assert out["counts"] == {"venter": 4, "svar": 1, "aktiv": 1, "unread": 6}
    assert all(c["origin_session_id"] == S1 for c in out["cards"])
    assert not any(c["agent_id"] == "fremmed" for c in out["cards"])


def test_a_card_shows_only_a_bounded_redacted_summary_never_the_full_output(pj):
    faelde = "pass" + "word=" + "hunter" + "2" * 8      # pragma: allowlist secret  (bygges; ingen fixture-noegle)
    long_out = f"Fundet i y.py, {faelde} " + "A" * 5000
    acc = pj.agent("ok", run="completed", terminal="completed", summary=long_out[:500])
    pj.art_.write_artifact(agent_id="ok", run_id=acc["run_id"], name="final.txt", data=long_out,
                           assignment_id=acc["assignment_id"], owner_user_id=A)
    card, = [c for c in pj.proj_.feed(A)["cards"] if c["agent_id"] == "ok"]
    assert card["summary"].startswith("Fundet i y.py, password=[")
    assert len(card["summary"]) <= pj.proj_.SUMMARY_LIMIT and "A" * 300 not in json.dumps(card)
    assert "hunter2" not in json.dumps(pj.proj_.feed(A)) and "hunter2" not in json.dumps(pj.proj_.overview(A))
    assert pj.proj_.safe_text("x\x00y\x07z   w") == "x y z w"


def test_an_unknown_run_status_is_attention_never_silence_read_as_success(pj):
    pj.agent("ny", run="noget-nyt")
    out = pj.proj_.overview(A)
    r = pj.row(out, "ny")
    assert (r["bucket"], r["attention"], r["reason"]) == ("unknown", True, "Ukendt tilstand – ikke tolket som succes")
    assert out["counts"] == {"active": 0, "queued": 0, "waiting": 0, "blocked": 0, "attention": 1, "open": 1}


def test_read_acknowledged_approved_and_model_claim_are_four_separate_states(pj):
    acc = pj.agent("bad", run="failed", terminal="failed", err=("AGENT_FAILED", "model"))
    card, = pj.proj_.feed(A)["cards"]
    assert card["state"] == {"read": False, "acknowledged": False, "model_claim": "accepted",
                             "assignment_status": "failed"}
    assert pj.proj_.mark_read(A, "agent", acc["assignment_id"]) is True
    card, = pj.proj_.feed(A)["cards"]
    assert (card["state"]["read"], card["state"]["acknowledged"], card["state"]["model_claim"]) == (
        True, False, "accepted")
    pj.c_.advance_delivery(message_id=pj.c_._conn().execute("SELECT message_id FROM agent_result_outbox").fetchone()[0],
                           owner_user_id=A, to_status="claimed_by_model_step")
    card, = pj.proj_.feed(A)["cards"]
    assert (card["state"]["read"], card["state"]["acknowledged"], card["state"]["model_claim"]) == (
        True, False, "claimed_by_model_step")                      # modellens claim kvitterer IKKE for brugeren
    assert pj.proj_.mark_read(B, "agent", acc["assignment_id"]) is False                 # en andens reference
    assert pj.proj_.acknowledge(A, acc["assignment_id"])["acknowledged"] is True
    assert pj.proj_.feed(A)["cards"] == []


def test_an_approved_approval_is_its_own_state_not_a_read_mark(pj):
    w = pj.agent("wapp", run="waiting_for_approval")
    r = pj.appr_.request(owner_user_id=A, origin_session_id=S1, assignment_id=w["assignment_id"], tool_name="bash",
                         arguments={"command": "make"}, run_id=w["run_id"])
    pj.appr_.decide(approval_id=r["approval_id"], decision="approve", actor_user_id=A, actor_kind="human",
                    digest=r["args_digest"])
    assert [c for c in pj.proj_.feed(A)["cards"] if c["ref_kind"] == "approval"] == []   # afgjort: ikke 'venter'
    assert pj.proj_.mark_read(A, "approval", r["approval_id"]) is True                   # reference findes, ikke godkendt


# --- handlinger ---------------------------------------------------------------------------------------------------

def test_actions_use_the_existing_service_with_the_session_from_the_db_and_accept_is_not_delivery(pj):
    pj.on()
    acc = pj.agent("a1", session=S1)
    out = pj.proj_.send_message(A, "a1", "tag den roede vej")
    assert out["status"] == "accepted" and out["delivery"] == "accepted" and out["assignment_id"] == acc["assignment_id"]
    assert out["receipt"] == {"kind": "message", "accepted": True, "confirmed": False, "code": "",
                              "state": "accepted", "delivered": False}
    assert out["audit_id"].startswith("desk-")
    stored = pj.c_._conn().execute("SELECT content, direction, kind FROM agent_messages WHERE agent_id='a1' "
                                   "AND kind='parent-message'").fetchone()
    assert stored["content"].startswith("[menneske") and out["audit_id"] in stored["content"]
    assert stored["content"].endswith("tag den roede vej")
    st = pj.proj_.stop(A, "a1")
    assert st["status"] == "stop_requested" and st["receipt"]["accepted"] and st["receipt"]["confirmed"] is False
    cl = pj.proj_.close(A, "a1")
    assert cl["status"] == "accepted" and cl["receipt"]["kind"] == "close"


def test_a_foreign_owner_cannot_message_stop_follow_up_or_close_and_nothing_is_written(pj):
    pj.on()
    pj.agent("a1", owner=A, session=S1)
    before = pj.c_._conn().execute("SELECT COUNT(*) FROM agent_messages").fetchone()[0]
    for call in (lambda: pj.proj_.send_message(B, "a1", "hej"), lambda: pj.proj_.stop(B, "a1"),
                 lambda: pj.proj_.followup(B, "a1", "nyt"), lambda: pj.proj_.close(B, "a1"),
                 lambda: pj.proj_.send_message("legacy_unscoped", "a1", "hej"), lambda: pj.proj_.stop("", "a1")):
        out = call()
        assert (out["status"], out["code"]) == ("error", "INVALID_SCOPE")
    assert pj.c_._conn().execute("SELECT COUNT(*) FROM agent_messages").fetchone()[0] == before
    reg = pj.c_._conn().execute("SELECT status, lifecycle_status FROM agent_registry WHERE agent_id='a1'").fetchone()
    assert (reg["status"], reg["lifecycle_status"]) == ("planned", "available")           # ikke stoppet, ikke lukket


def test_actions_are_refused_with_a_stable_code_while_the_engine_is_off(pj):
    pj.agent("a1")
    out = pj.proj_.send_message(A, "a1", "hej")
    assert (out["status"], out["code"]) == ("error", "POLICY_DENIED")
    assert out["receipt"]["accepted"] is False


def test_follow_up_on_a_finished_agent_creates_a_new_assignment_with_the_same_agent_id(pj):
    pj.on()
    first = pj.agent("a1", run="completed", terminal="completed")
    out = pj.proj_.followup(A, "a1", "gaa videre", idempotency_key="k1")
    assert out["status"] == "accepted" and out["agent_id"] == "a1" and out["assignment_id"] != first["assignment_id"]
    again = pj.proj_.followup(A, "a1", "gaa videre", idempotency_key="k1")
    assert again["assignment_id"] == out["assignment_id"] and again["replayed"] is True


# --- legacy ----------------------------------------------------------------------------------------------------------

def test_legacy_rows_with_no_contract_data_do_not_crash_and_never_leak_as_an_owners(pj):
    from core.runtime.db_agent_runtime import create_agent_registry_entry, create_agent_run
    for i in range(3):
        create_agent_registry_entry(agent_id=f"gl{i}", role="researcher", goal="gammelt arbejde",
                                    status="completed")
        create_agent_run(run_id=f"grun{i}", agent_id=f"gl{i}", status="completed", input_tokens=5)
    assert pj.proj_.overview(A, scope="all")["agents"] == []
    assert pj.proj_.feed(A)["cards"] == []
    assert pj.proj_.agent_detail(A, "gl0") is None
    assert pj.c_.mark_legacy_unscoped()["agents"] == 3
