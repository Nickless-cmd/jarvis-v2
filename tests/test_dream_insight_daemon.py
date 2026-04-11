"""Tests for dream_insight_daemon.py — TDD first pass (L1)."""
from __future__ import annotations

import sys
import types
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest


def _stub_modules():
    for name in [
        "core", "core.eventbus", "core.eventbus.bus",
        "core.runtime", "core.runtime.db",
    ]:
        if name not in sys.modules:
            sys.modules[name] = types.ModuleType(name)

    bus_mod = sys.modules["core.eventbus.bus"]
    if not hasattr(bus_mod, "event_bus"):
        mock_bus = MagicMock()
        mock_bus.publish = MagicMock()
        bus_mod.event_bus = mock_bus

    db_mod = sys.modules["core.runtime.db"]
    if not hasattr(db_mod, "insert_private_brain_record"):
        db_mod.insert_private_brain_record = MagicMock()


_stub_modules()

import importlib
dream_insight_daemon = importlib.import_module(
    "apps.api.jarvis_api.services.dream_insight_daemon"
)


def _reset():
    dream_insight_daemon._last_insight = ""
    dream_insight_daemon._insight_buffer = []
    dream_insight_daemon._last_persisted_signal_id = ""


def test_persist_new_dream_output_stores_record():
    """When a new signal_id arrives, it should persist a dream-insight."""
    _reset()
    db_mod = sys.modules["core.runtime.db"]
    db_mod.insert_private_brain_record.reset_mock()

    result = dream_insight_daemon.tick_dream_insight_daemon(
        signal_id="sig-abc-123",
        signal_summary="Jarvis drømte om orden i kaos.",
    )
    assert result["persisted"] is True
    db_mod.insert_private_brain_record.assert_called_once()


def test_same_signal_id_not_persisted_twice():
    """Same signal_id should not be persisted again."""
    _reset()
    dream_insight_daemon._last_persisted_signal_id = "sig-abc-123"
    db_mod = sys.modules["core.runtime.db"]
    db_mod.insert_private_brain_record.reset_mock()

    result = dream_insight_daemon.tick_dream_insight_daemon(
        signal_id="sig-abc-123",
        signal_summary="Jarvis drømte om orden i kaos.",
    )
    assert result["persisted"] is False
    db_mod.insert_private_brain_record.assert_not_called()


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
