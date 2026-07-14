"""Tests for the Fase 5 Task 1 server-side owner-only privilege gate on the
approval-timing axis in /v1/agent/step (apps/api/jarvis_api/routes/agent_loop.py
_apply_privilege_enforcement). Flag-gated (`jc_privilege_enforcement`, default
OFF) and inert for the owner role."""
from apps.api.jarvis_api.routes import agent_loop


def test_server_downgrades_nonowner_bypass_when_flag_on(monkeypatch):
    monkeypatch.setattr(agent_loop, "_flag", lambda name, default=False: name == "jc_privilege_enforcement")
    mode, downgraded = agent_loop._apply_privilege_enforcement("guest", "bypass")
    assert mode == "ask"
    assert downgraded is True


def test_server_downgrades_nonowner_full_auto_when_flag_on(monkeypatch):
    monkeypatch.setattr(agent_loop, "_flag", lambda name, default=False: name == "jc_privilege_enforcement")
    mode, downgraded = agent_loop._apply_privilege_enforcement("guest", "full-auto")
    assert mode == "ask"
    assert downgraded is True


def test_flag_off_leaves_nonowner_unchanged(monkeypatch):
    monkeypatch.setattr(agent_loop, "_flag", lambda name, default=False: False)
    mode, downgraded = agent_loop._apply_privilege_enforcement("guest", "bypass")
    assert mode == "bypass"
    assert downgraded is False


def test_owner_never_downgraded_even_with_flag_on(monkeypatch):
    monkeypatch.setattr(agent_loop, "_flag", lambda name, default=False: True)
    mode, downgraded = agent_loop._apply_privilege_enforcement("owner", "bypass")
    assert mode == "bypass"
    assert downgraded is False


def test_nonowner_ask_mode_never_downgraded(monkeypatch):
    """ask/auto-edit are already prompting/semi-prompting modes — no downgrade needed."""
    monkeypatch.setattr(agent_loop, "_flag", lambda name, default=False: True)
    mode, downgraded = agent_loop._apply_privilege_enforcement("guest", "ask")
    assert mode == "ask"
    assert downgraded is False


def test_empty_requested_mode_is_noop(monkeypatch):
    monkeypatch.setattr(agent_loop, "_flag", lambda name, default=False: True)
    mode, downgraded = agent_loop._apply_privilege_enforcement("guest", "")
    assert mode == ""
    assert downgraded is False
