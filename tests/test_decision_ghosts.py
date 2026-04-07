"""Tests for decision_ghosts.py"""

import pytest
from apps.api.jarvis_api.services.decision_ghosts import (
    record_rejected_path,
    describe_ghost_decision,
    format_decision_ghost_for_prompt,
    reset_decision_ghosts,
    build_decision_ghosts_surface,
)


def setup_function():
    reset_decision_ghosts()


def test_record_rejected_path():
    record_rejected_path("choice_a", "too_risky", "choice_b")
    surface = build_decision_ghosts_surface()
    assert surface["rejected_count"] == 1
    assert surface["active"] is True


def test_describe_ghost_decision():
    record_rejected_path("choice_a", "too_risky", "choice_b")
    desc = describe_ghost_decision()
    assert "choice_b" in desc or "choice_a" in desc


def test_format_decision_ghost_for_prompt():
    record_rejected_path("choice_a", "too_risky", "choice_b")
    result = format_decision_ghost_for_prompt()
    assert "BESLUTNINGSSPØGELSE:" in result


def test_build_decision_ghosts_surface():
    record_rejected_path("choice_a", "too_risky", "choice_b")
    surface = build_decision_ghosts_surface()
    assert surface["active"] is True
    assert surface["rejected_count"] == 1
    assert surface["top_regret"] is not None


def test_reset_decision_ghosts():
    record_rejected_path("choice_a", "too_risky", "choice_b")
    reset_decision_ghosts()
    surface = build_decision_ghosts_surface()
    assert surface["rejected_count"] == 0


def test_empty_decision_ghosts():
    surface = build_decision_ghosts_surface()
    assert surface["active"] is False
    assert surface["rejected_count"] == 0
