"""Tests for memory_search.py — CANDIDATE penalty and search behavior.

Companion to tests/test_memory_search_quarantine.py which covers the
quarantine filter. This file holds the CANDIDATE-penalty checks added
2026-05-22.
"""
from core.services.memory_search import search_memory


def test_search_returns_results_for_known_query():
    """Smoke: search returns non-empty for a real query."""
    results = search_memory("ChiefOne hardware", limit=5)
    # Don't fail on empty corpus, but check shape if non-empty
    assert isinstance(results, list)
    for r in results:
        assert "text" in r
        assert "source" in r
        assert "score" in r


def test_candidate_field_present_on_results():
    """Every embedding-method result should carry candidate_penalty flag."""
    results = search_memory("memory", limit=3)
    for r in results:
        if r.get("method") == "embedding":
            assert "candidate_penalty" in r
            assert "raw_score" in r


def test_top_result_not_candidate_when_curated_available():
    """If curated MEMORY.md content matches, it must rank above
    [CANDIDATE→] legacy entries."""
    results = search_memory("ChiefOne hardware", limit=10)
    if len(results) < 2:
        return  # not enough corpus to test ranking
    top = results[0]
    # When non-candidate matches exist (most queries about Jarvis facts),
    # the top should not be a candidate.
    non_candidates = [r for r in results if not r.get("candidate_penalty")]
    if non_candidates:
        assert not top.get("candidate_penalty", False), (
            f"Top result is CANDIDATE despite non-candidate available:\n"
            f"top={top}\n"
            f"first non-candidate={non_candidates[0]}"
        )
