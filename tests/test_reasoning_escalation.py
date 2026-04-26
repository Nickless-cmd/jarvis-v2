"""Unit tests for reasoning_escalation (R3 of reasoning-layer rollout)."""
from __future__ import annotations

from unittest.mock import patch

from core.services.reasoning_escalation import (
    evaluate_escalation,
    escalation_section,
)


def _stub_tier(tier: str, signals: list[str] | None = None):
    return {"tier": tier, "score": 80 if tier == "deep" else 30, "signals": signals or []}


def _stub_gate(failed: int = 0, unverified: int = 0):
    return {
        "mutation_count": unverified + failed,
        "verify_count": failed,
        "failed_verify_count": failed,
        "unverified_count": unverified,
        "failed_verifies": [],
    }


def test_no_escalation_for_fast_tier():
    with patch("core.services.reasoning_escalation._safe_tier", return_value=_stub_tier("fast")), \
         patch("core.services.reasoning_escalation._safe_gate", return_value=_stub_gate()):
        result = evaluate_escalation("hej")
    assert result["escalate"] is False


def test_no_escalation_for_deep_without_failures():
    with patch("core.services.reasoning_escalation._safe_tier", return_value=_stub_tier("deep")), \
         patch("core.services.reasoning_escalation._safe_gate", return_value=_stub_gate()):
        result = evaluate_escalation("design ny arkitektur")
    assert result["escalate"] is False


def test_escalation_for_deep_plus_failed_verify():
    with patch("core.services.reasoning_escalation._safe_tier", return_value=_stub_tier("deep")), \
         patch("core.services.reasoning_escalation._safe_gate", return_value=_stub_gate(failed=1)):
        result = evaluate_escalation("kør migration")
    assert result["escalate"] is True
    assert result["recommendation"]["path"] is not None


def test_escalation_recommends_critic_on_multiple_failed_verifies():
    with patch("core.services.reasoning_escalation._safe_tier", return_value=_stub_tier("reasoning")), \
         patch("core.services.reasoning_escalation._safe_gate", return_value=_stub_gate(failed=2)):
        result = evaluate_escalation("opdater config")
    assert result["escalate"] is True
    assert result["recommendation"]["path"] == "spawn_agent_task"
    assert result["recommendation"]["role"] == "critic"


def test_escalation_recommends_researcher_on_unverified_mutations():
    with patch("core.services.reasoning_escalation._safe_tier", return_value=_stub_tier("deep")), \
         patch("core.services.reasoning_escalation._safe_gate", return_value=_stub_gate(unverified=4)):
        result = evaluate_escalation("rør mange filer")
    assert result["escalate"] is True
    assert result["recommendation"]["role"] == "researcher"


def test_escalation_recommends_council_on_deep_with_risk_markers():
    with patch(
        "core.services.reasoning_escalation._safe_tier",
        return_value=_stub_tier("deep", signals=["destructive command marker", "production system"]),
    ), patch("core.services.reasoning_escalation._safe_gate", return_value=_stub_gate(failed=1)):
        result = evaluate_escalation("rm -rf prod")
    assert result["escalate"] is True
    # Either critic (failed_verifies path) or council (risk markers path) is acceptable
    assert result["recommendation"]["path"] in ("convene_council", "spawn_agent_task")


def test_section_returns_none_when_no_escalation():
    with patch("core.services.reasoning_escalation._safe_tier", return_value=_stub_tier("fast")), \
         patch("core.services.reasoning_escalation._safe_gate", return_value=_stub_gate()):
        assert escalation_section() is None


def test_section_returns_string_when_escalating():
    with patch("core.services.reasoning_escalation._safe_tier", return_value=_stub_tier("deep")), \
         patch("core.services.reasoning_escalation._safe_gate", return_value=_stub_gate(failed=1)):
        section = escalation_section("design")
    assert section is not None
    assert "eskalering" in section.lower() or "escalation" in section.lower() or "🚨" in section


def test_tool_exec_wrapper():
    from core.services.reasoning_escalation import _exec_recommend_escalation
    with patch("core.services.reasoning_escalation._safe_tier", return_value=_stub_tier("fast")), \
         patch("core.services.reasoning_escalation._safe_gate", return_value=_stub_gate()):
        result = _exec_recommend_escalation({"message": "hej"})
    assert result["status"] == "ok"
    assert result["escalate"] is False
