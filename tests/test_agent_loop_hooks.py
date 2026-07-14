"""Tests for the Fase 5 Task 3 server-side verdict-ledger wiring: a forwarded
brain-write deny on /v1/tools/execute records one row via
core.services.gate_verdict_ledger.record — additive logging, guard behaviour
unchanged."""
import asyncio

import pytest

from apps.api.jarvis_api.routes import agent_loop


def test_server_records_verdict_on_deny(monkeypatch):
    recorded = []
    monkeypatch.setattr(agent_loop, "_resolve_role", lambda: "guest")
    monkeypatch.setattr(agent_loop, "unalias", lambda n: n)
    monkeypatch.setattr(agent_loop, "check_brain_write_allowed", lambda name, role: False)
    monkeypatch.setattr(
        "core.services.gate_verdict_ledger.record",
        lambda **kw: recorded.append(kw),
    )
    body = agent_loop._ExecBody(name="write_file", arguments={"path": "/x"})
    with pytest.raises(Exception):
        asyncio.run(agent_loop.tools_execute(body))
    assert len(recorded) == 1
    assert recorded[0]["nerve"] == "jc_forward"
    assert recorded[0]["cluster"] == "brain_write"
    assert recorded[0]["decision"] == "deny"


def test_no_verdict_recorded_on_allow(monkeypatch):
    recorded = []
    monkeypatch.setattr(agent_loop, "_resolve_role", lambda: "owner")
    monkeypatch.setattr(agent_loop, "unalias", lambda n: n)
    monkeypatch.setattr(agent_loop, "check_brain_write_allowed", lambda name, role: True)
    monkeypatch.setattr(agent_loop, "execute_tool", lambda name, args: {"status": "ok"})
    monkeypatch.setattr(
        "core.services.gate_verdict_ledger.record",
        lambda **kw: recorded.append(kw),
    )
    body = agent_loop._ExecBody(name="read_file", arguments={"path": "/x"})
    asyncio.run(agent_loop.tools_execute(body))
    assert recorded == []


def test_ledger_failure_never_breaks_the_403(monkeypatch):
    """A logging failure must never mask the real gate decision."""
    monkeypatch.setattr(agent_loop, "_resolve_role", lambda: "guest")
    monkeypatch.setattr(agent_loop, "unalias", lambda n: n)
    monkeypatch.setattr(agent_loop, "check_brain_write_allowed", lambda name, role: False)

    def _boom(**kw):
        raise RuntimeError("ledger down")

    monkeypatch.setattr("core.services.gate_verdict_ledger.record", _boom)
    body = agent_loop._ExecBody(name="write_file", arguments={"path": "/x"})
    with pytest.raises(Exception) as exc_info:
        asyncio.run(agent_loop.tools_execute(body))
    assert getattr(exc_info.value, "status_code", None) == 403
