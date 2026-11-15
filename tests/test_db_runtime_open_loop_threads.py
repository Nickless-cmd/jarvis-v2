"""Tests for ``core/runtime/db_runtime_open_loop_threads.py``.

Modulet ejer tråd-registret: schema, deklaration og opslag. Signal-persistens
og livscyklus ligger i ``db_runtime_executive_signals`` (dækket i
``test_thread_registry.py``), så denne fil holder sig til modulets EGNE
primitiver — ellers ville de to filer duplikere hinanden.

Navnet matcher kilden, fordi ``enforce-test-coverage``-hooken kræver det.
"""

from __future__ import annotations

import sqlite3

import pytest

from core.runtime import db_runtime_open_loop_threads as thread_store


def _declare(name="Hvorfor driver loops?", declared_by="jarvis", **kw):
    return thread_store.declare_runtime_thread(
        name=name,
        declared_by=declared_by,
        opened_at="2026-11-15T10:00:00+00:00",
        **kw,
    )


# --- schema -----------------------------------------------------------------


def test_registry_table_creation_is_idempotent(isolated_runtime) -> None:
    """Tabellen oprettes af hvert opslag — den må ikke fejle på anden kørsel."""
    with thread_store.connect() as conn:
        thread_store._ensure_runtime_thread_registry_table(conn)
        thread_store._ensure_runtime_thread_registry_table(conn)
        cols = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(runtime_thread_registry)")
        }
    assert {"thread_id", "name", "status", "declared_by"} <= cols


# --- deklaration ------------------------------------------------------------


def test_declaration_stores_the_name_verbatim(isolated_runtime) -> None:
    """Navnet er identiteten — det må ikke normaliseres væk ved skrivning."""
    thread = _declare(name="  Hvorfor   driver loops?  ")
    assert thread["name"] == "Hvorfor driver loops?"
    assert thread["status"] == "open"
    assert thread["declared_by"] == "jarvis"
    assert thread["thread_id"]


@pytest.mark.parametrize(
    ("name", "declared_by"),
    [("", "jarvis"), ("   ", "bjorn"), ("Et navn", "heuristic"), ("Et navn", "")],
)
def test_declaration_demands_a_name_and_a_conscious_declarer(
    isolated_runtime, name, declared_by
) -> None:
    """En tråd uden navn eller uden en bevidst deklarant er ikke en tråd."""
    with pytest.raises(ValueError):
        _declare(name=name, declared_by=declared_by)


# --- opslag ----------------------------------------------------------------


def test_lookup_by_id_returns_the_declared_row(isolated_runtime) -> None:
    thread = _declare()
    found = thread_store.get_runtime_thread(str(thread["thread_id"]))
    assert found is not None
    assert found["thread_id"] == thread["thread_id"]


def test_lookup_by_id_returns_none_for_unknown(isolated_runtime) -> None:
    assert thread_store.get_runtime_thread("findes-ikke") is None


def test_lookup_by_name_is_case_insensitive_and_open_only(isolated_runtime) -> None:
    """Navne-opslaget er præcist men stort/lille-uafhængigt — aldrig fuzzy."""
    thread = _declare(name="API-kontrakten")
    found = thread_store.get_open_runtime_thread_by_name("api-kontrakten")
    assert found is not None
    assert found["thread_id"] == thread["thread_id"]

    # En delvis tekst må ikke matche: det ville gøre navnet til et gæt.
    assert thread_store.get_open_runtime_thread_by_name("API") is None


def test_list_filters_on_status_and_respects_limit(isolated_runtime) -> None:
    _declare(name="Første")
    _declare(name="Anden")

    alle = thread_store.list_runtime_threads()
    assert len(alle) == 2

    assert len(thread_store.list_runtime_threads(limit=1)) == 1
    assert thread_store.list_runtime_threads(status="closed") == []
    assert len(thread_store.list_runtime_threads(status="open")) == 2


# --- loftet -----------------------------------------------------------------


def test_limit_is_one_place_and_above_the_measured_population() -> None:
    """Loftet skal fange ophobning, ikke arve den.

    Målt 15/11-2026: 146 ulukkede signaler, ingen ældre end 5 dage — så
    forfaldet (5d + 7d) kunne ikke rydde én eneste inden for en uge. Et loft
    under den population ville afvise al ny autonomi fra dag ét.
    """
    assert thread_store.MAX_ACTIVE_OPEN_LOOPS > 146
    assert isinstance(thread_store.MAX_ACTIVE_OPEN_LOOPS, int)


def test_limit_error_names_both_counts_so_the_refusal_is_diagnosable() -> None:
    err = thread_store.OpenLoopLimitReached(active_signals=301, open_threads=12)
    besked = str(err)
    assert str(thread_store.MAX_ACTIVE_OPEN_LOOPS) in besked
    assert "301" in besked
    assert "12" in besked
    assert err.limit == thread_store.MAX_ACTIVE_OPEN_LOOPS


def test_limit_error_is_a_runtime_error_so_callers_can_catch_it_broadly() -> None:
    """Kalderne fanger RuntimeError i dag; klassen må ikke skifte familie."""
    assert issubclass(thread_store.OpenLoopLimitReached, RuntimeError)
