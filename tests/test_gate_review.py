"""Tests for gate_review — graderet selv-review-vurdering."""
from __future__ import annotations

from core.services.gate_review import review_gate
from core.services.gate_kernel import Decision


def test_red_on_high_risk():
    v = review_gate({"review": {"risk_level": "high", "score": 0.2}})
    assert v.decision is Decision.RED


def test_yellow_on_med_risk():
    assert review_gate({"review": {"risk_level": "med"}}).decision is Decision.YELLOW
    assert review_gate({"review": {"risk_level": "medium"}}).decision is Decision.YELLOW


def test_green_on_low_risk():
    assert review_gate({"review": {"risk_level": "low"}}).decision is Decision.GREEN
    assert review_gate({"review": {}}).decision is Decision.GREEN  # default low
