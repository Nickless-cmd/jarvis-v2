"""A2: spawn og registry-livscyklussen er koblet til agent-contract-v1 (rigtig sqlite)."""
from __future__ import annotations

import json

import pytest

CTX = {"user_id": "bjorn", "parent_session_id": "sess-1", "parent_run_id": "pr-1"}


@pytest.fixture
def env(isolated_runtime):
    import core.runtime.db_agent_contract as c
    import core.runtime.db_agent_runtime as rt
    from core.services.agent_runtime_spawn import spawn_agent_task

    def spawn(**kw):
        kw.setdefault("role", "researcher")
        kw.setdefault("goal", "find X")
        kw.setdefault("auto_execute", False)
        return spawn_agent_task(**kw)

    return c, rt, spawn


def _assignments(c):
    return [dict(r) for r in c._conn().execute("SELECT * FROM agent_assignments")]


def test_spawn_binds_owner_and_opens_assignment(env):
    c, rt, spawn = env
    agent = spawn(context=dict(CTX))
    row = rt.get_agent_registry_entry(agent["agent_id"])
    assert (row["owner_user_id"], row["owner_session_id"]) == ("bjorn", "sess-1")
    (a,) = _assignments(c)
    assert (a["agent_id"], a["owner_user_id"], a["origin_session_id"], a["parent_run_id"],
            a["status"], a["idempotency_key"]) == (
        agent["agent_id"], "bjorn", "sess-1", "pr-1", "queued", agent["agent_id"])
    assert c.queued_contract_run(agent["agent_id"]) != ""


def test_contract_tool_allowlist_does_not_depend_on_legacy_tools_flag(env, monkeypatch):
    c, rt, spawn = env
    from core.services import agent_runtime_spawn as M

    monkeypatch.setattr(M, "agent_tools_enabled", lambda: False)
    agent = spawn(context=dict(CTX), tool_policy="read-only", allowed_tools=["read_file"])
    row = rt.get_agent_registry_entry(agent["agent_id"])

    tools = M._snapshot_tools(row)
    assert {tool["function"]["name"] for tool in tools} == {"read_file"}


def test_contract_tool_scope_lookup_failure_cannot_silently_remove_tools(env, monkeypatch):
    _, rt, spawn = env
    from core.services import agent_runtime_spawn as M
    from core.runtime import db_agent_contract as contract

    agent = spawn(context=dict(CTX), tool_policy="read-only", allowed_tools=["read_file"])
    monkeypatch.setattr(contract, "open_assignment_for_agent",
                        lambda agent_id: (_ for _ in ()).throw(RuntimeError("DB unavailable")))

    with pytest.raises(RuntimeError, match="DB unavailable"):
        M._snapshot_tools(rt.get_agent_registry_entry(agent["agent_id"]))


def test_contract_tool_schema_failure_cannot_silently_remove_tools(env, monkeypatch):
    _, rt, spawn = env
    from core.services import agent_runtime_spawn as M
    from core.services import agent_runtime_base as base

    agent = spawn(context=dict(CTX), tool_policy="read-only", allowed_tools=["read_file"])
    monkeypatch.setattr(base, "_build_agent_tools_payload",
                        lambda allowed: (_ for _ in ()).throw(RuntimeError("schema unavailable")))

    with pytest.raises(RuntimeError, match="schema unavailable"):
        M._snapshot_tools(rt.get_agent_registry_entry(agent["agent_id"]))


def test_spawn_without_owner_or_session_stays_legacy_and_opens_nothing(env):
    c, rt, spawn = env
    for ctx in ({}, {"user_id": "bjorn"}, {"parent_session_id": "s"}):
        agent = spawn(context=dict(ctx))
        assert rt.get_agent_registry_entry(agent["agent_id"])["owner_user_id"] == \
            "legacy_unscoped"
    assert _assignments(c) == []


def test_persistent_agent_stays_legacy_while_the_engine_is_off(env):
    c, rt, spawn = env
    agent = spawn(context=dict(CTX), persistent=True, ttl_seconds=900)
    assert rt.get_agent_registry_entry(agent["agent_id"])["owner_user_id"] == "legacy_unscoped"
    assert _assignments(c) == []


def test_execution_adopts_the_contract_run_instead_of_adding_a_second(env):
    c, rt, spawn = env
    agent = spawn(context=dict(CTX))
    aid = agent["agent_id"]
    rid = c.queued_contract_run(aid)
    rt.create_agent_run(run_id=rid, agent_id=aid, status="starting",
                        started_at="2026-10-07T10:00:00Z", input_summary="find X")
    runs = rt.list_agent_runs()
    assert [(r["run_id"], r["status"]) for r in runs] == [(rid, "starting")]
    conn = c._conn()
    assert conn.execute("SELECT attempt_no, assignment_id != '' FROM agent_runs").fetchone()[:] \
        == (1, 1)
    assert _assignments(c)[0]["status"] == "active"


def test_completed_registry_status_settles_with_exactly_one_message(env):
    c, rt, spawn = env
    agent = spawn(context=dict(CTX))
    aid = agent["agent_id"]
    rt.create_agent_message(message_id="m1", thread_id="t", agent_id=aid,
                            direction="agent->jarvis", role="assistant",
                            kind="result", content="Svar: X findes i y.py")
    rt.update_agent_registry_entry(aid, status="completed")
    rt.update_agent_registry_entry(aid, status="completed")  # dobbelt kald
    (a,) = _assignments(c)
    assert a["status"] == "completed"
    msgs = c.list_pending_results(owner_user_id="bjorn", origin_session_id="sess-1")
    assert len(msgs) == 1
    payload = json.loads(msgs[0]["payload_json"])
    assert (payload["summary"], payload["status"], msgs[0]["recipient_agent_id"],
            msgs[0]["parent_run_id"]) == ("Svar: X findes i y.py", "completed", "jarvis", "pr-1")


@pytest.mark.parametrize("status,assignment_status,code", [
    ("failed", "failed", "AGENT_FAILED"),
    ("cancelled", "cancelled", "CANCELLED"),
    ("expired", "timed_out", "TIMED_OUT"),
])
def test_other_terminal_statuses_map_to_assignment_outcomes(env, status, assignment_status, code):
    c, rt, spawn = env
    agent = spawn(context=dict(CTX))
    rt.update_agent_registry_entry(agent["agent_id"], status=status)
    (a,) = _assignments(c)
    assert a["status"] == assignment_status
    (m,) = c.list_pending_results(owner_user_id="bjorn", origin_session_id="sess-1")
    assert json.loads(m["payload_json"])["error_code"] == code


@pytest.mark.parametrize("status", ["queued", "starting", "active", "scheduled", "suspended"])
def test_non_terminal_registry_statuses_do_not_settle(env, status):
    c, rt, spawn = env
    agent = spawn(context=dict(CTX))
    rt.update_agent_registry_entry(agent["agent_id"], status=status)
    assert _assignments(c)[0]["status"] == "queued"
    assert c.list_pending_results(owner_user_id="bjorn", origin_session_id="sess-1") == []


def test_legacy_agent_status_changes_are_untouched(env):
    c, rt, spawn = env
    agent = spawn(context={})
    rt.update_agent_registry_entry(agent["agent_id"], status="completed")
    assert rt.get_agent_registry_entry(agent["agent_id"])["status"] == "completed"
    assert _assignments(c) == []


def _stub_model(monkeypatch, text, *, boom=False):
    from core.services import agent_runtime_spawn as M

    class _F:
        def execute_with_role_or_fallback(self, **kw):
            if boom:
                raise RuntimeError("udbyder nede")
            return {"text": text, "input_tokens": 10, "output_tokens": 5, "status": "completed"}

    monkeypatch.setattr(M, "agent_tools_enabled", lambda: False)
    monkeypatch.setattr(M, "_snapshot_tools", lambda agent: [])
    monkeypatch.setattr(M, "_facade", lambda: _F())
    from core.services import agent_runtime_base as base
    monkeypatch.setattr(base, "_facade", lambda: M._facade())
    return M


def test_real_execution_path_runs_on_the_contract_run_and_settles(env, monkeypatch):
    c, rt, spawn = env
    M = _stub_model(monkeypatch, "Fandt X i y.py med evidens.")
    agent = spawn(context=dict(CTX))
    aid = agent["agent_id"]
    contract_run = c.queued_contract_run(aid)
    M.execute_agent_task(agent_id=aid)
    runs = rt.list_agent_runs()
    assert [r["run_id"] for r in runs] == [contract_run], "kun ét run, og det er kontraktens"
    (a,) = _assignments(c)
    assert a["status"] == "completed"
    (m,) = c.list_pending_results(owner_user_id="bjorn", origin_session_id="sess-1")
    payload = json.loads(m["payload_json"])
    assert (payload["status"], payload["last_run_id"], payload["attempt_run_ids"]) == (
        "completed", contract_run, [contract_run])
    assert "Fandt X" in payload["summary"]


def test_real_execution_failure_settles_failed_with_the_same_single_run(env, monkeypatch):
    c, rt, spawn = env
    M = _stub_model(monkeypatch, "", boom=True)
    agent = spawn(context=dict(CTX))
    aid = agent["agent_id"]
    contract_run = c.queued_contract_run(aid)
    M.execute_agent_task(agent_id=aid)
    assert [r["run_id"] for r in rt.list_agent_runs()] == [contract_run]
    (m,) = c.list_pending_results(owner_user_id="bjorn", origin_session_id="sess-1")
    payload = json.loads(m["payload_json"])
    assert (payload["status"], payload["error_code"], payload["last_run_id"]) == (
        "failed", "AGENT_FAILED", contract_run)


def test_persistent_failed_is_an_attempt_not_a_terminal_outcome(env):
    c, rt, spawn = env
    agent = spawn(context={}, persistent=True, ttl_seconds=900)
    aid = agent["agent_id"]
    c.bind_agent_owner(agent_id=aid, owner_user_id="bjorn", owner_session_id="sess-1")
    c.accept_assignment(agent_id=aid, owner_user_id="bjorn", origin_session_id="sess-1",
                        goal="vagt")
    rt.update_agent_registry_entry(aid, status="failed", failure_increment=1)
    assert _assignments(c)[0]["status"] == "queued"
    assert c.list_pending_results(owner_user_id="bjorn", origin_session_id="sess-1") == []


def test_unbound_spawn_reports_why(env):
    from core.services.agent_contract_bridge import bind_new_agent
    assert bind_new_agent(agent_id="x", parent_agent_id="jarvis", goal="g", persistent=False,
                          context={}) == {"bound": False, "reason": "no_owner_or_session"}
    assert bind_new_agent(agent_id="x", parent_agent_id="jarvis", goal="g", persistent=True,
                          context=dict(CTX)) == {"bound": False, "reason": "engine_off"}


def test_spawn_stores_assignment_json_for_the_first_run(env):
    import json

    from core.runtime import db_agent_artifacts as art

    c, rt, spawn = env
    agent = spawn(context=dict(CTX), goal="find X")
    (a,) = _assignments(c)
    run_id = c.queued_contract_run(agent["agent_id"])
    out = art.read_artifact(owner_user_id="bjorn", ref=f"{run_id}/assignment.json")
    doc = json.loads(out["content"])
    assert (doc["assignment_id"], doc["goal"], doc["parent_run_id"], doc["target"]) == (
        a["assignment_id"], "find X", "pr-1", "runtime-container")
    assert art.read_artifact(owner_user_id="anden", ref=f"{run_id}/assignment.json")["status"] == "NOT_FOUND"
