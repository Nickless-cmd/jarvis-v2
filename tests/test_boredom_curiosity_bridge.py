"""Tests for boredom_curiosity_bridge.py"""
import pytest
from datetime import timedelta

from apps.api.jarvis_api.services.boredom_curiosity_bridge import (
    add_boredom,
    should_spawn_curiosity,
    get_curiosity_prompt,
    get_active_curiosities,
    clear_curiosities,
    reset_boredom_curiosity_bridge,
    get_boredom_curiosity_state,
    build_boredom_curiosity_bridge_surface,
)


def setup_function():
    reset_boredom_curiosity_bridge()


def test_add_boredom_short():
    result = add_boredom(timedelta(minutes=1))
    assert "boredom_level" in result


def test_add_boredom_long():
    result = add_boredom(timedelta(minutes=30))
    assert result["boredom_level"] > 0


def test_should_spawn_curiosity_low():
    result = should_spawn_curiosity()
    assert result is False


def test_get_curiosity_prompt_empty():
    prompt = get_curiosity_prompt()
    assert prompt is None


def test_get_active_curiosities_empty():
    curiosities = get_active_curiosities()
    assert curiosities == []


def test_get_boredom_curiosity_state():
    state = get_boredom_curiosity_state()
    assert "boredom_level" in state
    assert "curiosity_count" in state
    assert "can_spawn" in state


def test_build_boredom_curiosity_bridge_surface():
    surface = build_boredom_curiosity_bridge_surface()
    assert "active" in surface
    assert "boredom_level" in surface
    assert "curiosity_count" in surface


def test_reset_boredom_curiosity_bridge():
    add_boredom(timedelta(minutes=30))
    reset_boredom_curiosity_bridge()
    state = get_boredom_curiosity_state()
    assert state["boredom_level"] == 0.0
    assert state["curiosity_count"] == 0


def test_clear_curiosities():
    add_boredom(timedelta(minutes=30))
    clear_curiosities()
    state = get_boredom_curiosity_state()
    assert state["curiosity_count"] == 0
