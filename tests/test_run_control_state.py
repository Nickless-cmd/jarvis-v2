"""Tests for run_control_state — især touch_active_visible_run heartbeat
(cross-proces liveness; Bjørn 2026-06-13).

29/10-2026: aktiv-slot'en er ÉN plads i hele huset. En kort tur kan tage den
mens et langt run er midt i sit; naar den korte tur er færdig rydder
`unregister_visible_run` pladsen, og saa doemte liveness-testen det lange run
dødt mens det koerte. Den udskudte genstart ventede derfor 5-8 sekunder i
stedet for 75 og draebte turen midt i svaret — maalt to gange samme dag
(14:51:40 og 14:56:06). Kontrakten er nu TO noegler: per-run-altid, slot'en
kun naar den stadig er min.
"""
from __future__ import annotations

from unittest.mock import patch

from core.services.visible_runs_sections import run_control_state as rcs


def test_touch_updates_heartbeat_for_matching_run():
    store = {"run_id": "auto-1", "session_id": "s1"}
    kontrol = {"run_id": "auto-1", "active": True}

    def fake_get(default=None):
        return store

    saved = {}
    skrevet = {}

    def fake_set(value):
        saved.update(value)

    with patch.object(rcs, "_get_active_visible_run_state", return_value=store), \
         patch.object(rcs, "_get_visible_run_control", return_value=kontrol), \
         patch.object(rcs, "_set_visible_run_control",
                      side_effect=lambda rid, p: skrevet.update({rid: dict(p)})), \
         patch.object(rcs, "set_runtime_state_value", side_effect=lambda k, v: saved.update(v)):
        rcs.touch_active_visible_run("auto-1")
    assert "last_activity_at" in saved
    assert saved.get("run_id") == "auto-1"
    # Per-run-noeglen skal ogsaa have heartbeatet — den er den der overlever
    # at pladsen bliver taget.
    assert "last_activity_at" in skrevet.get("auto-1", {})


def test_touch_does_not_revive_a_displaced_run_in_the_slot():
    """Pladsen er taget af en anden tur: den maa IKKE genoplives, men MIT
    eget per-run-heartbeat skal stadig skrives."""
    store = {"run_id": "kort-tur", "session_id": "s1"}
    kontrol = {"run_id": "lang-tur", "active": True}
    aktivt = {}
    skrevet = {}

    with patch.object(rcs, "_get_active_visible_run_state", return_value=store), \
         patch.object(rcs, "_get_visible_run_control", return_value=kontrol), \
         patch.object(rcs, "_set_visible_run_control",
                      side_effect=lambda rid, p: skrevet.update({rid: dict(p)})), \
         patch.object(rcs, "set_runtime_state_value",
                      side_effect=lambda k, v: aktivt.update(v)):
        rcs.touch_active_visible_run("lang-tur")

    assert aktivt == {}, "aktiv-slot'en maa ikke genoplives for en afloest tur"
    assert "last_activity_at" in skrevet.get("lang-tur", {}), (
        "per-run-heartbeatet mangler — saa doemmer liveness-testen et levende "
        "run doedt og genstarten draeber turen"
    )


def test_touch_noops_without_a_run_id():
    """Tomt run-id maa ikke skrive noget som helst (ingen noegle at skrive til)."""
    aktivt = {}
    with patch.object(rcs, "set_runtime_state_value",
                      side_effect=lambda k, v: aktivt.update(v)), \
         patch.object(rcs, "_set_visible_run_control") as set_control:
        rcs.touch_active_visible_run("")
    assert aktivt == {}
    set_control.assert_not_called()
