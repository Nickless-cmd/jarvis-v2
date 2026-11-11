"""Vagt: humør uden hændelser må ikke svinge på grund af tid alene.

Før fixet var værdien sin(phase_offset) + nudge, så et hændelsesløst humør
gik euphoric -> distressed inden for én ~63-min cyklus.
"""

from __future__ import annotations

import math

import pytest

from core.services import mood_oscillator as m


@pytest.fixture(autouse=True)
def _clean():
    m.reset_mood_oscillator()
    yield
    m.reset_mood_oscillator()


def test_no_events_time_alone_cannot_swing_mood():
    seen = set()
    value_min, value_max = 1.0, -1.0
    # to fulde gamle cyklusser (~63 min) i 30-sekunders skridt
    for _ in range(0, 2 * 3800, 30):
        m.tick(30.0)
        seen.add(m.get_current_mood())
        v = m._combined_value()
        value_min, value_max = min(value_min, v), max(value_max, v)
    assert seen == {"neutral"}, f"tid alene flyttede humøret: {seen}"
    assert value_max - value_min < 0.05


def test_known_bad_phase_from_production_is_neutral_without_events():
    # Persisteret tilstand 11/11: phase_offset=7137.05, nudge=0 -> sin=-0.60
    m._phase_offset = 7137.052866154887
    m._mood_nudge = 0.0
    assert abs(math.sin(m._phase_offset)) > 0.5  # sinus ville have givet udslag
    assert m.get_current_mood() == "neutral"


def test_events_still_move_mood_and_decay_back():
    m.apply_bump(-0.9, "test")
    assert m.get_current_mood() == "distressed"
    m.tick(30.0 * 100000)  # lang stilhed => henfaldet
    assert m.get_current_mood() == "neutral"


def test_phase_offset_still_reported_for_backcompat():
    r = m.tick(60.0)
    assert "phase_offset" in r and r["phase_offset"] > 0
