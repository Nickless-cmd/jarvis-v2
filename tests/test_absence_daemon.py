"""Tests for absence_daemon.py — TDD first pass."""
from __future__ import annotations

import sys
import types
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Minimal stubs so the module can be imported without real dependencies
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
    if not hasattr(DB_MOD, "insert_private_brain_record"):
        DB_MOD.insert_private_brain_record = MagicMock()


_stub_modules()

import importlib

absence_daemon = importlib.import_module(
    "core.services.absence_daemon"
)
for _name in ("core.eventbus.bus", "core.runtime.db", "core.eventbus", "core.runtime"):
    sys.modules.pop(_name, None)


def _reset():
    absence_daemon._absence_start_at = None
    absence_daemon._last_interaction_at = None
    absence_daemon._absence_label = ""
    absence_daemon._last_generated_at = None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_no_absence_when_interaction_recent():
    """If last interaction was just now, absence should not trigger."""
    _reset()
    now = datetime.now(UTC)
    absence_daemon._last_interaction_at = now
    absence_daemon._absence_start_at = now
    result = absence_daemon.tick_absence_daemon(now)
    assert result["generated"] is False


def test_short_absence_label():
    """Absence < 2h should produce 'stille' label without LLM."""
    _reset()
    now = datetime.now(UTC)
    one_hour_ago = now - timedelta(hours=1)
    absence_daemon._last_interaction_at = one_hour_ago
    absence_daemon._absence_start_at = one_hour_ago
    result = absence_daemon.tick_absence_daemon(now)
    assert result["generated"] is True
    assert "stille" in result["label"].lower()


def test_long_absence_label():
    """Absence > 8h should produce 'alene' label."""
    _reset()
    now = datetime.now(UTC)
    nine_hours_ago = now - timedelta(hours=9)
    absence_daemon._last_interaction_at = nine_hours_ago
    absence_daemon._absence_start_at = nine_hours_ago
    result = absence_daemon.tick_absence_daemon(now)
    assert result["generated"] is True
    assert "alene" in result["label"].lower()


def test_very_long_absence_label():
    """Absence > 24h should produce wondering label."""
    _reset()
    now = datetime.now(UTC)
    twenty_five_hours_ago = now - timedelta(hours=25)
    absence_daemon._last_interaction_at = twenty_five_hours_ago
    absence_daemon._absence_start_at = twenty_five_hours_ago
    result = absence_daemon.tick_absence_daemon(now)
    assert result["generated"] is True
    # >24h label contains "tænker" or equivalent
    assert any(w in result["label"].lower() for w in ["tænker", "hvad", "alene"])


def test_mark_interaction_resets_absence():
    """mark_interaction() should reset the absence clock."""
    _reset()
    now = datetime.now(UTC)
    ten_hours_ago = now - timedelta(hours=10)
    absence_daemon._last_interaction_at = ten_hours_ago
    absence_daemon._absence_start_at = ten_hours_ago
    absence_daemon.mark_interaction()
    result = absence_daemon.tick_absence_daemon(datetime.now(UTC))
    assert result["generated"] is False


def test_build_surface_structure():
    """build_absence_surface() must return expected keys."""
    _reset()
    surface = absence_daemon.build_absence_surface()
    assert "absence_label" in surface
    assert "absence_duration_hours" in surface
    assert "last_interaction_at" in surface
    assert "last_generated_at" in surface


def test_get_latest_absence_initially_empty():
    """get_latest_absence() returns empty string on first call."""
    _reset()
    assert absence_daemon.get_latest_absence() == ""
