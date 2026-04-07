"""Tests for mood_oscillator.py"""

import pytest
import math

from apps.api.jarvis_api.services.mood_oscillator import (
    tick,
    get_current_mood,
    get_mood_intensity,
    get_mood_description,
    format_mood_for_prompt,
    reset_mood_oscillator,
    build_mood_oscillator_surface,
)


def setup_function():
    reset_mood_oscillator()


def test_tick():
    result = tick(30.0)
    assert "phase_offset" in result
    assert "tick_count" in result
    assert result["tick_count"] == 1


def test_get_current_mood():
    tick(30.0)
    mood = get_current_mood()
    assert mood in ["euphoric", "content", "neutral", "melancholic", "distressed"]


def test_get_mood_intensity():
    tick(30.0)
    intensity = get_mood_intensity()
    assert 0 <= intensity <= 1


def test_get_mood_description():
    tick(30.0)
    desc = get_mood_description()
    assert isinstance(desc, str)
    assert len(desc) > 0


def test_format_mood_for_prompt():
    tick(30.0)
    result = format_mood_for_prompt()
    assert "STEMNING:" in result


def test_build_mood_oscillator_surface():
    tick(30.0)
    surface = build_mood_oscillator_surface()
    assert surface["active"] is True
    assert "current_mood" in surface
    assert "mood_description" in surface
    assert "summary" in surface


def test_reset_mood_oscillator():
    tick(30.0)
    reset_mood_oscillator()
    surface = build_mood_oscillator_surface()
    assert surface["tick_count"] == 0
