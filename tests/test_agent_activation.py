"""G3: persistente agenter - ejer ved spawn, ét assignment og én rute pr. aktivering. Rigtig sqlite, falsk facade."""
from __future__ import annotations

import json
import threading
from datetime import UTC, datetime, timedelta

import pytest

BJORN, ANDEN = "bjorn-id", "anden-bruger"
CTX = {"user_id": ANDEN, "parent_session_id": "sess-1", "parent_run_id": "pr-1"}


@pytest.fixture
def pa(isolated_runtime, monkeypatch):
    import core.runtime.db_agent_contract as c
    import core.runtime.db_agent_runtime as rt
    import core.services.agent_contract_service as svc
    import core.services.agent_runtime as ar
    import core.services.agent_runtime_spawn as sp
    from core.services import agent_model_router as M
    from core.services import in_flight_runs as ifr

    monkeypatch.setattr("core.identity.owner_resolver.owner_user_id", lambda: BJORN)
    ifr._mutate(lambda r: r.clear())
    svc.set_capability(True, role="owner")

    class F:
        def __init__(self): self.calls, self.fail = [], False
        def __call__(self, **kw):
            self.calls.append(kw)
            if self.fail:
                raise M.ModelCallFailed("nede", provider=kw["provider"], model=kw["model"])
            return {"text": "vagten fandt intet nyt", "provider": kw["provider"], "model": kw["model"],
                    "status": "completed"}

    f = F()
    monkeypatch.setattr(ar, "execute_with_role_or_fallback", f)
    monkeypatch.setattr(sp, "_snapshot_tools", lambda agent: [])

    class H:
        c_, rt_, svc_, sp_, f_ = c, rt, svc, sp, f

        def spawn(self, ctx=None, **kw):
            kw.setdefault("persistent", True)
            kw.setdefault("ttl_seconds", 900)
            return sp.spawn_agent_task(role="researcher", goal="hold oeje med X", auto_execute=False,
                                       context=dict(CTX if ctx is None else ctx), **kw)["agent_id"]

        def assignments(self, agent_id):
            return [dict(r) for r in c._conn().execute(
                "SELECT * FROM agent_assignments WHERE agent_id=? ORDER BY created_at", (agent_id,))]

        def outbox(self):
            return [dict(r) for r in c._conn().execute("SELECT * FROM agent_result_outbox ORDER BY created_at")]

        def n(self, table, where="1=1", args=()):
            return c._conn().execute(f"SELECT COUNT(*) FROM {table} WHERE {where}", args).fetchone()[0]

        def due(self, agent_id, slot):
            rt.update_agent_schedule(f"agent-schedule-{agent_id}", next_fire_at=slot, active=True)

    yield H()
    ifr._mutate(lambda r: r.clear())


def _scheduled(pa, agent_id, slot="2026-10-07T08:00:00+00:00"):
    pa.sp_.schedule_agent_task(agent_id=agent_id, delay_seconds=900)
    pa.due(agent_id, slot)
    return slot


# --- binding -----------------------------------------------------------------------------------

def test_a_persistent_agent_gets_its_authenticated_owner_and_session_but_no_assignment(pa):
    aid = pa.spawn()
    row = pa.rt_.get_agent_registry_entry(aid)
    assert (row["owner_user_id"], row["owner_session_id"]) == (ANDEN, "sess-1")
    assert pa.assignments(aid) == []


@pytest.mark.parametrize("ctx", [{}, {"user_id": ANDEN}, {"parent_session_id": "s"}])
def test_a_persistent_agent_without_owner_or_session_stays_legacy(pa, ctx):
    aid = pa.spawn(ctx=ctx)
    assert pa.rt_.get_agent_registry_entry(aid)["owner_user_id"] == "legacy_unscoped"


def test_with_the_engine_off_a_persistent_agent_stays_legacy_and_runs_as_before(pa):
    pa.svc_.set_capability(False)
    aid = pa.spawn()
    assert pa.rt_.get_agent_registry_entry(aid)["owner_user_id"] == "legacy_unscoped"
    pa.sp_.execute_agent_task(agent_id=aid)
    assert pa.assignments(aid) == [] and pa.outbox() == [] and "owner_user_id" not in pa.f_.calls[0]


# --- en aktivering = ét assignment + én rute + én terminalbesked -----------------------------------------

def test_each_activation_is_its_own_assignment_with_route_provenance_and_one_message(pa):
    from core.runtime import db_agent_route as R
    aid = pa.spawn()
    pa.sp_.execute_agent_task(agent_id=aid)
    pa.sp_.execute_agent_task(agent_id=aid)
    a1, a2 = pa.assignments(aid)
    assert a1["assignment_id"] != a2["assignment_id"]
    assert [(a["status"], a["owner_user_id"], a["origin_session_id"], a["operation"], a["parent_agent_id"],
             a["goal"]) for a in (a1, a2)] == [("completed", ANDEN, "sess-1", "activation", "jarvis",
                                               "hold oeje med X")] * 2
    msgs = pa.outbox()
    assert [m["assignment_id"] for m in msgs] == [a1["assignment_id"], a2["assignment_id"]]
    assert {m["result_type"] for m in msgs} == {"agent_result"} and {m["recipient_agent_id"] for m in msgs} == {"jarvis"}
    for a in (a1, a2):                                     # rute-proveniens (D) gaelder ogsaa dem
        (att,) = R.attempts_for_assignment(a["assignment_id"])
        assert (att["attempt"], att["route_source"], att["owner_user_id"]) == (1, "agent_pool", ANDEN)
        assert att["decision"]["activation"] is True and att["decision"]["candidates"]
    assert pa.rt_.get_agent_registry_entry(aid)["status"] == "scheduled"
    assert all(k["owner_user_id"] == ANDEN for k in pa.f_.calls)       # providerkaldet bærer den autentificerede ejer


def test_a_non_platform_owners_persistent_agent_never_gets_deepseek(pa):
    from core.runtime import db_agent_route as R
    aid = pa.spawn()
    pa.sp_.execute_agent_task(agent_id=aid)
    (att,) = R.attempts_for_assignment(pa.assignments(aid)[0]["assignment_id"])
    assert all(c["provider"] != "deepseek" for c in att["decision"]["candidates"])
    assert all(k["provider"] != "deepseek" for k in pa.f_.calls)


def test_the_long_term_agent_scenario_planned_wake_delivers_its_result_to_the_parent_inbox(pa):
    from core.services.agent_result_inbox import claim_for_model_step
    aid = pa.spawn()
    slot = _scheduled(pa, aid)
    out = pa.sp_.run_due_agent_schedules(limit=5)
    assert out["triggered_count"] == 1
    (a,) = pa.assignments(aid)
    assert (a["status"], a["created_by"], a["idempotency_key"]) == ("completed", "scheduler", f"activation:{aid}:{slot}")
    text = claim_for_model_step(owner_user_id=ANDEN, session_id="sess-1")
    assert aid in text and a["assignment_id"] in text and "vagten fandt intet nyt" in text
    assert claim_for_model_step(owner_user_id=ANDEN, session_id="sess-1") == ""      # claimes kun én gang
    assert claim_for_model_step(owner_user_id=BJORN, session_id="sess-1") == ""      # en anden ejer ser intet
    nxt = pa.rt_.get_agent_schedule(f"agent-schedule-{aid}")["next_fire_at"]
    assert nxt > datetime.now(UTC).isoformat()                                       # tidsplanen rykkede videre


def test_the_same_planned_slot_is_never_activated_twice(pa):
    aid = pa.spawn()
    slot = _scheduled(pa, aid)
    pa.sp_.run_due_agent_schedules(limit=5)
    calls = len(pa.f_.calls)
    pa.due(aid, slot)                                                    # samme slot igen (mistet/dobbelt)
    pa.sp_.run_due_agent_schedules(limit=5)
    assert len(pa.assignments(aid)) == 1 and len(pa.outbox()) == 1 and len(pa.f_.calls) == calls
    row = pa.rt_.get_agent_registry_entry(aid)
    assert "DUPLICATE_ACTIVATION" in row["last_error"]


def test_a_failed_activation_is_a_retry_in_the_same_assignment_not_a_result(pa):
    aid = pa.spawn()
    pa.f_.fail = True
    pa.sp_.execute_agent_task(agent_id=aid)
    (a,) = pa.assignments(aid)
    assert a["status"] == "active" and pa.outbox() == []                  # intet slutresultat, ingen parent-besked
    assert pa.rt_.get_agent_registry_entry(aid)["status"] == "scheduled"  # backoff - ikke terminal
    pa.f_.fail = False
    pa.sp_.execute_agent_task(agent_id=aid)                               # naeste aktivering genbruger assignmentet
    (a,) = pa.assignments(aid)
    runs = [r["attempt_no"] for r in pa.c_._conn().execute(
        "SELECT attempt_no FROM agent_runs WHERE assignment_id=? ORDER BY attempt_no", (a["assignment_id"],))]
    # aktivering 1: pulje-modellen svigtede (failover-forsoeg 1), cheap-lane-modellen ogsaa (forsoeg 2);
    # aktivering 2 genbruger assignmentet som forsoeg 3
    assert a["status"] == "completed" and runs == [1, 2, 3]
    (m,) = pa.outbox()
    assert len(json.loads(m["payload_json"])["attempt_run_ids"]) == 3


def test_scheduled_status_does_not_settle_a_non_persistent_agent(pa):
    aid = pa.sp_.spawn_agent_task(role="researcher", goal="g", auto_execute=False,
                                  context=dict(CTX))["agent_id"]
    pa.rt_.create_agent_run(run_id=pa.c_.queued_contract_run(aid), agent_id=aid, status="completed",
                            started_at="2026-10-07T10:00:00Z")       # selv med et FAERDIGT run
    pa.rt_.update_agent_registry_entry(aid, status="scheduled")
    assert [a["status"] for a in pa.assignments(aid)] == ["active"] and pa.outbox() == []


def test_a_finished_non_persistent_agent_is_not_given_an_activation_when_run_again(pa):
    aid = pa.sp_.spawn_agent_task(role="researcher", goal="g", auto_execute=False, context=dict(CTX))["agent_id"]
    pa.sp_.execute_agent_task(agent_id=aid)
    assert [a["status"] for a in pa.assignments(aid)] == ["completed"]
    pa.sp_.execute_agent_task(agent_id=aid)                           # et nyt assignment kommer fra followup_agent
    assert [a["operation"] for a in pa.assignments(aid)] == ["dispatch"]


# --- afslag: kill switch, livscyklus, model --------------------------------------------------------------

def _refused(pa, aid, code):
    assert pa.assignments(aid) == [] and pa.outbox() == [] and pa.f_.calls == []
    assert f"({code})" in pa.rt_.get_agent_registry_entry(aid)["last_error"]
    kinds = [m["kind"] for m in pa.rt_.list_agent_messages(agent_id=aid, thread_id=f"agent-thread-{aid}", limit=50)]
    assert "activation-refused" in kinds


def test_the_kill_switch_blocks_planned_activations(pa):
    aid = pa.spawn()
    pa.svc_.set_capability(False)
    surface = pa.sp_.execute_agent_task(agent_id=aid)
    assert surface["activation"]["code"] == "POLICY_DENIED"
    _refused(pa, aid, "POLICY_DENIED")


@pytest.mark.parametrize("life", ["suspended", "closing", "closed"])
def test_a_suspended_or_closing_agent_is_not_activated(pa, life):
    aid = pa.spawn()
    cn = pa.c_._conn()
    cn.execute("UPDATE agent_registry SET lifecycle_status=? WHERE agent_id=?", (life, aid))
    cn.commit()
    assert pa.sp_.execute_agent_task(agent_id=aid)["activation"]["code"] == "POLICY_DENIED"
    _refused(pa, aid, "POLICY_DENIED")


def test_no_allowed_model_means_no_activation_with_the_reasons(pa, monkeypatch):
    from core.services import agent_model_policy as pol
    monkeypatch.setattr(pol, "_agent_candidates", lambda **kw: [])
    aid = pa.spawn()
    surface = pa.sp_.execute_agent_task(agent_id=aid)
    assert surface["activation"]["code"] == "MODEL_UNAVAILABLE"
    _refused(pa, aid, "MODEL_UNAVAILABLE")


def test_a_legacy_persistent_agent_is_untouched_by_activation(pa):
    aid = pa.spawn(ctx={})
    pa.svc_.set_capability(False)
    pa.svc_.set_capability(True, role="owner")
    pa.sp_.execute_agent_task(agent_id=aid)
    assert pa.assignments(aid) == [] and pa.outbox() == [] and "owner_user_id" not in pa.f_.calls[0]


def test_two_simultaneous_activations_create_exactly_one_assignment(pa):
    from core.services.agent_activation import ensure_activation
    aid = pa.spawn()
    barrier, out, errors = threading.Barrier(2), [], []

    def go():
        try:
            barrier.wait(timeout=5)
            out.append(ensure_activation(aid)["status"])
        except BaseException as exc:                                  # traadens undtagelse er et testresultat
            errors.append(exc)

    ts = [threading.Thread(target=go) for _ in range(2)]
    [t.start() for t in ts]
    [t.join(timeout=10) for t in ts]
    assert errors == [] and len(pa.assignments(aid)) == 1
    assert sorted(out) in (["created", "reused"], ["created", "refused"])
