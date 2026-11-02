from __future__ import annotations

from core.services.inbox_importance import normalize_importance, prompt_order


def test_normalize_importance_defaults_unknown_values_to_normal():
    assert normalize_importance("critical") == "critical"
    assert normalize_importance("unknown") == "normal"
    assert normalize_importance(None) == "normal"


def test_prompt_order_prioritizes_unseen_then_importance():
    rows = [
        {"id": "seen-critical", "importance": "critical", "vist_at": "seen"},
        {"id": "unseen-low", "importance": "low", "vist_at": ""},
        {"id": "unseen-high", "importance": "high", "vist_at": ""},
    ]

    assert [row["id"] for row in sorted(rows, key=prompt_order)] == [
        "unseen-high",
        "unseen-low",
        "seen-critical",
    ]
