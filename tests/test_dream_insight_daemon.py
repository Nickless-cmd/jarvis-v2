"""Tests for dream_insight_daemon.py — TDD first pass (L1)."""
from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


BUS_MOD = None
DB_MOD = None


import importlib
dream_insight_daemon = importlib.import_module(
    "core.services.dream_insight_daemon"
)


def _stub_modules():
    """Isolate the daemon's dependency bindings without touching shared
    ``core.*`` modules. See tests/test_absence_daemon.py for rationale — the
    old sys.modules stub/pop dance leaked global state and poisoned unrelated
    tests in the full suite (AttributeError / sqlite3.OperationalError).
    """
    global BUS_MOD, DB_MOD
    mock_bus = MagicMock()
    mock_bus.publish = MagicMock()
    dream_insight_daemon.event_bus = mock_bus
    dream_insight_daemon.insert_private_brain_record = MagicMock()
    BUS_MOD = dream_insight_daemon
    DB_MOD = dream_insight_daemon


_stub_modules()


def _reset():
    dream_insight_daemon._last_insight = ""
    dream_insight_daemon._insight_buffer = []
    dream_insight_daemon._last_persisted_signal_id = ""


def test_persist_new_dream_output_stores_record():
    """When a new signal_id arrives, it should persist a dream-insight."""
    _reset()
    # patch direkte på modulets importerede reference — virker uanset om DB_MOD er stub eller rigtig
    with patch("core.services.dream_insight_daemon.insert_private_brain_record") as mock_insert:
        result = dream_insight_daemon.tick_dream_insight_daemon(
            signal_id="sig-abc-123",
            signal_summary="Jarvis drømte om orden i kaos.",
        )
    assert result["persisted"] is True
    mock_insert.assert_called_once()


def test_same_signal_id_not_persisted_twice():
    """Same signal_id should not be persisted again."""
    _reset()
    dream_insight_daemon._last_persisted_signal_id = "sig-abc-123"
    with patch("core.services.dream_insight_daemon.insert_private_brain_record") as mock_insert:
        result = dream_insight_daemon.tick_dream_insight_daemon(
            signal_id="sig-abc-123",
            signal_summary="Jarvis drømte om orden i kaos.",
        )
    assert result["persisted"] is False
    mock_insert.assert_not_called()


def test_empty_signal_not_persisted():
    """Empty signal_id or empty summary should not persist."""
    _reset()
    result = dream_insight_daemon.tick_dream_insight_daemon(
        signal_id="",
        signal_summary="",
    )
    assert result["persisted"] is False


def test_build_surface_structure():
    """build_dream_insight_surface() must return expected keys."""
    _reset()
    surface = dream_insight_daemon.build_dream_insight_surface()
    assert "latest_insight" in surface
    assert "insight_buffer" in surface
    assert "last_persisted_signal_id" in surface


def test_buffer_accumulates_insights():
    """Multiple new signals should accumulate in buffer."""
    _reset()
    for i, sig in enumerate(["sig-1", "sig-2", "sig-3"]):
        dream_insight_daemon.tick_dream_insight_daemon(
            signal_id=sig,
            signal_summary=f"Drøm {i}",
        )
    surface = dream_insight_daemon.build_dream_insight_surface()
    assert len(surface["insight_buffer"]) == 3
