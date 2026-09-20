"""Tests for samtalens tilladelses-niveau — én sandhed på serveren (20/9-2026).

Værd at holde fast: `ask` er standarden. En tvivl skal koste et spørgsmål, ikke
en mutation. Falder en ukendt værdi igennem til `trust`, åbner den for
værktøjer uden at nogen bad om det — det er den fejl testene her forhindrer.
"""
from __future__ import annotations

import sqlite3

import pytest

from core.services import session_permission as sp


@pytest.fixture()
def db(monkeypatch, tmp_path):
    """En frisk DB med den ene kolonne testen har brug for."""
    sti = tmp_path / "test.db"
    conn = sqlite3.connect(sti)
    conn.execute(
        "CREATE TABLE chat_sessions (session_id TEXT PRIMARY KEY, title TEXT NOT NULL DEFAULT '')"
    )
    conn.execute("INSERT INTO chat_sessions (session_id, title) VALUES ('s1', 'test')")
    conn.commit()
    conn.close()

    import contextlib

    @contextlib.contextmanager
    def _connect():
        c = sqlite3.connect(sti)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            c.close()

    monkeypatch.setattr(sp, "connect", _connect)
    return sti


def test_ukendt_samtale_er_ask(db):
    """Den sikre vej: en samtale vi ikke kender maa ikke aabne for fuld adgang."""
    assert sp.hent_permission("findes-ikke") == "ask"


def test_tomt_id_er_ask(db):
    assert sp.hent_permission("") == "ask"
    assert sp.hent_permission(None) == "ask"


def test_kolonnen_laves_dovent(db):
    """Kolonne-migrationen skal vaere idempotent — hent kaldes ved hver åbning."""
    assert sp.hent_permission("s1") == "ask"
    assert sp.hent_permission("s1") == "ask"  # anden gang: ALTER TABLE fejler, sluges


def test_rundtur_ask_til_trust_og_tilbage(db):
    assert sp.saet_permission("s1", "trust")["status"] == "ok"
    assert sp.hent_permission("s1") == "trust"
    assert sp.saet_permission("s1", "ask")["status"] == "ok"
    assert sp.hent_permission("s1") == "ask"


def test_ugyldigt_niveau_afvises(db):
    ud = sp.saet_permission("s1", "maaske")
    assert ud["status"] == "error"
    # Og den maa IKKE have aendret noget undervejs.
    assert sp.hent_permission("s1") == "ask"


def test_ukendt_samtale_kan_ikke_saettes(db):
    """Et skriv til en samtale der ikke findes skal sige det, ikke lykkes stille."""
    ud = sp.saet_permission("findes-ikke", "trust")
    assert ud["status"] == "error"
    assert "findes-ikke" in str(ud["error"])


def test_stort_bogstav_i_niveau_er_gyldigt(db):
    """Klienterne sender småt, men et 'TRUST' fra en gammel klient skal ikke
    stille blive afvist som ukendt — det normaliseres."""
    assert sp.saet_permission("s1", "TRUST")["status"] == "ok"
    assert sp.hent_permission("s1") == "trust"
