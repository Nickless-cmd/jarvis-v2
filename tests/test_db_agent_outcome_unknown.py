"""G4: tilstandsbesked ved outcome_unknown - saerskilt, DB-markeret, aldrig terminalbeskeden. Rigtig sqlite."""
from __future__ import annotations

import json
import threading
from datetime import UTC, datetime, timedelta

import pytest

OWNER, SESS = "bjorn", "sess-1"
T0 = datetime(2026, 10, 7, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def ou(isolated_runtime, monkeypatch):
    import core.runtime.db_agent_contract as c
    import core.runtime.db_agent_lease as L
    import core.runtime.db_agent_outcome_unknown as U
    import core.runtime.db_agent_wait as W
    from core.runtime.db_agent_runtime import create_agent_registry_entry, create_agent_tool_call
    from core.services import in_flight_runs as ifr

    ifr._mutate(lambda r: r.clear())
    seen = []
    monkeypatch.setattr("core.eventbus.bus.event_bus.publish", lambda name, payload=None, *a, **k: seen.append(name))

    class H:
        c_, L_, U_, W_, ifr_, events = c, L, U, W, ifr, seen

        def unknown(self, name="a1", owner=OWNER, session=SESS):
            """Et assignment hvis worker mistede leasen midt i et skrivende vaerktoejskald."""
            create_agent_registry_entry(agent_id=name, role="r", goal="g", tool_policy="worktree-write")
            c.bind_agent_owner(agent_id=name, owner_user_id=owner, owner_session_id=session)
            acc = c.accept_assignment(agent_id=name, owner_user_id=owner, origin_session_id=session, goal="g",
                                      parent_agent_id="jarvis", parent_run_id="pr")
            cn = c._conn()
            cn.execute("UPDATE agent_runs SET status='running', started_at='t' WHERE run_id=?", (acc["run_id"],))
            cn.execute("UPDATE agent_assignments SET status='active' WHERE assignment_id=?",
                       (acc["assignment_id"],))
            cn.commit()
            L.acquire(assignment_id=acc["assignment_id"], holder="w1", now=T0)
            create_agent_tool_call(tool_call_id=f"tc-{name}", run_id=acc["run_id"], agent_id=name,
                                   tool_name="write_file", status="running", started_at="t", finished_at="")
            return acc

        def expire(self):
            return L.reconcile_expired_leases(now=T0 + timedelta(seconds=200))

        def rows(self, where="1=1"):
            return [dict(r) for r in c._conn().execute(
                f"SELECT * FROM agent_result_outbox WHERE {where} ORDER BY created_at")]

    yield H()
    ifr._mutate(lambda r: r.clear())


def test_a_lost_lease_mid_write_gives_one_distinct_state_message_and_no_terminal_one(ou):
    acc = ou.unknown()
    assert ou.expire() == [{"assignment_id": acc["assignment_id"], "action": "outcome_unknown",
                            "open_tool_calls": 1}]
    (m,) = ou.rows()
    assert (m["message_kind"], m["state_code"], m["result_type"], m["owner_user_id"], m["origin_session_id"],
            m["recipient_agent_id"], m["parent_run_id"], m["last_run_id"], m["delivery_status"],
            m["resolved_at"]) == ("state", "outcome_unknown", f"outcome_unknown:{acc['run_id']}", OWNER, SESS,
                                  "jarvis", "pr", acc["run_id"], "accepted", "")
    assert json.loads(m["payload_json"]) == {
        "state": "outcome_unknown", "status": "outcome_unknown", "terminal": False, "retry_allowed": False,
        "agent_id": "a1", "assignment_id": acc["assignment_id"], "run_id": acc["run_id"],
        "last_run_id": acc["run_id"], "reason": "lease_expired_with_open_tool_call", "open_tool_calls": 1,
        "needs": "verified_or_human_decision"}
    assert ou.rows("result_type='agent_result'") == []
    a = ou.c_.get_assignment(assignment_id=acc["assignment_id"], owner_user_id=OWNER)
    assert (a["status"], a["terminal_at"]) == ("waiting", "")
    assert "agent.outcome_unknown" in ou.events


def test_the_state_message_does_not_satisfy_or_fire_a_wait_contract(ou):
    acc = ou.unknown()
    ct = ou.W_.register_wait(owner_user_id=OWNER, origin_session_id=SESS, parent_run_id="pr",
                             assignment_ids=[acc["assignment_id"]], condition="first_terminal")
    ou.expire()
    assert ou.W_.get_contract(ct["contract_id"])["status"] == "registered"
    assert {k: v for k, v in ou.ifr_._load().items() if v.get("wake_kind")} == {}


def test_the_parent_claims_the_state_message_like_any_other_and_only_once(ou):
    from core.services.agent_result_inbox import claim_for_model_step
    acc = ou.unknown()
    ou.expire()
    text = claim_for_model_step(owner_user_id=OWNER, session_id=SESS)
    assert "TILSTAND, IKKE ET RESULTAT" in text and acc["assignment_id"] in text
    assert "Antag IKKE succes og gentag IKKE handlingen" in text
    assert ou.rows()[0]["delivery_status"] == "claimed_by_model_step"
    assert claim_for_model_step(owner_user_id=OWNER, session_id=SESS) == ""
    assert claim_for_model_step(owner_user_id="en-anden", session_id=SESS) == ""


def test_desk_can_project_unresolved_states_by_marker_scoped_to_the_owner(ou):
    acc = ou.unknown()
    ou.expire()
    assert [r["assignment_id"] for r in ou.U_.list_unresolved(owner_user_id=OWNER)] == [acc["assignment_id"]]
    assert ou.U_.list_unresolved(owner_user_id="en-anden") == []


def test_a_late_registry_status_never_settles_an_unresolved_outcome(ou):
    from core.runtime.db_agent_runtime import update_agent_registry_entry
    acc = ou.unknown()
    ou.expire()
    for status in ("completed", "cancelled", "expired", "failed"):
        update_agent_registry_entry("a1", status=status)               # sen succes / timeout / annullering
    assert ou.rows("result_type='agent_result'") == []
    assert ou.c_.get_assignment(assignment_id=acc["assignment_id"], owner_user_id=OWNER)["status"] == "waiting"


def test_an_unresolved_agent_is_not_run_again_automatically(ou, monkeypatch):
    import core.services.agent_runtime as ar
    import core.services.agent_runtime_spawn as sp
    calls = []
    monkeypatch.setattr(ar, "execute_with_role_or_fallback", lambda **kw: calls.append(kw) or {"text": "x"})
    ou.unknown()
    ou.expire()
    out = sp.execute_agent_task(agent_id="a1")
    assert out["blocked"]["code"] == "OUTCOME_UNKNOWN" and calls == []
    assert ou.U_.is_blocked("a1") is True


# --- afgoerelsen: kun et menneske/verificering, og stadig kun ÉN terminal besked ------------------------

@pytest.mark.parametrize("outcome,status,code", [("completed", "completed", ""), ("failed", "failed", "OUTCOME_UNKNOWN"),
                                                  ("cancelled", "cancelled", "OUTCOME_UNKNOWN")])
def test_a_human_decision_sends_exactly_one_terminal_message_and_closes_the_state(ou, outcome, status, code):
    acc = ou.unknown()
    ou.expire()
    out = ou.U_.resolve_outcome_unknown(owner_user_id=OWNER, assignment_id=acc["assignment_id"], outcome=outcome,
                                        decided_by="bjorn", actor_kind="human", note="tjekket i repoet")
    assert out["resolved"] is True and out["terminal"]["committed"] is True
    terminal = ou.rows("result_type='agent_result'")
    assert len(terminal) == 1
    p = json.loads(terminal[0]["payload_json"])
    assert (p["status"], p["error_code"], p["last_run_id"]) == (status, code, acc["run_id"])
    assert "bjorn" in p["summary"]
    assert ou.rows("message_kind='state'")[0]["resolved_at"] != "" and ou.U_.list_unresolved(owner_user_id=OWNER) == []
    run = ou.c_._conn().execute("SELECT status FROM agent_runs WHERE run_id=?", (acc["run_id"],)).fetchone()
    assert run["status"] == ("completed" if outcome == "completed" else outcome)
    assert ou.U_.is_blocked("a1") is False
    again = ou.c_.commit_terminal_outcome(assignment_id=acc["assignment_id"], status="failed")
    assert again["committed"] is False and len(ou.rows("result_type='agent_result'")) == 1


@pytest.mark.parametrize("kw,code", [
    ({"actor_kind": "model", "decided_by": "jarvis"}, "POLICY_DENIED"),
    ({"actor_kind": "human", "decided_by": " "}, "POLICY_DENIED"),
    ({"actor_kind": "human", "decided_by": "bjorn", "outcome": "succes"}, "INVALID_TRANSITION"),
    ({"actor_kind": "human", "decided_by": "bjorn", "owner_user_id": "en-anden"}, "INVALID_SCOPE"),
])
def test_only_a_human_or_verifier_of_the_owner_can_decide_and_nothing_changes_otherwise(ou, kw, code):
    acc = ou.unknown()
    ou.expire()
    args = {"owner_user_id": OWNER, "assignment_id": acc["assignment_id"], "outcome": "completed"}
    args.update(kw)
    with pytest.raises(ou.c_.ContractError) as e:
        ou.U_.resolve_outcome_unknown(**args)
    assert e.value.code == code
    assert ou.rows("result_type='agent_result'") == [] and ou.U_.is_blocked("a1") is True


def test_an_assignment_without_an_unresolved_outcome_cannot_be_decided(ou):
    ou.unknown()          # leasen er IKKE udloebet endnu
    with pytest.raises(ou.c_.ContractError) as e:
        ou.U_.resolve_outcome_unknown(owner_user_id=OWNER, assignment_id=ou.c_.open_assignment_for_agent("a1")["assignment_id"],
                                      outcome="completed", decided_by="bjorn", actor_kind="human")
    assert e.value.code == "INVALID_TRANSITION"


def test_two_simultaneous_decisions_produce_one_terminal_message(ou):
    acc = ou.unknown()
    ou.expire()
    barrier, res, errs = threading.Barrier(2), [], []

    def go(outcome):
        try:
            barrier.wait(timeout=5)
            res.append(ou.U_.resolve_outcome_unknown(owner_user_id=OWNER, assignment_id=acc["assignment_id"],
                                                     outcome=outcome, decided_by="bjorn", actor_kind="human"))
        except BaseException as exc:                                  # traadens undtagelse er et testresultat
            errs.append(exc)

    ts = [threading.Thread(target=go, args=(o,)) for o in ("completed", "failed")]
    [t.start() for t in ts]
    [t.join(timeout=10) for t in ts]
    assert len(res) == 1 and len(errs) == 1 and errs[0].code == "INVALID_TRANSITION"
    assert len(ou.rows("result_type='agent_result'")) == 1


def test_the_notice_is_idempotent_per_run_and_a_second_unknown_run_gets_its_own(ou):
    acc = ou.unknown()
    ou.expire()
    cn = ou.c_._conn()
    cn.execute("BEGIN IMMEDIATE")
    again = ou.U_.notify_outcome_unknown(cn, assignment_id=acc["assignment_id"], run_id=acc["run_id"], reason="x")
    other = ou.U_.notify_outcome_unknown(cn, assignment_id=acc["assignment_id"], run_id="run-2", reason="y")
    cn.commit()
    assert again == ou.rows()[0]["message_id"] and other != again and len(ou.rows("message_kind='state'")) == 2
    assert ou.U_.notify_outcome_unknown(ou.c_._conn(), assignment_id="findes-ikke", run_id="r", reason="z") == ""
