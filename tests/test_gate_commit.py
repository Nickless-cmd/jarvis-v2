"""Tests for gate_commit — Commit-clusterens GRADEREDE gate gennem Centralen."""
from __future__ import annotations

from unittest.mock import patch

from core.services.gate_commit import commit_gate, veto_gate
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


# ── veto_gate (merged ind i commit-cluster 2026-06-22) ───────────────────
def test_veto_blocks_red():
    with patch("core.services.veto_gate.check_veto",
               return_value=(False, "du virkede tøvende — bekræft venligst")):
        v = veto_gate({"tool_name": "operator_bash", "user_message": "nej vent"})
    assert v.decision is Decision.RED and v.action == "block"
    assert "tøvende" in (v.evidence or {}).get("reason", "")


def test_veto_allows_green():
    with patch("core.services.veto_gate.check_veto", return_value=(True, None)):
        v = veto_gate({"tool_name": "web_search", "user_message": "ja kør"})
    assert v.decision is Decision.GREEN


def test_veto_fail_open_through_central():
    """veto_gate kaster → central (cognitiv) fail-open'er til SKIP (ingen blok)."""
    from core.services.central_core import Central
    from core.services.central_trace import TraceSink
    from core.services.central_switches import CircuitBreaker
    from core.services.gate_kernel import GateClass
    c = Central(sink=TraceSink(), breaker=CircuitBreaker(), emit=lambda *a: None)
    with patch("core.services.veto_gate.check_veto", side_effect=RuntimeError("boom")):
        v = c.decide("veto", {"tool_name": "x", "run_id": "v1"},
                     veto_gate, cluster="commit", klass=GateClass.COGNITIVE)
    assert v.decision is Decision.SKIP
