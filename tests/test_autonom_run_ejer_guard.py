"""Ejer-tjek i start_autonomous_run (12/11-2026).

Bevis for at tjekket naaede forbi: run-guarden (`blokeringsgrund`) blev kaldt.
Den spioneres og returnerer en blokering, saa intet run startes i nogen case;
en AFVISNING fra ejer-tjekket ses som at guarden IKKE blev kaldt.
"""
from __future__ import annotations

import sqlite3

import pytest

import core.runtime.db_core as db_core
import core.services.visible_autonomous_run as var

BJORN = "bjorn-owner"
MIKKEL = "mikkel-id"


@pytest.fixture
def harness(monkeypatch):
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute(
        "CREATE TABLE chat_sessions (session_id TEXT PRIMARY KEY, "
        "owner_user_id TEXT NOT NULL DEFAULT '')"
    )

    class _Conn:
        def __enter__(self):
            return conn

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(db_core, "connect", lambda: _Conn())
    monkeypatch.setattr(
        "core.identity.owner_resolver.owner_user_id", lambda: BJORN
    )
    guard_calls: list[str] = []

    def _guard(origin, session):
        guard_calls.append(session)
        return "optaget"  # blokerer -> intet run startes

    monkeypatch.setattr("core.services.run_guard.blokeringsgrund", _guard)

    def add(sid, owner):
        conn.execute("INSERT INTO chat_sessions VALUES (?, ?)", (sid, owner))

    return add, guard_calls


def _start(sid):
    return var.start_autonomous_run("hej", session_id=sid, origin="inbox")


def test_fremmed_stemplet_session_afvises(harness):
    add, guard = harness
    add("chat-mikkel", MIKKEL)
    assert _start("chat-mikkel") is False
    assert guard == []  # afvist FOER run-guarden


def test_egen_stemplet_session_slipper_igennem(harness):
    add, guard = harness
    add("chat-bjorn", BJORN)
    _start("chat-bjorn")
    assert guard == ["chat-bjorn"]


def test_ustemplet_session_slipper_igennem(harness):
    add, guard = harness
    add("chat-legacy", "")
    _start("chat-legacy")
    assert guard == ["chat-legacy"]


def test_silo_slipper_igennem_selv_med_fremmed_stempel(harness):
    add, guard = harness
    add("auto-heartbeat-20261112", MIKKEL)
    _start("auto-heartbeat-20261112")
    assert guard == ["auto-heartbeat-20261112"]


def test_ukendt_session_slipper_igennem(harness):
    _add, guard = harness
    _start("chat-findes-ikke")
    assert guard == ["chat-findes-ikke"]


def test_system_ejer_og_force_user_id(harness):
    add, guard = harness
    add("chat-sys", "system")
    _start("chat-sys")
    assert guard == ["chat-sys"]
    add("chat-mikkel2", MIKKEL)
    # eksplicit force_user_id == sessionens ejer -> igennem
    var.start_autonomous_run("hej", session_id="chat-mikkel2", origin="inbox",
                             force_user_id=MIKKEL)
    assert guard[-1] == "chat-mikkel2"
    # force_user_id != ejer -> afvist
    n = len(guard)
    assert var.start_autonomous_run("hej", session_id="chat-mikkel2",
                                    origin="inbox", force_user_id="andre") is False
    assert len(guard) == n
