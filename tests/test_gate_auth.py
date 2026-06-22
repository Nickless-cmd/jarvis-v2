"""Tests for gate_auth 🔒 — tool-access rolle-håndhævelse, SECURITY fail-closed."""
from __future__ import annotations

from unittest.mock import patch

from core.services.gate_auth import auth_gate
from core.services.gate_kernel import Decision, GateClass


def test_owner_and_unbound_always_green():
    assert auth_gate({"role": "owner", "name": "operator_bash"}).decision is Decision.GREEN
    assert auth_gate({"role": "", "name": "operator_bash"}).decision is Decision.GREEN


def test_member_allowed_green():
    with patch("core.tools.tool_scoping.is_tool_allowed", return_value=True):
        v = auth_gate({"role": "member", "scope": "code", "name": "web_search"})
    assert v.decision is Decision.GREEN


def test_member_disallowed_red():
    with patch("core.tools.tool_scoping.is_tool_allowed", return_value=False):
        v = auth_gate({"role": "member", "scope": "chat", "name": "operator_bash"})
    assert v.decision is Decision.RED and v.action == "block"
    assert v.klass is GateClass.SECURITY


def test_fail_CLOSED_through_central_on_gate_exception():
    """SECURITY: hvis is_tool_allowed KASTER for en member → fail-CLOSED RED (deny)."""
    from core.services.central_core import Central
    from core.services.central_trace import TraceSink
    from core.services.central_switches import CircuitBreaker
    c = Central(sink=TraceSink(), breaker=CircuitBreaker(), emit=lambda *a: None)
    with patch("core.tools.tool_scoping.is_tool_allowed", side_effect=RuntimeError("boom")):
        v = c.decide("tool_access", {"role": "member", "scope": "chat", "name": "operator_bash"},
                     auth_gate, cluster="auth", klass=GateClass.SECURITY)
    assert v.decision is Decision.RED  # fail-CLOSED deny, ikke allow


def test_owner_never_reaches_failing_check():
    # owner returnerer GREEN FØR is_tool_allowed kaldes → kan aldrig låses ude
    with patch("core.tools.tool_scoping.is_tool_allowed", side_effect=RuntimeError("boom")):
        v = auth_gate({"role": "owner", "name": "operator_bash"})
    assert v.decision is Decision.GREEN
