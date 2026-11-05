"""Tests for signal-decay-daemonen og dens flade.

Dækker især batch-loftets signal (5/11-2026): loftet må ikke gøre en backlog
usynlig — den skal kunne ses som ``deferred_tables`` på fladen.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest


def _reset() -> None:
    import core.services.signal_decay_daemon as sdd

    sdd._last_tick_at = None
    sdd._last_result = {}


def test_surface_viser_deferred_tables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Rammer en tabel loftet, skal fladen sige det — ellers er loftet tavst.

    Mutationstestet: fjernes ``deferred_tables`` fra fladen, fejler denne test.
    """
    import core.services.signal_decay_daemon as sdd

    _reset()
    monkeypatch.setattr(
        "core.runtime.db.signal_decay_archive_and_delete",
        lambda stale_hours=24: {
            "archived": 5000,
            "tables_scanned": 35,
            "per_table": {"runtime_goal_signals": 5000},
            "truncated_tables": 1,
        },
    )
    monkeypatch.setattr("core.runtime.db.signal_archive_cleanup", lambda max_age_days=30: 0)

    sdd.tick_signal_decay_daemon()
    flade = sdd.build_signal_decay_surface()

    assert flade["last_archived"] == 5000
    assert flade["deferred_tables"] == 1


def test_surface_er_nul_naar_loftet_ikke_naas(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ingen afkortning må ikke rapporteres som en backlog der ikke findes."""
    import core.services.signal_decay_daemon as sdd

    _reset()
    monkeypatch.setattr(
        "core.runtime.db.signal_decay_archive_and_delete",
        lambda stale_hours=24: {
            "archived": 12,
            "tables_scanned": 35,
            "per_table": {"runtime_goal_signals": 12},
            "truncated_tables": 0,
        },
    )
    monkeypatch.setattr("core.runtime.db.signal_archive_cleanup", lambda max_age_days=30: 0)

    sdd.tick_signal_decay_daemon()
    assert sdd.build_signal_decay_surface()["deferred_tables"] == 0


def test_surface_uden_koersel_er_nul() -> None:
    """Før første tick må fladen ikke påstå et loft der aldrig blev målt."""
    import core.services.signal_decay_daemon as sdd

    _reset()
    flade = sdd.build_signal_decay_surface()
    assert flade["deferred_tables"] == 0
    assert flade["last_tick_at"] == ""


def test_tick_videresender_truncated_tables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Kæden fra arkivering til flade må ikke tabe signalet undervejs."""
    import core.services.signal_decay_daemon as sdd

    _reset()
    monkeypatch.setattr(
        "core.runtime.db.signal_decay_archive_and_delete",
        lambda stale_hours=24: {
            "archived": 7,
            "tables_scanned": 35,
            "per_table": {"t": 7},
            "truncated_tables": 3,
        },
    )
    monkeypatch.setattr("core.runtime.db.signal_archive_cleanup", lambda max_age_days=30: 0)

    resultat = sdd.tick_signal_decay_daemon()
    assert resultat["generated"] is True
    assert resultat["truncated_tables"] == 3
    assert sdd.build_signal_decay_surface()["deferred_tables"] == 3
    assert sdd.get_signal_decay_stats()["last_result"]["truncated_tables"] == 3
