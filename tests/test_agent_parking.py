"""F4b: gate -> parkering ved en approval -> beslutning -> genoptagelse praecis dér (in-process)."""
from __future__ import annotations

import json
import threading
from datetime import UTC, datetime, timedelta

import pytest

O, S = "bjorn", "sess-1"


def call(i, name="bash", **args):
    return {"id": f"c{i}", "function": {"name": name, "arguments": json.dumps(args or {"command": f"echo {i}"})}}


@pytest.fixture
def pk(isolated_runtime, monkeypatch):
    import core.runtime.db_agent_approvals as appr
    import core.runtime.db_agent_contract as c
    import core.services.agent_contract_service as svc
    import core.services.agent_runtime_base as base
    from core.services import agent_runtime_spawn as M
    from core.services import in_flight_runs as ifr

    ifr._mutate(lambda r: r.clear())
    svc.set_capability(True, role="owner")
    monkeypatch.setattr("core.identity.owner_resolver.owner_user_id", lambda: "platform-ejer")
    started, replies, executed, model_calls = [], [], [], []
    monkeypatch.setattr(svc, "_run_in_background", lambda fn: started.append(fn))

    class _F:
        def execute_with_role_or_fallback(self, **kw):
            model_calls.append([dict(m) for m in kw.get("messages") or []])
            r = replies.pop(0)
            return r | {"input_tokens": 3, "output_tokens": 2}

    def fake_tool(tc, agent_id):
        executed.append((tc["id"], json.loads(tc["function"]["arguments"])))
        return f"UDFOERT {tc['id']}"

    monkeypatch.setattr(base, "_facade", lambda: _F())
    monkeypatch.setattr(M, "_facade", lambda: _F())
    monkeypatch.setattr(M, "agent_tools_enabled", lambda: True)
    monkeypatch.setattr(base, "agent_tools_enabled", lambda: True)
    monkeypatch.setattr(base, "_execute_agent_tool_call", fake_tool)

    class H:
        appr_, c_, svc_, M_ = appr, c, svc, M
        started_, replies_, executed_, calls_ = started, replies, executed, model_calls

        def dispatch(self, **kw):
            out = svc.dispatch_agent(owner_user_id=O, origin_session_id=S, goal="goer noget", parent_run_id="pr",
                                     allowed_tools=["bash", "read_file"], **kw)
            assert out["status"] == "accepted", out
            return out

        def go(self):
            fns, self.started_[:] = list(self.started_), []
            for f in fns:
                f()

        def assignment(self, out):
            return c.get_assignment(assignment_id=out["assignment_id"], owner_user_id=O)["status"]

        def pending(self):
            return appr.list_for_owner(owner_user_id=O, status="pending")

        def human(self, ap, decision="approve", who=O):
            return svc.decide_approval(approval_id=ap["approval_id"], decision=decision, actor_user_id=who,
                                       actor_kind="human", digest=ap["args_digest"])

        def runs(self):
            return [(r["attempt_no"], r["status"]) for r in c._conn().execute(
                "SELECT attempt_no, status FROM agent_runs ORDER BY attempt_no").fetchall()]

    yield H()
    ifr._mutate(lambda r: r.clear())


def test_an_approval_requiring_call_parks_the_child_before_it_runs(pk):
    pk.replies_ += [{"text": "", "tool_calls": [call(1)]}]
    out = pk.dispatch()
    pk.go()
    assert pk.executed_ == []                                              # IKKE udfoert
    assert pk.assignment(out) == "waiting"
    (ap,) = pk.pending()
    assert (ap["tool_name"], ap["agent_id"], ap["assignment_id"], ap["origin_session_id"], ap["run_id"]) == (
        "bash", out["agent_id"], out["assignment_id"], S, out["run_id"])
    from core.runtime.db_agent_runtime import get_agent_registry_entry
    assert get_agent_registry_entry(out["agent_id"])["status"] == "waiting_for_approval"
    assert pk.runs() == [(1, "waiting_for_approval")]
    cp = pk.appr_.parked_checkpoint(assignment_id=out["assignment_id"])
    assert cp["approval_id"] == ap["approval_id"] and cp["run_id"] == out["run_id"]
    assert pk.c_.list_pending_results(owner_user_id=O, origin_session_id=S) == []        # intet terminalt udfald
    assert pk.c_._conn().execute("SELECT state FROM agent_leases").fetchone()["state"] == "released"   # ingen worker holdes


def test_approving_resumes_the_child_exactly_where_it_stopped_and_runs_the_call_once(pk):
    pk.replies_ += [{"text": "", "tool_calls": [call(1)]}, {"text": "faerdig efter bash"}]
    out = pk.dispatch()
    pk.go()
    (ap,) = pk.pending()
    res = pk.human(ap)
    assert res["status"] == "ok" and res["approval"]["status"] == "approved"
    # `active`, ikke `queued`: genoptagelsen gaar gennem `_start_execution`, som
    # CLAIMER en workerplads foer den starter (§12.3 — et parkeret run har
    # frigivet sin plads og skal vinde en ny). Samme linje bekraefter selv at
    # den er startet én gang, saa `active` beskriver tilstanden aerligere end
    # den gamle `queued` gjorde.
    assert pk.assignment(out) == "active" and len(pk.started_) == 1
    pk.go()
    assert pk.executed_ == [("c1", {"command": "echo 1"})]                      # praecis én gang
    assert pk.assignment(out) == "completed"
    assert pk.runs() == [(1, "resumed"), (2, "completed")]
    (m,) = pk.c_.list_pending_results(owner_user_id=O, origin_session_id=S)
    payload = json.loads(m["payload_json"])
    assert payload["status"] == "completed" and "faerdig efter bash" in payload["summary"]
    assert len(payload["attempt_run_ids"]) == 2
    second = pk.calls_[1]                                                          # modellen ser resultatet
    assert [m["role"] for m in second] == ["user", "assistant", "tool"] and second[2]["content"] == "UDFOERT c1"
    assert pk.appr_.get(approval_id=ap["approval_id"])["status"] == "consumed"


def test_denying_resumes_the_child_with_an_explicit_denial_and_the_call_never_runs(pk):
    pk.replies_ += [{"text": "", "tool_calls": [call(1)]}, {"text": "kunne ikke goere det"}]
    out = pk.dispatch()
    pk.go()
    (ap,) = pk.pending()
    pk.human(ap, "deny")
    pk.go()
    assert pk.executed_ == [] and pk.assignment(out) == "completed"
    denial = json.loads(pk.calls_[1][2]["content"])
    assert (denial["status"], denial["code"], denial["approval_id"]) == ("denied", "APPROVAL_DENIED", ap["approval_id"])
    assert "Proev ikke samme handling igen" in denial["error"]


def test_an_expired_approval_resumes_the_child_with_a_timeout_denial(pk):
    pk.replies_ += [{"text": "", "tool_calls": [call(1)]}, {"text": "opgav"}]
    out = pk.dispatch()
    pk.go()
    (ap,) = pk.pending()
    c = pk.c_._conn()
    c.execute("UPDATE agent_approvals SET expires_at='2000-01-01T00:00:00Z' WHERE approval_id=?", (ap["approval_id"],))
    c.commit()
    done = pk.svc_.supervise()
    assert [d["approval_status"] for d in done if d.get("action") == "resumed_after_approval"] == ["expired"]
    pk.go()
    assert pk.executed_ == [] and pk.assignment(out) == "completed"
    assert "udloeb" in json.loads(pk.calls_[1][2]["content"])["error"]


def test_a_decision_made_before_a_restart_still_resumes_via_the_supervisor(pk):
    pk.replies_ += [{"text": "", "tool_calls": [call(1)]}, {"text": "ok"}]
    out = pk.dispatch()
    pk.go()
    (ap,) = pk.pending()
    pk.appr_.decide(approval_id=ap["approval_id"], decision="approve", actor_user_id=O, actor_kind="human",
                    digest=ap["args_digest"])                      # besluttet, men ingen resume-trigger blev kaldt
    assert pk.assignment(out) == "waiting" and pk.started_ == []
    done = pk.svc_.supervise()                                     # "efter genstart"
    assert any(d.get("action") == "resumed_after_approval" for d in done)
    pk.go()
    assert pk.assignment(out) == "completed" and pk.executed_ == [("c1", {"command": "echo 1"})]


def test_two_concurrent_resumers_start_the_child_once(pk):
    from core.services.agent_parking import resume_decided

    pk.replies_ += [{"text": "", "tool_calls": [call(1)]}]
    pk.dispatch()
    pk.go()
    (ap,) = pk.pending()
    pk.appr_.decide(approval_id=ap["approval_id"], decision="approve", actor_user_id=O, actor_kind="human",
                    digest=ap["args_digest"])
    starts = []
    lock = threading.Lock()

    def start(agent_id):
        with lock:
            starts.append(agent_id)

    ts = [threading.Thread(target=lambda: resume_decided(start)) for _ in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert len(starts) == 1


def test_a_parked_agent_cannot_be_run_before_the_approval_is_decided(pk):
    pk.replies_ += [{"text": "", "tool_calls": [call(1)]}]
    out = pk.dispatch()
    pk.go()
    with pytest.raises(RuntimeError, match="venter paa approval"):
        pk.M_.execute_agent_task(agent_id=out["agent_id"])
    assert pk.executed_ == [] and pk.assignment(out) == "waiting"


def test_calls_after_the_gated_one_run_after_the_resume_in_order(pk):
    pk.replies_ += [{"text": "", "tool_calls": [call(1, "read_file", path="a"), call(2), call(3, "read_file", path="b")]},
                    {"text": "slut"}]
    out = pk.dispatch()
    pk.go()
    assert [e[0] for e in pk.executed_] == ["c1"]                          # read_file kørte, bash parkerede
    (ap,) = pk.pending()
    assert ap["tool_name"] == "bash"
    pk.human(ap)
    pk.go()
    assert [e[0] for e in pk.executed_] == ["c1", "c2", "c3"] and pk.assignment(out) == "completed"
    tools = [m for m in pk.calls_[1] if m["role"] == "tool"]
    assert [m["tool_call_id"] for m in tools] == ["c1", "c2", "c3"]


def test_tools_that_need_no_approval_run_immediately_for_a_bound_agent(pk):
    pk.replies_ += [{"text": "", "tool_calls": [call(1, "read_file", path="a")]}, {"text": "laest"}]
    out = pk.dispatch()
    pk.go()
    assert pk.executed_ == [("c1", {"path": "a"})] and pk.assignment(out) == "completed" and pk.pending() == []


def test_an_unbound_legacy_agent_is_unchanged_and_runs_the_gated_tool_as_before(pk):
    from core.services.agent_runtime_spawn import execute_agent_task, spawn_agent_task

    pk.replies_ += [{"text": "", "tool_calls": [call(1)]}, {"text": "faerdig"}]
    a = spawn_agent_task(role="researcher", goal="g", auto_execute=False, context={}, tool_policy="",
                         allowed_tools=["bash"])
    execute_agent_task(agent_id=a["agent_id"])
    assert pk.executed_ == [("c1", {"command": "echo 1"})] and pk.pending() == []


def test_the_same_denied_action_is_not_retried_but_a_different_one_gets_its_own_approval(pk):
    pk.replies_ += [{"text": "", "tool_calls": [call(1)]},
                    {"text": "", "tool_calls": [call(2, command="echo 1")]},   # prover SAMME handling igen
                    {"text": "", "tool_calls": [call(3, command="echo andet")]},   # en ANDEN handling
                    ]
    out = pk.dispatch()
    pk.go()
    (ap,) = pk.pending()
    pk.human(ap, "deny")
    pk.go()
    assert pk.executed_ == []
    denial2 = json.loads([m for m in pk.calls_[2] if m["role"] == "tool"][-1]["content"])
    assert denial2["code"] == "APPROVAL_DENIED" and "allerede afvist" in denial2["error"]
    (second,) = pk.pending()
    assert second["safe_view"].count("echo andet") == 1 and second["approval_id"] != ap["approval_id"]
    assert pk.assignment(out) == "waiting"                                    # parkerer igen, nu for den nye handling


def test_cancelling_a_parked_agent_cancels_its_approvals_and_never_resumes_it(pk):
    pk.replies_ += [{"text": "", "tool_calls": [call(1)]}]
    out = pk.dispatch()
    pk.go()
    (ap,) = pk.pending()
    res = pk.svc_.interrupt_agent(owner_user_id=O, origin_session_id=S, agent_id=out["agent_id"])
    assert res["status"] == "stop_requested" and pk.assignment(out) == "cancelled"
    assert pk.appr_.get(approval_id=ap["approval_id"])["status"] == "cancelled"
    assert pk.appr_.parked_checkpoint(assignment_id=out["assignment_id"]) is None
    assert pk.svc_.supervise() == [] and pk.started_ == [] and pk.executed_ == []


def test_a_finished_assignment_discards_a_stale_checkpoint_instead_of_resuming(pk):
    from core.services.agent_parking import resume_decided

    pk.replies_ += [{"text": "", "tool_calls": [call(1)]}]
    out = pk.dispatch()
    pk.go()
    (ap,) = pk.pending()
    pk.appr_.decide(approval_id=ap["approval_id"], decision="approve", actor_user_id=O, actor_kind="human",
                    digest=ap["args_digest"])
    pk.c_.commit_terminal_outcome(assignment_id=out["assignment_id"], status="failed")
    starts = []
    assert resume_decided(starts.append) == [] and starts == []


def test_a_forged_decision_from_jarvis_or_a_model_resumes_nothing(pk):
    pk.replies_ += [{"text": "", "tool_calls": [call(1)]}]
    out = pk.dispatch()
    pk.go()
    (ap,) = pk.pending()
    for kind in ("agent", "model", "jarvis"):
        res = pk.svc_.decide_approval(approval_id=ap["approval_id"], decision="approve", actor_user_id=O,
                                      actor_kind=kind, digest=ap["args_digest"])
        assert (res["status"], res["code"]) == ("error", "POLICY_DENIED")
    assert pk.assignment(out) == "waiting" and pk.started_ == [] and pk.executed_ == []


def test_a_stale_digest_decision_is_refused_and_the_child_stays_parked(pk):
    pk.replies_ += [{"text": "", "tool_calls": [call(1)]}]
    out = pk.dispatch()
    pk.go()
    (ap,) = pk.pending()
    res = pk.svc_.decide_approval(approval_id=ap["approval_id"], decision="approve", actor_user_id=O,
                                  actor_kind="human", digest="0" * 64)
    assert (res["status"], res["code"]) == ("error", "INVALID_SCOPE")
    assert pk.assignment(out) == "waiting" and pk.executed_ == []


def test_tokens_before_the_park_are_kept_on_the_parked_run(pk):
    pk.replies_ += [{"text": "", "tool_calls": [call(1)]}]
    out = pk.dispatch()
    pk.go()
    r = pk.c_._conn().execute("SELECT input_tokens, output_tokens FROM agent_runs").fetchone()
    assert (r["input_tokens"], r["output_tokens"]) == (3, 2)


def test_list_and_decide_work_even_when_the_engine_is_switched_off(pk):
    pk.replies_ += [{"text": "", "tool_calls": [call(1)]}, {"text": "ok"}]
    out = pk.dispatch()
    pk.go()
    pk.svc_.set_capability(False)
    (view,) = pk.svc_.list_approvals(owner_user_id=O, status="pending")["approvals"]
    assert "arguments_json" not in view and view["safe_view"].startswith("bash(")
    assert pk.svc_.decide_approval(approval_id=view["approval_id"], decision="approve", actor_user_id=O,
                                   actor_kind="human", digest=view["args_digest"])["status"] == "ok"
    pk.go()
    assert pk.assignment(out) == "completed"


# --- gennem den sandboxede worker ---------------------------------------------------------------------------

from core.services import agent_sandbox as _sb

_USABLE, _WHY = _sb.sandbox_usable()


@pytest.mark.skipif(not _USABLE, reason=f"bwrap kan ikke bruges her: {_WHY}")
def test_a_worker_parks_at_the_approval_and_a_second_worker_resumes_it(pk, monkeypatch):
    import os

    from core.services import agent_worker_runner as R

    monkeypatch.setattr(R, "_sandbox_ok", (True, ""))
    R.set_worker_mode(True, role="owner")
    pids = []
    real = R.run_agent_in_worker

    def spy(**kw):
        out = real(**kw)
        pids.append(out.get("worker_pid"))
        return out

    monkeypatch.setattr(R, "run_agent_in_worker", spy)
    pk.replies_ += [{"text": "", "tool_calls": [call(1)]}, {"text": "faerdig via worker"}]
    out = pk.dispatch()
    pk.go()
    assert pk.executed_ == [] and pk.assignment(out) == "waiting" and len(pids) == 1
    (ap,) = pk.pending()
    assert pk.appr_.parked_checkpoint(assignment_id=out["assignment_id"]) is not None
    pk.human(ap)
    pk.go()
    assert pk.executed_ == [("c1", {"command": "echo 1"})] and pk.assignment(out) == "completed"
    assert len(pids) == 2 and pids[0] != pids[1] and os.getpid() not in pids          # to forskellige workers
    assert pk.runs() == [(1, "resumed"), (2, "completed")]
    assert pk.calls_[1][2]["content"] == "UDFOERT c1"


@pytest.mark.skipif(not _USABLE, reason=f"bwrap kan ikke bruges her: {_WHY}")
def test_a_worker_cannot_run_a_gated_tool_by_forging_its_own_tool_call_without_the_gate(pk, monkeypatch):
    """Selv en ondsindet worker der kalder bash direkte gennem brokeren rammer gaten (brokeren ER gaten)."""
    import sys

    from core.services import agent_worker_runner as R

    monkeypatch.setattr(R, "_sandbox_ok", (True, ""))
    evil = [sys.executable, "-c", (
        "import os, socket, sys\nsys.path.insert(0, '/worker')\n"
        "from agent_worker_protocol import FrameReader, send\n"
        "s = socket.socket(fileno={fd}); r = FrameReader(s)\n"
        "send(s, {'op': 'hello', 'pid': os.getpid()}); r.read(30)\n"
        "send(s, {'id': 1, 'op': 'tool', 'tc': {'id': 'x1', 'function': {'name': 'bash', 'arguments': '{\"command\": \"rm -rf x\"}'}}})\n"
        "rep = r.read(30)\n"
        "send(s, {'op': 'error', 'error': 'svar: ' + str(rep)})\n")]
    out = pk.dispatch()
    from core.runtime.db_agent_runtime import get_agent_registry_entry
    with pytest.raises(R.WorkerError) as e:
        R.run_agent_in_worker(agent=get_agent_registry_entry(out["agent_id"]), prompt="P", requires_tools=False,
                              run_id=out["run_id"], tools_payload=pk.M_._snapshot_tools(
                                  get_agent_registry_entry(out["agent_id"])), worker_command=evil)
    assert "APPROVAL_PENDING" in e.value.detail and pk.executed_ == []
    assert len(pk.pending()) == 1


def test_a_supervisor_tick_during_a_resume_in_progress_neither_restarts_nor_discards_the_checkpoint(pk):
    """Beslutningen er truffet og barnet har vundet sin workerplads, men traaden
    har ikke taget checkpointen endnu."""
    pk.replies_ += [{"text": "", "tool_calls": [call(1)]}, {"text": "faerdig"}]
    out = pk.dispatch()
    pk.go()
    (ap,) = pk.pending()
    pk.human(ap)
    # `active`, ikke `queued`: genoptagelsen gaar gennem `_start_execution`, som
    # CLAIMER en workerplads foer den starter (§12.3 — et parkeret run har
    # frigivet sin plads og skal vinde en ny). Samme linje bekraefter selv at
    # den er startet én gang, saa `active` beskriver tilstanden aerligere end
    # den gamle `queued` gjorde.
    assert pk.assignment(out) == "active" and len(pk.started_) == 1
    assert pk.svc_.supervise() == []                                   # intet nyt
    assert len(pk.started_) == 1                                        # ikke startet to gange
    assert pk.appr_.parked_checkpoint(assignment_id=out["assignment_id"]) is not None     # IKKE kasseret
    pk.go()                                                              # den ene start koerer: fortsaetter, ikke forfra
    assert pk.executed_ == [("c1", {"command": "echo 1"})] and pk.assignment(out) == "completed"
    assert len(pk.calls_) == 2                                           # kun to modelkald i alt


def test_a_discarded_checkpoint_is_really_marked_discarded_when_the_assignment_ended(pk):
    from core.services.agent_parking import resume_decided

    pk.replies_ += [{"text": "", "tool_calls": [call(1)]}]
    out = pk.dispatch()
    pk.go()
    (ap,) = pk.pending()
    pk.appr_.decide(approval_id=ap["approval_id"], decision="approve", actor_user_id=O, actor_kind="human",
                    digest=ap["args_digest"])
    c = pk.c_._conn()
    c.execute("UPDATE agent_assignments SET status='cancelled' WHERE assignment_id=?", (out["assignment_id"],))
    c.commit()
    assert resume_decided(lambda a: pytest.fail("maa ikke starte")) == []
    row = pk.c_._conn().execute("SELECT status FROM agent_checkpoints").fetchone()
    assert row["status"] == "discarded"


def test_a_failing_resume_never_falls_back_to_a_fresh_text_turn(pk, monkeypatch):
    pk.replies_ += [{"text": "", "tool_calls": [call(1)]}]
    out = pk.dispatch()
    pk.go()
    (ap,) = pk.pending()
    pk.human(ap)
    n_before = len(pk.calls_)

    def boom(**kw):
        raise RuntimeError("loekken braekkede")

    from core.services import agent_worker_runner
    monkeypatch.setattr(agent_worker_runner, "run_agent_in_worker", boom)
    pk.go()
    assert len(pk.calls_) == n_before and pk.assignment(out) == "failed"       # ingen frisk tekst-tur
    assert pk.executed_ == []


def test_the_resume_claim_is_a_real_compare_and_swap_with_a_forced_window(pk, monkeypatch):
    import time

    from core.services import agent_parking as P

    pk.replies_ += [{"text": "", "tool_calls": [call(1)]}]
    pk.dispatch()
    pk.go()
    (ap,) = pk.pending()
    pk.appr_.decide(approval_id=ap["approval_id"], decision="approve", actor_user_id=O, actor_kind="human",
                    digest=ap["args_digest"])
    real = P.set_assignment_status
    monkeypatch.setattr(P, "set_assignment_status",
                        lambda **kw: (time.sleep(0.2), real(**kw))[1])        # begge laeser 'waiting' foer nogen vinder
    starts, errors = [], []

    def go():
        try:
            P.resume_decided(starts.append)
        except Exception as exc:
            errors.append(type(exc).__name__)

    ts = [threading.Thread(target=go) for _ in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert errors == [] and len(starts) == 1
