"""Tests for continuity.py — focus on cache-stability of mood/activity output.

These tests verify that the formatted continuity block stays stable under
small mood drift, which is the property that lets DeepSeek's prompt cache
survive between consecutive chat turns. See 2026-05-22 commit message.
"""
from core.services.continuity import build_wake_up_block


def _capsule(mood: dict | None = None, recent: dict | None = None) -> dict:
    return {
        "wake_provenance": {"hours_since_last_session": 0.0},
        "mood": mood or {},
        "attention": {"current_focus": "test focus"},
        "relation": {},
        "somatic": {},
        "goals": {},
        "recent_activity": recent or {},
    }


def test_small_mood_drift_does_not_change_output():
    """0.50 vs 0.49 must produce identical output (cache-stable)."""
    a = build_wake_up_block(_capsule(mood={
        "curiosity": 0.50, "fatigue": 0.10,
        "frustration": 0.00, "confidence": 0.50,
    }))
    b = build_wake_up_block(_capsule(mood={
        "curiosity": 0.49, "fatigue": 0.11,
        "frustration": 0.00, "confidence": 0.51,
    }))
    assert a == b, f"small drift broke equality:\nA={a}\nB={b}"


def test_large_mood_change_does_change_output():
    """0.5 → 0.8 must move bucket and be visible."""
    a = build_wake_up_block(_capsule(mood={"curiosity": 0.50}))
    b = build_wake_up_block(_capsule(mood={"curiosity": 0.80}))
    assert a != b
    assert "curiosity=0.5" in a
    assert "curiosity=0.8" in b


def test_mood_one_decimal_format():
    """Bucketed mood uses one decimal (e.g. 0.5 not 0.50)."""
    out = build_wake_up_block(_capsule(mood={
        "curiosity": 0.5, "fatigue": 0.0,
        "frustration": 0.0, "confidence": 0.5,
    }))
    assert "curiosity=0.5" in out
    # No two-decimal formatting
    assert "curiosity=0.50" not in out


def test_last_activity_and_exchange_not_present():
    """These were removed — they duplicated transcript content and churned."""
    out = build_wake_up_block(_capsule(
        mood={"curiosity": 0.5},
        recent={
            "last_tool_result_summary": "ran tool X with result Y",
            "last_5_messages": [
                {"role": "user", "content": "first message"},
                {"role": "assistant", "content": "first reply"},
            ],
        },
    ))
    assert "Last activity:" not in out
    assert "Last exchange:" not in out
    assert "ran tool X" not in out
    assert "first message" not in out


def test_none_mood_value_handled():
    """Missing mood values should be skipped gracefully."""
    out = build_wake_up_block(_capsule(mood={
        "curiosity": None, "fatigue": 0.3,
    }))
    assert "curiosity" not in out
    assert "fatigue=0.3" in out
