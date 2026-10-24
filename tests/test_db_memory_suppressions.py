"""Tests for memory_suppressions — «don't mention this again».

Bruger en RIGTIG sqlite3-forbindelse paa en tmp-fil, ikke en fake. En fake der
returnerer de samme raekker uanset SQL kan ikke se en WHERE-gren, og saa kan
testen ikke afgoere om bruger-isolationen virker (maalt 24/10-2026: det er
praecis den fejlklasse jeg selv har skrevet om).
"""
from __future__ import annotations

import sqlite3

import pytest

from core.runtime import db_memory_suppressions as S


@pytest.fixture()
def tmp_db(tmp_path, monkeypatch):
    """Én rigtig sqlite-forbindelse pr. test, delt af alle kald."""
    sti = tmp_path / "sup.sqlite"

    def _connect():
        conn = sqlite3.connect(str(sti), timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(S, "connect", _connect)
    yield sti


def test_ensure_table_er_idempotent(tmp_db):
    S.ensure_table()
    S.ensure_table()
    with sqlite3.connect(str(tmp_db)) as conn:
        navne = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    assert S._TABLE in navne


def test_suppress_skriver_og_list_active_ser_den(tmp_db):
    r = S.suppress(user_id="bjorn", emne="maraton", grund="ikke laengere relevant")
    assert r["status"] == "ok"
    aktive = S.list_active(user_id="bjorn")
    assert [a["emne"] for a in aktive] == ["maraton"]
    assert aktive[0]["id"] == r["id"]


def test_tomt_emne_afvises_uden_at_skrive(tmp_db):
    r = S.suppress(user_id="bjorn", emne="   ")
    assert r["status"] == "error"
    assert S.list_active(user_id="bjorn") == []


def test_lift_fjerner_fra_aktive_men_bevarer_raekken(tmp_db):
    r = S.suppress(user_id="bjorn", emne="ankel")
    assert S.lift(user_id="bjorn", suppression_id=r["id"])["status"] == "ok"
    assert S.list_active(user_id="bjorn") == []
    with sqlite3.connect(str(tmp_db)) as conn:
        n = conn.execute(
            f"SELECT COUNT(*) FROM {S._TABLE} WHERE id = ?", (r["id"],)).fetchone()[0]
    assert n == 1, "raekken skal bevares — ophaevelse er ikke en sletning"


def test_lift_paa_ukendt_id_fejler(tmp_db):
    assert S.lift(user_id="bjorn", suppression_id="findes-ikke")["status"] == "error"


def test_lift_kan_ikke_ske_to_gange(tmp_db):
    r = S.suppress(user_id="bjorn", emne="dobbelt")
    assert S.lift(user_id="bjorn", suppression_id=r["id"])["status"] == "ok"
    assert S.lift(user_id="bjorn", suppression_id=r["id"])["status"] == "error"


def test_bruger_isolation_list_active(tmp_db):
    """WHERE user_id-grenen: Bjørns emne maa ikke ramme Michelles liste."""
    S.suppress(user_id="bjorn", emne="maraton")
    assert S.list_active(user_id="michelle") == []
    assert [a["emne"] for a in S.list_active(user_id="bjorn")] == ["maraton"]


def test_bruger_isolation_lift(tmp_db):
    """En anden bruger maa ikke kunne ophaeve Bjørns undertrykkelse."""
    r = S.suppress(user_id="bjorn", emne="privat")
    udefra = S.lift(user_id="michelle", suppression_id=r["id"])
    assert udefra["status"] == "error"
    assert [a["emne"] for a in S.list_active(user_id="bjorn")] == ["privat"]


def test_er_undertrykt_matcher_delstreng(tmp_db):
    S.suppress(user_id="bjorn", emne="maraton")
    ramte = S.er_undertrykt(
        user_id="bjorn", tekst="Jeg traener til MARATON i maj")
    assert ramte == ["maraton"]


def test_er_undertrykt_rammer_ikke_fremmed_tekst(tmp_db):
    S.suppress(user_id="bjorn", emne="maraton")
    assert S.er_undertrykt(user_id="bjorn", tekst="Jeg spiser vegetarisk") == []


def test_er_undertrykt_ser_bort_fra_ophaevede(tmp_db):
    r = S.suppress(user_id="bjorn", emne="ankel")
    S.lift(user_id="bjorn", suppression_id=r["id"])
    assert S.er_undertrykt(user_id="bjorn", tekst="min ankel er fin") == []


def test_er_undertrykt_med_tom_tekst_giver_ingen(tmp_db):
    S.suppress(user_id="bjorn", emne="maraton")
    assert S.er_undertrykt(user_id="bjorn", tekst="") == []
