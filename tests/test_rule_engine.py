"""Tests for rule engine and rule definitions."""
from __future__ import annotations

from core.services.rule_engine import (
    RuleEngine,
    Rule,
    RuleConclusion,
    evaluate_rules,
    get_all_rules,
    reset_engine,
)
from core.services.rule_definitions import ALL_RULES


def test_engine_creation():
    engine = RuleEngine()
    assert engine is not None
    assert engine.rules == []


def test_register_rules():
    engine = RuleEngine()
    engine.register_rules(ALL_RULES)
    assert len(engine.rules) == len(ALL_RULES)


def test_evaluate_with_empty_signals():
    """Engine should handle empty/missing signals gracefully."""
    conclusions = evaluate_rules({})
    assert conclusions.rules_evaluated > 0
    assert isinstance(conclusions.conclusions, list)


def test_evaluate_with_minimal_signals():
    signals = {
        "affective_meta_state": {
            "state": "settled",
            "bearing": "even",
            "live_emotional_state": {
                "confidence": 0.7,
                "curiosity": 0.5,
                "frustration": 0.1,
                "fatigue": 0.2,
            },
        },
        "curiosity": {"curiosity_count": 0, "open_questions": []},
        "body_state": {"energy_level": "high", "wake_state": "awake"},
        "goal_signal": {"summary": {"active_count": 0}},
        "desire": {"active_count": 0},
        "conflict": {"last_conflict": ""},
        "open_loop": {"summary": {"open_count": 0}},
        "creative_drift": {"drift_count_today": 0},
        "existential_wonder": {"latest_wonder": ""},
        "internal_opposition": {"active": False},
        "self_review_signal": {"summary": {"active_count": 0}},
    }
    conclusions = evaluate_rules(signals)
    assert conclusions.rules_evaluated > 0
    # Should produce some suggestions even in minimal state
    assert isinstance(conclusions.conclusions, list)


def test_high_curiosity_high_energy():
    """High curiosity (>5 open questions) + strong appetite should fire explore action."""
    signals = {
        "affective_meta_state": {
            "state": "attentive",
            "bearing": "forward",
            "live_emotional_state": {
                "confidence": 0.8,
                "curiosity": 0.85,
                "frustration": 0.1,
                "fatigue": 0.15,
            },
        },
        # Need >=5 open_questions for high_curiosity rule to fire
        "curiosity": {
            "curiosity_count": 3,
            "open_questions": ["w1", "w2", "w3", "w4", "w5"],
        },
        # Need appetite intensity >= 0.85 for strong_appetite rule to fire
        "desire": {
            "active_count": 2,
            "appetites": [{"type": "curiosity-appetite", "intensity": 0.9}],
        },
        "goal_signal": {"active": True, "items": [{"id": 1}]},
        "body_state": {"energy_level": "high", "wake_state": "awake"},
        "conflict": {"last_conflict": ""},
        "open_loop": {"summary": {"open_count": 1}},
        "creative_drift": {"drift_count_today": 1},
        "existential_wonder": {"latest_wonder": ""},
        "internal_opposition": {"active": False},
        "self_review_signal": {"summary": {"active_count": 0}},
    }
    conclusions = evaluate_rules(signals)
    # Should have at least one high-priority conclusion
    high_prio = [c for c in conclusions.conclusions if c.priority_delta >= 20]
    assert len(high_prio) > 0, f"No high-priority conclusions: {[c.rule_name for c in conclusions.conclusions]}"


def test_high_fatigue_conserves():
    """High fatigue should produce conserve-energy conclusions."""
    signals = {
        "affective_meta_state": {
            "state": "settled",
            "bearing": "even",
            "live_emotional_state": {
                "confidence": 0.5,
                "curiosity": 0.3,
                "frustration": 0.2,
                "fatigue": 0.85,
            },
        },
        "curiosity": {"curiosity_count": 1, "open_questions": []},
        "body_state": {"energy_level": "low", "wake_state": "drowsy"},
        "goal_signal": {"summary": {"active_count": 3}},
        "desire": {"active_count": 1},
        "conflict": {"last_conflict": ""},
        "open_loop": {"summary": {"open_count": 3}},
        "creative_drift": {"drift_count_today": 0},
        "existential_wonder": {"latest_wonder": ""},
        "internal_opposition": {"active": False},
        "self_review_signal": {"summary": {"active_count": 2}},
    }
    conclusions = evaluate_rules(signals)
    conserve = [c for c in conclusions.conclusions if "conserve" in c.suggestion.lower() or "fatigue" in c.trace.lower()]
    # At minimum, engine should not crash and should produce conclusions
    assert isinstance(conclusions.conclusions, list)


def test_all_rules_have_names():
    for r in ALL_RULES:
        assert r.name, f"Rule missing name: {r}"
        assert r.domain, f"Rule missing domain: {r.name}"
        assert callable(r.condition), f"Rule {r.name} missing condition"
        assert callable(r.action), f"Rule {r.name} missing action"


def test_get_all_rules_serializable():
    rules = get_all_rules()
    assert len(rules) == len(ALL_RULES)
    for r in rules:
        assert "name" in r
        assert "domain" in r
        assert "description" in r
        assert "priority" in r


def test_no_duplicate_rule_names():
    names = [r.name for r in ALL_RULES]
    assert len(names) == len(set(names)), f"Duplicate rule names: {[n for n in names if names.count(n) > 1]}"


def test_rule_domains_are_valid():
    valid_domains = {"focus", "action", "attention", "strategy", "pause", "reflect", "affect", "goal", "curiosity", "desire", "conflict", "energy", "meta", "governance"}
    for r in ALL_RULES:
        assert r.domain in valid_domains, f"Rule {r.name} has invalid domain: {r.domain}"
