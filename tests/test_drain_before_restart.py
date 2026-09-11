"""En genstart midt i en tur koster syv runder. Gaten skal ikke gætte.

Målt 11/9-2026: `--timeout-graceful-shutdown 30` lod turen køre runde 3 → 10
EFTER shutdown-signalet, og smed derefter det hele væk. Gaten her er den
eneste vej der både sparer de 30 sekunder og redder runderne.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from scripts.drain_before_restart import levende, vent


def _db(tmp_path, value: dict | None, alder_s: float = 1.0, navn: str = "t.db") -> str:
    sti = str(tmp_path / navn)
    con = sqlite3.connect(sti)
    con.execute("CREATE TABLE runtime_state_kv (key TEXT PRIMARY KEY, "
                "value_json TEXT, updated_at TEXT)")
    if value is not None:
        t = (datetime.now(UTC) - timedelta(seconds=alder_s)).isoformat()
        con.execute("INSERT INTO runtime_state_kv VALUES (?,?,?)",
                    ("visible_runs.active_run", json.dumps(value), t))
    con.commit()
    con.close()
    return sti


def test_levende_tur_spaerrer(tmp_path):
    assert levende(_db(tmp_path, {"active": True})) is True


def test_uanset_hvilken_session_det_er(tmp_path):
    """Gaten spoerger «lever NOGET» — ikke «lever denne session».

    Noeglen holder ét run ad gangen, saa et samtidigt autonomt run kan staa der
    i stedet for den synlige tur. For en genstart er det lige meget hvis tur
    det er; alt levende arbejde tabes."""
    db = _db(tmp_path, {"active": True, "session_id": "en-helt-anden"})
    assert levende(db) is True


def test_gammelt_livstegn_er_ikke_levende(tmp_path):
    assert levende(_db(tmp_path, {"active": True}, alder_s=600)) is False


def test_inaktiv_og_tom_er_frit(tmp_path):
    assert levende(_db(tmp_path, {"active": False}, navn="a.db")) is False
    assert levende(_db(tmp_path, None, navn="b.db")) is False


def test_db_hikke_er_UAFGJORT_ikke_frit(tmp_path):
    """Den farlige retning. Laeses en fejl som «frit», koerer genstarten
    praecis naar vi er mindst sikre paa at den er ufarlig."""
    assert levende(str(tmp_path / "findes-ikke.db")) is None


def test_vent_giver_op_paa_uafgjort_uden_at_kalde_det_frit(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.drain_before_restart.POLL_SEKUNDER", 0.0)
    kode = vent(loft=5.0, db=str(tmp_path / "findes-ikke.db"))
    assert kode == 2, "uafgjort maa hverken blive 0 (frit) eller 1 (optaget)"


def test_vent_melder_optaget_naar_loftet_naas(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.drain_before_restart.POLL_SEKUNDER", 0.0)
    assert vent(loft=0.0, db=_db(tmp_path, {"active": True})) == 1
