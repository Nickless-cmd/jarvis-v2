"""Tests for dream_insight_daemon.py — TDD first pass (L1)."""
from __future__ import annotations

import sys
import types
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


BUS_MOD = None
DB_MOD = None


def _stub_modules():
    global BUS_MOD, DB_MOD
    for name in [
        "core", "core.eventbus", "core.eventbus.bus",
        "core.runtime", "core.runtime.db",
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
dream_insight_daemon = importlib.import_module(
    "core.services.dream_insight_daemon"
)
for _name in ("core.eventbus.bus", "core.runtime.db", "core.eventbus", "core.runtime"):
    sys.modules.pop(_name, None)


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
