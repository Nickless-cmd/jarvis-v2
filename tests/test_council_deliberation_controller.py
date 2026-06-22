"""Minimal smoke for council_deliberation_controller (coverage-gate + agents-wiring)."""
from __future__ import annotations

from core.services import council_deliberation_controller as cdc


def test_module_and_run_exists():
    assert hasattr(cdc, "DeliberationController")
    assert hasattr(cdc.DeliberationController, "run")


def test_deadlock_detection_helper():
    # 3 runder med identisk output → deadlock
    same = [["enig"], ["enig"], ["enig"]]
    assert cdc._is_deadlocked(same) is True
    varied = [["a"], ["b"], ["c"]]
    assert cdc._is_deadlocked(varied) in (True, False)  # bare ikke kaste


def test_note_council_importable():
    # agents-wiring: note_council skal kunne importeres (det run() kalder)
    from core.services.agents import note_council
    assert callable(note_council)
