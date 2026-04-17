"""Tests for emergent_bridge.py"""
import pytest

from core.services.emergent_bridge import (
    should_influence_prompt,
    get_influencing_emergents,
    format_emergent_for_prompt,
    reset_emergent_bridge,
    get_emergent_bridge_state,
    build_emergent_bridge_surface,
)


def setup_function():
    reset_emergent_bridge()


def test_should_influence_prompt_no_signals():
    result = should_influence_prompt()
    assert result is False


def test_get_influencing_emergents_empty():
    result = get_influencing_emergents()
    assert result == []


def test_format_emergent_for_prompt_empty():
    result = format_emergent_for_prompt()
    assert result == ""


def test_get_emergent_bridge_state():
    state = get_emergent_bridge_state()
    assert "influence_count" in state
    assert "can_influence" in state


def test_build_emergent_bridge_surface():
    surface = build_emergent_bridge_surface()
    assert "active" in surface
    assert "influence_count" in surface
    assert "summary" in surface


def test_reset_emergent_bridge():
    reset_emergent_bridge()
    state = get_emergent_bridge_state()
    assert state["influence_count"] == 0
