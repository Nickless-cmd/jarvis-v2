"""Tredje gren: et run der ALDRIG har kostet noget.

Bjørn 3/10-2026: genstarts-vagten sagde «IKKE genstartet: 1 aktive» i over en
time. Rækken var `visible-5c75993a`, status `running` siden 17:03:50 — men dens
eneste event var startøjeblikket, den havde INGEN omkostninger, og den var tavs
i 61 minutter mens samtalen fortsatte.

`_ryd_visible_drift` fandtes allerede og er bygget mod præcis den slags, men
dens alders-grænse er seks timer, fordi fravær fra `in_flight_runs` er et svagt
bevis. En række uden ÉN `costs`-post bærer sit eget, uafhængige bevis — og to
uafhængige fravær tåler en kortere alder.

Testene her kører mod en RIGTIG sqlite, så det er SQL'en der måles. Den
eksisterende drift-test fakeer forbindelsen og returnerer rækker uanset
forespørgslen; den kan derfor ikke se en gren.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from core.services import session_boot_reconciler as sbr


def _iso(minutter_siden: float) -> str:
    return (datetime.now(UTC) - timedelta(minutes=minutter_siden)).isoformat()


@pytest.fixture
def db(monkeypatch, tmp_path):
    sti = tmp_path / "t.db"
    c = sqlite3.connect(sti)
    c.execute("CREATE TABLE visible_runs (run_id TEXT, status TEXT, "
              "started_at TEXT, finished_at TEXT)")
    c.execute("CREATE TABLE costs (run_id TEXT)")
    c.commit(); c.close()

    import contextlib

    @contextlib.contextmanager
    def _connect():
        k = sqlite3.connect(sti)
        k.row_factory = sqlite3.Row
        try:
            yield k
            k.commit()
        finally:
            k.close()

    import core.runtime.db as _db
    monkeypatch.setattr(_db, "connect", _connect)
    # Intet kendes af det andet lager → fraværet gælder.
    monkeypatch.setattr(sbr.in_flight_runs, "_load", lambda: {})
    # Stemplerne importeres LOKALT i loekken (importen er cirkulaer med vilje),
    # saa vagten skal sidde paa deres eget modul — `sbr` har dem aldrig.
    import core.services.visible_runs_outcomes as vro
    stemplet: list[str] = []
    monkeypatch.setattr(vro, "stamp_visible_run_interrupted",
                        lambda rid, reason="": stemplet.append(rid))
    monkeypatch.setattr(vro, "stamp_visible_run_superseded",
                        lambda rid, reason="": stemplet.append(rid))

    def _tilfoej(run_id, status, alder_min, finished=None, med_omkostning=False):
        k = sqlite3.connect(sti)
        k.execute("INSERT INTO visible_runs VALUES (?,?,?,?)",
                  (run_id, status, _iso(alder_min), finished))
        if med_omkostning:
            k.execute("INSERT INTO costs VALUES (?)", (run_id,))
        k.commit(); k.close()

    return {"tilfoej": _tilfoej, "stemplet": stemplet}


def test_zombien_uden_omkostninger_fanges_efter_30_min(db):
    """Selve fejlen han saa. 61 minutter, ingen omkostninger — og den stod
    uroert fordi den seks timers graense ikke var naaet."""
    db["tilfoej"]("visible-5c75993a", "running", 61)
    assert sbr._ryd_visible_drift(True) == 1
    assert db["stemplet"] == ["visible-5c75993a"]


def test_et_LEVENDE_run_med_omkostninger_roeres_IKKE(db):
    """Den afgoerende forskel. Et run der har lavet model-kald er i gang,
    uanset hvor laenge det har varet — maalt: 64 af 64 gennemfoerte runs havde
    omkostninger, og en tur kan sagtens tage ti minutter."""
    db["tilfoej"]("visible-levende", "running", 120, med_omkostning=True)
    assert sbr._ryd_visible_drift(True) == 0
    assert db["stemplet"] == []


def test_et_UNGT_run_uden_omkostninger_roeres_ikke(db):
    """Et run der lige er startet har endnu ikke naaet sit foerste kald."""
    db["tilfoej"]("visible-ny", "running", 2)
    assert sbr._ryd_visible_drift(True) == 0


def test_graensen_er_praecis(db):
    db["tilfoej"]("visible-lige-under", "running",
                  sbr._UDEN_OMKOSTNING_MINUTTER - 1)
    assert sbr._ryd_visible_drift(True) == 0
    db["tilfoej"]("visible-lige-over", "running",
                  sbr._UDEN_OMKOSTNING_MINUTTER + 1)
    assert sbr._ryd_visible_drift(True) == 1
    assert db["stemplet"] == ["visible-lige-over"]


def test_den_SEKS_TIMERS_gren_gaelder_stadig(db):
    """Den gamle regel maa ikke forsvinde: et gammelt run MED omkostninger
    fanges stadig af alderen alene."""
    db["tilfoej"]("visible-gammel", "running", 60 * 7, med_omkostning=True)
    assert sbr._ryd_visible_drift(True) == 1


def test_skygge_skriver_IKKE(db):
    """Samme kontakt som resten af reconcileren."""
    db["tilfoej"]("visible-zombie", "running", 61)
    assert sbr._ryd_visible_drift(False) == 1
    assert db["stemplet"] == [], "der blev stemplet i skygge-tilstand"


def test_en_raekke_der_KENDES_af_det_andet_lager_roeres_ikke(db, monkeypatch):
    """Fravaer er hele beviset. Kendes posten, er der en proces der streamer."""
    db["tilfoej"]("visible-kendt", "running", 61)
    monkeypatch.setattr(sbr.in_flight_runs, "_load",
                        lambda: {"x": {"run_id": "visible-kendt"}})
    assert sbr._ryd_visible_drift(True) == 0
