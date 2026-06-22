"""Tests for gate_privacy 🔒 — cross-user-deling, SECURITY fail-closed."""
from __future__ import annotations

from unittest.mock import patch

from core.services.gate_privacy import privacy_gate
from core.services.gate_kernel import Decision, GateClass


def test_yellow_when_other_user_mentioned():
    with patch("core.services.cross_user_share_guard.check_against_registry",
               return_value={"needs_confirmation": True, "mentioned_users": ["Lotte"], "prompt": "p"}):
        v = privacy_gate({"text": "Lotte sagde...", "current_user_id": "u1"})
    assert v.decision is Decision.YELLOW and v.klass is GateClass.SECURITY
    assert (v.evidence or {}).get("mentioned_users") == ["Lotte"]


def test_green_when_clean():
    with patch("core.services.cross_user_share_guard.check_against_registry",
               return_value={"needs_confirmation": False, "mentioned_users": [], "prompt": ""}):
        v = privacy_gate({"text": "hej", "current_user_id": "u1"})
    assert v.decision is Decision.GREEN


def test_fail_CLOSED_through_central_on_gate_exception():
    """SECURITY: hvis gaten KASTER, fail-CLOSED → RED (deny), IKKE allow."""
    from core.services.central_core import Central
    from core.services.central_trace import TraceSink
    from core.services.central_switches import CircuitBreaker
    c = Central(sink=TraceSink(), breaker=CircuitBreaker(), emit=lambda *a: None)
    with patch("core.services.cross_user_share_guard.check_against_registry",
               side_effect=RuntimeError("boom")):
        v = c.decide("cross_user_share", {"text": "x", "current_user_id": "u1"},
                     privacy_gate, cluster="privacy", klass=GateClass.SECURITY)
    assert v.decision is Decision.RED  # fail-CLOSED (modsat cognitiv SKIP)


def test_security_nerve_cannot_be_disabled_only_isolated():
    from core.services import central_switches as sw
    from core.services.gate_kernel import GateClass as GK
    r = sw.set_enabled("nerve", "cross_user_share", False, klass=GK.SECURITY)
    assert r.get("ok") is False  # sikkerheds-nerve kan ikke slås fra
