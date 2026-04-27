"""Unit tests for tool_pattern_miner."""
from __future__ import annotations

from unittest.mock import patch

from core.services.tool_pattern_miner import (
    _extract_sequences,
    find_candidate_composites,
    composite_candidates_section,
)


def _inv(tool: str, session_id: str = "s1"):
    return {"tool": tool, "ts": "2026-04-27T08:00:00Z", "session_id": session_id}


def test_extract_sequences_finds_repeating_pair():
    invs = [_inv("a"), _inv("b"), _inv("c"), _inv("a"), _inv("b"), _inv("c")]
    seqs = _extract_sequences(invs, min_len=2, max_len=3)
    assert ("a", "b") in seqs
    assert seqs[("a", "b")] == 2


def test_extract_sequences_skips_same_tool_sequences():
    invs = [_inv("x"), _inv("x"), _inv("x")]
    seqs = _extract_sequences(invs, min_len=2, max_len=3)
    # Should NOT count (x, x) — that's looping, not pattern
    assert seqs == {} or all(len(set(s)) > 1 for s in seqs.keys())


def test_extract_sequences_groups_by_session():
    invs = [
        _inv("a", "s1"), _inv("b", "s1"),
        _inv("b", "s2"), _inv("a", "s2"),
    ]
    seqs = _extract_sequences(invs, min_len=2, max_len=2)
    # Each session has its own sequence
    assert ("a", "b") in seqs
    assert ("b", "a") in seqs


def test_find_candidates_returns_empty_when_no_invocations():
    with patch("core.services.tool_pattern_miner._recent_tool_invocations", return_value=[]):
        result = find_candidate_composites()
    assert result["candidates"] == []
    assert result["total_invocations"] == 0


def test_find_candidates_filters_below_min_repeat():
    # 2 occurrences only — below default min_repeat=3
    invs = [_inv("a"), _inv("b"), _inv("a"), _inv("b")]
    with patch("core.services.tool_pattern_miner._recent_tool_invocations", return_value=invs):
        result = find_candidate_composites(min_repeat=3)
    assert result["candidates"] == []


def test_find_candidates_returns_ranked_by_score():
    # (a,b) appears 4x, (c,d) appears 3x — both qualify, (a,b) ranks higher
    invs = (
        [_inv(t) for t in ["a", "b", "a", "b", "a", "b", "a", "b"]]
        + [_inv(t, "s2") for t in ["c", "d", "c", "d", "c", "d"]]
    )
    with patch("core.services.tool_pattern_miner._recent_tool_invocations", return_value=invs):
        result = find_candidate_composites(min_repeat=3)
    candidates = result["candidates"]
    assert len(candidates) >= 2
    # First candidate has higher score than later ones
    assert candidates[0]["score"] >= candidates[1]["score"]


def test_section_returns_none_with_no_candidates():
    with patch("core.services.tool_pattern_miner.find_candidate_composites",
               return_value={"candidates": []}):
        assert composite_candidates_section() is None


def test_section_lists_top_candidates():
    with patch("core.services.tool_pattern_miner.find_candidate_composites", return_value={
        "candidates": [
            {"sequence": ["read", "write"], "count": 5, "score": 10, "suggested_name": "x"},
            {"sequence": ["bash", "verify"], "count": 4, "score": 8, "suggested_name": "y"},
        ],
    }):
        section = composite_candidates_section()
    assert section is not None
    assert "read → write" in section
    assert "bash → verify" in section
    assert "5×" in section
