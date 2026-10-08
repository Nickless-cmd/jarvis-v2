"""Expired queue positions settle once and never overtake a worker claim."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest


@pytest.fixture
def d(isolated_runtime):
    from core.runtime import db_agent_contract as c
    from core.runtime import db_agent_deadlines as deadlines
    from core.runtime.db_agent_runtime import create_agent_registry_entry

    def make(name: str):
        create_agent_registry_entry(agent_id=name, role="researcher", goal="test")
        c.bind_agent_owner(agent_id=name, owner_user_id="owner", owner_session_id="session")
        return c.accept_assignment(agent_id=name, owner_user_id="owner",
                                   origin_session_id="session", goal="work",
                                   parent_agent_id="jarvis")

    return c, deadlines, make


def test_queue_expiry_has_one_terminal_message_and_run_status(d):
    c, deadlines, make = d
    acc = make("a1")
    conn = c._conn()
    conn.execute("UPDATE agent_assignments SET queue_deadline_at=? WHERE assignment_id=?",
                 ("2026-10-07T00:00:00Z", acc["assignment_id"]))
    conn.commit()
    now = datetime(2026, 10, 8, tzinfo=UTC)
    assert deadlines.expire_due_queues(now=now) == [
        {"assignment_id": acc["assignment_id"], "action": "queue_timed_out"}]
    assert deadlines.expire_due_queues(now=now) == []
    assert conn.execute("SELECT status FROM agent_runs WHERE run_id=?",
                        (acc["run_id"],)).fetchone()[0] == "timed_out"
    assert conn.execute("SELECT COUNT(*) FROM agent_result_outbox WHERE assignment_id=?",
                        (acc["assignment_id"],)).fetchone()[0] == 1


def test_claimed_worker_cannot_be_expired_by_queue_sweep(d):
    from core.runtime.db_agent_capacity import claim_worker_slot, mark_ready

    c, deadlines, make = d
    acc = make("a1")
    conn = c._conn()
    assert mark_ready(assignment_id=acc["assignment_id"])
    assert claim_worker_slot(assignment_id=acc["assignment_id"])
    conn.execute("UPDATE agent_assignments SET queue_deadline_at=? WHERE assignment_id=?",
                 ("2026-10-07T00:00:00Z", acc["assignment_id"]))
    conn.commit()
    assert deadlines.expire_due_queues(now=datetime(2026, 10, 8, tzinfo=UTC)) == []
    assert c.get_assignment(assignment_id=acc["assignment_id"], owner_user_id="owner")["status"] == "active"


def test_worker_cannot_claim_an_expired_queue_place_before_supervisor_scans(d):
    from core.runtime.db_agent_capacity import claim_worker_slot, mark_ready

    c, deadlines, make = d
    acc = make("a1")
    assert mark_ready(assignment_id=acc["assignment_id"])
    conn = c._conn()
    conn.execute("UPDATE agent_assignments SET queue_deadline_at=? WHERE assignment_id=?",
                 ("2026-10-07T00:00:00Z", acc["assignment_id"]))
    conn.commit()
    assert claim_worker_slot(assignment_id=acc["assignment_id"]) is False
    assert deadlines.expire_due_queues(now=datetime(2026, 10, 8, tzinfo=UTC))


def test_only_owner_can_extend_a_still_queued_deadline(d):
    c, deadlines, make = d
    acc = make("a1")
    later = datetime.now(UTC) + timedelta(hours=3)
    assert deadlines.extend_queue_deadline(assignment_id=acc["assignment_id"],
                                           owner_user_id="other", until=later) is False
    assert deadlines.extend_queue_deadline(assignment_id=acc["assignment_id"],
                                           owner_user_id="owner", until=later) is True
    assert deadlines.extend_queue_deadline(assignment_id=acc["assignment_id"],
                                           owner_user_id="owner", until=later) is False
