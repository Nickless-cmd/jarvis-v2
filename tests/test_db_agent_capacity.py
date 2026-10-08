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
