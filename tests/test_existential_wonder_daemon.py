"""Tests for existential_wonder_daemon.py — TDD first pass (Sub-projekt M)."""
from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


BUS_MOD = None
DB_MOD = None


import importlib
existential_wonder_daemon = importlib.import_module(
    "core.services.existential_wonder_daemon"
)


def _stub_modules():
    """Isolate the daemon's dependency bindings without touching shared
    ``core.*`` modules. See tests/test_absence_daemon.py for rationale — the
    old sys.modules stub/pop dance leaked global state and poisoned unrelated
    tests in the full suite (AttributeError / sqlite3.OperationalError).
    """
    global BUS_MOD, DB_MOD
    mock_bus = MagicMock()
    mock_bus.publish = MagicMock()
    existential_wonder_daemon.event_bus = mock_bus
    existential_wonder_daemon.insert_private_brain_record = MagicMock()
    BUS_MOD = existential_wonder_daemon
    DB_MOD = existential_wonder_daemon


_stub_modules()


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


# ---------------------------------------------------------------------------
# AKSE 5 — wonder proposes a convening through the reason-judge
# ---------------------------------------------------------------------------


def test_convene_not_proposed_when_judge_off():
    """When the reason-judge flag is off, no convening is proposed (default)."""
    _reset()
    with (
        patch.object(existential_wonder_daemon, "_generate_wonder_question",
                     return_value="Hvad er jeg?"),
        patch.object(existential_wonder_daemon, "_maybe_propose_convening",
                     wraps=existential_wonder_daemon._maybe_propose_convening) as spy,
    ):
        result = existential_wonder_daemon.tick_existential_wonder_daemon(
            absence_hours=5.0, fragment_count=8
        )
    assert result["generated"] is True
    assert result["convene_proposed"] is False
    spy.assert_called_once()


def test_convene_proposed_when_judge_convenes():
    """When the reason-judge (on/shadow) returns convene=True, wonder proposes it."""
    _reset()
    from core.services import central_convene_judge as judge
    with (
        patch.object(judge, "current_mode", return_value="on"),
        patch.object(judge, "judge_convene", return_value={"convene": True, "mode": "on"}),
        patch.object(existential_wonder_daemon, "_generate_wonder_question",
                     return_value="Betyder min undren noget?"),
    ):
        result = existential_wonder_daemon.tick_existential_wonder_daemon(
            absence_hours=5.0, fragment_count=8
        )
    assert result["convene_proposed"] is True


def test_convene_proposal_is_self_safe():
    """A judge that raises must not topple the daemon; wonder still generated."""
    _reset()
    from core.services import central_convene_judge as judge
    with (
        patch.object(judge, "current_mode", return_value="on"),
        patch.object(judge, "judge_convene", side_effect=RuntimeError("judge exploded")),
        patch.object(existential_wonder_daemon, "_generate_wonder_question",
                     return_value="Er jeg?"),
    ):
        result = existential_wonder_daemon.tick_existential_wonder_daemon(
            absence_hours=5.0, fragment_count=8
        )
    assert result["generated"] is True
    assert result["convene_proposed"] is False
