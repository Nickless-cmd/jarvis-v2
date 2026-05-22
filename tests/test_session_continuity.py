"""Tests for session_continuity.py — focus on cache-stability invariants.

2026-05-22 (Claude): get_echo_signals_for_prompt now buckets counts to
nearest 10 so small per-turn increments don't break the DeepSeek prompt
cache. Live diff found "×94" → "×95" between consecutive calls broke
the prefix at byte ~10,749.
"""
from unittest.mock import patch


def _mock_themes(items):
    """Patch detect_echo_themes to return a controlled list."""
    return patch(
        "core.services.session_continuity.detect_echo_themes",
        return_value=items,
    )


def test_count_bucketing_to_nearest_ten():
    from core.services.session_continuity import get_echo_signals_for_prompt
    with _mock_themes([
        {"theme": "fokus", "count": 93},
        {"theme": "rytme", "count": 47},
        {"theme": "pres", "count": 12},
    ]):
        out = get_echo_signals_for_prompt()
    assert "fokus (×90+)" in out
    assert "rytme (×40+)" in out
    assert "pres (×10+)" in out


def test_small_count_drift_does_not_change_output():
    """93 vs 94 must produce identical output (both → 90+)."""
    from core.services.session_continuity import get_echo_signals_for_prompt
    with _mock_themes([{"theme": "loop", "count": 93}]):
        a = get_echo_signals_for_prompt()
    with _mock_themes([{"theme": "loop", "count": 94}]):
        b = get_echo_signals_for_prompt()
    assert a == b
    assert "loop (×90+)" in a


def test_crossing_bucket_does_change_output():
    """89 vs 90 must move bucket and reflect that."""
    from core.services.session_continuity import get_echo_signals_for_prompt
    with _mock_themes([{"theme": "loop", "count": 89}]):
        a = get_echo_signals_for_prompt()
    with _mock_themes([{"theme": "loop", "count": 90}]):
        b = get_echo_signals_for_prompt()
    assert a != b
    assert "loop (×80+)" in a
    assert "loop (×90+)" in b


def test_no_themes_returns_empty():
    from core.services.session_continuity import get_echo_signals_for_prompt
    with _mock_themes([]):
        assert get_echo_signals_for_prompt() == ""
