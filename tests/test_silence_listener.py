"""Tests for silence_listener.py"""

import pytest
from core.services.silence_listener import (
    experience_silence,
    describe_silence,
    format_silence_for_prompt,
    reset_silence_listener,
    build_silence_listener_surface,
)


def setup_function():
    reset_silence_listener()


def test_experience_silence_short():
    experience_silence(30)
    surface = build_silence_listener_surface()
    assert surface["experience_count"] == 0


def test_experience_silence_long():
    experience_silence(120)
    surface = build_silence_listener_surface()
    assert surface["experience_count"] == 1
    assert surface["active"] is True


def test_describe_silence():
    experience_silence(90)
    desc = describe_silence()
    assert "stilhed" in desc


def test_format_silence_for_prompt():
    experience_silence(100)
    result = format_silence_for_prompt()
    assert "STILHED:" in result


def test_build_silence_listener_surface():
    experience_silence(70)
    surface = build_silence_listener_surface()
    assert "experience_count" in surface
    assert "latest" in surface


def test_reset_silence_listener():
    experience_silence(90)
    reset_silence_listener()
    surface = build_silence_listener_surface()
    assert surface["experience_count"] == 0


def test_empty_silence_listener():
    surface = build_silence_listener_surface()
    assert surface["active"] is False
    assert surface["experience_count"] == 0
