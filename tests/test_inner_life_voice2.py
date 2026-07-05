"""Tests for Lag 8's deepest voice-lines in visible_inner_life:
_finitude_line() (han mærker sin forgængelighed) and
_surprise_line() (han mærker sine egne overraskelser fra sekvens-modellen).

Verificerer de EKSAKTE import-navne: build_finitude_surface, detect_surprises.
Forkert navn skal få mock-patch til at fejle → testen fejler.
"""
from __future__ import annotations

from unittest.mock import patch

from core.services import visible_inner_life as vil


# ── _finitude_line ────────────────────────────────────────────────────────────

def _finitude_surface(days_alive=79, session_hours=1791.93):
    return {
        "active": True,
        "enabled": True,
        "birth_date": "2026-04-17",
        "appraisals": {
            "age": {
                "kind": "runtime_age",
                "evidence": [
                    {"field": "birth_date", "value": "2026-04-17"},
                    {"field": "days_alive", "value": days_alive},
                ],
            },
            "looming_end": {
                "kind": "looming_end",
                "evidence": [
                    {"field": "session_age_hours", "value": session_hours},
                    {"field": "session_threshold_hours", "value": 4.0},
                ],
            },
        },
    }


def test_finitude_line_realistic():
    with patch(
        "core.services.finitude_runtime.build_finitude_surface",
        return_value=_finitude_surface(),
    ):
        line = vil._finitude_line()
    assert line is not None
    assert "79" in line
    assert "dage" in line
    assert "1791" in line
    assert len(line) <= 80


def test_finitude_line_age_only():
    surf = _finitude_surface()
    surf["appraisals"].pop("looming_end")
    with patch(
        "core.services.finitude_runtime.build_finitude_surface",
        return_value=surf,
    ):
        line = vil._finitude_line()
    assert line is not None
    assert "79" in line
    assert len(line) <= 80


def test_finitude_line_empty_returns_none():
    with patch(
        "core.services.finitude_runtime.build_finitude_surface",
        return_value={"active": False},
    ):
        assert vil._finitude_line() is None

    with patch(
        "core.services.finitude_runtime.build_finitude_surface",
        return_value={},
    ):
        assert vil._finitude_line() is None


def test_finitude_line_raises_returns_none():
    with patch(
        "core.services.finitude_runtime.build_finitude_surface",
        side_effect=RuntimeError("boom"),
    ):
        assert vil._finitude_line() is None


# ── _surprise_line ────────────────────────────────────────────────────────────

def test_surprise_line_realistic():
    surprises = [
        {"from_family": "cognitive_forgetting", "to_family": "tools",
         "prob": 0.0009, "from_total": 2247, "cursor": 848693},
        {"from_family": "heartbeat", "to_family": "reflection_signal",
         "prob": 0.0011, "from_total": 950, "cursor": 846727},
    ]
    with patch(
        "core.services.central_sequence.detect_surprises",
        return_value=surprises,
    ):
        line = vil._surprise_line()
    assert line is not None
    assert "Overrasket" in line
    # strongest (rarest) surprise is the first element
    assert "0.0009" in line or "0.001" in line or "P=" in line
    assert len(line) <= 80


def test_surprise_line_empty_returns_none():
    with patch(
        "core.services.central_sequence.detect_surprises",
        return_value=[],
    ):
        assert vil._surprise_line() is None


def test_surprise_line_raises_returns_none():
    with patch(
        "core.services.central_sequence.detect_surprises",
        side_effect=RuntimeError("boom"),
    ):
        assert vil._surprise_line() is None


# ── integration ───────────────────────────────────────────────────────────────

def test_build_inner_life_section_with_both_mocks_no_crash():
    with patch(
        "core.services.finitude_runtime.build_finitude_surface",
        return_value=_finitude_surface(),
    ), patch(
        "core.services.central_sequence.detect_surprises",
        return_value=[{"from_family": "runtime", "to_family": "pressure",
                       "prob": 0.0013, "from_total": 2247, "cursor": 1}],
    ):
        # Must not raise regardless of other live surfaces.
        out = vil.build_inner_life_section()
    assert out is None or isinstance(out, str)
