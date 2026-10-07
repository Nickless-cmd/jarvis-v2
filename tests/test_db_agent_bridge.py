"""E: bro-invocation-lageret. Rigtig sqlite; ingen model, ingen bro."""
from __future__ import annotations

import pytest

OWNER, CLIENT = "u1", "desk-1"


@pytest.fixture
def bdb(isolated_runtime):
    import core.runtime.db_agent_bridge as B
    from core.runtime.db_agent_contract import ContractError

    class H:
        B_, Err = B, ContractError

        def begin(self, iid="inv-1", tool="operator_write_file", klass="write", args=None, owner=OWNER,
                  client=CLIENT):
            return B.begin(invocation_id=iid, owner_user_id=owner, origin_session_id="s1", agent_id="a1",
                           assignment_id="asg-1", run_id="run-1", client_id=client, tool=tool,
                           idem_class=klass, args=args if args is not None else {"path": "/x"})

        def state(self, iid="inv-1"):
            return B.get(iid)["state"]
    return H()


def test_begin_is_idempotent_for_the_same_call_and_refuses_a_different_one(bdb):
    first = bdb.begin()
    assert (first["state"], first["attempts"], first["idem_class"]) == ("pending", 0, "write")
    assert bdb.begin()["created_at"] == first["created_at"]
    with pytest.raises(bdb.Err) as e:
        bdb.begin(args={"path": "/andet"})
    assert e.value.code == "IDEMPOTENCY_CONFLICT"
    with pytest.raises(bdb.Err):
        bdb.begin(owner="u2")                                  # et id er bundet til netop ejerens kald
    with pytest.raises(bdb.Err) as e2:
        bdb.begin(iid="inv-2", klass="maybe")
    assert e2.value.code == "INVALID_SCOPE"


def test_the_lifecycle_pending_sent_succeeded_and_a_second_finish_changes_nothing(bdb):
    bdb.begin()
    bdb.B_.mark_sent("inv-1")
    row = bdb.B_.get("inv-1")
    assert (row["state"], row["attempts"], bool(row["sent_at"])) == ("sent", 1, True)
    assert bdb.B_.finish("inv-1", ok=True, result={"bytes_written": 3}) is True
    done = bdb.B_.get("inv-1")
    assert (done["state"], done["result_json"], done["error"]) == ("succeeded", '{"bytes_written": 3}', "")
    assert bdb.B_.finish("inv-1", ok=False, error="senere") is False
    assert bdb.state() == "succeeded"


def test_a_failed_known_outcome_keeps_the_client_error(bdb):
    bdb.begin()
    bdb.B_.mark_sent("inv-1")
    bdb.B_.finish("inv-1", ok=False, error="ENOENT: /x")
    row = bdb.B_.get("inv-1")
    assert (row["state"], row["error"], row["result_json"]) == ("failed", "ENOENT: /x", "")


def test_unknown_only_from_an_open_call_and_a_late_reply_closes_it(bdb):
    bdb.begin()
    assert bdb.B_.mark_unknown("inv-1", "timeout") is True
    assert bdb.B_.mark_unknown("inv-1", "igen") is False
    assert bdb.state() == "outcome_unknown"
    assert [r["invocation_id"] for r in bdb.B_.unknown_for_assignment("asg-1")] == ["inv-1"]
    assert bdb.B_.finish("inv-1", ok=True, result="sent svar") is True
    row = bdb.B_.get("inv-1")
    assert (row["state"], row["resolution"]) == ("succeeded", "late_reply")
    assert bdb.B_.unknown_for_assignment("asg-1") == []


def test_abort_unsent_only_when_nothing_ever_left_the_server(bdb):
    bdb.begin("a")
    assert bdb.B_.abort_unsent("a", "offline") is True and bdb.state("a") == "failed"
    bdb.begin("b")
    bdb.B_.mark_sent("b")
    assert bdb.B_.abort_unsent("b", "offline") is False and bdb.state("b") == "sent"


@pytest.mark.parametrize("status,expected", [
    ("completed", "verified_executed"), ("failed", "verified_executed"),
    ("not_started", "verified_not_executed"), ("running", "unchanged"), ("unknown", "unchanged"),
    ("opfundet", "unchanged"),
])
def test_the_clients_own_status_decides_an_unknown_call(bdb, status, expected):
    bdb.begin()
    bdb.B_.mark_unknown("inv-1", "timeout")
    out = bdb.B_.apply_client_report(owner_user_id=OWNER, client_id=CLIENT, reports=[
        {"invocation_id": "inv-1", "status": status, "result": "ok", "error": "boom"}])
    assert out == {"inv-1": expected}
    assert bdb.state() == (expected if expected != "unchanged" else "outcome_unknown")
    if status == "completed":
        assert bdb.B_.get("inv-1")["result_json"] == "ok"


def test_a_client_cannot_decide_another_owners_or_another_clients_call(bdb):
    bdb.begin()
    bdb.B_.mark_unknown("inv-1", "timeout")
    for owner, client in (("u2", CLIENT), (OWNER, "telefon-1")):
        out = bdb.B_.apply_client_report(owner_user_id=owner, client_id=client, reports=[
            {"invocation_id": "inv-1", "status": "not_started"}, {"invocation_id": "findes-ikke", "status": "completed"}])
        assert out == {"inv-1": "ignored_unknown_invocation", "findes-ikke": "ignored_unknown_invocation"}
    assert bdb.state() == "outcome_unknown"


def test_a_settled_call_is_not_reopened_by_a_later_report(bdb):
    bdb.begin()
    bdb.B_.mark_sent("inv-1")
    bdb.B_.finish("inv-1", ok=True, result="ok")
    out = bdb.B_.apply_client_report(owner_user_id=OWNER, client_id=CLIENT, reports=[
        {"invocation_id": "inv-1", "status": "not_started"}])
    assert out == {"inv-1": "already_succeeded"} and bdb.state() == "succeeded"


def test_unresolved_for_client_lists_open_and_unknown_for_that_owner_and_client_only(bdb):
    bdb.begin("a")
    bdb.begin("b")
    bdb.B_.mark_unknown("b", "x")
    bdb.begin("c")
    bdb.B_.mark_sent("c")
    bdb.B_.finish("c", ok=True, result="r")
    bdb.begin("d", client="telefon-1")
    assert [r["invocation_id"] for r in bdb.B_.unresolved_for_client(OWNER, CLIENT)] == ["a", "b"]
    assert bdb.B_.unresolved_for_client("u2", CLIENT) == []


def test_human_resolution_only_for_the_owner_and_only_for_an_unknown_call(bdb):
    bdb.begin()
    with pytest.raises(bdb.Err) as e:
        bdb.B_.human_resolve(invocation_id="inv-1", owner_user_id=OWNER, executed=True, actor_user_id=OWNER)
    assert e.value.code == "POLICY_DENIED"                      # ikke uafgjort endnu
    bdb.B_.mark_unknown("inv-1", "timeout")
    with pytest.raises(bdb.Err) as e2:
        bdb.B_.human_resolve(invocation_id="inv-1", owner_user_id="u2", executed=True, actor_user_id="u2")
    assert e2.value.code == "INVALID_SCOPE"
    row = bdb.B_.human_resolve(invocation_id="inv-1", owner_user_id=OWNER, executed=False, actor_user_id=OWNER)
    assert (row["state"], row["resolution"]) == ("human_resolved", "human:u1:not_executed")


def test_a_long_result_is_clipped(bdb):
    bdb.begin()
    bdb.B_.mark_sent("inv-1")
    bdb.B_.finish("inv-1", ok=True, result="x" * 50_000)
    assert len(bdb.B_.get("inv-1")["result_json"]) == bdb.B_.RESULT_LIMIT


def test_a_pending_row_that_has_ever_been_sent_cannot_be_aborted_as_unsent(bdb):
    bdb.begin()
    import core.runtime.db_agent_contract as c
    conn = c._conn()
    conn.execute("UPDATE agent_bridge_invocations SET attempts=1 WHERE invocation_id='inv-1'")   # pending men afsendt
    conn.commit()
    assert bdb.B_.abort_unsent("inv-1", "offline") is False and bdb.state() == "pending"
    bdb.B_.unmark_sent("inv-1")                                      # kun ``sent`` kan rulles tilbage
    assert bdb.B_.get("inv-1")["attempts"] == 1
