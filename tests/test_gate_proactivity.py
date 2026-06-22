"""Tests for gate_proactivity — konsolideret GRADERET verifikations-gate (R2/R2.5)."""
from __future__ import annotations

from unittest.mock import patch

from core.services.gate_proactivity import proactivity_gate
from core.services.gate_kernel import Decision


def test_red_when_r25_hard_blocks():
    with patch("core.services.r2_5_blocking_gate.r2_5_block_section",
               return_value="R2.5 block (verifikation required):\n..."):
        v = proactivity_gate({"reasoning_tier": "deep"})
    assert v.decision is Decision.RED and v.action == "block"
    assert (v.evidence or {}).get("priority") == 95
    assert "R2.5" in (v.evidence or {}).get("text", "")


def test_yellow_when_r2_soft_surface():
    with patch("core.services.r2_5_blocking_gate.r2_5_block_section", return_value=None), \
         patch("core.services.verification_gate.verification_gate_section",
               return_value="Verification gate: 2 unverified mutations"):
        v = proactivity_gate({"reasoning_tier": "fast"})
    assert v.decision is Decision.YELLOW and v.action == "warn"
    assert (v.evidence or {}).get("priority") == 23


def test_green_when_no_concern():
    with patch("core.services.r2_5_blocking_gate.r2_5_block_section", return_value=None), \
         patch("core.services.verification_gate.verification_gate_section", return_value=None):
        v = proactivity_gate({"reasoning_tier": "fast"})
    assert v.decision is Decision.GREEN


def test_fail_open_through_central():
    from core.services.central_core import Central
    from core.services.central_trace import TraceSink
    from core.services.central_switches import CircuitBreaker
    from core.services.gate_kernel import GateClass
    c = Central(sink=TraceSink(), breaker=CircuitBreaker(), emit=lambda *a: None)
    with patch("core.services.r2_5_blocking_gate.r2_5_block_section",
               side_effect=RuntimeError("boom")), \
         patch("core.services.verification_gate.verification_gate_section",
               side_effect=RuntimeError("boom")):
        v = c.decide("verification", {"reasoning_tier": "deep"},
                     proactivity_gate, cluster="proactivity", klass=GateClass.COGNITIVE)
    # gate selv fail-open'er internt → GREEN (ikke kast); central ville ellers SKIP'e
    assert v.decision in (Decision.GREEN, Decision.SKIP)
