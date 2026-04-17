"""Tests for code_aesthetic_daemon.py — TDD first pass (L2)."""
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
code_aesthetic_daemon = importlib.import_module(
    "core.services.code_aesthetic_daemon"
)
for _name in ("core.eventbus.bus", "core.runtime.db", "core.eventbus", "core.runtime"):
    sys.modules.pop(_name, None)


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
