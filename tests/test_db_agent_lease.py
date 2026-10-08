"""C2: workerlease med fencing-token, supervisor-genopretning uden blind genudfoerelse."""
from __future__ import annotations

import json
import time
from datetime import UTC, datetime, timedelta

import pytest

T0 = datetime(2026, 10, 7, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def ls(isolated_runtime, monkeypatch):
    import core.runtime.db_agent_contract as c
    import core.runtime.db_agent_lease as lease
    import core.services.agent_contract_service as svc
    from core.runtime.db_agent_runtime import create_agent_registry_entry

    class H:
        c_, l_, svc_ = c, lease, svc
        started: list = []

        def assignment(self, name="a1", owner="bjorn", session="s1"):
            create_agent_registry_entry(agent_id=name, role="r", goal="g")
            c.bind_agent_owner(agent_id=name, owner_user_id=owner, owner_session_id=session)
            return c.accept_assignment(agent_id=name, owner_user_id=owner, origin_session_id=session,
                                       goal="g", parent_agent_id="jarvis", parent_run_id="pr")

        def expire(self, assignment_id):
            cn = c._conn()
            cn.execute("UPDATE agent_leases SET lease_until='2000-01-01T00:00:00Z' WHERE assignment_id=?",
                       (assignment_id,))
            cn.commit()

        def run_row(self, run_id):
            r = c._conn().execute("SELECT * FROM agent_runs WHERE run_id=?", (run_id,)).fetchone()
            return {k: r[k] for k in r.keys()}

        def tool_call(self, run_id, agent_id, finished):
            from core.runtime.db_agent_runtime import create_agent_tool_call
            create_agent_tool_call(tool_call_id=f"tc-{run_id}-{finished}", run_id=run_id,
                                   agent_id=agent_id, tool_name="write_file", status="running",
                                   started_at="2026-10-07T12:00:00Z",
                                   finished_at="2026-10-07T12:00:01Z" if finished else "")

    h = H()
    h.started = []
    monkeypatch.setattr(svc, "_run_in_background", lambda fn: h.started.append(fn))
    return h


# --- lease-grundlaget ---------------------------------------------------------------------

def test_acquire_gives_increasing_tokens_and_refuses_a_live_lease(ls):
    acc = ls.assignment()
    a = acc["assignment_id"]
    t1 = ls.l_.acquire(assignment_id=a, holder="w1", now=T0)
    assert t1 == 1
    with pytest.raises(ls.c_.ContractError) as e:
        ls.l_.acquire(assignment_id=a, holder="w2", now=T0 + timedelta(seconds=30))
    assert e.value.code == "LEASE_HELD"
    t2 = ls.l_.acquire(assignment_id=a, holder="w2", now=T0 + timedelta(seconds=91))   # udloebet
    assert t2 == 2


def test_renew_extends_only_for_the_current_holder_token_and_before_expiry(ls):
    a = ls.assignment()["assignment_id"]
    tok = ls.l_.acquire(assignment_id=a, holder="w1", now=T0)
    R = ls.l_.renew
    assert R(assignment_id=a, holder="w1", token=tok, now=T0 + timedelta(seconds=30)) is True
    assert R(assignment_id=a, holder="w2", token=tok, now=T0 + timedelta(seconds=31)) is False
    assert R(assignment_id=a, holder="w1", token=tok + 1, now=T0 + timedelta(seconds=31)) is False
    assert ls.l_.is_current(assignment_id=a, token=tok, now=T0 + timedelta(seconds=100)) is True   # 30+90
    # udloebet -> kan IKKE fornyes (supervisoren overtager)
    assert R(assignment_id=a, holder="w1", token=tok, now=T0 + timedelta(seconds=400)) is False
    assert ls.l_.is_current(assignment_id=a, token=tok, now=T0 + timedelta(seconds=400)) is False


def test_a_takeover_makes_the_old_token_stale_even_if_the_old_worker_wakes_up(ls):
    a = ls.assignment()["assignment_id"]
    old = ls.l_.acquire(assignment_id=a, holder="w1", now=T0)
    new = ls.l_.acquire(assignment_id=a, holder="w2", now=T0 + timedelta(seconds=120))
    assert ls.l_.is_current(assignment_id=a, token=old, now=T0 + timedelta(seconds=121)) is False
    assert ls.l_.is_current(assignment_id=a, token=new, now=T0 + timedelta(seconds=121)) is True
    assert ls.l_.renew(assignment_id=a, holder="w1", token=old, now=T0 + timedelta(seconds=121)) is False


def test_release_ends_the_lease_and_a_new_holder_can_take_over_at_once(ls):
    a = ls.assignment()["assignment_id"]
    tok = ls.l_.acquire(assignment_id=a, holder="w1", now=T0)
    assert ls.l_.release(assignment_id=a, holder="w1", token=tok) is True
    assert ls.l_.release(assignment_id=a, holder="w1", token=tok) is False
    assert ls.l_.acquire(assignment_id=a, holder="w2", now=T0 + timedelta(seconds=1)) == tok + 1


# --- scope og fencing ----------------------------------------------------------------------------

def test_scope_without_an_assignment_is_a_noop_and_current(ls):
    from core.runtime.db_agent_runtime import create_agent_registry_entry

    create_agent_registry_entry(agent_id="legacy", role="r", goal="g")
    with ls.l_.agent_lease_scope("legacy") as sc:
        assert sc is None and ls.l_.scope_is_current() is True
    assert ls.l_.scope_is_current() is True


def test_scope_holds_renews_and_releases_the_lease(ls):
    acc = ls.assignment()
    a = acc["assignment_id"]
    with ls.l_.agent_lease_scope("a1", lease_seconds=0.6, renew_seconds=0.1) as sc:
        assert sc["token"] == 1 and ls.l_.scope_is_current() is True
        time.sleep(1.0)                    # laengere end den oprindelige lease: kun fornyelse holder den
        assert ls.l_.scope_is_current() is True
    row = ls.c_._conn().execute("SELECT state FROM agent_leases WHERE assignment_id=?", (a,)).fetchone()
    assert row["state"] == "released"
    assert ls.l_.scope_is_current() is True            # uden for scope: ingen begraensning


def test_scope_refuses_to_run_when_another_worker_holds_a_live_lease(ls):
    acc = ls.assignment()
    ls.l_.acquire(assignment_id=acc["assignment_id"], holder="anden")
    with pytest.raises(ls.c_.ContractError) as e:
        with ls.l_.agent_lease_scope("a1"):
            pytest.fail("blokken maa ikke koere")
    assert e.value.code == "LEASE_HELD"


def test_a_stale_scope_is_not_current_and_stays_lost(ls):
    acc = ls.assignment()
    with ls.l_.agent_lease_scope("a1", renew_seconds=60) as sc:
        ls.expire(acc["assignment_id"])
        ls.l_.acquire(assignment_id=acc["assignment_id"], holder="ny-worker")
        assert ls.l_.scope_is_current() is False
        assert sc["lost"].is_set() and ls.l_.scope_is_current() is False


def test_scope_check_is_fail_closed_on_a_database_error(ls, monkeypatch):
    acc = ls.assignment()
    with ls.l_.agent_lease_scope("a1", renew_seconds=60):
        monkeypatch.setattr(ls.l_, "is_current", lambda **k: (_ for _ in ()).throw(RuntimeError("db")))
        assert ls.l_.scope_is_current() is False


def test_a_stale_worker_cannot_write_the_terminal_outcome(ls):
    from core.runtime.db_agent_runtime import update_agent_registry_entry

    acc = ls.assignment()
    with ls.l_.agent_lease_scope("a1", renew_seconds=60):
        ls.expire(acc["assignment_id"])
        ls.l_.acquire(assignment_id=acc["assignment_id"], holder="ny-worker")
        update_agent_registry_entry("a1", status="completed")        # gammel worker skriver
    a = ls.c_.get_assignment(assignment_id=acc["assignment_id"], owner_user_id="bjorn")
    assert a["status"] == "queued"
    assert ls.c_.list_pending_results(owner_user_id="bjorn", origin_session_id="s1") == []


def test_the_current_worker_settles_normally(ls):
    from core.runtime.db_agent_runtime import update_agent_registry_entry

    acc = ls.assignment()
    with ls.l_.agent_lease_scope("a1", renew_seconds=60):
        update_agent_registry_entry("a1", status="completed")
    assert ls.c_.get_assignment(assignment_id=acc["assignment_id"], owner_user_id="bjorn")["status"] == "completed"
    assert len(ls.c_.list_pending_results(owner_user_id="bjorn", origin_session_id="s1")) == 1


def test_a_stale_worker_cannot_start_another_tool_call(ls, monkeypatch):
    import core.services.agent_runtime_base as base
    import core.tools.simple_tools as st

    monkeypatch.setattr(st, "execute_tool", lambda *a, **k: pytest.fail("vaerktoej koert af stale worker"))
    acc = ls.assignment()
    call = {"function": {"name": "read_file", "arguments": "{}"}}
    with ls.l_.agent_lease_scope("a1", renew_seconds=60):
        ls.expire(acc["assignment_id"])
        ls.l_.acquire(assignment_id=acc["assignment_id"], holder="ny-worker")
        out = json.loads(base._execute_agent_tool_call(call, agent_id="a1"))
    assert (out["status"], out["code"]) == ("error", "LEASE_LOST")


# --- supervisor ----------------------------------------------------------------------------------

def _expired(ls, name="a1"):
    acc = ls.assignment(name)
    ls.l_.acquire(assignment_id=acc["assignment_id"], holder="doed-worker", now=T0)
    return acc


def test_nothing_expired_means_nothing_done(ls):
    acc = ls.assignment()
    ls.l_.acquire(assignment_id=acc["assignment_id"], holder="levende", now=T0)
    assert ls.l_.reconcile_expired_leases(now=T0 + timedelta(seconds=30)) == []


def test_expired_lease_without_open_tool_calls_fails_the_run_and_retries_as_a_new_attempt(ls):
    acc = _expired(ls)
    done = ls.l_.reconcile_expired_leases(now=T0 + timedelta(seconds=200))
    assert done == [{"assignment_id": acc["assignment_id"], "action": "retry", "attempt": 2,
                     "agent_id": "a1"}]
    r = ls.run_row(acc["run_id"])
    assert (r["status"], r["error_code"], r["error_phase"], r["failure_reason"]) == (
        "failed", "LEASE_EXPIRED", "recovery", "lease_expired")
    assert ls.c_.get_assignment(assignment_id=acc["assignment_id"], owner_user_id="bjorn")["status"] == "queued"
    assert ls.c_.list_pending_results(owner_user_id="bjorn", origin_session_id="s1") == []   # ingen tidlig besked


def test_two_supervisors_see_the_same_lease_and_only_one_acts(ls):
    _expired(ls)
    first = ls.l_.reconcile_expired_leases(now=T0 + timedelta(seconds=200))
    second = ls.l_.reconcile_expired_leases(now=T0 + timedelta(seconds=200))
    assert len(first) == 1 and second == []


def test_an_open_tool_call_means_outcome_unknown_and_no_blind_retry(ls):
    acc = _expired(ls)
    ls.tool_call(acc["run_id"], "a1", finished=False)
    done = ls.l_.reconcile_expired_leases(now=T0 + timedelta(seconds=200))
    assert done == [{"assignment_id": acc["assignment_id"], "action": "outcome_unknown",
                     "open_tool_calls": 1}]
    assert ls.run_row(acc["run_id"])["status"] == "outcome_unknown"
    assert ls.c_.get_assignment(assignment_id=acc["assignment_id"], owner_user_id="bjorn")["status"] == "waiting"
    pending = ls.c_.list_pending_results(owner_user_id="bjorn", origin_session_id="s1")
    assert [m for m in pending if m["message_kind"] == "terminal"] == []      # ingen terminalbesked...
    assert [(m["message_kind"], m["state_code"]) for m in pending] == [("state", "outcome_unknown")]   # ...kun tilstanden


def test_a_finished_tool_call_does_not_block_a_safe_retry(ls):
    acc = _expired(ls)
    ls.tool_call(acc["run_id"], "a1", finished=True)
    done = ls.l_.reconcile_expired_leases(now=T0 + timedelta(seconds=200))
    assert done[0]["action"] == "retry"


def test_second_expiry_exhausts_the_safe_attempts_and_ends_with_one_failed_result(ls):
    acc = _expired(ls)
    ls.l_.reconcile_expired_leases(now=T0 + timedelta(seconds=200))
    # forsoeg 2: nyt run bundet til assignmentet, ny worker doer
    cn = ls.c_._conn()
    cn.execute("INSERT INTO agent_runs (run_id, agent_id, status, assignment_id, owner_user_id, "
               "attempt_no, created_at, updated_at) VALUES ('run-2','a1','running',?,?,2,'t','t')",
               (acc["assignment_id"], "bjorn"))
    cn.commit()
    ls.l_.acquire(assignment_id=acc["assignment_id"], holder="doed-worker-2", now=T0 + timedelta(seconds=300))
    done = ls.l_.reconcile_expired_leases(now=T0 + timedelta(seconds=500))
    assert done == [{"assignment_id": acc["assignment_id"], "action": "failed", "attempts": 2}]
    a = ls.c_.get_assignment(assignment_id=acc["assignment_id"], owner_user_id="bjorn")
    assert a["status"] == "failed"
    (m,) = ls.c_.list_pending_results(owner_user_id="bjorn", origin_session_id="s1")
    payload = json.loads(m["payload_json"])
    assert payload["attempt_run_ids"] == [acc["run_id"], "run-2"] and payload["error_code"] == "AGENT_FAILED"


def test_a_terminal_assignment_is_left_alone(ls):
    acc = _expired(ls)
    ls.c_.commit_terminal_outcome(assignment_id=acc["assignment_id"], status="completed")
    assert ls.l_.reconcile_expired_leases(now=T0 + timedelta(seconds=200)) == []


def test_service_supervise_restarts_a_safe_retry_in_the_background(ls):
    acc = ls.assignment()
    ls.l_.acquire(assignment_id=acc["assignment_id"], holder="doed-worker")
    ls.expire(acc["assignment_id"])
    done = ls.svc_.supervise()
    assert [d["action"] for d in done] == ["retry"] and len(ls.started) == 1
    assert ls.svc_.supervise() == [] and len(ls.started) == 1          # ingen dobbelt genstart


def test_the_dispatcher_tick_supervises_even_when_the_engine_is_switched_off(ls, monkeypatch):
    from core.services import visible_run_recovery_dispatcher as d

    assert ls.svc_.capability_enabled() is False
    acc = ls.assignment()
    ls.l_.acquire(assignment_id=acc["assignment_id"], holder="doed-worker")
    ls.expire(acc["assignment_id"])
    monkeypatch.setattr("core.services.run_event_log.active_run_for_session", lambda s: None)
    d.recover_due_once(owner="api")
    assert ls.run_row(acc["run_id"])["status"] == "failed" and len(ls.started) == 1


def test_claim_is_atomic_only_the_first_caller_wins(ls):
    acc = _expired(ls)
    a = acc["assignment_id"]
    late = T0 + timedelta(seconds=200)
    assert ls.l_._claim(a, 1, late) is True
    assert ls.l_._claim(a, 1, late) is False
    assert ls.l_._claim(a, 99, late) is False                 # forkert token


def test_a_supervisor_that_loses_the_claim_decides_nothing(ls, monkeypatch):
    _expired(ls)
    monkeypatch.setattr(ls.l_, "_claim", lambda *a, **k: False)
    monkeypatch.setattr(ls.l_, "_decide", lambda *a, **k: pytest.fail("taberen maa ikke handle"))
    assert ls.l_.reconcile_expired_leases(now=T0 + timedelta(seconds=200)) == []


def test_execute_agent_task_really_holds_the_lease_while_the_agent_runs(ls, monkeypatch):
    from core.services import agent_runtime_spawn as M
    from core.services.agent_runtime_spawn import execute_agent_task, spawn_agent_task

    seen = {}

    class _F:
        def execute_with_role_or_fallback(self, **kw):
            row = ls.c_._conn().execute("SELECT state, fencing_token FROM agent_leases").fetchone()
            seen["during"] = (row["state"], row["fencing_token"], ls.l_.scope_is_current())
            return {"text": "klar", "input_tokens": 1, "output_tokens": 1, "status": "completed"}

    monkeypatch.setattr(M, "agent_tools_enabled", lambda: False)
    monkeypatch.setattr(M, "_snapshot_tools", lambda agent: [])
    monkeypatch.setattr(M, "_facade", lambda: _F())
    from core.services import agent_runtime_base as base
    monkeypatch.setattr(base, "_facade", lambda: M._facade())
    agent = spawn_agent_task(role="researcher", goal="g", auto_execute=False,
                             context={"user_id": "bjorn", "parent_session_id": "s1"})
    execute_agent_task(agent_id=agent["agent_id"])
    assert seen["during"] == ("held", 1, True)
    row = ls.c_._conn().execute("SELECT state FROM agent_leases").fetchone()
    assert row["state"] == "released"
    (a,) = [r for r in ls.c_._conn().execute("SELECT status FROM agent_assignments")]
    assert a["status"] == "completed"
