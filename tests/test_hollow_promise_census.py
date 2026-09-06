"""Optælling af tomme løfter — den ægte rate, uafhængigt af hvad værnet greb.

Bygget mod en RIGTIG sqlite-database frem for mocks: hele pointen med
folketællingen er SQL'en, og en mock ville teste at jeg kan skrive en mock.
"""
from __future__ import annotations

import sqlite3

import pytest

from core.services import hollow_promise_census as hpc


def _seed(sti):
    """Minimal skygge af de to tabeller optællingen læser."""
    c = sqlite3.connect(sti)
    c.executescript("""
        CREATE TABLE chat_messages (message_id TEXT, session_id TEXT, role TEXT,
                                    content TEXT, created_at TEXT);
        CREATE TABLE visible_runs (run_id TEXT, model TEXT,
                                   started_at TEXT, finished_at TEXT);
        CREATE TABLE events (kind TEXT, payload_json TEXT, created_at TEXT);
    """)
    return c


def _tid(minut, sekund=0):
    return f"2999-01-01T00:{minut:02d}:{sekund:02d}+00:00"


@pytest.fixture
def db(tmp_path, monkeypatch):
    sti = tmp_path / "t.db"
    c = _seed(str(sti))

    def _forbind():
        forb = sqlite3.connect(str(sti))
        forb.row_factory = None
        return forb

    monkeypatch.setattr(hpc, "connect", _forbind)
    monkeypatch.setattr(hpc, "_since", lambda hours: "2000-01-01T00:00:00+00:00")
    return c


def _tur(c, session, model, minut, svar, med_vaerktoej):
    c.execute("INSERT INTO visible_runs VALUES (?,?,?,?)",
              (f"run-{minut}", model, _tid(minut), _tid(minut + 1)))
    # Rækkefølgen INDE i turen bærer betydningen: bruger → (værktøj) → svar.
    c.execute("INSERT INTO chat_messages VALUES (?,?,?,?,?)",
              (f"u{minut}", session, "user", "gør noget", _tid(minut, 1)))
    if med_vaerktoej:
        c.execute("INSERT INTO chat_messages VALUES (?,?,?,?,?)",
                  (f"t{minut}", session, "tool", "[resultat]", _tid(minut, 20)))
    c.execute("INSERT INTO chat_messages VALUES (?,?,?,?,?)",
              (f"a{minut}", session, "assistant", svar, _tid(minut, 40)))
    c.commit()


def test_et_loefte_uden_vaerktoej_taelles_som_tomt(db):
    _tur(db, "s1", "vision", 10, "Lad mig tjekke config'en.", med_vaerktoej=False)
    r = hpc.census(24)
    assert r["models"][0]["hollow"] == 1
    assert r["hollow_total"] == 1


def test_samme_loefte_MED_et_vaerktoejskald_er_ikke_tomt(db):
    _tur(db, "s1", "vision", 10, "Lad mig tjekke config'en.", med_vaerktoej=True)
    assert hpc.census(24)["hollow_total"] == 0


def test_et_svar_uden_loefte_er_ikke_tomt(db):
    """Mange svar behøver slet ikke et værktøj. Kun de LOVEDE tæller."""
    _tur(db, "s1", "vision", 10, "Ja, det er rigtigt.", med_vaerktoej=False)
    assert hpc.census(24)["hollow_total"] == 0


def test_raten_regnes_pr_model(db):
    _tur(db, "s1", "vision", 10, "Lad mig tjekke config'en.", med_vaerktoej=False)
    _tur(db, "s1", "vision", 20, "Lad mig hente loggen.", med_vaerktoej=False)
    _tur(db, "s1", "flash", 30, "Lad mig tjekke config'en.", med_vaerktoej=True)
    pr_model = {m["model"]: m for m in hpc.census(24)["models"]}
    assert pr_model["vision"]["hollow_pct"] == 100.0
    assert pr_model["flash"]["hollow_pct"] == 0.0


def test_escaped_er_dem_vaernet_IKKE_greb(db):
    """Tallet der betyder noget. Et værn der fanger 12 af 31 ser perfekt ud
    hvis man kun tæller sine egne fangster."""
    for i, minut in enumerate((10, 20, 30)):
        _tur(db, "s1", "vision", minut, "Lad mig tjekke config'en.", med_vaerktoej=False)
    db.execute("INSERT INTO events VALUES (?,?,?)",
               ("runtime.hollow_promise_detected", "{}", _tid(11)))
    db.commit()
    r = hpc.census(24)
    assert r["hollow_total"] == 3
    assert r["guard_detected"] == 1
    assert r["escaped"] == 2


def test_overlappende_runs_taeller_ikke_samme_svar_flere_gange(db):
    """Første udgave brugte et JOIN og matchede ét svar mod hvert overlappende
    run — 1.959 «ture» hvor der var nogle få snese."""
    _tur(db, "s1", "vision", 10, "Lad mig tjekke config'en.", med_vaerktoej=False)
    db.execute("INSERT INTO visible_runs VALUES (?,?,?,?)",
               ("run-overlap", "flash", _tid(9), _tid(30)))
    db.commit()
    r = hpc.census(24)
    assert sum(m["turns"] for m in r["models"]) == 1


def test_en_daarlig_database_giver_tomt_svar_ikke_en_exception(monkeypatch):
    monkeypatch.setattr(hpc, "connect",
                        lambda: (_ for _ in ()).throw(RuntimeError("nede")))
    r = hpc.census(24)
    assert r["available"] is False and r["models"] == []
