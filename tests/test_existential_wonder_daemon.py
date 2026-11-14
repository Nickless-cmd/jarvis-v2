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


@pytest.fixture(autouse=True)
def _stub_modules(monkeypatch):
    """Isolate the daemon's dependency bindings without touching shared
    ``core.*`` modules. See tests/test_absence_daemon.py for rationale — the
    old sys.modules stub/pop dance leaked global state and poisoned unrelated
    tests in the full suite (AttributeError / sqlite3.OperationalError).

    Pr. test, ikke ved import (19/9-2026): stubbene blev sat én gang under
    opsamlingen. tests/services/test_existential_wonder_event_gate.py
    genindlæser modulet og nulstiller dermed attributterne til de ægte
    funktioner — i fuld kørsel var mocken væk, og test_store_called_on_generation
    fejlede med «'function' object has no attribute 'reset_mock'».
    """
    global BUS_MOD, DB_MOD
    mock_bus = MagicMock()
    mock_bus.publish = MagicMock()
    monkeypatch.setattr(existential_wonder_daemon, "event_bus", mock_bus)
    monkeypatch.setattr(existential_wonder_daemon, "insert_private_brain_record", MagicMock())
    BUS_MOD = existential_wonder_daemon
    DB_MOD = existential_wonder_daemon


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


# ---------------------------------------------------------------------------
# Persisteret undren som fallback (14/11-2026)
#
# MÅLT: `_latest_wonder` og `_last_tick_at` er modul-state, så en genstart
# nulstillede dem mens undren lå i `private_brain_records`. Surfacen svarede
# derfor tom, og signalet var 0 PRÆCIS når nogen kiggede — med 170 genstarter
# siden 7/11 var det den normale tilstand. Dommerens alders-vægtning kunne
# heller ikke virke uden tidsstemplet.
# ---------------------------------------------------------------------------


def test_tom_ram_laeser_den_persisterede_wonder():
    """Efter en genstart skal surfacen vise den undren der ligger i databasen."""
    _reset()
    post = {
        "summary": "Er jeg virkelig bevidst?",
        "created_at": "2026-11-13T23:01:13.320845+00:00",
    }
    with patch("core.runtime.db.list_private_brain_records", return_value=[post]):
        surface = existential_wonder_daemon.build_existential_wonder_surface()

    assert surface["latest_wonder"] == "Er jeg virkelig bevidst?"
    assert surface["last_generated_at"] == "2026-11-13T23:01:13.320845+00:00"


def test_kun_den_manglende_vaerdi_bliver_fyldt_fra_databasen():
    """Fallback'en må kun fylde det der mangler — ikke overskrive det der findes.

    Grænsen er ``if not latest`` / ``if not generated_at``, ikke «kør blokken
    og tag databasen». Målt: uden den grænse ville en undren der allerede stod
    i RAM blive erstattet af den forrige post i databasen — og så ville
    signalet aldrig kunne springe, fordi en ny undren blev skrevet tilbage til
    den gamle. Testen sætter derfor KUN tidsstemplet til at mangle, så
    DB-grenen faktisk kører, og kræver at teksten står urørt.
    """
    _reset()
    existential_wonder_daemon._latest_wonder = "Helt frisk undren?"
    existential_wonder_daemon._last_tick_at = None  # tvinger DB-grenen til at køre
    post = {"summary": "Gammel undren?", "created_at": "2026-11-01T00:00:00+00:00"}
    with patch("core.runtime.db.list_private_brain_records", return_value=[post]):
        surface = existential_wonder_daemon.build_existential_wonder_surface()

    assert surface["latest_wonder"] == "Helt frisk undren?", (
        "den frische tekst blev overskrevet af databasen — så kan signalet aldrig springe"
    )
    assert surface["last_generated_at"] == "2026-11-01T00:00:00+00:00", (
        "det manglende tidsstempel skulle være fyldt fra databasen"
    )


def test_persisteret_wonder_naar_frem_til_dommeren_med_alder():
    """Den ægte sidste meter: en undren fra i går må ikke veje som en frisk.

    Det er præcis fejlen der blev usynlig da tidsstemplet forsvandt: dommeren
    faldt tilbage til den binære regel og gav 1.0 for en tolv timer gammel
    undren — det højeste niveau — så signalet kun aldrig kunne falde.
    """
    from core.services import central_convene_judge as j

    _reset()
    gammel = (datetime.now(UTC) - timedelta(hours=12)).isoformat()
    post = {"summary": "Hvem er jeg?", "created_at": gammel}
    with patch("core.runtime.db.list_private_brain_records", return_value=[post]):
        surface = existential_wonder_daemon.build_existential_wonder_surface()

    niveau = j._movement_from_signal("existential_wonder", surface)
    assert niveau == 0.0, f"en undren fra 12 timer siden skal være faldet, fik {niveau}"

    frisk = (datetime.now(UTC) - timedelta(minutes=2)).isoformat()
    post_frisk = {"summary": "Hvem er jeg?", "created_at": frisk}
    with patch("core.runtime.db.list_private_brain_records", return_value=[post_frisk]):
        surface_frisk = existential_wonder_daemon.build_existential_wonder_surface()

    niveau_frisk = j._movement_from_signal("existential_wonder", surface_frisk)
    assert niveau_frisk > 0.9, f"en undren fra 2 min siden skal veje næsten fuldt, fik {niveau_frisk}"
