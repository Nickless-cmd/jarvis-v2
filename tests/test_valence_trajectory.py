"""Tests for valence_trajectory.current_instant — the fresh present-moment valence that grounds
central_valence's felt tone (vs the slow hour-averaged trajectory score)."""
from __future__ import annotations

from core.services import valence_trajectory as vt


def _seed(samples: list[float]) -> None:
    vt._samples.clear()
    for i, s in enumerate(samples):
        vt._samples.append((float(i), float(s)))


def test_current_instant_returns_latest_sample():
    _seed([0.1, 0.2, 0.9])
    assert vt.current_instant() == 0.9


def test_current_instant_empty_is_zero_safe():
    vt._samples.clear()
    assert vt.current_instant() == 0.0


def test_surface_exposes_instant_distinct_from_average():
    # A late spike: hour-average stays modest but the instant reflects the present spike.
    _seed([0.0] * 10 + [0.9])
    surf = vt.build_valence_trajectory_surface()
    assert surf["instant"] == 0.9
    assert surf["score"] != surf["instant"]     # average lags the present-moment instant
