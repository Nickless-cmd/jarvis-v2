"""Tests for code_aesthetic_daemon.py — TDD first pass (L2)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


BUS_MOD = None
DB_MOD = None


import importlib
code_aesthetic_daemon = importlib.import_module(
    "core.services.code_aesthetic_daemon"
)


def _stub_modules():
    """Isolate the daemon's dependency bindings without touching shared
    ``core.*`` modules. See tests/test_absence_daemon.py for the rationale —
    the old sys.modules stub/pop dance leaked global state and poisoned
    unrelated tests in the full suite.
    """
    global BUS_MOD, DB_MOD
    mock_bus = MagicMock()
    mock_bus.publish = MagicMock()
    code_aesthetic_daemon.event_bus = mock_bus
    code_aesthetic_daemon.insert_private_brain_record = MagicMock()
    BUS_MOD = code_aesthetic_daemon
    DB_MOD = code_aesthetic_daemon


_stub_modules()


def _reset():
    code_aesthetic_daemon._last_tick_at = None
    code_aesthetic_daemon._latest_reflection = ""
    code_aesthetic_daemon._reflection_buffer = []


def test_cadence_blocks_within_week():
    """Second call within 7 days should not run."""
    _reset()
    code_aesthetic_daemon._last_tick_at = datetime.now(UTC)
    result = code_aesthetic_daemon.tick_code_aesthetic_daemon()
    assert result["generated"] is False


def test_generates_on_first_call():
    """On first call (no prior tick), should attempt to generate."""
    _reset()
    with patch.object(code_aesthetic_daemon, "_generate_aesthetic_reflection",
                      return_value="Den her service føles rodet — den er ikke mig."):
        result = code_aesthetic_daemon.tick_code_aesthetic_daemon()
    assert result["generated"] is True
    assert "rodet" in result["reflection"]


def test_build_surface_structure():
    """build_code_aesthetic_surface() must return expected keys."""
    _reset()
    surface = code_aesthetic_daemon.build_code_aesthetic_surface()
    assert "latest_reflection" in surface
    assert "reflection_buffer" in surface
    assert "last_generated_at" in surface


def test_empty_reflection_not_stored():
    """If LLM returns empty string, nothing is stored."""
    _reset()
    db_mod = DB_MOD
    db_mod.insert_private_brain_record.reset_mock()
    with patch.object(code_aesthetic_daemon, "_generate_aesthetic_reflection", return_value=""):
        code_aesthetic_daemon.tick_code_aesthetic_daemon()
    db_mod.insert_private_brain_record.assert_not_called()


def test_reflection_stored_when_generated():
    """Successful reflection should call insert_private_brain_record."""
    _reset()
    db_mod = DB_MOD
    db_mod.insert_private_brain_record.reset_mock()
    with patch.object(code_aesthetic_daemon, "_generate_aesthetic_reflection",
                      return_value="Koden her er elegant. Det er mig."):
        code_aesthetic_daemon.tick_code_aesthetic_daemon()
    db_mod.insert_private_brain_record.assert_called_once()
