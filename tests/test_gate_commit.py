"""Tests for gate_commit — Commit-clusterens GRADEREDE gate gennem Centralen."""
from __future__ import annotations

from unittest.mock import patch

from core.services.gate_commit import commit_gate
from core.services.gate_kernel import Decision


def test_hard_conflict_red_block():
    with patch("core.services.decision_gate.evaluate_decision_conflict",
               return_value=("hard", "blok-grund")):
        v = commit_gate({"tool_name": "operator_bash"})
    assert v.decision is Decision.RED and v.action == "block"


def test_soft_conflict_yellow_warn():
    with patch("core.services.decision_gate.evaluate_decision_conflict",
               return_value=("soft", "blød advarsel")):
        v = commit_gate({"tool_name": "web_search"})
    assert v.decision is Decision.YELLOW and v.action == "warn"


def test_no_conflict_green():
    with patch("core.services.decision_gate.evaluate_decision_conflict",
               return_value=("none", None)):
        v = commit_gate({"tool_name": "web_search"})
    assert v.decision is Decision.GREEN


def test_fail_open_through_central():
    """commit_gate kaster → central().decide (cognitiv) fail-open'er til SKIP."""
    from core.services.central_core import Central
    from core.services.central_trace import TraceSink
    from core.services.central_switches import CircuitBreaker
    from core.services.gate_kernel import GateClass
    c = Central(sink=TraceSink(), breaker=CircuitBreaker(), emit=lambda *a: None)
    with patch("core.services.decision_gate.evaluate_decision_conflict",
               side_effect=RuntimeError("boom")):
        v = c.decide("decision_gate", {"tool_name": "x", "run_id": "cg1"},
                     commit_gate, cluster="commit", klass=GateClass.COGNITIVE)
    assert v.decision is Decision.SKIP
