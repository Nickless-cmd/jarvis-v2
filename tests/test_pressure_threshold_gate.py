"""Tests for pressure_threshold_gate — tærskler + Proactivity-cluster instrument."""
from __future__ import annotations

from core.services import pressure_threshold_gate as ptg


def test_direction_thresholds_present_and_bounded():
    assert ptg._DIRECTION_THRESHOLDS  # ikke tom
    for direction, val in ptg._DIRECTION_THRESHOLDS.items():
        assert 0.0 < float(val) <= 1.0, f"{direction} tærskel uden for [0,1]"


def test_run_threshold_gate_tick_is_self_safe():
    # tick må aldrig kaste (best-effort daemon-nerve); returnerer en dict
    out = ptg.run_threshold_gate_tick()
    assert isinstance(out, dict)
