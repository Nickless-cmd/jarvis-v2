"""Tests for memory_decay_daemon.py — TDD first pass."""
from __future__ import annotations

import sys
import types
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------

BUS_MOD = None
DB_MOD = None


def _stub_modules():
    global BUS_MOD, DB_MOD
    for name in [
        "core",
        "core.eventbus",
        "core.eventbus.bus",
        "core.runtime",
        "core.runtime.db",
    ]:
        if name not in sys.modules:
            sys.modules[name] = types.ModuleType(name)

    repo_root = Path(__file__).resolve().parents[1]
    sys.modules["core"].__path__ = [str(repo_root / "core")]
    sys.modules["core.eventbus"].__path__ = [str(repo_root / "core" / "eventbus")]
    sys.modules["core.runtime"].__path__ = [str(repo_root / "core" / "runtime")]

    BUS_MOD = sys.modules["core.eventbus.bus"]
    if not hasattr(BUS_MOD, "event_bus"):
        mock_bus = MagicMock()
        mock_bus.publish = MagicMock()
        BUS_MOD.event_bus = mock_bus

    DB_MOD = sys.modules["core.runtime.db"]
    DB_MOD.decay_private_brain_records = MagicMock(return_value=5)
    DB_MOD.get_salient_private_brain_records = MagicMock(return_value=[])
    DB_MOD.update_private_brain_record_salience = MagicMock()
    DB_MOD.list_private_brain_records = MagicMock(return_value=[])


_stub_modules()

import importlib

memory_decay_daemon = importlib.import_module(
    "core.services.memory_decay_daemon"
)
for _name in ("core.eventbus.bus", "core.runtime.db", "core.eventbus", "core.runtime"):
    sys.modules.pop(_name, None)


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
    db_mod = DB_MOD
    db_mod.decay_private_brain_records.reset_mock()

    memory_decay_daemon._last_decay_at = datetime.now(UTC)
    result = memory_decay_daemon.tick_memory_decay_daemon()
    assert result["decayed"] is False
    db_mod.decay_private_brain_records.assert_not_called()


def test_decay_called_after_24h():
    """decay_private_brain_records should be called if >24h since last run."""
    _reset()
    db_mod = DB_MOD
    db_mod.decay_private_brain_records.reset_mock()
    db_mod.get_salient_private_brain_records.return_value = []

    memory_decay_daemon._last_decay_at = datetime.now(UTC) - timedelta(hours=25)
    result = memory_decay_daemon.tick_memory_decay_daemon()
    assert result["decayed"] is True
    db_mod.decay_private_brain_records.assert_called_once()


def test_hold_fast_sets_salience_to_one():
    """hold_fast(record_id) should set salience to 1.0."""
    _reset()
    db_mod = DB_MOD
    db_mod.update_private_brain_record_salience.reset_mock()
    memory_decay_daemon.hold_fast("pb-test-123")
    db_mod.update_private_brain_record_salience.assert_called_once_with("pb-test-123", 1.0)


def test_rediscovery_surfaces_near_forgotten_record():
    """With a low-salience record present, rediscovery should surface it."""
    _reset()
    db_mod = DB_MOD
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
    db_mod = DB_MOD
    db_mod.decay_private_brain_records.reset_mock()
    db_mod.get_salient_private_brain_records.return_value = []

    result = memory_decay_daemon.tick_memory_decay_daemon()
    assert result["decayed"] is True
