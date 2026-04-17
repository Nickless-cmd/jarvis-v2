"""Tests for parallel_selves.py"""

import pytest
from core.services.parallel_selves import (
    get_active_self,
    set_active_self,
    describe_self_plural,
    format_self_for_prompt,
    build_parallel_selves_surface,
)


def test_get_active_self():
    self_type = get_active_self()
    assert self_type in ["curious", "cautious", "playful", "deep"]


def test_set_active_self():
    set_active_self("cautious")
    assert get_active_self() == "cautious"


def test_set_active_self_invalid():
    set_active_self("invalid")
    assert get_active_self() != "invalid"


def test_describe_self_plural():
    desc = describe_self_plural()
    assert isinstance(desc, str)
    assert len(desc) > 0


def test_format_self_for_prompt():
    result = format_self_for_prompt()
    assert "SELV:" in result


def test_build_parallel_selves_surface():
    surface = build_parallel_selves_surface()
    assert surface["active"] is True
    assert "current_self" in surface
    assert "selves" in surface
