"""Tests for user_model_daemon.py — TDD first pass."""
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
    DB_MOD.recent_visible_runs = MagicMock(return_value=[])
    if not hasattr(DB_MOD, "insert_private_brain_record"):
        DB_MOD.insert_private_brain_record = MagicMock()


_stub_modules()

import importlib

user_model_daemon = importlib.import_module(
    "core.services.user_model_daemon"
)
for _name in ("core.eventbus.bus", "core.runtime.db", "core.eventbus", "core.runtime"):
    sys.modules.pop(_name, None)


def _reset():
    user_model_daemon._user_model = {}
    user_model_daemon._last_generated_at = None
    user_model_daemon._last_tick_at = None
    user_model_daemon._model_summary = ""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_cadence_gate_prevents_early_call():
    """Second call within 10 min should not re-analyze."""
    _reset()
    db_mod = DB_MOD
    db_mod.recent_visible_runs.reset_mock()

    user_model_daemon._last_tick_at = datetime.now(UTC)
    result = user_model_daemon.tick_user_model_daemon([])
    assert result["generated"] is False
    db_mod.recent_visible_runs.assert_not_called()


def test_generates_from_recent_runs():
    """With recent run text_previews, model should be updated."""
    _reset()
    db_mod = DB_MOD
    db_mod.recent_visible_runs.return_value = [
        {"text_preview": "Kan du hjælpe mig med en hurtig ting?", "lane": "visible"},
        {"text_preview": "Tak!", "lane": "visible"},
    ]
    with patch.object(user_model_daemon, "_generate_model_summary", return_value="Brugeren virker travl og kortfattet."):
        result = user_model_daemon.tick_user_model_daemon([
            "Kan du hjælpe mig med en hurtig ting?",
            "Tak!",
        ])
    assert result["generated"] is True
    assert user_model_daemon._model_summary == "Brugeren virker travl og kortfattet."


def test_build_surface_structure():
    """build_user_model_surface() must return expected keys."""
    _reset()
    surface = user_model_daemon.build_user_model_surface()
    assert "model_summary" in surface
    assert "user_model" in surface
    assert "last_generated_at" in surface


def test_short_messages_detected_as_terse():
    """Short messages (avg < 20 chars) should set communication_style to 'terse'."""
    _reset()
    short_messages = ["Ok", "Ja", "Tak", "Godt", "Fine"]
    style = user_model_daemon._detect_communication_style(short_messages)
    assert style == "terse"


def test_long_messages_detected_as_verbose():
    """Long messages (avg > 100 chars) should set communication_style to 'verbose'."""
    _reset()
    long_messages = [
        "Jeg tænker at vi måske burde overveje at lave en mere grundig analyse af situationen for at sikre at vi tager den rigtige beslutning.",
        "Det her er en kompleks problemstilling der kræver at vi ser på mange forskellige aspekter og overvejer konsekvenserne nøje.",
    ]
    style = user_model_daemon._detect_communication_style(long_messages)
    assert style == "verbose"


def test_get_user_model_summary_initially_empty():
    """get_user_model_summary() returns empty before any generation."""
    _reset()
    assert user_model_daemon.get_user_model_summary() == ""


def test_question_heavy_detected():
    """Many questions in messages should be flagged in model."""
    _reset()
    question_messages = [
        "Hvad er det bedste?",
        "Hvordan gør man det?",
        "Kan du forklare?",
        "Er det rigtigt?",
    ]
    model = user_model_daemon._analyze_messages(question_messages)
    assert model.get("question_heavy") is True
