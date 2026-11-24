"""Måleværktøjet for koordinering §8: nøgler, nul vs. 'kan ikke måles', read-only."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

_STI = Path(__file__).resolve().parent.parent / "scripts" / "koordinering_maaling.py"
_spec = importlib.util.spec_from_file_location("koordinering_maaling", _STI)
km = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(km)

NU = datetime.now(UTC)


def _iso(min_siden: float = 0) -> str:
    return (NU - timedelta(minutes=min_siden)).isoformat()


@pytest.fixture
def db(tmp_path):
    p = tmp_path / "jarvis.db"
    c = sqlite3.connect(p)
    c.executescript(
        """
        CREATE TABLE events (id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, payload_json TEXT, created_at TEXT);
        CREATE TABLE runtime_initiatives (id INTEGER PRIMARY KEY AUTOINCREMENT, initiative_id TEXT, focus TEXT,
            status TEXT, disposition_reason TEXT DEFAULT '', detected_at TEXT, updated_at TEXT DEFAULT '',
            next_attempt_at TEXT DEFAULT '', blocked_reason TEXT DEFAULT '');
        CREATE TABLE runtime_tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT, kind TEXT, origin TEXT,
            status TEXT, origin_ref TEXT DEFAULT '', updated_at TEXT DEFAULT '');
        """
    )
    c.commit()
    c.close()
    return p


def _kør(db, hours=24):
    conn = km.åbn_readonly(db)
    try:
        return km.mål(conn, hours, NU)
    finally:
        conn.close()


def test_returnerer_de_ni_noegler_med_kilde_og_funktion(db):
    res = _kør(db)
    assert set(res) == set(km.NØGLER) and len(res) == 9
    for m in res.values():
        assert m["kilde"] and m["funktion"] and m["hvordan"]
        assert (m["værdi"] is None) == (m["kan_ikke_måles"] is not None)


def test_uden_beslutningsevents_er_det_kan_ikke_maales_ikke_nul(db):
    res = _kør(db)
    for nøgle in (km.NØGLER[2], km.NØGLER[6], km.NØGLER[7]):
        assert res[nøgle]["værdi"] is None
        assert "coordination.decision" in res[nøgle]["kan_ikke_måles"]
    # Målinger der ikke hviler på eventet må godt give et ægte nul.
    assert res[km.NØGLER[0]]["værdi"] == 0
    assert res[km.NØGLER[3]]["værdi"] == 0
    # Principielt umålelige forbliver umålelige.
    assert res[km.NØGLER[4]]["værdi"] is None
    assert res[km.NØGLER[5]]["værdi"] is None


def test_med_beslutningsevent_bliver_maalt_nul_til_et_rigtigt_nul(db):
    c = sqlite3.connect(db)
    c.execute("INSERT INTO events (kind,payload_json,created_at) VALUES (?,?,?)",
              ("coordination.decision",
               json.dumps({"decision": "accepted", "reason": "ny-handling"}), _iso(5)))
    c.commit(); c.close()
    res = _kør(db)
    assert res[km.NØGLER[7]]["værdi"] == 0          # målt: ingen race
    assert res[km.NØGLER[6]]["værdi"] == 0          # målt: ingen coordinated
    assert res[km.NØGLER[2]]["værdi"] == 0.0        # 0 af 1 beslutninger


def test_taeller_coordinated_og_race(db):
    c = sqlite3.connect(db)
    for d, r in (("coordinated", "tabt-klaim-race"), ("coordinated", "x"), ("accepted", "ny-handling")):
        c.execute("INSERT INTO events (kind,payload_json,created_at) VALUES (?,?,?)",
                  ("coordination.decision",
                   json.dumps({"decision": d, "reason": r, "covering": {"ref": "t1"} if d == "coordinated" else {}}),
                   _iso(5)))
    c.commit(); c.close()
    res = _kør(db)
    assert res[km.NØGLER[6]]["værdi"] == 2
    assert res[km.NØGLER[7]]["værdi"] == 1
    assert res[km.NØGLER[2]]["tæller"] == 2 and res[km.NØGLER[2]]["nævner"] == 3


def test_selvstaendige_runs_og_fastsiddende(db):
    c = sqlite3.connect(db)
    c.execute("INSERT INTO runtime_initiatives (initiative_id,focus,status,detected_at) VALUES ('i1','a','acted',?)", (_iso(10),))
    c.execute("INSERT INTO runtime_initiatives (initiative_id,focus,status,detected_at) VALUES ('i2','b','pending',?)", (_iso(60 * 8),))
    c.execute("INSERT INTO runtime_tasks (task_id,kind,origin,status,origin_ref) VALUES ('t','initiative-followup','heartbeat:initiative','running','tick|i1')")
    c.commit(); c.close()
    res = _kør(db, hours=24)
    assert res[km.NØGLER[0]]["værdi"] == 2
    assert res[km.NØGLER[1]]["værdi"] == 0.5
    assert res[km.NØGLER[8]]["pending_gamle"] == 1


def test_ingen_initiativer_giver_kan_ikke_maales_for_andel(db):
    assert _kør(db)[km.NØGLER[1]]["værdi"] is None


def _hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_skriver_ikke_til_databasen(db, capsys):
    før = _hash(db)
    assert km.main(["--db", str(db), "--json"]) == 0
    assert _hash(db) == før
    assert len(json.loads(capsys.readouterr().out)["målinger"]) == 9
    # Selve forbindelsen afviser skrivning.
    conn = km.åbn_readonly(db)
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("INSERT INTO events (kind,payload_json,created_at) VALUES ('x','{}','')")
    conn.close()
