"""Samlet LLM-egress-observation + Bölge-3 cheap-eligibility."""
from __future__ import annotations

from core.services import central_llm_egress as E


def test_cheap_eligible_by_purpose():
    assert E.classify_cheap_eligible(lane="primary", purpose="summarize", autonomous=False) is True
    assert E.classify_cheap_eligible(lane="cheap", purpose="classify", autonomous=False) is True


def test_identity_lane_not_eligible():
    # Synlig chat / identitet → behold den stærke model
    assert E.classify_cheap_eligible(lane="visible", purpose="", autonomous=False) is False
    assert E.classify_cheap_eligible(lane="primary", purpose="reasoning", autonomous=False) is False


def test_autonomous_internal_eligible():
    assert E.classify_cheap_eligible(lane="daemon", purpose="", autonomous=True) is True


def test_observe_self_safe():
    # Må aldrig kaste, uanset input
    E.observe(lane="primary", provider="deepseek", model="m", purpose="factual",
              input_tokens=10, output_tokens=5, source="test")
    E.observe(lane="", provider="", model="", purpose="")


def test_surface():
    s = E.build_llm_egress_surface()
    assert "cheap_eligible_purposes" in s
