"""Queue reservations are separate from worker slots and survive races."""
from __future__ import annotations

import threading

import pytest


@pytest.fixture
def contract(isolated_runtime):
    from core.runtime import db_agent_contract as c
    from core.runtime.db_agent_runtime import create_agent_registry_entry

    def agent(index: int, owner: str = "owner") -> str:
        aid = f"capacity-agent-{index}"
        create_agent_registry_entry(agent_id=aid, role="researcher", goal="capacity")
        conn = c._conn()
        conn.execute("UPDATE agent_registry SET owner_user_id=? WHERE agent_id=?", (owner, aid))
        conn.commit()
        return aid

    return c, agent


def _accept(c, agent_id: str, parent: str):
    return c.accept_assignment(agent_id=agent_id, owner_user_id="owner",
                               origin_session_id="session", goal="work",
                               parent_agent_id=parent)


def test_eight_queued_per_parent_and_active_frees_queue_place(contract):
    c, agent = contract
    accepted = [_accept(c, agent(i), "parent") for i in range(8)]
    with pytest.raises(c.ContractError) as exc:
        _accept(c, agent(8), "parent")
    assert exc.value.code == "CAPACITY"
    assert c._conn().execute("SELECT COUNT(*) FROM agent_assignments").fetchone()[0] == 8

    conn = c._conn()
    conn.execute("UPDATE agent_assignments SET status='active' WHERE assignment_id=?",
                 (accepted[0]["assignment_id"],))
    conn.commit()
    assert _accept(c, agent(9), "parent")["status"] == "queued"


def test_twenty_four_queued_globally(contract):
    c, agent = contract
    for i in range(24):
        _accept(c, agent(i), f"parent-{i // 8}")
    with pytest.raises(c.ContractError) as exc:
        _accept(c, agent(24), "parent-4")
    assert exc.value.code == "CAPACITY"
    assert c._conn().execute("SELECT COUNT(*) FROM agent_assignments").fetchone()[0] == 24


def test_parallel_admission_has_no_overflow_or_partial_runs(contract):
    c, agent = contract
    for i in range(16):
        agent(i)
    barrier = threading.Barrier(16)
    results: list[str] = []
    lock = threading.Lock()

    def attempt(i: int):
        barrier.wait()
        try:
            _accept(c, f"capacity-agent-{i}", "same-parent")
            outcome = "accepted"
        except c.ContractError as exc:
            outcome = exc.code
        with lock:
            results.append(outcome)

    threads = [threading.Thread(target=attempt, args=(i,)) for i in range(16)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
        assert not thread.is_alive()
    assert results.count("accepted") == 8
    assert results.count("CAPACITY") == 8
    conn = c._conn()
    assert conn.execute("SELECT COUNT(*) FROM agent_assignments").fetchone()[0] == 8
    assert conn.execute("SELECT COUNT(*) FROM agent_runs WHERE assignment_id!=''").fetchone()[0] == 8


def test_worker_claim_needs_readiness_and_parent_slot_frees_on_terminal(contract):
    from core.runtime import db_agent_capacity as capacity

    c, agent = contract
    assignments = [_accept(c, agent(i), "parent") for i in range(7)]
    first = assignments[0]["assignment_id"]
    assert capacity.claim_worker_slot(assignment_id=first) is False
    for acc in assignments:
        assert capacity.mark_ready(assignment_id=acc["assignment_id"]) is True
    for acc in assignments[:6]:
        assert capacity.claim_worker_slot(assignment_id=acc["assignment_id"]) is True
    seventh = assignments[6]["assignment_id"]
    assert capacity.claim_worker_slot(assignment_id=seventh) is False
    assert capacity.claim_worker_slot(assignment_id=first) is False
    c.commit_terminal_outcome(assignment_id=first, status="completed")
    assert capacity.claim_worker_slot(assignment_id=seventh) is True


def test_worker_claim_enforces_owner_and_global_caps(contract):
    from core.runtime import db_agent_capacity as capacity

    c, agent = contract
    claims = []
    for i in range(24):
        owner = "owner" if i < 12 else "other"
        aid = agent(i, owner)
        acc = c.accept_assignment(agent_id=aid, owner_user_id=owner,
                                  origin_session_id="session", goal="work",
                                  parent_agent_id=f"parent-{i // 4}")
        capacity.mark_ready(assignment_id=acc["assignment_id"])
        claims.append((owner, acc["assignment_id"]))
    assert sum(capacity.claim_worker_slot(assignment_id=aid) for owner, aid in claims[:12]) == 8
    assert sum(capacity.claim_worker_slot(assignment_id=aid) for owner, aid in claims[12:]) == 4
    assert c._conn().execute("SELECT COUNT(*) FROM agent_assignments WHERE status='active'").fetchone()[0] == 12


def test_failed_start_releases_only_an_unstarted_claim(contract):
    from core.runtime import db_agent_capacity as capacity

    c, agent = contract
    first = _accept(c, agent(1), "parent")
    capacity.mark_ready(assignment_id=first["assignment_id"])
    assert capacity.claim_worker_slot(assignment_id=first["assignment_id"])
    assert capacity.release_unstarted_claim(assignment_id=first["assignment_id"])
    assert c.get_assignment(assignment_id=first["assignment_id"], owner_user_id="owner")["status"] == "queued"

    assert capacity.claim_worker_slot(assignment_id=first["assignment_id"])
    conn = c._conn()
    conn.execute("UPDATE agent_runs SET started_at=? WHERE run_id=?", ("2026-10-08T00:00:00Z", first["run_id"]))
    conn.commit()
    assert capacity.release_unstarted_claim(assignment_id=first["assignment_id"]) is False
    assert c.get_assignment(assignment_id=first["assignment_id"], owner_user_id="owner")["status"] == "active"
