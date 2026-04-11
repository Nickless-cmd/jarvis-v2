"""Tests for memory_decay_daemon.py — TDD first pass."""
from __future__ import annotations

import sys
import types
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch, call

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
    db_mod.decay_private_brain_records = MagicMock(return_value=5)
    db_mod.get_salient_private_brain_records = MagicMock(return_value=[])
    db_mod.update_private_brain_record_salience = MagicMock()
    db_mod.list_private_brain_records = MagicMock(return_value=[])


_stub_modules()

import importlib

memory_decay_daemon = importlib.import_module(
    "apps.api.jarvis_api.services.memory_decay_daemon"
)


def _reset():
    memory_decay_daemon._last_decay_at = None
    memory_decay_daemon._last_rediscovery = ""
    memory_decay_daemon._rediscovery_buffer = []


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_cadence_prevents_early_re_decay():
    """Second call within 24h should not trigger decay."""
    _reset()
    db_mod = sys.modules["core.runtime.db"]
    db_mod.decay_private_brain_records.reset_mock()

    memory_decay_daemon._last_decay_at = datetime.now(UTC)
    result = memory_decay_daemon.tick_memory_decay_daemon()
    assert result["decayed"] is False
    db_mod.decay_private_brain_records.assert_not_called()


def test_decay_called_after_24h():
    """decay_private_brain_records should be called if >24h since last run."""
    _reset()
    db_mod = sys.modules["core.runtime.db"]
    db_mod.decay_private_brain_records.reset_mock()
    db_mod.get_salient_private_brain_records.return_value = []

    memory_decay_daemon._last_decay_at = datetime.now(UTC) - timedelta(hours=25)
    result = memory_decay_daemon.tick_memory_decay_daemon()
    assert result["decayed"] is True
    db_mod.decay_private_brain_records.assert_called_once()


def test_hold_fast_sets_salience_to_one():
    """hold_fast(record_id) should set salience to 1.0."""
    _reset()
    db_mod = sys.modules["core.runtime.db"]
    db_mod.update_private_brain_record_salience.reset_mock()
    memory_decay_daemon.hold_fast("pb-test-123")
    db_mod.update_private_brain_record_salience.assert_called_once_with("pb-test-123", 1.0)


def test_rediscovery_surfaces_near_forgotten_record():
    """With a low-salience record present, rediscovery should surface it."""
    _reset()
    db_mod = sys.modules["core.runtime.db"]
    near_forgotten = {
        "record_id": "pb-old-1",
        "summary": "En gammel tanke om stjernernes alder",
        "salience": 0.08,
        "record_type": "private-carry",
    }
    db_mod.list_private_brain_records.return_value = [near_forgotten]

    result = memory_decay_daemon.maybe_rediscover(force=True)
    assert result is not None
    assert result["record_id"] == "pb-old-1"


def test_build_surface_structure():
    """build_memory_decay_surface() must return expected keys."""
    _reset()
    surface = memory_decay_daemon.build_memory_decay_surface()
    assert "last_decay_at" in surface
    assert "last_rediscovery" in surface
    assert "rediscovery_buffer" in surface


def test_no_decay_on_first_call():
    """On first ever call (no prior decay), daemon should run decay."""
    _reset()
    db_mod = sys.modules["core.runtime.db"]
    db_mod.decay_private_brain_records.reset_mock()
    db_mod.get_salient_private_brain_records.return_value = []

    result = memory_decay_daemon.tick_memory_decay_daemon()
    assert result["decayed"] is True
