"""Loop-liveness-synlighed for core/services/forgetting_runtime.py (dø-skjult-fix)."""
from __future__ import annotations
import importlib
from pathlib import Path


def test_imports():
    assert importlib.import_module("core.services.forgetting_runtime") is not None


def test_loop_error_reaches_central():
    src = Path("core/services/forgetting_runtime.py").read_text(encoding="utf-8")
    assert "observe_operational_liveness" in src, "loop-except skal nå Centralen"
