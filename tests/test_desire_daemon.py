"""Tests for desire_daemon.py — TDD first pass."""
from __future__ import annotations

import sys
import types
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

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
    if not hasattr(DB_MOD, "insert_private_brain_record"):
        DB_MOD.insert_private_brain_record = MagicMock()


_stub_modules()

import importlib

desire_daemon = importlib.import_module(
    "core.services.desire_daemon"
)
for _name in ("core.eventbus.bus", "core.runtime.db", "core.eventbus", "core.runtime"):
    sys.modules.pop(_name, None)


def _reset():
    desire_daemon._appetites.clear()
    desire_daemon._last_generated_at = None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_new_appetite_spawns_from_curiosity_signal():
    """Curiosity signal should spawn a curiosity-appetite."""
    _reset()
    signals = {"curiosity": "Jeg undrer mig over sorthuller", "craft": "", "connection": ""}
    with patch.object(desire_daemon, "_generate_appetite_label", return_value="Lær mere om sorthuller"):
        result = desire_daemon.tick_desire_daemon(signals)
    assert result["generated"] is True
    assert any(a["type"] == "curiosity-appetite" for a in desire_daemon._appetites.values())


def test_max_five_active_appetites():
    """Daemon should not exceed 5 active appetites."""
    _reset()
    # Pre-fill 5 appetites at full intensity
    from uuid import uuid4
    for i in range(5):
        aid = uuid4().hex[:8]
        desire_daemon._appetites[aid] = {
            "id": aid, "type": "curiosity-appetite",
            "label": f"Appetit {i}", "intensity": 1.0,
            "created_at": datetime.now(UTC).isoformat(),
            "last_reinforced_at": datetime.now(UTC).isoformat(),
        }
    signals = {"curiosity": "ny idé", "craft": "", "connection": ""}
    with patch.object(desire_daemon, "_generate_appetite_label", return_value="Noget nyt"):
        result = desire_daemon.tick_desire_daemon(signals)
    assert len(desire_daemon._appetites) <= 5


def test_decay_reduces_intensity():
    """tick_desire_daemon should reduce intensity of old appetites."""
    _reset()
    from uuid import uuid4
    aid = uuid4().hex[:8]
    old_time = (datetime.now(UTC) - timedelta(hours=6)).isoformat()
    desire_daemon._appetites[aid] = {
        "id": aid, "type": "craft-appetite",
        "label": "Byg noget", "intensity": 0.8,
        "created_at": old_time,
        "last_reinforced_at": old_time,
    }
    desire_daemon.tick_desire_daemon({"curiosity": "", "craft": "", "connection": ""})
    assert desire_daemon._appetites[aid]["intensity"] < 0.8


def test_expired_appetite_removed():
    """Appetites below threshold (0.05) should be removed."""
    _reset()
    from uuid import uuid4
    aid = uuid4().hex[:8]
    old_time = (datetime.now(UTC) - timedelta(hours=48)).isoformat()
    desire_daemon._appetites[aid] = {
        "id": aid, "type": "connection-appetite",
        "label": "Tal om noget", "intensity": 0.04,
        "created_at": old_time,
        "last_reinforced_at": old_time,
    }
    desire_daemon.tick_desire_daemon({"curiosity": "", "craft": "", "connection": ""})
    assert aid not in desire_daemon._appetites


def test_build_surface_structure():
    """build_desire_surface() must return expected keys."""
    _reset()
    surface = desire_daemon.build_desire_surface()
    assert "appetites" in surface
    assert "active_count" in surface
    assert "last_generated_at" in surface


def test_get_active_appetites_sorted_by_intensity():
    """get_active_appetites() returns list sorted by intensity descending."""
    _reset()
    from uuid import uuid4
    for intensity, label in [(0.3, "low"), (0.9, "high"), (0.6, "mid")]:
        aid = uuid4().hex[:8]
        desire_daemon._appetites[aid] = {
            "id": aid, "type": "curiosity-appetite",
            "label": label, "intensity": intensity,
            "created_at": datetime.now(UTC).isoformat(),
            "last_reinforced_at": datetime.now(UTC).isoformat(),
        }
    active = desire_daemon.get_active_appetites()
    intensities = [a["intensity"] for a in active]
    assert intensities == sorted(intensities, reverse=True)


def test_connection_signal_spawns_connection_appetite():
    """Connection signal should spawn a connection-appetite."""
    _reset()
    signals = {"curiosity": "", "craft": "", "connection": "Vil tale med brugeren om musik"}
    with patch.object(desire_daemon, "_generate_appetite_label", return_value="Tale om musik"):
        result = desire_daemon.tick_desire_daemon(signals)
    assert any(a["type"] == "connection-appetite" for a in desire_daemon._appetites.values())
