"""Tests for initiative_accumulator.py"""
import pytest
from datetime import timedelta

from core.services.initiative_accumulator import (
    accumulate_wants,
    get_top_want,
    get_wants_by_type,
    format_wants_for_prompt,
    clear_wants_by_type,
    reset_initiative_accumulator,
    get_initiative_accumulator_state,
    build_initiative_accumulator_surface,
)


def setup_function():
    reset_initiative_accumulator()


def test_accumulate_wants_short_duration():
    result = accumulate_wants(timedelta(minutes=1))
    assert result["accumulated"] == 0


def test_accumulate_wants_dreaming_phase():
    result = accumulate_wants(timedelta(minutes=5))
    assert "life_phase" in result
    assert "total_wants" in result


def test_get_top_want_none():
    want = get_top_want()
    assert want is None


def test_format_wants_for_prompt_empty():
    result = format_wants_for_prompt()
    assert result == ""


def test_get_initiative_accumulator_state():
    state = get_initiative_accumulator_state()
    assert "want_count" in state
    assert "top_want" in state


def test_build_initiative_accumulator_surface():
    surface = build_initiative_accumulator_surface()
    assert "active" in surface
    assert "want_count" in surface


def test_reset_initiative_accumulator():
    accumulate_wants(timedelta(minutes=5))
    reset_initiative_accumulator()
    state = get_initiative_accumulator_state()
    assert state["want_count"] == 0


def test_clear_wants_by_type():
    accumulate_wants(timedelta(minutes=5))
    clear_wants_by_type("clarity")
    state = get_initiative_accumulator_state()
    assert state["want_count"] == 0
