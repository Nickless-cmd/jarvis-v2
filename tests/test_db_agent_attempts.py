"""G1: failover som nyt synligt runforsoeg - rigtig sqlite, falsk facade, ingen terminalbesked undervejs."""
from __future__ import annotations

import json
import threading
from datetime import UTC, datetime, timedelta

import pytest

ANDEN = "anden-bruger"
CHAIN = [
    {"route_source": "agent_pool", "provider": "copilot-premium", "model": "m1"},
    {"route_source": "agent_pool", "provider": "copilot-premium", "model": "m2"},
    {"route_source": "cheap_lane_fallback", "provider": "kilo", "model": "m3"},
]


@pytest.fixture
def at(isolated_runtime, monkeypatch):
    import core.runtime.db_agent_attempts as A
    import core.runtime.db_agent_contract as c
    import core.runtime.db_agent_lease as L
    import core.runtime.db_agent_route as R
    from core.runtime.db_agent_runtime import create_agent_registry_entry
    from core.services import agent_model_router as M
    from core.services import in_flight_runs as ifr

    monkeypatch.setattr("core.identity.owner_resolver.owner_user_id", lambda: "bjorn-id")
    ifr._mutate(lambda r: r.clear())

    class F:
        def __init__(self): self.calls, self.fail = [], set()
        def execute_with_role_or_fallback(self, **kw):
            self.calls.append(kw)
            if f"{kw['provider']}/{kw['model']}" in self.fail:
                raise M.ModelCallFailed("nede", provider=kw["provider"], model=kw["model"])
            return {"text": "ok", "provider": kw["provider"], "model": kw["model"], "status": "completed"}

    class H:
        A_, c_, L_, R_, M_ = A, c, L, R, M
        f = F()

        def agent(self, name="a1", policy="read-only-runtime"):
            create_agent_registry_entry(agent_id=name, role="researcher", goal="g", tool_policy=policy,
                                        provider="copilot-premium", model="m1")
            c.bind_agent_owner(agent_id=name, owner_user_id=ANDEN, owner_session_id="s1")
            acc = c.accept_assignment(agent_id=name, owner_user_id=ANDEN, origin_session_id="s1",
                                      goal="g", parent_agent_id="jarvis", parent_run_id="pr")
            R.record_decision(assignment_id=acc["assignment_id"], agent_id=name, owner_user_id=ANDEN,
                              decision={"route_source": "agent_pool", "provider": "copilot-premium",
                                        "model": "m1", "candidates": CHAIN, "rejected": []}, attempt=1)
            cn = c._conn()                                  # runnet er i gang
            cn.execute("UPDATE agent_runs SET status='running', started_at='2026-10-07T10:00:00Z', "
                       "provider='copilot-premium', model='m1', "
                       "input_summary='g', input_payload_json='{\"prompt\":\"p\"}' WHERE run_id=?",
                       (acc["run_id"],))
            cn.execute("UPDATE agent_assignments SET status='active' WHERE assignment_id=?",
                       (acc["assignment_id"],))
            cn.execute("INSERT INTO agent_run_prompts (run_id, assignment_id, agent_id, owner_user_id, "
                       "delegation_version, role_version, layer_digests_json, effective_text, provider, "
                       "model, tool_names_json, tool_schema_sha256, created_at) VALUES "
                       "(?,?,?,?,'d1','r1','{}','prompttekst','copilot-premium','m1','[]','x','t')",
                       (acc["run_id"], acc["assignment_id"], name, ANDEN))
            cn.commit()
            return {"agent_id": name, "tool_policy": policy, "provider": "copilot-premium", "model": "m1"}, acc

        def call(self, agent, run_id="", **kw):
            return M.call_agent_model(agent=agent, facade=self.f, requires_tools=True, lane="agent",
                                      provider=agent["provider"], model=agent["model"], run_id=run_id, **kw)

        def runs(self, assignment_id):
            return [dict(r) for r in c._conn().execute(
                "SELECT * FROM agent_runs WHERE assignment_id=? ORDER BY attempt_no", (assignment_id,))]

        def n(self, table, where="1=1", args=()):
            return c._conn().execute(f"SELECT COUNT(*) FROM {table} WHERE {where}", args).fetchone()[0]

    yield H()
    ifr._mutate(lambda r: r.clear())


def test_a_failover_is_a_new_visible_run_attempt_with_its_own_failure_record(at):
    ag, acc = at.agent()
    at.f.fail = {"copilot-premium/m1"}
    assert at.call(ag, run_id=acc["run_id"])["model"] == "m2"
    old, new = at.runs(acc["assignment_id"])
    assert (old["run_id"], old["attempt_no"], old["status"], old["error_phase"], old["error_code"],
            old["provider_status"]) == (acc["run_id"], 1, "failed", "model", "MODEL_FAILOVER", "failed")
    assert "copilot-premium/m1" in old["failure_reason"] and old["finished_at"] != ""
    assert (new["attempt_no"], new["status"], new["provider"], new["model"], new["assignment_id"],
            new["owner_user_id"], new["finished_at"]) == (2, "running", "copilot-premium", "m2",
                                                          acc["assignment_id"], ANDEN, "")
    assert new["run_id"] != old["run_id"] and new["input_payload_json"] == old["input_payload_json"]
    route = at.R_.attempts_for_assignment(acc["assignment_id"])
    assert [(r["attempt"], r["model"]) for r in route] == [(1, "m1"), (2, "m2")]
    assert (route[1]["decision"]["run_id"], route[1]["decision"]["failed_run_id"]) == (new["run_id"], old["run_id"])
    reg = at.c_._conn().execute("SELECT provider, model FROM agent_registry WHERE agent_id='a1'").fetchone()
    assert (reg["provider"], reg["model"]) == ("copilot-premium", "m2")
    snap = at.c_._conn().execute("SELECT provider, model, effective_text FROM agent_run_prompts "
                                 "WHERE run_id=?", (new["run_id"],)).fetchone()
    assert tuple(snap) == ("copilot-premium", "m2", "prompttekst")        # prompten gaelder det nye forsoeg
    assert at.A_.live_run_id(old["run_id"]) == new["run_id"]


def test_a_second_failover_chains_a_third_attempt_from_the_stale_run_id(at):
    ag, acc = at.agent()
    at.f.fail = {"copilot-premium/m1", "copilot-premium/m2"}
    assert at.call(ag, run_id=acc["run_id"])["model"] == "m3"
    runs = at.runs(acc["assignment_id"])
    assert [(r["attempt_no"], r["status"], r["error_code"], r["model"]) for r in runs] == [
        (1, "failed", "MODEL_FAILOVER", "m1"), (2, "failed", "MODEL_FAILOVER", "m2"),
        (3, "running", "", "m3")]
    assert at.A_.live_run_id(acc["run_id"]) == runs[2]["run_id"]
    assert [(a["attempt_no"], a["model"]) for a in at.A_.attempts_for_assignment(acc["assignment_id"])] == [
        (1, "m1"), (2, "m2"), (3, "m3")]


def test_a_healthy_first_candidate_creates_no_extra_run(at):
    ag, acc = at.agent()
    at.call(ag, run_id=acc["run_id"])
    assert [r["run_id"] for r in at.runs(acc["assignment_id"])] == [acc["run_id"]]


def test_the_failover_sends_no_terminal_message_wakes_no_parent_and_leaves_the_assignment_open(at):
    from core.runtime.db_agent_wait import register_wait
    from core.services import in_flight_runs as ifr
    ag, acc = at.agent()
    ct = register_wait(owner_user_id=ANDEN, origin_session_id="s1", parent_run_id="pr",
                       assignment_ids=[acc["assignment_id"]], condition="first_terminal")
    assert ct["status"] == "registered"
    at.f.fail = {"copilot-premium/m1", "copilot-premium/m2"}
    at.call(ag, run_id=acc["run_id"])
    assert at.n("agent_result_outbox") == 0
    assert at.c_.get_assignment(assignment_id=acc["assignment_id"], owner_user_id=ANDEN)["status"] == "active"
    assert at.n("agent_wait_contracts", "status='registered'") == 1
    assert ifr._mutate(lambda r: dict(r)) == {}                      # ingen vaegge-intention
    # ... og naar assignmentet SIDEN afgoeres, er der praecis ÉN terminalbesked med alle forsoeg
    out = at.c_.commit_terminal_outcome(assignment_id=acc["assignment_id"], status="completed", summary="fundet")
    assert out["committed"] is True
    assert at.n("agent_result_outbox") == 1
    payload = json.loads(out["message"]["payload_json"])
    runs = at.runs(acc["assignment_id"])
    assert payload["attempt_run_ids"] == [r["run_id"] for r in runs] and payload["last_run_id"] == runs[2]["run_id"]
    again = at.c_.commit_terminal_outcome(assignment_id=acc["assignment_id"], status="failed")
    assert again["committed"] is False and at.n("agent_result_outbox") == 1
    assert at.n("agent_wait_contracts", "status='fired'") == 1       # foerst nu, ved det ene terminalcommit


def test_the_failed_attempt_gets_a_non_terminal_artifact_in_the_manifest(at):
    ag, acc = at.agent()
    at.f.fail = {"copilot-premium/m1"}
    at.call(ag, run_id=acc["run_id"])
    from core.runtime import db_agent_artifacts as art
    rec = art.get_artifact_record(run_id=acc["run_id"], name="result.json")
    body = json.loads(open(rec["path"]).read())
    assert (body["status"], body["terminal"], body["error_code"], body["successor_run_id"] != "") == (
        "failed_attempt", False, "MODEL_FAILOVER", True)


# --- lease og fencing ---------------------------------------------------------------------------

def _scope(at, acc, **over):
    sc = {"assignment_id": acc["assignment_id"], "holder": "w1", "token": 1,
          "lost": threading.Event(), "stop": threading.Event()}
    sc.update(over)
    return sc


def _snapshot(at, acc):
    return (len(at.runs(acc["assignment_id"])), at.n("agent_route_decisions"),
            tuple(at.c_._conn().execute("SELECT provider, model FROM agent_registry WHERE agent_id='a1'").fetchone()),
            at.runs(acc["assignment_id"])[0]["status"])


@pytest.mark.parametrize("case", ["lost_flag", "token_overtaken", "lease_expired", "lease_released"])
def test_a_worker_without_a_current_lease_cannot_start_a_failover_attempt(at, case):
    ag, acc = at.agent()
    tok = at.L_.acquire(assignment_id=acc["assignment_id"], holder="w1")
    sc = _scope(at, acc, token=tok)
    if case == "lost_flag":
        sc["lost"].set()
    elif case == "token_overtaken":
        cn = at.L_._conn()                   # ÉN forbindelse: connect() ruller en aaben transaktion tilbage
        cn.execute("UPDATE agent_leases SET fencing_token=fencing_token+1 WHERE assignment_id=?",
                   (acc["assignment_id"],))
        cn.commit()
    elif case == "lease_expired":
        cn = at.L_._conn()
        cn.execute("UPDATE agent_leases SET lease_until=? WHERE assignment_id=?",
                   ("2000-01-01T00:00:00Z", acc["assignment_id"]))
        cn.commit()
    else:
        at.L_.release(assignment_id=acc["assignment_id"], holder="w1", token=tok)
    at.f.fail = {"copilot-premium/m1"}
    before = _snapshot(at, acc)
    tk = at.L_._scope.set(sc)
    try:
        with pytest.raises(at.c_.ContractError) as e:
            at.call(ag, run_id=acc["run_id"])
    finally:
        at.L_._scope.reset(tk)
    assert e.value.code == "LEASE_LOST"
    assert _snapshot(at, acc) == before                              # intet nyt run, intet nyt forsoeg, intet skift
    assert [c["model"] for c in at.f.calls] == ["m1"]               # modellen m2 blev aldrig kaldt


def test_a_worker_with_the_current_lease_may_fail_over(at):
    ag, acc = at.agent()
    tok = at.L_.acquire(assignment_id=acc["assignment_id"], holder="w1")
    at.f.fail = {"copilot-premium/m1"}
    tk = at.L_._scope.set(_scope(at, acc, token=tok))
    try:
        assert at.call(ag, run_id=acc["run_id"])["model"] == "m2"
    finally:
        at.L_._scope.reset(tk)
    assert len(at.runs(acc["assignment_id"])) == 2


@pytest.mark.parametrize("terminal", ["completed", "failed", "cancelled", "timed_out"])
def test_a_finished_assignment_cannot_be_failed_over(at, terminal):
    ag, acc = at.agent()
    at.c_.commit_terminal_outcome(assignment_id=acc["assignment_id"], status=terminal)
    with pytest.raises(at.c_.ContractError) as e:
        at.A_.begin_failover_attempt(from_run_id=acc["run_id"], reason="x",
                                     decision={"route_source": "agent_pool", "provider": "p", "model": "m"})
    assert e.value.code == "INVALID_TRANSITION"
    assert len(at.runs(acc["assignment_id"])) == 1


def test_two_workers_failing_over_the_same_run_create_exactly_one_successor(at):
    ag, acc = at.agent()
    decision = {"route_source": "agent_pool", "provider": "copilot-premium", "model": "m2"}
    barrier, results, errors = threading.Barrier(2), [], []

    def go():
        try:
            barrier.wait(timeout=5)
            results.append(at.A_.begin_failover_attempt(from_run_id=acc["run_id"], decision=decision, reason="r"))
        except BaseException as exc:                                  # traadens undtagelse er et testresultat
            errors.append(exc)

    ts = [threading.Thread(target=go) for _ in range(2)]
    [t.start() for t in ts]
    [t.join(timeout=10) for t in ts]
    assert len(results) == 1 and len(errors) == 1
    assert isinstance(errors[0], at.c_.ContractError) and errors[0].code == "INVALID_TRANSITION"
    assert len(at.runs(acc["assignment_id"])) == 2
    assert at.n("agent_route_decisions") == 2


def test_an_unknown_or_unbound_run_is_refused(at):
    ag, acc = at.agent()
    with pytest.raises(at.c_.ContractError) as e:
        at.A_.begin_failover_attempt(from_run_id="run-findes-ikke", reason="x",
                                     decision={"route_source": "agent_pool", "provider": "p", "model": "m"})
    assert e.value.code == "INVALID_SCOPE"


def test_live_run_id_leaves_other_failed_runs_alone(at):
    ag, acc = at.agent()
    cn = at.c_._conn()
    cn.execute("UPDATE agent_runs SET status='failed', error_code='LEASE_EXPIRED' WHERE run_id=?", (acc["run_id"],))
    cn.commit()
    assert at.A_.live_run_id(acc["run_id"]) == acc["run_id"]          # kun et MODEL_FAILOVER-forsoeg afloeses
    assert at.A_.live_run_id("") == "" and at.A_.live_run_id("ukendt") == "ukendt"


def test_model_failovers_do_not_use_up_the_safe_retries_after_a_worker_loss(at):
    ag, acc = at.agent()
    at.f.fail = {"copilot-premium/m1"}
    at.call(ag, run_id=acc["run_id"])                                 # to forsoeg, det foerste er et modelskift
    at.L_.acquire(assignment_id=acc["assignment_id"], holder="w1", now=datetime(2026, 10, 7, tzinfo=UTC))
    done = at.L_.reconcile_expired_leases(now=datetime(2026, 10, 7, tzinfo=UTC) + timedelta(seconds=200))
    assert [(d["action"], d["attempt"]) for d in done] == [("retry", 2)]   # ikke «failed (forsoeg opbrugt)»


def test_a_legacy_agent_is_never_given_failover_runs(at):
    from core.runtime.db_agent_runtime import create_agent_registry_entry, create_agent_run
    create_agent_registry_entry(agent_id="leg", role="r", goal="g", provider="copilot-premium", model="m1")
    create_agent_run(run_id="run-leg", agent_id="leg", status="starting")
    at.f.fail = {"copilot-premium/m1"}
    with pytest.raises(at.M_.ModelCallFailed):
        at.call({"agent_id": "leg", "tool_policy": "", "provider": "copilot-premium", "model": "m1"},
                run_id="run-leg")
    assert at.n("agent_runs", "agent_id='leg'") == 1 and at.n("agent_route_decisions") == 0


# --- hele vejen: dispatch -> execute_agent_task -> failover -> ét terminalt udfald ---------------------

@pytest.fixture
def e2e(at, monkeypatch):
    import core.services.agent_contract_service as svc
    import core.services.agent_runtime as ar
    from core.services import agent_model_policy as pol

    monkeypatch.setattr(svc, "_run_in_background", lambda fn: None)
    monkeypatch.setattr(pol, "_agent_candidates",
                        lambda *, role, min_tokens, exclude, allow_paid:
                        ([("copilot-premium", "m1"), ("copilot-premium", "m2")] if allow_paid else [])
                        + [("kilo", "m3")])
    monkeypatch.setattr(pol, "_evaluate", lambda p, m, *, owner, role, needs_tools: ("", False))
    monkeypatch.setattr(pol, "_cost_class", lambda p: "paid" if p == "copilot-premium" else "free")
    svc.set_capability(True, role="owner")
    monkeypatch.setattr(ar, "execute_with_role_or_fallback", at.f.execute_with_role_or_fallback)
    return svc


def _dispatch_and_run(at, svc):
    from core.services.agent_runtime_spawn import execute_agent_task
    out = svc.dispatch_agent(owner_user_id=ANDEN, origin_session_id="s1", goal="find X", parent_run_id="pr")
    assert out["status"] == "accepted", out
    execute_agent_task(agent_id=out["agent_id"])
    return out


def test_end_to_end_the_completed_status_lands_on_the_last_attempt_and_one_message_is_sent(at, e2e):
    at.f.fail = {"copilot-premium/m1"}
    out = _dispatch_and_run(at, e2e)
    runs = at.runs(out["assignment_id"])
    assert [(r["attempt_no"], r["status"], r["model"]) for r in runs] == [
        (1, "failed", "m1"), (2, "completed", "m2")]
    assert runs[1]["model"] == "m2" and runs[1]["output_summary"] != ""
    a = at.c_.get_assignment(assignment_id=out["assignment_id"], owner_user_id=ANDEN)
    assert a["status"] == "completed"
    assert at.n("agent_result_outbox", "assignment_id=?", (out["assignment_id"],)) == 1
    payload = json.loads(at.c_._conn().execute("SELECT payload_json FROM agent_result_outbox").fetchone()[0])
    assert payload["attempt_run_ids"] == [r["run_id"] for r in runs] and payload["last_run_id"] == runs[1]["run_id"]


def test_end_to_end_a_chain_where_every_model_fails_ends_with_one_failed_terminal_message(at, e2e):
    at.f.fail = {"copilot-premium/m1", "copilot-premium/m2", "kilo/m3"}
    out = _dispatch_and_run(at, e2e)
    runs = at.runs(out["assignment_id"])
    assert [r["status"] for r in runs] == ["failed", "failed", "failed"]
    assert [r["error_code"] for r in runs[:2]] == ["MODEL_FAILOVER", "MODEL_FAILOVER"]
    assert at.c_.get_assignment(assignment_id=out["assignment_id"], owner_user_id=ANDEN)["status"] == "failed"
    assert at.n("agent_result_outbox") == 1


# --- loekke-I/O og worker-broker foelger det nye forsoeg -------------------------------------------------

def test_the_in_process_loop_io_follows_the_failover_so_tool_records_land_on_the_live_run(at, monkeypatch):
    import core.services.agent_runtime_base as base
    monkeypatch.setattr(base, "_facade", lambda: at.f)
    ag, acc = at.agent()
    at.f.fail = {"copilot-premium/m1"}
    io = base._InProcessLoopIO(agent=ag, run_id=acc["run_id"])
    io.model(messages=[], tools=[], requires_tools=True, provider="copilot-premium", model="m1")
    live = at.runs(acc["assignment_id"])[1]["run_id"]
    assert io.run_id == live != acc["run_id"]


def test_the_in_process_loop_io_rebinds_even_when_the_whole_chain_fails(at, monkeypatch):
    import core.services.agent_runtime_base as base
    monkeypatch.setattr(base, "_facade", lambda: at.f)
    ag, acc = at.agent()
    at.f.fail = {"copilot-premium/m1", "copilot-premium/m2", "kilo/m3"}
    io = base._InProcessLoopIO(agent=ag, run_id=acc["run_id"])
    with pytest.raises(Exception) as e:
        io.model(messages=[], tools=[], requires_tools=True, provider="copilot-premium", model="m1")
    assert getattr(e.value, "code", "") == "MODEL_UNAVAILABLE"
    assert io.run_id == at.runs(acc["assignment_id"])[2]["run_id"]


def test_the_worker_broker_follows_the_failover_for_model_and_text_calls(at, monkeypatch):
    import core.services.agent_runtime_base as base
    from core.services.agent_worker_runner import _Broker
    monkeypatch.setattr(base, "_facade", lambda: at.f)
    ag, acc = at.agent()
    at.f.fail = {"copilot-premium/m1"}
    br = _Broker(agent=ag, run_id=acc["run_id"], prompt="p", tools_payload=[], provider="copilot-premium",
                 model="m1", max_tool_calls=3)
    br.handle({"op": "model_text", "requires_tools": False})
    live = at.runs(acc["assignment_id"])[1]["run_id"]
    assert br.run_id == br._io.run_id == live
