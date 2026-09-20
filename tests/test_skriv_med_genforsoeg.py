"""Genforsøg ved kortvarig skrivelås.

Målt 20/9-2026 på CT105: `busy_timeout` er 5 s, og i ro er ventetiden på
skrivelåsen 0,000 s (median og max over 12 forsøg). Men kl. 05:40:38 fyrede to
daglige opgaver i SAMME sekund, og under de to parallelle ture holdt låsen over
5 s. Tre skrivninger døde med «database is locked»: cheap-lane's rute-spor,
inner_voice_shadow og en inner_note-berigelse. Otte på tre døgn.

Den farligste af dem er berigelsen: en inner_note beriges kun ÉN gang, så en
tabt skrivning efterlader noten med sin skabelon-tekst for altid.
"""
from __future__ import annotations

import sqlite3
import threading
import time

import pytest

from core.runtime.db_core import skriv_med_genforsoeg


def test_laast_base_genforsoeges_og_lykkes():
    forsoeg = []

    def skriv():
        forsoeg.append(1)
        if len(forsoeg) < 3:
            raise sqlite3.OperationalError("database is locked")
        return "skrevet"

    assert skriv_med_genforsoeg(skriv) == "skrevet"
    assert len(forsoeg) == 3


def test_opgiver_til_sidst_og_kaster_laasen_videre():
    def skriv():
        raise sqlite3.OperationalError("database is locked")

    with pytest.raises(sqlite3.OperationalError):
        skriv_med_genforsoeg(skriv, forsoeg=2, pause=0.001)


def test_ANDRE_fejl_genforsoeges_IKKE():
    """En ægte fejl må ikke gemme sig bag fire stille forsøg — den skal frem
    med det samme, ellers ser en skema-fejl ud som kontention."""
    forsoeg = []

    def skriv():
        forsoeg.append(1)
        raise sqlite3.OperationalError("no such table: pjat")

    with pytest.raises(sqlite3.OperationalError, match="no such table"):
        skriv_med_genforsoeg(skriv)
    assert len(forsoeg) == 1, "en skema-fejl blev genforsøgt"


def test_pausen_vokser():
    tider = []

    def skriv():
        tider.append(time.perf_counter())
        if len(tider) < 4:
            raise sqlite3.OperationalError("database is busy")

    skriv_med_genforsoeg(skriv, pause=0.02)
    mellemrum = [b - a for a, b in zip(tider, tider[1:])]
    assert mellemrum[1] > mellemrum[0] and mellemrum[2] > mellemrum[1], mellemrum


def test_ÆGTE_laast_base_overlever(tmp_path):
    """Uden mock: en anden forbindelse holder skrivelåsen i 0,6 s, og skrivningen
    skal alligevel nå igennem. Det er præcis mønsteret fra kl. 05:41."""
    sti = tmp_path / "t.db"
    opsaet = sqlite3.connect(sti)
    opsaet.execute("CREATE TABLE spor (v TEXT)")
    opsaet.commit()
    opsaet.close()

    # check_same_thread=False: låsen slippes fra en timer-tråd.
    holder = sqlite3.connect(sti, timeout=5, check_same_thread=False)
    holder.execute("BEGIN IMMEDIATE")
    slip = threading.Timer(0.6, lambda: (holder.execute("ROLLBACK"), holder.close()))
    slip.start()

    def skriv():
        conn = sqlite3.connect(sti, timeout=0.1)
        try:
            conn.execute("INSERT INTO spor VALUES ('nået frem')")
            conn.commit()
        finally:
            conn.close()

    skriv_med_genforsoeg(skriv, forsoeg=6, pause=0.1)
    slip.join()

    kontrol = sqlite3.connect(sti)
    assert kontrol.execute("SELECT v FROM spor").fetchall() == [("nået frem",)]
    kontrol.close()
