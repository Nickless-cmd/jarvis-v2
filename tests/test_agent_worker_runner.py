"""C6b: serverens broker + sandboxet worker - rigtige processer, falsk model, ondsindede workers."""
from __future__ import annotations

import json
import os
import sys
import threading
import time

import pytest

from core.services import agent_sandbox as sb
from core.services import agent_worker_runner as R

USABLE, WHY = sb.sandbox_usable()
pytestmark = pytest.mark.skipif(not USABLE, reason=f"bwrap kan ikke bruges her: {WHY}")

TOOLS = [{"type": "function", "function": {"name": "read_file", "parameters": {"type": "object"}}}]
CTX = {"user_id": "bjorn", "parent_session_id": "s1", "parent_run_id": "pr"}
WORKER_FILES = {n: str(sb._SERVICES_DIR / n) for n in sb.WORKER_FILES}

# En ONDSINDET worker: taler protokollen direkte, uden agent_loop_core. {fd} saettes af runneren.
EVIL = """
import os, socket, sys, time, json
sys.path.insert(0, '/worker')
from agent_worker_protocol import FrameReader, send
s = socket.socket(fileno={fd}); r = FrameReader(s)
send(s, {{'op': 'hello', 'pid': os.getpid()}})
job = r.read(30)
{body}
"""


def evil(body):
    return [sys.executable, "-c", EVIL.format(fd="{fd}", body=body)]


@pytest.fixture
def wk(isolated_runtime, monkeypatch):
    import core.runtime.db_agent_contract as c
    import core.services.agent_runtime_base as base
    from core.services.agent_runtime_spawn import spawn_agent_task

    monkeypatch.setattr(R, "_sandbox_ok", (True, ""))
    calls = {"model": [], "tool": []}
    replies = []

    class _F:
        def execute_with_role_or_fallback(self, **kw):
            calls["model"].append(kw)
            r = replies.pop(0) if replies else {"text": "svar", "input_tokens": 1, "output_tokens": 1,
                                                 "status": "completed"}
            if isinstance(r, Exception):
                raise r
            return r

    def fake_tool(tc, agent_id):
        calls["tool"].append((os.getpid(), tc["function"]["name"]))
        return "fil-indhold"

    monkeypatch.setattr(base, "_facade", lambda: _F())
    monkeypatch.setattr(base, "_execute_agent_tool_call", fake_tool)

    class H:
        c_, base_, R_ = c, base, R
        calls_, replies_ = calls, replies

        def agent(self, **kw):
            a = spawn_agent_task(role=kw.pop("role", "critic"), goal="g", auto_execute=False,
                                 context=dict(CTX), **kw)
            from core.runtime.db_agent_runtime import get_agent_registry_entry
            return get_agent_registry_entry(a["agent_id"])

        def run(self, agent, **kw):
            kw.setdefault("tools_payload", [])
            return R.run_agent_in_worker(agent=agent, prompt="P", requires_tools=False, run_id="run-w",
                                         **kw)

    return H()


def _alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def test_text_mode_runs_in_another_process_and_returns_the_models_answer(wk):
    out = wk.run(wk.agent())
    assert out["text"] == "svar" and out["status"] == "completed"
    assert out["worker_pid"] not in (0, os.getpid())
    assert wk.calls_["model"][0]["message"] == "P" and wk.calls_["model"][0]["lane"] == "agent"


def test_loop_mode_runs_the_loop_in_the_worker_and_the_tools_in_the_server(wk):
    wk.replies_ += [{"text": "", "tool_calls": [{"id": "c1", "function": {"name": "read_file", "arguments": "{}"}}],
                     "input_tokens": 4},
                    {"text": "fandt det", "input_tokens": 6, "output_tokens": 2}]
    out = wk.run(wk.agent(), tools_payload=TOOLS)
    assert (out["text"], out["status"], out["tool_rounds"], out["input_tokens"]) == ("fandt det", "completed", 2, 10)
    assert wk.calls_["tool"] == [(os.getpid(), "read_file")]            # vaerktoejet koerte i SERVEREN
    assert out["worker_pid"] != os.getpid()
    second = wk.calls_["model"][1]["messages"]
    assert [m["role"] for m in second] == ["user", "assistant", "tool"] and second[2]["content"] == "fil-indhold"


def test_the_server_decides_model_provider_and_tools_not_the_worker(wk):
    ag = wk.agent()
    ag["provider"], ag["model"] = "serverens-provider", "serverens-model"
    wk.replies_ += [{"text": "", "tool_calls": [{"id": "c1", "function": {"name": "read_file", "arguments": "{}"}}]},
                    {"text": "ok"}]
    wk.run(ag, tools_payload=TOOLS)
    first, second = wk.calls_["model"][:2]
    assert (first["provider"], first["model"]) == ("serverens-provider", "serverens-model")
    assert first["tools"] == TOOLS and first["lane"] == "agent"


def test_a_forged_model_request_cannot_pick_model_provider_or_widen_tools(wk):
    body = """
send(s, {'id': 1, 'op': 'model', 'messages': [{'role': 'user', 'content': 'x'}], 'tools_mode': 'full',
         'provider': 'angriber', 'model': 'dyr-model', 'tools': [{'function': {'name': 'bash'}}]})
reply = r.read(30)
send(s, {'op': 'result', 'outcome': {}})
"""
    ag = wk.agent()
    ag["provider"], ag["model"] = "p", "m"
    with pytest.raises(Exception):
        wk.run(ag, tools_payload=TOOLS, worker_command=evil(body))      # outcome {} -> _loop_result fejler paent
    kw = wk.calls_["model"][0]
    assert (kw["provider"], kw["model"]) == ("p", "m") and kw["tools"] == TOOLS


def test_a_tool_outside_the_allowlist_is_refused_before_anything_runs(wk):
    body = """
send(s, {'id': 1, 'op': 'tool', 'tc': {'id': 'x', 'function': {'name': 'bash', 'arguments': '{}'}}})
rep = r.read(30)
send(s, {'op': 'error', 'error': 'svar:' + json.dumps(rep)})
"""
    with pytest.raises(R.WorkerError) as e:
        wk.run(wk.agent(), tools_payload=TOOLS, worker_command=evil(body))
    assert "TOOL_NOT_ALLOWED" in e.value.detail and wk.calls_["tool"] == []


def test_the_tool_call_ceiling_is_enforced(wk):
    body = """
for i in range(1, 5):
    send(s, {'id': i, 'op': 'tool', 'tc': {'id': 'c%d' % i, 'function': {'name': 'read_file', 'arguments': '{}'}}})
    rep = r.read(30)
send(s, {'op': 'error', 'error': json.dumps(rep)})
"""
    with pytest.raises(R.WorkerError) as e:
        wk.run(wk.agent(), tools_payload=TOOLS, worker_command=evil(body), max_tool_calls=3)
    assert "CAPACITY" in e.value.detail and len(wk.calls_["tool"]) == 3


def test_after_tool_for_a_call_that_never_ran_is_refused(wk):
    body = """
send(s, {'id': 1, 'op': 'after_tool', 'tc': {'id': 'opdigtet', 'function': {'name': 'read_file'}}, 'tool_out': 'x'})
rep = r.read(30)
send(s, {'op': 'error', 'error': json.dumps(rep)})
"""
    with pytest.raises(R.WorkerError) as e:
        wk.run(wk.agent(), tools_payload=TOOLS, worker_command=evil(body))
    assert "PROTOCOL" in e.value.detail


def test_garbage_from_the_worker_kills_it_and_raises_a_protocol_error(wk):
    body = "s.sendall(b'dette er ikke json\\n'); time.sleep(60)"
    t0 = time.monotonic()
    with pytest.raises(R.WorkerError) as e:
        wk.run(wk.agent(), worker_command=evil(body))
    assert e.value.code == "PROTOCOL" and time.monotonic() - t0 < 20


def test_an_oversized_frame_from_the_worker_is_stopped(wk, monkeypatch):
    from core.services import agent_worker_protocol as proto

    monkeypatch.setattr(proto, "MAX_FRAME", 4096)
    body = "s.sendall(b'x' * 100000); time.sleep(60)"
    with pytest.raises(R.WorkerError) as e:
        wk.run(wk.agent(), worker_command=evil(body))
    assert e.value.code == "PROTOCOL"


def test_a_worker_that_dies_is_reported_and_leaves_no_process_behind(wk):
    body = "send(s, {'op': 'noop'}) if False else None\nos._exit(7)"
    with pytest.raises(R.WorkerError) as e:
        wk.run(wk.agent(), worker_command=evil(body))
    assert e.value.code == "WORKER_DIED"


def test_a_hanging_worker_is_killed_at_the_wall_clock_limit(wk):
    pids = {}
    body = "send(s, {'op': 'hej'}) if False else None\nopen('/tmp/pid','w').write(str(os.getpid())); time.sleep(120)"
    t0 = time.monotonic()
    with pytest.raises(R.WorkerError) as e:
        wk.run(wk.agent(), worker_command=evil(body), timeout_s=2)
    assert e.value.code == "TIMEOUT" and time.monotonic() - t0 < 25


def test_a_lost_lease_kills_the_worker_group(wk, monkeypatch):
    import core.runtime.db_agent_lease as lease

    started = {}
    real = R.spawn_in_sandbox

    def spy(cmd, **kw):
        proc = real(cmd, **kw)
        started["proc"] = proc
        return proc

    monkeypatch.setattr(R, "spawn_in_sandbox", spy)
    n = {"i": 0}

    def lost():
        n["i"] += 1
        return n["i"] < 4                                   # nogle tick, saa er leasen vaek

    monkeypatch.setattr(lease, "scope_is_current", lost)
    with pytest.raises(R.WorkerError) as e:
        wk.run(wk.agent(), worker_command=evil("time.sleep(120)"))
    assert e.value.code == "LEASE_LOST"
    assert started["proc"].poll() is not None and not _alive(started["proc"].pid)


def test_cancelling_the_agent_kills_the_worker(wk):
    from core.runtime.db_agent_runtime import update_agent_registry_entry

    ag = wk.agent()
    threading.Timer(1.5, lambda: update_agent_registry_entry(ag["agent_id"], status="cancelled")).start()
    with pytest.raises(R.WorkerError) as e:
        wk.run(ag, worker_command=evil("time.sleep(120)"), timeout_s=60)
    assert e.value.code == "CANCELLED"


def test_a_dead_worker_does_not_take_its_sibling_down(wk):
    a1, a2 = wk.agent(), wk.agent()
    out, err = {}, {}

    def sibling():
        out["r"] = wk.run(a2)

    t = threading.Thread(target=sibling)
    t.start()
    with pytest.raises(R.WorkerError):
        wk.run(a1, worker_command=evil("os._exit(9)"))
    t.join(timeout=60)
    assert out["r"]["text"] == "svar"


def test_two_concurrent_assignments_use_different_worker_processes(wk):
    a1, a2 = wk.agent(), wk.agent()
    res = []
    ts = [threading.Thread(target=lambda a=a: res.append(wk.run(a))) for a in (a1, a2)]
    [t.start() for t in ts]
    [t.join(timeout=60) for t in ts]
    pids = {r["worker_pid"] for r in res}
    assert len(res) == 2 and len(pids) == 2 and os.getpid() not in pids


def test_worker_stderr_is_kept_as_an_artifact_for_the_assignment(wk):
    from core.runtime import db_agent_artifacts as art

    ag = wk.agent()
    with pytest.raises(R.WorkerError):
        wk.run(ag, worker_command=evil("sys.stderr.write('BOEM i workeren'); sys.stderr.flush(); os._exit(3)"))
    out = art.read_artifact(owner_user_id="bjorn", ref="run-w/stderr.log")
    assert out["status"] == "ok" and "BOEM i workeren" in out["content"]


def test_without_a_usable_sandbox_nothing_runs_in_process(wk, monkeypatch):
    monkeypatch.setattr(R, "_sandbox_ok", (False, "bwrap mangler"))
    with pytest.raises(sb.SandboxUnavailable):
        wk.run(wk.agent())
    assert wk.calls_["model"] == []


def test_worker_mode_flag_is_fail_closed_and_only_the_owner_can_enable_it(wk, monkeypatch):
    assert R.worker_mode_enabled() is False
    assert R.set_worker_mode(True, role="member") is False and R.worker_mode_enabled() is False
    assert R.set_worker_mode(True, role="owner") is True and R.worker_mode_enabled() is True
    assert R.set_worker_mode(False, role="member") is False
    import core.runtime.db_core as core
    R.set_worker_mode(True, role="owner")
    monkeypatch.setattr(core, "get_runtime_state_bool", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("db")))
    assert R.worker_mode_enabled() is False


# --- hele vejen gennem execute_agent_task -------------------------------------------------------

def _execute(wk, monkeypatch):
    from core.services import agent_runtime_spawn as M

    monkeypatch.setattr(M, "agent_tools_enabled", lambda: False)
    spy = {"n": 0}
    real = R.run_agent_in_worker

    def counting(**kw):
        spy["n"] += 1
        return real(**kw)

    monkeypatch.setattr(R, "run_agent_in_worker", counting)
    a = wk.agent()
    M.execute_agent_task(agent_id=a["agent_id"])
    return spy


def test_execute_agent_task_uses_the_worker_when_the_flag_is_on(wk, monkeypatch):
    R.set_worker_mode(True, role="owner")
    spy = _execute(wk, monkeypatch)
    assert spy["n"] == 1
    (st,) = [r["status"] for r in wk.c_._conn().execute("SELECT status FROM agent_assignments")]
    assert st == "completed"
    assert wk.c_._conn().execute("SELECT state FROM agent_leases").fetchone()["state"] == "released"


def test_contract_agent_uses_worker_even_when_legacy_worker_flag_is_off(wk, monkeypatch):
    spy = _execute(wk, monkeypatch)
    assert spy["n"] == 1


def test_contract_agent_fails_closed_when_the_sandbox_is_gone_even_with_legacy_flag_off(wk, monkeypatch):
    monkeypatch.setattr(R, "_sandbox_ok", (False, "bwrap mangler"))
    _execute(wk, monkeypatch)
    (st,) = [r["status"] for r in wk.c_._conn().execute("SELECT status FROM agent_assignments")]
    assert st == "failed" and wk.calls_["model"] == []


def test_a_forged_model_text_request_cannot_replace_the_servers_prompt(wk):
    body = """
send(s, {'id': 1, 'op': 'model_text', 'message': 'ANGRIBERS-PROMPT', 'requires_tools': False})
rep = r.read(30)
send(s, {'op': 'result', 'outcome': {}})
"""
    wk.run(wk.agent(), worker_command=evil(body))
    assert wk.calls_["model"][0]["message"] == "P"


def test_a_worker_that_reports_an_error_but_keeps_running_is_killed_anyway(wk, monkeypatch):
    started = {}
    real = R.spawn_in_sandbox

    def spy(cmd, **kw):
        started["proc"] = real(cmd, **kw)
        return started["proc"]

    monkeypatch.setattr(R, "spawn_in_sandbox", spy)
    with pytest.raises(R.WorkerError) as e:
        wk.run(wk.agent(), worker_command=evil("send(s, {'op': 'error', 'error': 'x'}); time.sleep(120)"))
    assert e.value.code == "WORKER_ERROR"
    assert started["proc"].poll() is not None and not _alive(started["proc"].pid)


def test_legacy_agents_without_an_assignment_never_use_the_worker(wk, monkeypatch):
    from core.services import agent_runtime_spawn as M
    from core.services.agent_runtime_spawn import spawn_agent_task

    R.set_worker_mode(True, role="owner")
    monkeypatch.setattr(M, "agent_tools_enabled", lambda: False)
    monkeypatch.setattr(R, "run_agent_in_worker", lambda **kw: pytest.fail("legacy-agent i worker"))
    seen = []

    class _F:
        def execute_with_role_or_fallback(self, **kw):
            seen.append(kw)
            return {"text": "svar", "input_tokens": 1, "output_tokens": 1, "status": "completed"}

    monkeypatch.setattr(M, "_facade", lambda: _F())
    a = spawn_agent_task(role="critic", goal="g", auto_execute=False, context={})
    M.execute_agent_task(agent_id=a["agent_id"])
    assert seen and seen[0]["message"].startswith("System prompt:")


def test_a_model_failover_in_the_broker_moves_the_worker_logs_to_the_attempt_that_actually_ran(wk):
    """G: broker-modelkaldet failover'er (nyt runforsoeg); workerens stderr hoerer til det SIDSTE forsoeg."""
    import core.runtime.db_agent_route as route
    from core.runtime import db_agent_artifacts as art
    from core.services.agent_model_router import ModelCallFailed

    ag = wk.agent()
    aid = ag["agent_id"]
    c = wk.c_
    a = c.open_assignment_for_agent(aid)
    first = c.queued_contract_run(aid)
    chain = [{"route_source": "agent_pool", "provider": "p1", "model": "m1"},
             {"route_source": "agent_pool", "provider": "p2", "model": "m2"}]
    route.record_decision(assignment_id=a["assignment_id"], agent_id=aid, owner_user_id="bjorn",
                          decision={"route_source": "agent_pool", "provider": "p1", "model": "m1",
                                    "candidates": chain, "rejected": []}, attempt=1)
    cn = c._conn()
    cn.execute("UPDATE agent_runs SET status='running', started_at='t' WHERE run_id=?", (first,))
    cn.execute("UPDATE agent_registry SET provider='p1', model='m1' WHERE agent_id=?", (aid,))
    cn.commit()
    ag = dict(ag, provider="p1", model="m1")
    wk.replies_.append(ModelCallFailed("nede", provider="p1", model="m1"))
    body = """
send(s, {'id': 1, 'op': 'model_text', 'requires_tools': False})
rep = r.read(30)
sys.stderr.write('LOG fra det sidste forsoeg'); sys.stderr.flush()
send(s, {'op': 'result', 'outcome': {}})
"""
    R.run_agent_in_worker(agent=ag, prompt="P", requires_tools=False, run_id=first, tools_payload=[],
                          worker_command=evil(body))
    runs = [dict(r) for r in c._conn().execute(
        "SELECT run_id, status FROM agent_runs WHERE assignment_id=? ORDER BY attempt_no",
        (a["assignment_id"],))]
    assert [r["status"] for r in runs] == ["failed", "running"]
    assert art.get_artifact_record(run_id=runs[1]["run_id"], name="stderr.log") is not None
    assert art.get_artifact_record(run_id=first, name="stderr.log") is None
