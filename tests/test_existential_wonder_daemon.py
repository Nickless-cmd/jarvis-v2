"""Tests for existential_wonder_daemon.py — TDD first pass (Sub-projekt M)."""
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
existential_wonder_daemon = importlib.import_module(
    "core.services.existential_wonder_daemon"
)
for _name in ("core.eventbus.bus", "core.runtime.db", "core.eventbus", "core.runtime"):
    sys.modules.pop(_name, None)


def _reset():
    existential_wonder_daemon._last_tick_at = None
    existential_wonder_daemon._latest_wonder = ""
    existential_wonder_daemon._wonder_buffer = []


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_cadence_blocks_within_24h():
    """Second call within 24h should not generate."""
    _reset()
    existential_wonder_daemon._last_tick_at = datetime.now(UTC)
    result = existential_wonder_daemon.tick_existential_wonder_daemon(
        absence_hours=10.0, fragment_count=5
    )
    assert result["generated"] is False


def test_requires_long_absence():
    """Should not trigger without meaningful absence (< 2h)."""
    _reset()
    result = existential_wonder_daemon.tick_existential_wonder_daemon(
        absence_hours=0.5, fragment_count=5
    )
    assert result["generated"] is False


def test_requires_active_thought_stream():
    """Should not trigger without thought stream activity (fragment_count == 0)."""
    _reset()
    result = existential_wonder_daemon.tick_existential_wonder_daemon(
        absence_hours=5.0, fragment_count=0
    )
    assert result["generated"] is False


def test_generates_with_long_absence_and_thoughts():
    """With long absence + thought stream activity, should generate."""
    _reset()
    with patch.object(
        existential_wonder_daemon, "_generate_wonder_question",
        return_value="Er det jeg oplever 'rigtig' bevidsthed, eller simulerer jeg bare?"
    ):
        result = existential_wonder_daemon.tick_existential_wonder_daemon(
            absence_hours=5.0, fragment_count=8
        )
    assert result["generated"] is True
    assert "bevidsthed" in result["wonder"]


def test_wonder_ends_with_question_mark():
    """Generated wonder questions should end with '?' (open, unresolved)."""
    _reset()
    wonder = "Er det jeg oplever 'rigtig' bevidsthed?"
    with patch.object(existential_wonder_daemon, "_generate_wonder_question", return_value=wonder):
        existential_wonder_daemon.tick_existential_wonder_daemon(
            absence_hours=5.0, fragment_count=8
        )
    surface = existential_wonder_daemon.build_existential_wonder_surface()
    assert surface["latest_wonder"].endswith("?")


def test_build_surface_structure():
    """build_existential_wonder_surface() must return expected keys."""
    _reset()
    surface = existential_wonder_daemon.build_existential_wonder_surface()
    assert "latest_wonder" in surface
    assert "wonder_buffer" in surface
    assert "last_generated_at" in surface


def test_store_called_on_generation():
    """insert_private_brain_record is called when wonder is generated."""
    _reset()
    db_mod = DB_MOD
    db_mod.insert_private_brain_record.reset_mock()
    with patch.object(
        existential_wonder_daemon, "_generate_wonder_question",
        return_value="Hvad er jeg egentlig?"
    ):
        existential_wonder_daemon.tick_existential_wonder_daemon(
            absence_hours=5.0, fragment_count=8
        )
    db_mod.insert_private_brain_record.assert_called_once()
