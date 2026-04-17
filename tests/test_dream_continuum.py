"""Tests for dream_continuum.py"""
import pytest
from datetime import timedelta

from core.services.dream_continuum import (
    evolve_dreams,
    get_dream_thoughts,
    get_top_dream_thought,
    format_dreams_for_prompt,
    get_dream_maturity,
    reset_dream_continuum,
    build_dream_continuum_surface,
    DreamThought,
)
from core.services.dream_carry_over import (
    adopt_dream,
    _ACTIVE_DREAMS,
    _DREAM_ARCHIVE,
)


def setup_function():
    reset_dream_continuum()
    _ACTIVE_DREAMS.clear()
    _DREAM_ARCHIVE.clear()


def test_evolve_dreams_no_dreams():
    result = evolve_dreams(timedelta(minutes=5))
    assert result["evolved_count"] == 0


def test_evolve_dreams_with_dream():
    adopt_dream(dream_id="test-dream-1", content="En drøm om fremtiden")
    result = evolve_dreams(timedelta(minutes=5))
    assert result["evolved_count"] >= 1


def test_get_dream_maturity():
    adopt_dream(dream_id="test-dream-2", content="Test drøm")
    evolve_dreams(timedelta(minutes=5))
    maturity = get_dream_maturity("test-dream-2")
    assert maturity > 0


def test_get_dream_thoughts():
    adopt_dream(dream_id="test-dream-3", content="Test drøm med tanker")
    evolve_dreams(timedelta(minutes=5))
    thoughts = get_dream_thoughts("test-dream-3")
    assert len(thoughts) >= 1


def test_get_top_dream_thought():
    adopt_dream(dream_id="test-dream-4", content="Vigtig drøm")
    evolve_dreams(timedelta(minutes=5))
    top = get_top_dream_thought()
    assert top is not None
    assert len(top) > 0


def test_format_dreams_for_prompt_with_dream():
    adopt_dream(dream_id="test-dream-5", content="En test drøm")
    result = format_dreams_for_prompt()
    assert "DREAM:" in result or "DRØM-TANKER:" in result


def test_build_dream_continuum_surface():
    adopt_dream(dream_id="test-dream-6", content="En test drøm")
    surface = build_dream_continuum_surface()
    assert "dream_count" in surface
    assert "maturity_levels" in surface


def test_reset_dream_continuum():
    adopt_dream(dream_id="test-dream-7", content="Drøm der slettes")
    reset_dream_continuum()
    surface = build_dream_continuum_surface()
    assert surface["dream_count"] >= 0
