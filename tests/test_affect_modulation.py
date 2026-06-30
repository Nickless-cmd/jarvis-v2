"""Tests for the condensed affect-modulation section (2026-06-22 round 3)."""
from unittest.mock import patch

from core.services import affect_modulation as am


def test_section_is_compact_single_line():
    with patch.object(
        am, "compute_affect_modulated_params",
        return_value={"max_tool_calls_per_turn": 36},
    ), patch.dict(am.DEFAULTS, {"max_tool_calls_per_turn": 40}, clear=False):
        out = am.affect_modulation_section()
    assert out is not None
    assert "Affect-sat" in out
    assert "max_tool_calls_per_turn=36" in out
    # the verbose "follow as a standing order" preamble is gone
    assert "standing order" not in out
    assert out.count("\n") == 0  # one compact line


def test_section_none_without_overrides():
    with patch.object(am, "compute_affect_modulated_params", return_value={}):
        assert am.affect_modulation_section() is None


def test_section_none_when_nothing_changed():
    with patch.object(
        am, "compute_affect_modulated_params",
        return_value={"max_tool_calls_per_turn": 40},
    ), patch.dict(am.DEFAULTS, {"max_tool_calls_per_turn": 40}, clear=False):
        assert am.affect_modulation_section() is None


def test_default_max_rounds_is_sane_backstop():
    """2026-06-30 (#4): default-cap sænket 100 → 30. Loop-gaten + syntese-pausen
    afslutter normale runs langt tidligere; dette er kun et backstop mod
    runaway-spiraler. Må aldrig krybe tilbage mod 100."""
    budget = am.compute_agentic_loop_budget()
    assert budget["max_rounds"] == 30


def test_resume_and_pressure_cap_below_default():
    """Resume- og pres-modulering skal stadig sænke UNDER default (ikke hæve)."""
    resume = am.compute_agentic_loop_budget(resume_context=True)
    assert resume["max_rounds"] <= 30
