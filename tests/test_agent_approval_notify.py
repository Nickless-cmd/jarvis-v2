"""F4c: hvem faar at vide, hvornaar Jarvis vaekkes, og at et brugerstop spaerrer vaekningen."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

O, S, RUN = "bjorn", "sess-1", "visible-parent"


@pytest.fixture
def nt(isolated_runtime, monkeypatch):
    import core.runtime.db_agent_approvals as appr
    import core.runtime.db_agent_contract as c
    import core.runtime.db_agent_wait as wait
    import core.services.agent_approval_notify as N
    from core.runtime.db_agent_runtime import create_agent_registry_entry
    from core.services import in_flight_runs as ifr

    ifr._mutate(lambda r: r.clear())
    monkeypatch.setattr("core.identity.owner_resolver.owner_user_id", lambda: "platform-ejer")
    busy = {"v": None}
    monkeypatch.setattr("core.services.run_event_log.active_run_for_session", lambda s: busy["v"])

    class H:
        appr_, c_, wait_, N_, ifr_, busy_ = appr, c, wait, N, ifr, busy

        def req(self, name="a1", cmd="rm -rf build", session=S, parent_run=RUN):
            create_agent_registry_entry(agent_id=name, role="executor", goal="g")
            c.bind_agent_owner(agent_id=name, owner_user_id=O, owner_session_id=session)
            acc = c.accept_assignment(agent_id=name, owner_user_id=O, origin_session_id=session, goal="g",
                                      parent_agent_id="jarvis", parent_run_id=parent_run)
            return appr.request(owner_user_id=O, origin_session_id=session, assignment_id=acc["assignment_id"],
                                tool_name="bash", arguments={"command": cmd}, run_id=acc["run_id"])

        def wakes(self):
            return {k: v for k, v in ifr._load().items() if v.get("wake_kind") == "agent_approval"}

        def fresh(self, r):
            return appr.get(approval_id=r["approval_id"])

    yield H()
    ifr._mutate(lambda r: r.clear())


def test_an_idle_parent_gets_exactly_one_system_marked_wake_for_the_approval(nt):
    r = nt.req()
    task = nt.N_.on_requested(r)
    (tid, rec), = nt.wakes().items()
    assert task == tid == f"agentappr-{r['approval_id']}"
    assert (rec["status"], rec["session_id"], rec["force_user_id"], rec["kind"], rec["parent_run_id"]) == (
        "recovering", S, O, "visible", RUN)
    assert rec["original_request"].startswith("[SYSTEM — approval venter, ikke en besked fra brugeren]")
    assert "bash(" in rec["original_request"] and "IKKE godkende" in rec["original_request"]
    assert nt.fresh(r)["wake_task_id"] == tid
    nt.N_.on_requested(nt.fresh(r))                                        # idempotent
    assert len(nt.wakes()) == 1


def test_an_active_parent_is_not_woken_it_gets_the_request_at_its_next_step(nt):
    nt.busy_["v"] = "visible-live"
    r = nt.req()
    assert nt.N_.on_requested(r) == "" and nt.wakes() == {}


def test_an_unknown_session_state_counts_as_busy_never_a_duplicate_run(nt, monkeypatch):
    monkeypatch.setattr("core.services.run_event_log.active_run_for_session",
                        lambda s: (_ for _ in ()).throw(RuntimeError("log nede")))
    assert nt.N_.on_requested(nt.req()) == "" and nt.wakes() == {}


def test_the_supervisor_tick_wakes_a_parent_that_ended_before_it_could_mention_it(nt):
    nt.busy_["v"] = "visible-live"
    r = nt.req()
    nt.N_.on_requested(r)
    soon = datetime.now(UTC) + timedelta(seconds=5)
    late = datetime.now(UTC) + timedelta(seconds=60)
    nt.busy_["v"] = None                                                  # parent sluttede
    assert nt.N_.ensure_wakes(now=soon) == []                             # endnu inden for GRACE
    assert nt.N_.ensure_wakes(now=late) == [f"agentappr-{r['approval_id']}"]
    assert nt.N_.ensure_wakes(now=late) == [] and len(nt.wakes()) == 1


def test_the_supervisor_tick_skips_busy_sessions_announced_and_decided_approvals(nt):
    late = datetime.now(UTC) + timedelta(seconds=60)
    busy, announced, decided = nt.req("a1"), nt.req("a2", cmd="x2"), nt.req("a3", cmd="x3")
    nt.appr_.claim_announcements(owner_user_id=O, origin_session_id=S)      # alle tre omtalt -> ingen vaekning
    assert nt.N_.ensure_wakes(now=late) == []
    nt.appr_.decide(approval_id=decided["approval_id"], decision="deny", actor_user_id=O, actor_kind="human",
                    digest=decided["args_digest"])
    nt.busy_["v"] = "live"
    assert nt.N_.ensure_wakes(now=late) == []


def test_a_manual_user_stop_blocks_the_wake_but_the_approval_stays_pending_and_visible(nt):
    r = nt.req()
    nt.wait_.block_wakes_for_run(run_id=RUN)                                # brugeren stoppede parentens run
    assert nt.N_.on_requested(r) == "" and nt.N_.ensure_wakes(now=datetime.now(UTC) + timedelta(minutes=5)) == []
    assert nt.wakes() == {} and nt.fresh(r)["status"] == "pending"
    assert [x["approval_id"] for x in nt.appr_.list_for_owner(owner_user_id=O, status="pending")] == [r["approval_id"]]


def test_a_stop_after_the_wake_was_planned_cancels_it_before_it_starts(nt):
    r = nt.req()
    nt.N_.on_requested(r)
    out = nt.wait_.block_wakes_for_run(run_id=RUN)
    assert out["cancelled"] == 1
    (rec,) = nt.wakes().values()
    assert rec["status"] == "cancelled" and nt.fresh(r)["status"] == "pending"


def test_a_stop_of_another_run_does_not_block(nt):
    r = nt.req()
    nt.wait_.block_wakes_for_run(run_id="visible-andet")
    assert nt.N_.on_requested(r) != ""


def test_two_approvals_in_one_session_share_one_wake_never_two_parent_runs(nt):
    a, b = nt.req("a1", cmd="1"), nt.req("a2", cmd="2")
    nt.N_.on_requested(a)
    nt.N_.on_requested(nt.fresh(b))
    assert len(nt.wakes()) == 1
    assert nt.fresh(a)["wake_task_id"] == nt.fresh(b)["wake_task_id"] != ""


def test_deciding_cancels_a_planned_wake(nt):
    r = nt.req()
    nt.N_.on_requested(r)
    assert nt.N_.cancel_wake(nt.fresh(r), "afgjort") is True
    (rec,) = nt.wakes().values()
    assert rec["status"] == "cancelled"
    assert nt.N_.cancel_wake({"wake_task_id": ""}, "x") is False


def test_the_dispatcher_starts_the_approval_wake_through_the_existing_recovery_path(nt, monkeypatch):
    from core.services import visible_run_recovery_dispatcher as d

    r = nt.req()
    nt.N_.on_requested(r)
    seen = {}
    monkeypatch.setattr("core.services.visible_runs_sections.detached_run.start_user_run_detached",
                        lambda **kw: seen.update(kw) or "visible-wake-appr")
    out = d.recover_due_once(owner="api")
    assert (out["started"], out["run_id"]) == (1, "visible-wake-appr")
    assert seen["session_id"] == S and seen["force_user_id"] == O and "bash(" in seen["message"]
    assert seen["message"].startswith("[SYSTEM — approval venter")


def test_a_decided_approval_never_reaches_the_dispatcher(nt, monkeypatch):
    from core.services import visible_run_recovery_dispatcher as d

    r = nt.req()
    nt.N_.on_requested(r)
    nt.appr_.decide(approval_id=r["approval_id"], decision="deny", actor_user_id=O, actor_kind="human",
                    digest=r["args_digest"])
    nt.N_.cancel_wake(nt.fresh(r), "afgjort")
    monkeypatch.setattr("core.services.visible_runs_sections.detached_run.start_user_run_detached",
                        lambda **kw: pytest.fail("vaekning efter afgoerelse"))
    assert d.recover_due_once(owner="api")["started"] == 0


def test_a_wake_is_not_shown_as_an_interrupted_task(nt):
    nt.N_.on_requested(nt.req())
    assert nt.ifr_.recovery_snapshot(S) is None


def test_a_decided_approval_can_never_be_staged_for_a_wake(nt):
    r = nt.req()
    nt.appr_.decide(approval_id=r["approval_id"], decision="deny", actor_user_id=O, actor_kind="human",
                    digest=r["args_digest"])
    assert nt.N_.stage(nt.fresh(r)) == "" and nt.wakes() == {}


def test_the_supervisor_tick_itself_plants_the_wake_for_an_old_unannounced_approval(nt):
    import core.services.agent_contract_service as svc

    r = nt.req()
    c = nt.c_._conn()
    c.execute("UPDATE agent_approvals SET created_at='2000-01-01T00:00:00Z' WHERE approval_id=?", (r["approval_id"],))
    c.commit()
    svc.supervise()
    assert list(nt.wakes()) == [f"agentappr-{r['approval_id']}"]


def test_deciding_through_the_service_cancels_the_planned_wake(nt):
    import core.services.agent_contract_service as svc

    r = nt.req()
    nt.N_.on_requested(r)
    out = svc.decide_approval(approval_id=r["approval_id"], decision="deny", actor_user_id=O, actor_kind="human",
                              digest=r["args_digest"])
    assert out["status"] == "ok"
    (rec,) = nt.wakes().values()
    assert rec["status"] == "cancelled"
