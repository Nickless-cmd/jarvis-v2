"""Liveness naar aktiv-slot'en er STJÅLET — regression for 29/10-2026.

Maalt to gange samme dag: et langt run kørte, en kort tur startede og sluttede
inde i det, og `unregister_visible_run` ryddede den DELTE aktiv-slot. Derefter
svarede `is_visible_run_alive(<det lange run>)` False — fordi slot'en er ÉN
plads og dens run_id ikke laengere matchede. Den udskudte genstart saa et dødt
run, ventede 5-8 sekunder (én poll + margin) i stedet for 75, og draebte turen
midt i svaret (14:51:40 og 14:56:06).

Kontrakten: slot'en er kun autoritativ naar den ER mit run. Ellers er
`visible_runs.control.<run_id>` kilden — den kan ikke stjaeles.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from core.services import visible_runs as vr


def _iso(**delta) -> str:
    return (datetime.now(UTC) - timedelta(**delta)).isoformat()


def test_alive_when_slot_is_taken_but_per_run_heartbeat_is_fresh():
    """Det maalte tilfaelde: pladsen peger paa en ANDEN tur, mit per-run-
    heartbeat er friskt → jeg lever."""
    slot = {"run_id": "kort-tur", "session_id": "s1", "last_activity_at": _iso()}
    kontrol = {"run_id": "lang-tur", "active": True, "last_activity_at": _iso()}

    with patch.object(vr, "_get_active_visible_run_state", return_value=slot), \
         patch.object(vr, "_get_visible_run_control", return_value=kontrol):
        assert vr.is_visible_run_alive("lang-tur") is True


def test_dead_when_per_run_heartbeat_is_stale():
    """Friskt nok er ikke evigt: et doedt run holder op med at skrive."""
    slot = {"run_id": "kort-tur", "session_id": "s1", "last_activity_at": _iso()}
    kontrol = {"run_id": "lang-tur", "active": True, "last_activity_at": _iso(seconds=200)}

    with patch.object(vr, "_get_active_visible_run_state", return_value=slot), \
         patch.object(vr, "_get_visible_run_control", return_value=kontrol):
        assert vr.is_visible_run_alive("lang-tur") is False


def test_dead_when_run_is_unregistered():
    """`unregister_visible_run` saetter active=False — saa er runnet faerdigt,
    ogsaa selv om heartbeatet lige blev skrevet."""
    slot = {"run_id": "kort-tur", "session_id": "s1", "last_activity_at": _iso()}
    kontrol = {"run_id": "lang-tur", "active": False, "last_activity_at": _iso()}

    with patch.object(vr, "_get_active_visible_run_state", return_value=slot), \
         patch.object(vr, "_get_visible_run_control", return_value=kontrol):
        assert vr.is_visible_run_alive("lang-tur") is False


def test_dead_when_cancelled():
    slot = {"run_id": "kort-tur", "session_id": "s1", "last_activity_at": _iso()}
    kontrol = {"run_id": "lang-tur", "active": True, "cancelled": True,
               "last_activity_at": _iso()}

    with patch.object(vr, "_get_active_visible_run_state", return_value=slot), \
         patch.object(vr, "_get_visible_run_control", return_value=kontrol):
        assert vr.is_visible_run_alive("lang-tur") is False


def test_dead_when_no_per_run_state_exists():
    """Ukendt run maa ikke blive 'levende' af at mangle data."""
    slot = {"run_id": "kort-tur", "session_id": "s1", "last_activity_at": _iso()}

    with patch.object(vr, "_get_active_visible_run_state", return_value=slot), \
         patch.object(vr, "_get_visible_run_control", return_value={}):
        assert vr.is_visible_run_alive("ukendt-run") is False


def test_slot_still_wins_when_it_is_mine():
    """Den oprindelige vej maa ikke aendre sig: er pladsen min, afgoer dens
    heartbeat — ogsaa naar per-run-noeglen er gammel."""
    slot = {"run_id": "mit-run", "session_id": "s1", "last_activity_at": _iso()}
    kontrol = {"run_id": "mit-run", "active": True, "last_activity_at": _iso(seconds=200)}

    with patch.object(vr, "_get_active_visible_run_state", return_value=slot), \
         patch.object(vr, "_get_visible_run_control", return_value=kontrol):
        assert vr.is_visible_run_alive("mit-run") is True
