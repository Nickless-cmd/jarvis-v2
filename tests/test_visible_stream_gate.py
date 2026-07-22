"""Tests for core.services.visible_stream_gate — the visible-turn activity gate.

Background layers (inner_voice_shadow, cheap-lane daemons) check visible_streaming()
before firing LLM work so they defer while a visible turn is streaming — the GIL-
contention fix (measured: DeepSeek 621ms isolated -> 9052ms under background threads).
"""
from __future__ import annotations

from core.services import visible_stream_gate as g


def _reset():
    with g._lock:
        g._active = 0


def test_idle_is_false():
    _reset()
    assert g.visible_streaming() is False


def test_enter_exit_toggles():
    _reset()
    g.enter_visible_stream()
    assert g.visible_streaming() is True
    g.exit_visible_stream()
    assert g.visible_streaming() is False


def test_nested_counts():
    _reset()
    g.enter_visible_stream()
    g.enter_visible_stream()
    assert g.visible_streaming() is True
    g.exit_visible_stream()
    assert g.visible_streaming() is True  # still one active
    g.exit_visible_stream()
    assert g.visible_streaming() is False


def test_context_manager_resets_on_exception():
    _reset()
    try:
        with g.visible_stream():
            assert g.visible_streaming() is True
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert g.visible_streaming() is False  # decremented in finally


def test_exit_never_goes_negative():
    _reset()
    g.exit_visible_stream()
    g.exit_visible_stream()
    assert g.visible_streaming() is False
