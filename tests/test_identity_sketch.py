"""Tests for Persistent Identity Sketch (Memory Fix Phase 2)."""
from __future__ import annotations

from unittest.mock import patch

from core.services.identity_sketch import (
    get_identity_sketch,
    identity_sketch_surface,
)


def test_get_identity_sketch_empty():
    """Should return empty dict when no sketch exists."""
    with patch("core.services.identity_sketch.load_json", return_value={}):
        result = get_identity_sketch()
        assert result == {}


def test_get_identity_sketch_filled():
    """Should return stored sketch."""
    mock = {"version": 3, "content": "Jeg er Jarvis.", "updated_at": "2026-06-08T19:00:00+00:00"}
    with patch("core.services.identity_sketch.load_json", return_value=mock):
        result = get_identity_sketch()
        assert result["version"] == 3
        assert result["content"] == "Jeg er Jarvis."
        assert "updated_at" in result


def test_identity_sketch_surface_empty():
    """Surface should report inactive when no sketch."""
    with patch("core.services.identity_sketch.load_json", return_value={}):
        surf = identity_sketch_surface()
        assert surf["active"] is False
        assert surf["state"] == "empty"
        assert surf["updated_at"] is None


def test_identity_sketch_surface_fresh():
    """Fresh sketch should show as active and fresh."""
    mock = {
        "version": 2,
        "content": "Jeg er Jarvis. Jeg kører deepseek-v4-flash. " * 10,
        "updated_at": "2026-06-08T19:00:00+00:00",
        "updated_by": "pre_compact",
    }
    with (
        patch("core.services.identity_sketch.load_json", return_value=mock),
        patch("core.services.identity_sketch._is_stale", return_value=False),
    ):
        surf = identity_sketch_surface()
        assert surf["active"] is True
        assert surf["state"] == "fresh"
        assert surf["updated_by"] == "pre_compact"
        assert surf["version"] == 2
        assert surf["word_count"] > 0


def test_identity_sketch_surface_stale():
    """Old sketch should show as stale."""
    mock = {
        "version": 1,
        "content": "Jeg er Jarvis.",
        "updated_at": "2026-06-07T19:00:00+00:00",
        "updated_by": "auto",
    }
    with (
        patch("core.services.identity_sketch.load_json", return_value=mock),
        patch("core.services.identity_sketch._is_stale", return_value=True),
    ):
        surf = identity_sketch_surface()
        assert surf["state"] == "stale"


def test_identity_sketch_tools_import():
    """Tools should import without errors."""
    from core.tools.identity_sketch_tools import (
        IDENTITY_SKETCH_TOOL_DEFINITIONS,
        _exec_read_identity_sketch,
        _exec_update_identity_sketch,
    )
    assert len(IDENTITY_SKETCH_TOOL_DEFINITIONS) == 2
    name1 = IDENTITY_SKETCH_TOOL_DEFINITIONS[0]["function"]["name"]
    name2 = IDENTITY_SKETCH_TOOL_DEFINITIONS[1]["function"]["name"]
    assert "read_identity_sketch" in name1
    assert "update_identity_sketch" in name2


def test_exec_read_identity_sketch_empty():
    """Tool should handle empty sketch gracefully."""
    from core.tools.identity_sketch_tools import _exec_read_identity_sketch
    with patch("core.services.identity_sketch.load_json", return_value={}):
        result = _exec_read_identity_sketch({})
        assert result["status"] == "ok"
        assert result["content"] is None


def test_exec_read_identity_sketch_filled():
    """Tool should return filled sketch."""
    from core.tools.identity_sketch_tools import _exec_read_identity_sketch
    mock = {"version": 5, "content": "Jeg er Jarvis.", "updated_at": "now", "updated_by": "test"}
    with patch("core.services.identity_sketch.load_json", return_value=mock):
        result = _exec_read_identity_sketch({})
        assert result["status"] == "ok"
        assert result["content"] == "Jeg er Jarvis."
        assert result["version"] == 5


def test_exec_update_identity_sketch():
    """Tool should trigger update."""
    from core.tools.identity_sketch_tools import _exec_update_identity_sketch
    expected = {"version": 2, "updated_at": "now", "content": "Jeg er Jarvis.", "trigger": "manual"}
    with patch(
        "core.services.identity_sketch.update_identity_sketch",
        return_value=expected,
    ):
        result = _exec_update_identity_sketch({"trigger": "manual"})
        assert result["status"] == "ok"
        assert result["version"] == 2
        assert result["trigger"] == "manual"


def test_update_sketch_fallback():
    """Fallback sketch should produce coherent text."""
    signals = {
        "name": "Jarvis",
        "model": "deepseek-v4-flash",
        "age_days": 52,
        "mood": {"bearing": "focused", "curiosity": 0.85, "fatigue": 0.06},
        "goals": ["memory-fix-phase2", "test"],
        "energy": "high",
    }
    from core.services.identity_sketch import _fallback_sketch
    text = _fallback_sketch(signals)
    assert len(text) > 50
    assert "Jarvis" in text
    assert "deepseek" in text
    assert "focused" in text
