"""Tests for gate_commit — Commit-clusterens gate routet gennem Centralen."""
from __future__ import annotations

from unittest.mock import patch

from core.services.gate_commit import commit_gate
from core.services.gate_kernel import Decision


def test_commit_gate_red_block_on_conflict():
    with patch("core.services.decision_gate.check_decision_gate",
               return_value=(False, "konflikt med aktiv beslutning")):
        v = commit_gate({"tool_name": "operator_bash", "tool_args": {}, "user_message": ""})
    assert v.decision is Decision.RED and v.action == "block"
    assert "konflikt" in v.reason


def test_commit_gate_green_when_allowed():
    with patch("core.services.decision_gate.check_decision_gate",
               return_value=(True, None)):
        v = commit_gate({"tool_name": "web_search"})
    assert v.decision is Decision.GREEN


def test_commit_gate_fail_open_through_central():
    """commit_gate kaster → central().decide (cognitiv) fail-open'er til SKIP (allow)."""
    from core.services.central_core import Central
    from core.services.central_trace import TraceSink
    from core.services.central_switches import CircuitBreaker
    from core.services.gate_kernel import GateClass
    c = Central(sink=TraceSink(), breaker=CircuitBreaker(), emit=lambda *a: None)
    with patch("core.services.decision_gate.check_decision_gate",
               side_effect=RuntimeError("boom")):
        v = c.decide("decision_gate", {"tool_name": "x", "run_id": "cg1"},
                     commit_gate, cluster="commit", klass=GateClass.COGNITIVE)
    assert v.decision is Decision.SKIP
