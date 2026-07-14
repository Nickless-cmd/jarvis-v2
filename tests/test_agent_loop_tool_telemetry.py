"""Tests for the Fase 5 Task 20 per-tool telemetry wiring in agent_loop.py:
tools_execute() (forwarded tools, server-timed) and agent_step() (client-
reported tool_steps for locally-executed tools). Flag-gated
(jc_tool_telemetry, default OFF)."""
import asyncio

from apps.api.jarvis_api.routes import agent_loop


def test_tools_execute_publishes_telemetry_when_flag_on(monkeypatch):
    published = []
    monkeypatch.setattr(agent_loop, "_resolve_role", lambda: "owner")
    monkeypatch.setattr(agent_loop, "unalias", lambda n: n)
    monkeypatch.setattr(agent_loop, "check_brain_write_allowed", lambda name, role: True)
    monkeypatch.setattr(agent_loop, "execute_tool", lambda name, args: {"status": "ok"})
    monkeypatch.setattr(agent_loop, "_flag", lambda name, default=False: name == "jc_tool_telemetry")
    monkeypatch.setattr("core.services.jc_tool_telemetry.publish_tool_step",
                        lambda **kw: published.append(kw) or True)
    body = agent_loop._ExecBody(name="read_file", arguments={"path": "/x"})
    result = asyncio.run(agent_loop.tools_execute(body))
    assert result["result"] == {"status": "ok"}
    assert len(published) == 1
    assert published[0]["tool"] == "read_file"
    assert published[0]["status"] == "ok"


def test_tools_execute_no_publish_when_flag_off(monkeypatch):
    published = []
    monkeypatch.setattr(agent_loop, "_resolve_role", lambda: "owner")
    monkeypatch.setattr(agent_loop, "unalias", lambda n: n)
    monkeypatch.setattr(agent_loop, "check_brain_write_allowed", lambda name, role: True)
    monkeypatch.setattr(agent_loop, "execute_tool", lambda name, args: {"status": "ok"})
    monkeypatch.setattr(agent_loop, "_flag", lambda name, default=False: False)
    monkeypatch.setattr("core.services.jc_tool_telemetry.publish_tool_step",
                        lambda **kw: published.append(kw) or True)
    body = agent_loop._ExecBody(name="read_file", arguments={"path": "/x"})
    asyncio.run(agent_loop.tools_execute(body))
    assert published == []
