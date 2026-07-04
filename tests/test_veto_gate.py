"""Fail-open-synlighed for core/services/veto_gate.py (dø-skjult-fix)."""
from __future__ import annotations
import importlib
from pathlib import Path


def test_imports():
    assert importlib.import_module("core.services.veto_gate") is not None


def test_fail_open_is_visible():
    src = Path("core/services/veto_gate.py").read_text(encoding="utf-8")
    assert "record_central_incident" in src, "check_veto fail-open skal flagge til Centralen"
