"""G3: feed-referencer og signal-outbox - en reference pr. assignment, signal der overlever et crash."""
from __future__ import annotations

import pytest

A, B, S = "bjorn", "anden", "sess-1"


@pytest.fixture
def fd(isolated_runtime, monkeypatch):
    import core.runtime.db_agent_approvals as appr
    import core.runtime.db_agent_contract as c
    import core.runtime.db_agent_feed as feed
    from core.eventbus.bus import event_bus
    from core.runtime.db_agent_runtime import create_agent_registry_entry

    sent: list = []
    monkeypatch.setattr(event_bus, "publish", lambda kind, payload=None, **kw: sent.append((kind, payload)))

    class H:
        feed_, c_, appr_, sent_ = feed, c, appr, sent

        def agent(self, name, owner=A, session=S):
            create_agent_registry_entry(agent_id=name, role="r", goal="g")
            c.bind_agent_owner(agent_id=name, owner_user_id=owner, owner_session_id=session)
            return c.accept_assignment(agent_id=name, owner_user_id=owner, origin_session_id=session, goal="g",
                                       parent_agent_id="jarvis", parent_run_id="pr")

        def refs(self):
            return [tuple(r) for r in c._conn().execute(
                "SELECT ref_kind, owner_user_id, agent_id FROM agent_feed_refs ORDER BY ref_kind, agent_id")]

    return H()


def test_every_assignment_and_approval_gets_exactly_one_reference_legacy_rows_get_none(fd):
    a1, a2 = fd.agent("a1"), fd.agent("a2", owner=B, session="sx")
    fd.appr_.request(owner_user_id=A, origin_session_id=S, assignment_id=a1["assignment_id"], tool_name="bash",
                     arguments={"command": "ls"})
    from core.runtime.db_agent_runtime import create_agent_registry_entry
    create_agent_registry_entry(agent_id="legacy", role="r", goal="g")
    c = fd.c_._conn()                                             # en assignment med legacy-ejer (kan ikke accepteres)
    c.execute("INSERT INTO agent_assignments (assignment_id, agent_id, owner_user_id, origin_session_id, goal, "
              "created_at, updated_at) VALUES ('asg-legacy','legacy','legacy_unscoped','s','g','t','t')")
    c.commit()
    assert fd.feed_.ensure_refs() == 3
    assert fd.feed_.ensure_refs() == 0                                             # idempotent
    assert fd.refs() == [("agent", A, "a1"), ("agent", B, "a2"), ("approval", A, "a1")]
    assert set(fd.feed_.refs_for_owner(A)) == {("agent", a1["assignment_id"]),
                                               ("approval", fd.c_._conn().execute(
                                                   "SELECT approval_id FROM agent_approvals").fetchone()[0])}
    assert fd.feed_.refs_for_owner("legacy_unscoped") == {} and fd.feed_.refs_for_owner("") == {}
    assert ("agent", a2["assignment_id"]) not in fd.feed_.refs_for_owner(A)


def test_a_signal_carries_only_ids_and_state_and_is_sent_once_per_state_change(fd):
    a1 = fd.agent("a1")
    out = fd.feed_.signal_changes()
    assert fd.sent_ == [("notifikation.agent", {"user_id": A, "ref_kind": "agent", "ref_id": a1["assignment_id"],
                                                "agent_id": "a1", "state": "queued:queued"})]
    assert out == [fd.sent_[0][1]]
    assert fd.feed_.signal_changes() == [] and len(fd.sent_) == 1                   # ingen gentagelse uden aendring
    c = fd.c_._conn()
    c.execute("UPDATE agent_runs SET status='running' WHERE run_id=?", (a1["run_id"],))
    c.execute("UPDATE agent_assignments SET status='active' WHERE assignment_id=?", (a1["assignment_id"],))
    c.commit()
    assert [p["state"] for p in fd.feed_.signal_changes()] == ["active:running"]
    fd.c_.commit_terminal_outcome(assignment_id=a1["assignment_id"], status="completed", summary="HEMMELIGT RESUME")
    assert len(fd.sent_) == 3 and fd.sent_[-1][1]["state"] == "completed:running"      # via commit-hooken
    assert "HEMMELIGT" not in repr(fd.sent_)                                           # aldrig agentindhold


def test_a_crash_between_assignment_commit_and_push_does_not_lose_the_notification(fd, monkeypatch):
    from core.eventbus.bus import event_bus
    a1 = fd.agent("a1")
    fd.feed_.signal_changes()
    fd.sent_.clear()

    def down(kind, payload=None, **kw):
        raise RuntimeError("bussen er nede")
    monkeypatch.setattr(event_bus, "publish", down)
    res = fd.c_.commit_terminal_outcome(assignment_id=a1["assignment_id"], status="failed",
                                        error_code="AGENT_FAILED", error_phase="model")
    assert res["committed"] is True and fd.sent_ == []                                 # udfaldet staar, signalet gik tabt
    assert fd.c_.get_assignment(assignment_id=a1["assignment_id"], owner_user_id=A)["status"] == "failed"
    assert fd.feed_.signal_changes() == []                                             # stadig nede: intet noteret
    monkeypatch.setattr(event_bus, "publish", lambda kind, payload=None, **kw: fd.sent_.append((kind, payload)))
    out = fd.feed_.signal_changes()                                                    # supervisor-tikket
    assert [p["state"] for p in out] == ["failed:queued"] and len(fd.sent_) == 1
    assert fd.feed_.signal_changes() == []


def test_an_approval_is_its_own_reference_and_its_status_change_is_signalled(fd):
    a1 = fd.agent("a1")
    r = fd.appr_.request(owner_user_id=A, origin_session_id=S, assignment_id=a1["assignment_id"], tool_name="bash",
                         arguments={"command": "ls"})
    fd.feed_.signal_changes()
    fd.sent_.clear()
    fd.appr_.decide(approval_id=r["approval_id"], decision="deny", actor_user_id=A, actor_kind="human",
                    digest=r["args_digest"])
    assert [(p["ref_kind"], p["ref_id"], p["state"]) for p in fd.feed_.signal_changes()] == [
        ("approval", r["approval_id"], "denied")]


def test_read_and_acknowledge_are_owner_scoped_idempotent_and_separate(fd):
    a1 = fd.agent("a1")
    assert fd.feed_.mark_read(owner_user_id=B, ref_kind="agent", ref_id=a1["assignment_id"]) is False
    assert fd.feed_.acknowledge(owner_user_id="legacy_unscoped", ref_kind="agent", ref_id=a1["assignment_id"]) is False
    assert fd.feed_.mark_read(owner_user_id=A, ref_kind="bogus", ref_id=a1["assignment_id"]) is False
    assert fd.feed_.mark_read(owner_user_id=A, ref_kind="agent", ref_id=a1["assignment_id"]) is True
    ref = fd.feed_.refs_for_owner(A)[("agent", a1["assignment_id"])]
    assert ref["read_at"] and ref["acknowledged_at"] == ""
    first = ref["read_at"]
    assert fd.feed_.mark_read(owner_user_id=A, ref_kind="agent", ref_id=a1["assignment_id"]) is True
    assert fd.feed_.refs_for_owner(A)[("agent", a1["assignment_id"])]["read_at"] == first   # skrives ikke om
    assert fd.feed_.acknowledge(owner_user_id=A, ref_kind="agent", ref_id=a1["assignment_id"]) is True
    ref = fd.feed_.refs_for_owner(A)[("agent", a1["assignment_id"])]
    assert ref["acknowledged_at"] and ref["acknowledged_by"] == A
