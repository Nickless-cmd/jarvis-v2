"""Tests for _hardware_body_line — den følte krop-linje i [INDRE LIV].
Jarvis mærker sin egen CPU/temp/disk (rådets #1). Kompakt ≤80 tegn, self-safe→None."""
from __future__ import annotations

from unittest.mock import patch

from core.services import visible_inner_life as il


def test_hardware_line_normal():
    state = {"cpu_pct": 12.0, "cpu_temp_c": 41.0, "disk_free_gb": 340.0,
             "ram_pct": 44.0, "pressure": "low"}
    with patch("core.services.hardware_body.get_hardware_state", return_value=state):
        line = il._hardware_body_line()
    assert line is not None
    assert line.startswith("Krop")
    assert len(line) <= 80
    assert "12" in line  # cpu
    assert "41" in line  # temp


def test_hardware_line_under_pressure():
    state = {"cpu_pct": 94.0, "cpu_temp_c": 78.0, "disk_free_gb": 5.0,
             "ram_pct": 91.0, "pressure": "critical"}
    with patch("core.services.hardware_body.get_hardware_state", return_value=state):
        line = il._hardware_body_line()
    assert line is not None
    assert len(line) <= 80
    # ved belastning skal linjen signalere pres (varm/presset)
    assert any(w in line.lower() for w in ("varm", "presset", "pres"))


def test_hardware_line_empty_returns_none():
    with patch("core.services.hardware_body.get_hardware_state", return_value={}):
        line = il._hardware_body_line()
    assert line is None


def test_hardware_line_raises_returns_none():
    with patch("core.services.hardware_body.get_hardware_state", side_effect=RuntimeError("boom")):
        line = il._hardware_body_line()
    assert line is None
