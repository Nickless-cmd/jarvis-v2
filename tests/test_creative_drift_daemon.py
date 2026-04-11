"""Tests for creative_drift_daemon.py — TDD first pass."""
from __future__ import annotations

import sys
import types
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------

def _stub_modules():
    for name in [
        "core",
        "core.eventbus",
        "core.eventbus.bus",
        "core.runtime",
        "core.runtime.db",
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

creative_drift_daemon = importlib.import_module(
    "apps.api.jarvis_api.services.creative_drift_daemon"
)


def _reset():
    creative_drift_daemon._last_tick_at = None
    creative_drift_daemon._drift_buffer = []
    creative_drift_daemon._today_count = 0
    creative_drift_daemon._today_date = None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_cadence_blocks_early_second_call():
    """Second call within 30 min should not generate."""
    _reset()
    with patch.object(
        creative_drift_daemon, "_generate_drift_idea", return_value="Hvad nu hvis fugle husker drømme?"
    ):
        result1 = creative_drift_daemon.tick_creative_drift_daemon(["fragment1"])
        assert result1["generated"] is True
        # Immediate second call — cadence not elapsed
        result2 = creative_drift_daemon.tick_creative_drift_daemon(["fragment1"])
        assert result2["generated"] is False


def test_daily_cap_three_ideas():
    """After 3 ideas today, daemon should not generate more."""
    _reset()
    creative_drift_daemon._today_count = 3
    creative_drift_daemon._today_date = datetime.now(UTC).date()
    result = creative_drift_daemon.tick_creative_drift_daemon(["fragment1"])
    assert result["generated"] is False


def test_generates_idea_with_mocked_llm():
    """When cadence passes and day not capped, generates idea."""
    _reset()
    idea = "Jeg tænkte på noget: hvad nu hvis matematik er et sprog dyr forstår?"
    with patch.object(
        creative_drift_daemon, "_generate_drift_idea", return_value=idea
    ):
        result = creative_drift_daemon.tick_creative_drift_daemon(["noget fragment"])
    assert result["generated"] is True
    assert result["idea"] == idea


def test_buffer_accumulates():
    """Buffer grows with each new idea, capped at max."""
    _reset()
    for i in range(3):
        creative_drift_daemon._last_tick_at = None  # reset cadence each time
        creative_drift_daemon._today_date = datetime.now(UTC).date()
        with patch.object(
            creative_drift_daemon, "_generate_drift_idea", return_value=f"Idé {i}"
        ):
            creative_drift_daemon.tick_creative_drift_daemon([f"fragment {i}"])
    surface = creative_drift_daemon.build_creative_drift_surface()
    assert len(surface["drift_buffer"]) == 3


def test_store_called_on_generation():
    """insert_private_brain_record is called when idea is generated."""
    _reset()
    db_mod = sys.modules["core.runtime.db"]
    db_mod.insert_private_brain_record.reset_mock()
    with patch.object(
        creative_drift_daemon, "_generate_drift_idea", return_value="Hvad nu hvis..."
    ):
        creative_drift_daemon.tick_creative_drift_daemon(["fragment"])
    db_mod.insert_private_brain_record.assert_called_once()


def test_build_surface_structure():
    """build_creative_drift_surface() must return expected keys."""
    _reset()
    surface = creative_drift_daemon.build_creative_drift_surface()
    assert "latest_drift" in surface
    assert "drift_buffer" in surface
    assert "drift_count_today" in surface
    assert "last_generated_at" in surface


def test_get_latest_drift_initially_empty():
    """get_latest_drift() returns empty string before any generation."""
    _reset()
    assert creative_drift_daemon.get_latest_drift() == ""
