from __future__ import annotations
from core.services.contradiction_resolver import classify_tier, pick_survivor

def _finding(**kw):
    base = {
        "decision_id": "d1", "decision_directive": "Svar altid kort",
        "decision_priority": 3, "review_id": 7,
        "review_text": "Jeg svarer ikke kort nok i lange tr%ade",
        "overlap_tokens": ["svar", "kort", "nok"], "detected_at": "2026-07-10T10:00:00+00:00",
    }
    base.update(kw); return base

def test_pick_survivor_review_wins_by_recency_same_authority():
    # Decision og self-review er begge self-derived → tie → nyere critique vinder.
    s = pick_survivor(_finding())
    assert s["winner"] == "review"
    assert s["loser"] == "decision"
    assert s["confidence"] == "high"      # 3 overlap-tokens
    assert "recency" in s["rule"]

def test_pick_survivor_confidence_medium_two_tokens():
    s = pick_survivor(_finding(overlap_tokens=["svar", "kort"]))
    assert s["confidence"] == "medium"

def test_pick_survivor_confidence_low_one_token():
    s = pick_survivor(_finding(overlap_tokens=["svar"]))
    assert s["confidence"] == "low"

def test_classify_tier_operational_is_auto():
    assert classify_tier(_finding()) == "auto"

def test_classify_tier_identity_keyword_escalates():
    assert classify_tier(_finding(decision_directive="Jeg er nysgerrig af natur")) == "escalate"

def test_classify_tier_high_priority_escalates():
    assert classify_tier(_finding(decision_priority=9)) == "escalate"

def test_classify_tier_low_confidence_escalates():
    # Svag overlap → for usikkert til auto → escalate (konservativt).
    assert classify_tier(_finding(overlap_tokens=["svar"])) == "escalate"
