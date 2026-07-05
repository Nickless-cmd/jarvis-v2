"""Tests for unified_recall.py — krydsreference mellem hukommelsessystemer."""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _isolate():
    """Ensure no real memory systems are called."""
    with patch("core.services.unified_recall._safe_search_memory", return_value=[]), \
         patch("core.services.unified_recall._safe_search_brain", return_value=[]), \
         patch("core.services.unified_recall._safe_recall_memories", return_value=[]):
        yield


# ---------------------------------------------------------------------------
# unified_recall
# ---------------------------------------------------------------------------

class TestUnifiedRecall:

    def test_empty_query_returns_empty(self):
        from core.services.unified_recall import unified_recall
        assert unified_recall("") == {}
        assert unified_recall("   ") == {}

    def test_finds_in_memory_md_only(self):
        from core.services.unified_recall import unified_recall
        with patch("core.services.unified_recall._safe_search_memory",
                    return_value=[{"title": "Bjørn", "content": "Bjørn er min bruger"}]):
            result = unified_recall("Bjørn")
            assert "Bjørn" in result
            assert result["Bjørn"]["memory_md"] is True
            assert result["Bjørn"]["brain"] is False
            assert result["Bjørn"]["arkiv"] is False

    def test_finds_in_brain_only(self):
        from core.services.unified_recall import unified_recall
        with patch("core.services.unified_recall._safe_search_brain",
                    return_value=[{"title": "Centralen", "content": "Mit nervesystem"}]):
            result = unified_recall("Centralen")
            assert "Centralen" in result
            assert result["Centralen"]["brain"] is True
            assert result["Centralen"]["memory_md"] is False

    def test_finds_in_arkiv_only(self):
        from core.services.unified_recall import unified_recall
        with patch("core.services.unified_recall._safe_recall_memories",
                    return_value=[{"title": "Eftermiddagslys", "content": "Lys over skrivebordet"}]):
            result = unified_recall("lys")
            assert any("Eftermiddagslys" in k or "lys" in k.lower() for k in result)

    def test_cross_reference_multiple_systems(self):
        from core.services.unified_recall import unified_recall
        with patch("core.services.unified_recall._safe_search_memory",
                    return_value=[{"title": "Bjørn", "content": "Bjørn er min bruger"}]), \
             patch("core.services.unified_recall._safe_search_brain",
                    return_value=[{"title": "Bjørn", "content": "Bjørn relation"}]):
            result = unified_recall("Bjørn")
            assert "Bjørn" in result
            assert result["Bjørn"]["memory_md"] is True
            assert result["Bjørn"]["brain"] is True
            assert result["Bjørn"]["arkiv"] is False

    def test_system_failure_graceful(self):
        """If one system fails, others still return results."""
        from core.services.unified_recall import unified_recall
        with patch("core.services.unified_recall._safe_search_memory",
                    return_value=[{"title": "Test", "content": "data"}]), \
             patch("core.services.unified_recall._safe_search_brain",
                    return_value=[]):  # brain returns empty (simulating failure)
            result = unified_recall("Test")
            assert "Test" in result
            assert result["Test"]["memory_md"] is True
            assert result["Test"]["brain"] is False

    def test_long_query_truncated(self):
        from core.services.unified_recall import unified_recall
        long_query = "x" * 300
        # Should not crash — just truncate
        result = unified_recall(long_query)
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# get_unified_recall_hints
# ---------------------------------------------------------------------------

class TestUnifiedRecallHints:

    def test_no_query_returns_empty(self):
        from core.services.unified_recall import get_unified_recall_hints
        assert get_unified_recall_hints(None) == []
        assert get_unified_recall_hints("") == []
        assert get_unified_recall_hints("   ") == []

    def test_hint_format(self):
        from core.services.unified_recall import get_unified_recall_hints
        with patch("core.services.unified_recall._safe_search_memory",
                    return_value=[{"title": "Bjørn", "content": "data"}]), \
             patch("core.services.unified_recall._safe_search_brain",
                    return_value=[{"title": "Bjørn", "content": "data"}]):
            hints = get_unified_recall_hints("Bjørn")
            assert len(hints) >= 1
            assert "Bjørn" in hints[0]
            assert "MEMORY" in hints[0] or "brain" in hints[0]

    def test_hint_max_length(self):
        from core.services.unified_recall import get_unified_recall_hints
        with patch("core.services.unified_recall._safe_search_memory",
                    return_value=[{"title": "A" * 100, "content": "data"}]):
            hints = get_unified_recall_hints("test")
            for hint in hints:
                assert len(hint) <= 80

    def test_hint_limit(self):
        from core.services.unified_recall import get_unified_recall_hints
        with patch("core.services.unified_recall._safe_search_memory",
                    return_value=[{"title": f"Topic{i}", "content": "data"} for i in range(10)]):
            hints = get_unified_recall_hints("test", limit=2)
            assert len(hints) <= 2


# ---------------------------------------------------------------------------
# _extract_topic
# ---------------------------------------------------------------------------

class TestExtractTopic:

    def test_title_preferred(self):
        from core.services.unified_recall import _extract_topic
        assert _extract_topic({"title": "Bjørn", "content": "lang tekst"}) == "Bjørn"

    def test_heading_fallback(self):
        from core.services.unified_recall import _extract_topic
        assert _extract_topic({"heading": "Centralen"}) == "Centralen"

    def test_content_truncation(self):
        from core.services.unified_recall import _extract_topic
        result = _extract_topic({"content": "x" * 100})
        assert len(result) <= 40

    def test_unknown_fallback(self):
        from core.services.unified_recall import _extract_topic
        assert _extract_topic({}) == "ukendt"