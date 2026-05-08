"""Smoke tests for rule_definitions + rule_engine wiring."""
from __future__ import annotations


def test_all_rules_count_in_range():
    from core.services.rule_definitions import ALL_RULES
    assert 30 <= len(ALL_RULES) <= 50, (
        f"expected 30-50 rules, got {len(ALL_RULES)}"
    )


def test_all_rules_cover_six_domains():
    from core.services.rule_definitions import ALL_RULES
    domains = {r.domain for r in ALL_RULES}
    expected = {"focus", "action", "attention", "strategy", "pause", "reflect"}
    assert expected.issubset(domains), (
        f"missing domains: {expected - domains}"
    )


def test_all_rules_have_required_fields():
    from core.services.rule_definitions import ALL_RULES
    for r in ALL_RULES:
        assert r.name, f"rule missing name: {r}"
        assert r.description, f"rule {r.name} missing description"
        assert r.domain, f"rule {r.name} missing domain"
        assert callable(r.condition), f"rule {r.name} condition not callable"
        assert callable(r.action), f"rule {r.name} action not callable"


def test_engine_loads_and_evaluates_empty_signals():
    from core.services.rule_engine import evaluate_rules, reset_engine
    reset_engine()
    result = evaluate_rules({})
    # With empty signals most rules should not fire — but engine must run cleanly
    assert result.rules_evaluated >= 30
    assert len(result.errors) == 0, f"errors: {result.errors}"


def test_engine_evaluates_real_signals_without_errors():
    """Run engine against actual signal surfaces; verify no rule crashes."""
    from core.services.rule_engine import evaluate_rules, reset_engine
    from core.services.signal_surface_router import list_all_surfaces
    reset_engine()
    signals = list_all_surfaces()
    result = evaluate_rules(signals)
    assert len(result.errors) == 0, (
        f"rule errors against real signals: {result.errors[:3]}"
    )


def test_high_curiosity_rule_fires_on_synthetic_input():
    """Synthetic signal that should trip the curiosity rule."""
    from core.services.rule_engine import evaluate_rules, reset_engine
    reset_engine()
    fake = {
        "curiosity": {"open_questions": ["a", "b", "c", "d", "e", "f"]},
    }
    result = evaluate_rules(fake)
    fired = [c.rule_name for c in result.conclusions]
    assert "high_curiosity_promotes_exploration" in fired


def test_strong_appetite_rule_fires():
    from core.services.rule_engine import evaluate_rules, reset_engine
    reset_engine()
    fake = {
        "desire": {"appetites": [{"intensity": 0.92, "label": "test"}]},
    }
    result = evaluate_rules(fake)
    fired = [c.rule_name for c in result.conclusions]
    assert "strong_appetite_focus" in fired


def test_critical_self_erasure_rule_fires_with_max_priority():
    """Self-erasure should fire with critical urgency and large negative delta."""
    from core.services.rule_engine import evaluate_rules, reset_engine
    reset_engine()
    fake = {
        "metabolism_state": {"self_erasure_state": "active"},
    }
    result = evaluate_rules(fake)
    self_erasure_conclusions = [
        c for c in result.conclusions
        if c.rule_name == "metabolism_self_erasure_critical_pause"
    ]
    assert len(self_erasure_conclusions) == 1
    c = self_erasure_conclusions[0]
    assert c.urgency == "critical"
    assert c.priority_delta < -30  # significant pull-back
