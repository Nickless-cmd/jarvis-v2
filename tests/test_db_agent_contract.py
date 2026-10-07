"""Leverance A: assignment/run/outbox-kontrakten mod rigtig sqlite (ingen fake)."""
from __future__ import annotations

import json
import threading

import pytest


@pytest.fixture
def m(isolated_runtime):
    import core.runtime.db_agent_contract as mod
    from core.runtime.db_agent_runtime import create_agent_registry_entry

    def make_agent(agent_id: str, owner: str | None) -> None:
        create_agent_registry_entry(agent_id=agent_id, role="scout", goal="g")
        if owner is not None:
            c = mod._conn()
            c.execute("UPDATE agent_registry SET owner_user_id=? WHERE agent_id=?",
                      (owner, agent_id))
            c.commit()

    mod.make_agent = make_agent
    return mod


def _accept(m, **kw):
    base = dict(agent_id="a1", owner_user_id="bjorn", origin_session_id="s1",
                goal="find X", parent_agent_id="jarvis", parent_run_id="pr1")
    base.update(kw)
    return m.accept_assignment(**base)


def _counts(m):
    c = m._conn()
    return tuple(c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                 for t in ("agent_assignments", "agent_runs", "agent_result_outbox"))


def test_accept_creates_assignment_and_first_run(m):
    m.make_agent("a1", "bjorn")
    out = _accept(m, idempotency_key="k1")
    assert out["status"] == "queued" and out["replayed"] is False
    assert out["contract_version"] == "agent-contract-v1"
    a = m.get_assignment(assignment_id=out["assignment_id"], owner_user_id="bjorn")
    assert (a["agent_id"], a["origin_session_id"], a["parent_run_id"], a["status"]) == (
        "a1", "s1", "pr1", "queued")
    run = m._conn().execute("SELECT * FROM agent_runs WHERE run_id=?",
                            (out["run_id"],)).fetchone()
    assert (run["assignment_id"], run["owner_user_id"], run["attempt_no"]) == (
        out["assignment_id"], "bjorn", 1)


def test_idempotency_replay_and_conflict(m):
    m.make_agent("a1", "bjorn")
    first = _accept(m, idempotency_key="k1")
    again = _accept(m, idempotency_key="k1")
    assert again["replayed"] is True
    assert (again["assignment_id"], again["run_id"]) == (first["assignment_id"], first["run_id"])
    assert _counts(m) == (1, 1, 0)
    with pytest.raises(m.ContractError) as e:
        _accept(m, idempotency_key="k1", goal="noget andet")
    assert e.value.code == "IDEMPOTENCY_CONFLICT"
    assert _counts(m) == (1, 1, 0)


@pytest.mark.parametrize("kw,agent_owner,code", [
    ({"owner_user_id": ""}, "bjorn", "INVALID_SCOPE"),
    ({"owner_user_id": "legacy_unscoped"}, "bjorn", "INVALID_SCOPE"),
    ({"origin_session_id": ""}, "bjorn", "INVALID_SCOPE"),
    ({"goal": "  "}, "bjorn", "INVALID_SCOPE"),
    ({"agent_id": "ukendt"}, "bjorn", "INVALID_SCOPE"),
    ({"owner_user_id": "anden"}, "bjorn", "POLICY_DENIED"),
    ({}, None, "POLICY_DENIED"),  # legacy_unscoped agent
])
def test_rejected_accept_leaves_nothing_behind(m, kw, agent_owner, code):
    m.make_agent("a1", agent_owner)
    with pytest.raises(m.ContractError) as e:
        _accept(m, **kw)
    assert e.value.code == code
    assert _counts(m) == (0, 0, 0)


def test_one_active_assignment_per_agent_and_closing_agent_refuses(m):
    m.make_agent("a1", "bjorn")
    _accept(m)
    with pytest.raises(m.ContractError) as e:
        _accept(m, goal="to")
    assert e.value.code == "CAPACITY"
    m.make_agent("a2", "bjorn")
    c = m._conn()
    c.execute("UPDATE agent_registry SET lifecycle_status='closing' WHERE agent_id='a2'")
    c.commit()
    with pytest.raises(m.ContractError) as e:
        _accept(m, agent_id="a2")
    assert e.value.code == "POLICY_DENIED"


def test_terminal_commit_writes_outcome_and_exactly_one_message(m):
    m.make_agent("a1", "bjorn")
    acc = _accept(m)
    first = m.commit_terminal_outcome(assignment_id=acc["assignment_id"], status="completed",
                                      summary="fandt X", artifact_ref="art/1")
    assert first["committed"] is True
    msg = first["message"]
    payload = json.loads(msg["payload_json"])
    assert (msg["recipient_agent_id"], msg["parent_run_id"], msg["origin_session_id"],
            msg["delivery_status"], msg["last_run_id"]) == (
        "jarvis", "pr1", "s1", "accepted", acc["run_id"])
    assert payload["status"] == "completed" and payload["attempt_run_ids"] == [acc["run_id"]]
    # Et andet forsoeg paa at afgoere (selv med andet udfald) aendrer intet.
    second = m.commit_terminal_outcome(assignment_id=acc["assignment_id"], status="failed",
                                       error_code="X")
    assert second["committed"] is False and second["assignment_status"] == "completed"
    assert second["message"]["message_id"] == msg["message_id"]
    assert _counts(m) == (1, 1, 1)


def test_non_terminal_status_is_rejected_without_side_effects(m):
    m.make_agent("a1", "bjorn")
    acc = _accept(m)
    with pytest.raises(m.ContractError) as e:
        m.commit_terminal_outcome(assignment_id=acc["assignment_id"], status="running")
    assert e.value.code == "INVALID_TRANSITION"
    assert _counts(m) == (1, 1, 0)


def test_concurrent_terminal_commits_give_one_message(m):
    m.make_agent("a1", "bjorn")
    acc = _accept(m)
    results: list = []

    def go(status):
        results.append(m.commit_terminal_outcome(
            assignment_id=acc["assignment_id"], status=status)["committed"])

    ts = [threading.Thread(target=go, args=(s,)) for s in ("completed", "failed", "cancelled")]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert sorted(results) == [False, False, True]
    assert _counts(m)[2] == 1


def test_retry_run_is_listed_but_sends_no_extra_terminal_message(m):
    m.make_agent("a1", "bjorn")
    acc = _accept(m)
    c = m._conn()
    c.execute("UPDATE agent_runs SET status='failed' WHERE run_id=?", (acc["run_id"],))
    c.execute("INSERT INTO agent_runs (run_id, agent_id, status, assignment_id, owner_user_id,"
              " attempt_no, created_at, updated_at) VALUES ('run-retry','a1','running',?,?,2,"
              "'t','t')", (acc["assignment_id"], "bjorn"))
    c.commit()
    assert _counts(m)[2] == 0  # fejlet forsoeg alene er ikke et slutresultat
    out = m.commit_terminal_outcome(assignment_id=acc["assignment_id"], status="completed")
    payload = json.loads(out["message"]["payload_json"])
    assert payload["attempt_run_ids"] == [acc["run_id"], "run-retry"]
    assert payload["last_run_id"] == "run-retry"
    assert _counts(m)[2] == 1


def test_delivery_only_moves_forward_and_only_for_owner(m):
    m.make_agent("a1", "bjorn")
    acc = _accept(m)
    mid = m.commit_terminal_outcome(assignment_id=acc["assignment_id"],
                                    status="completed")["message"]["message_id"]
    with pytest.raises(m.ContractError):
        m.advance_delivery(message_id=mid, owner_user_id="anden", to_status="delivered")
    assert m.advance_delivery(message_id=mid, owner_user_id="bjorn",
                              to_status="claimed_by_model_step")["delivery_status"] == \
        "claimed_by_model_step"
    # baglaens og dobbelt claim er no-ops
    assert m.advance_delivery(message_id=mid, owner_user_id="bjorn",
                              to_status="delivered")["delivery_status"] == "claimed_by_model_step"


def test_reads_are_filtered_by_owner_and_session(m):
    m.make_agent("a1", "bjorn")
    acc = _accept(m)
    m.commit_terminal_outcome(assignment_id=acc["assignment_id"], status="completed")
    assert len(m.list_pending_results(owner_user_id="bjorn", origin_session_id="s1")) == 1
    assert m.list_pending_results(owner_user_id="bjorn", origin_session_id="s2") == []
    assert m.list_pending_results(owner_user_id="anden", origin_session_id="s1") == []
    assert m.get_assignment(assignment_id=acc["assignment_id"], owner_user_id="anden") is None
    with pytest.raises(m.ContractError):
        m.list_pending_results(owner_user_id="", origin_session_id="s1")


def test_legacy_rows_are_marked_never_backfilled(m):
    m.make_agent("old", None)
    assert m.mark_legacy_unscoped()["agents"] == 1
    row = m._conn().execute("SELECT owner_user_id FROM agent_registry "
                            "WHERE agent_id='old'").fetchone()
    assert row["owner_user_id"] == "legacy_unscoped"


def test_schema_migration_is_idempotent_on_pre_existing_tables(m):
    c = m._conn()
    m.ensure_agent_contract_tables(c)
    m.ensure_agent_contract_tables(c)
    cols = {r[1] for r in c.execute("PRAGMA table_info(agent_runs)")}
    assert {"assignment_id", "owner_user_id", "attempt_no"} <= cols
