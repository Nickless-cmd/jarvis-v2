"""B2: ventekontrakt, vaekning gennem den eksisterende dispatch-sti og brugerstop-spaerre."""
from __future__ import annotations

import json
import threading

import pytest

OWNER, SESS, RUN = "bjorn", "sess-1", "visible-parent"


@pytest.fixture
def w(isolated_runtime):
    import core.runtime.db_agent_contract as c
    import core.runtime.db_agent_wait as wait
    from core.runtime.db_agent_runtime import create_agent_registry_entry
    from core.services import in_flight_runs as ifr

    # state_store-afskaermningen deles af hele testsessionen: ryd foer og efter.
    ifr._mutate(lambda r: r.clear())

    class H:
        k, wait_, ifr_ = c, wait, ifr

        def child(self, name, owner=OWNER, session=SESS):
            create_agent_registry_entry(agent_id=name, role="r", goal="g")
            c.bind_agent_owner(agent_id=name, owner_user_id=owner, owner_session_id=session)
            return c.accept_assignment(agent_id=name, owner_user_id=owner,
                                       origin_session_id=session, goal="g",
                                       parent_agent_id="jarvis", parent_run_id=RUN)["assignment_id"]

        def done(self, aid, status="completed"):
            return c.commit_terminal_outcome(assignment_id=aid, status=status)

        def reg(self, ids, cond="all_terminal", run=RUN, owner=OWNER, session=SESS):
            return wait.register_wait(owner_user_id=owner, origin_session_id=session,
                                      parent_run_id=run, assignment_ids=ids, condition=cond)

        def wakes(self):
            return {k: v for k, v in ifr._load().items() if v.get("wake_kind")}

    yield H()
    ifr._mutate(lambda r: r.clear())


def test_wait_registered_then_child_finishes_writes_exactly_one_system_marked_wake(w):
    a = w.child("a1")
    ct = w.reg([a])
    assert ct["status"] == "registered" and w.wakes() == {}
    w.done(a)
    assert w.wait_.get_contract(ct["contract_id"])["status"] == "fired"
    (task, rec), = w.wakes().items()
    assert task == f"agentwake-{ct['contract_id']}"
    assert (rec["status"], rec["session_id"], rec["force_user_id"], rec["kind"],
            rec["wake_kind"], rec["notice_pending"], rec["recovery_limit"]) == (
        "recovering", SESS, OWNER, "visible", "agent_wait", False, 1)
    assert rec["original_request"].startswith("[SYSTEM — agentvækning, ikke en besked fra brugeren]")
    assert a in rec["original_request"]
    assert w.wait_.get_contract(ct["contract_id"])["wake_task_id"] == task


def test_all_terminal_waits_for_both_and_fires_once(w):
    a, b = w.child("a1"), w.child("a2")
    ct = w.reg([a, b])
    w.done(a)
    assert w.wakes() == {} and w.wait_.get_contract(ct["contract_id"])["status"] == "registered"
    w.done(b, "failed")  # et fejlet barn er terminalt
    assert len(w.wakes()) == 1


def test_first_terminal_fires_on_first_and_second_adds_nothing(w):
    a, b = w.child("a1"), w.child("a2")
    w.reg([a, b], "first_terminal")
    w.done(a)
    w.done(b)
    assert len(w.wakes()) == 1


def test_already_terminal_children_fire_at_registration(w):
    a = w.child("a1")
    w.done(a, "cancelled")
    ct = w.reg([a])
    assert ct["status"] == "fired" and len(w.wakes()) == 1


def test_concurrent_terminal_commits_give_one_wake(w):
    ids = [w.child(f"c{i}") for i in range(4)]
    w.reg(ids, "first_terminal")
    ts = [threading.Thread(target=w.done, args=(i,)) for i in ids]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert len(w.wakes()) == 1


@pytest.mark.parametrize("owner,session", [("anden", SESS), (OWNER, "andensession")])
def test_foreign_assignment_cannot_be_waited_on(w, owner, session):
    a = w.child("a1")
    with pytest.raises(w.k.ContractError) as e:
        w.reg([a], owner=owner, session=session)
    assert e.value.code == "INVALID_SCOPE"
    assert w.k._conn().execute("SELECT COUNT(*) FROM agent_wait_contracts").fetchone()[0] == 0


def test_user_stop_before_child_finishes_blocks_the_wake_but_keeps_the_result(w):
    a = w.child("a1")
    ct = w.reg([a])
    assert w.wait_.block_wakes_for_run(run_id=RUN) == {"blocked": 1, "cancelled": 0}
    w.done(a)
    assert w.wakes() == {}
    assert w.wait_.get_contract(ct["contract_id"])["status"] == "stopped"
    (m,) = w.k.list_pending_results(owner_user_id=OWNER, origin_session_id=SESS)
    assert m["delivery_status"] == "accepted"  # ligger klar til brugerens naeste tur


def test_user_stop_after_the_wake_was_planned_cancels_it_before_it_starts(w, monkeypatch):
    a = w.child("a1")
    w.reg([a])
    w.done(a)
    (task, _), = w.wakes().items()
    assert w.wait_.block_wakes_for_run(run_id=RUN) == {"blocked": 0, "cancelled": 1}
    assert w.wakes()[task]["status"] == "cancelled"
    from core.services import visible_run_recovery_dispatcher as d
    monkeypatch.setattr("core.services.visible_runs_sections.detached_run.start_user_run_detached",
                        lambda **kw: pytest.fail("vækningen må ikke starte efter brugerstop"))
    assert d.recover_due_once(owner="api")["started"] == 0


def test_stop_marker_written_before_registration_makes_the_contract_stopped(w):
    a = w.child("a1")
    w.wait_.block_wakes_for_run(run_id=RUN)
    ct = w.reg([a])
    assert ct["status"] == "stopped"
    w.done(a)
    assert w.wakes() == {}


def test_stop_of_another_run_does_not_block(w):
    a = w.child("a1")
    w.reg([a])
    w.wait_.block_wakes_for_run(run_id="visible-andet")
    w.done(a)
    assert len(w.wakes()) == 1


def test_dispatcher_starts_the_wake_through_claim_due_recovery(w, monkeypatch):
    a = w.child("a1")
    w.reg([a])
    w.done(a)
    seen = {}
    monkeypatch.setattr("core.services.visible_runs_sections.detached_run.start_user_run_detached",
                        lambda **kw: seen.update(kw) or "visible-wake-1")
    monkeypatch.setattr("core.services.run_event_log.active_run_for_session", lambda s: None)
    from core.services import visible_run_recovery_dispatcher as d
    out = d.recover_due_once(owner="api")
    assert (out["started"], out["run_id"], out["generation"]) == (1, "visible-wake-1", 1)
    assert (seen["session_id"], seen["force_user_id"], seen["recovery_attempt"]) == (SESS, OWNER, 1)
    assert seen["message"].startswith("[SYSTEM — agentvækning")
    assert d.recover_due_once(owner="api")["started"] == 0  # ét ventepunkt = ét run


def test_busy_session_defers_the_wake_instead_of_starting_a_second_run(w, monkeypatch):
    a = w.child("a1")
    w.reg([a])
    w.done(a)
    monkeypatch.setattr("core.services.run_event_log.active_run_for_session", lambda s: "visible-x")
    monkeypatch.setattr("core.services.visible_runs_sections.detached_run.start_user_run_detached",
                        lambda **kw: pytest.fail("single-flight brudt"))
    from core.services import visible_run_recovery_dispatcher as d
    out = d.recover_due_once(owner="api")
    assert (out["started"], out["error"]) == (0, "session-optaget")


def test_an_existing_pending_recovery_in_the_session_absorbs_the_wake(w):
    from core.services.agent_wake_intentions import stage_wake

    w.ifr_.mark_started(run_id="visible-old", session_id=SESS, user_message="gammelt arbejde")
    w.ifr_.settle_recovering("visible-old", reason="shutdown")
    a = w.child("a1")
    ct = w.reg([a])
    w.done(a)
    assert w.wakes() == {}
    assert w.wait_.get_contract(ct["contract_id"])["wake_task_id"] == "visible-old"
    assert stage_wake(task_id="x", session_id=SESS, owner_user_id=OWNER,
                      message="m")["merged"] is True


def test_a_wake_is_not_shown_as_an_interrupted_task(w):
    a = w.child("a1")
    w.reg([a])
    w.done(a)
    assert w.ifr_.recovery_snapshot(SESS) is None


def test_a_wake_lost_between_commit_and_file_is_picked_up_later(w, monkeypatch):
    import core.services.agent_wake_intentions as aw

    real = aw.stage_wake
    monkeypatch.setattr(aw, "stage_wake", lambda **kw: (_ for _ in ()).throw(OSError("disk")))
    a = w.child("a1")
    ct = w.reg([a])
    w.done(a)
    assert w.wakes() == {} and w.wait_.get_contract(ct["contract_id"])["wake_task_id"] == ""
    monkeypatch.setattr(aw, "stage_wake", real)
    assert w.wait_.materialize_pending_wakes() == [ct["contract_id"]]
    assert len(w.wakes()) == 1
    assert w.wait_.materialize_pending_wakes() == []


def test_user_stop_settlement_writes_the_barrier_first(w, monkeypatch):
    from core.services import visible_run_segment_settlement as s

    order = []
    real = w.wait_.block_wakes_for_run
    monkeypatch.setattr(w.wait_, "block_wakes_for_run",
                        lambda **kw: order.append("blokeret") or real(**kw))
    monkeypatch.setattr(s, "settle_segment_exit",
                        lambda **kw: order.append("journal") or "udfald")
    a = w.child("a1")
    ct = w.reg([a])
    assert s.settle_user_stop(run_id=RUN, session_id=SESS) == "udfald"
    assert order == ["blokeret", "journal"]
    assert w.wait_.get_contract(ct["contract_id"])["status"] == "stopped"


def test_dispatcher_tick_recovers_a_wake_lost_between_commit_and_file(w, monkeypatch):
    import core.services.agent_wake_intentions as aw

    real = aw.stage_wake
    monkeypatch.setattr(aw, "stage_wake", lambda **kw: (_ for _ in ()).throw(OSError("disk")))
    a = w.child("a1")
    w.reg([a])
    w.done(a)
    assert w.wakes() == {}
    monkeypatch.setattr(aw, "stage_wake", real)
    seen = {}
    monkeypatch.setattr("core.services.visible_runs_sections.detached_run.start_user_run_detached",
                        lambda **kw: seen.update(kw) or "visible-wake-2")
    monkeypatch.setattr("core.services.run_event_log.active_run_for_session", lambda s: None)
    from core.services import visible_run_recovery_dispatcher as d
    out = d.recover_due_once(owner="api")
    assert out["started"] == 1 and seen["session_id"] == SESS
