"""Sentinel — et angreb der ikke kan flytte noget er en mening, ikke en handling.

Målt 13/11-2026: `attack()` regnede `proposed_confidence = conf / 2.0` ud,
gemte den i en kolonne der hed `proposed_`, og skrev ALDRIG tilbage. `_enforced()`
var en shadow-flag der var slukket — og der fandtes ingen kode bag den, så
«håndhævelse» var en gren der ikke eksisterede.

Angrebet var altså et forslag i en tabel ingen læser. Det er samme fejlform som
Smiths «Trin 2 — bundet» uden en binding: en tilstand der påstår en handling der
ikke findes.

Disse tests holder på at angrebet LANDER — og at det stadig kan afvises ærligt.
"""

from __future__ import annotations

import sqlite3
from unittest import mock

import pytest

from core.services import central_sentinel as sn


@pytest.fixture
def hyp(monkeypatch):
    """Én aktiv hypotese i en isoleret base — aldrig produktionens."""
    sti = "/tmp/test_sentinel_hyp.db"

    def _connect():
        conn = sqlite3.connect(sti)
        conn.row_factory = sqlite3.Row
        return conn

    with _connect() as c:
        c.execute("DROP TABLE IF EXISTS central_hypotheses")
        c.execute(
            """CREATE TABLE central_hypotheses (
                hyp_id TEXT PRIMARY KEY, source TEXT, statement TEXT,
                confidence REAL, status TEXT, resolved_at TEXT)"""
        )
        c.execute(
            "INSERT INTO central_hypotheses VALUES (?,?,?,?,?,?)",
            ("clh-top", "dream", "En hypotese der kan angribes", 0.80, "active", None),
        )
        c.commit()

    monkeypatch.setattr(sn, "connect", _connect)
    return _connect


def _conf(connect) -> float:
    with connect() as c:
        return float(c.execute(
            "SELECT confidence FROM central_hypotheses WHERE hyp_id='clh-top'"
        ).fetchone()[0])


def test_angrebet_flytter_confidence(hyp):
    """Den afgørende kontrakt: et angreb skal ændre noget der lever."""
    kaldt = {}

    def _land(cid, hyp_id, **kw):
        kaldt["cid"], kaldt["hyp_id"] = cid, hyp_id
        with hyp() as c:
            c.execute("UPDATE central_hypotheses SET confidence=0.4 WHERE hyp_id=?", (hyp_id,))
            c.commit()
        return {"applied": True, "before": 0.8, "after": 0.4, "reason": "falsified"}

    with mock.patch("core.services.central_consequence.land_confidence", _land), \
         mock.patch.object(sn, "_observe"):
        r = sn.attack()

    assert r["ok"] is True
    assert kaldt == {"cid": "sentinel", "hyp_id": "clh-top"}
    assert r["applied"] is True
    assert r["confidence_after"] == 0.4
    assert _conf(hyp) == pytest.approx(0.4), "vaerdien skal staa i basen, ikke kun i returen"


def test_en_afvist_landing_rapporteres_aerligt(hyp):
    """`applied=False` med en grund er et rigtigt svar. En tavs no-op er ikke."""
    def _land(*_a, **_k):
        return {"applied": False, "before": 0.8, "after": None,
                "reason": "dagsloft ramt (8/8)"}

    with mock.patch("core.services.central_consequence.land_confidence", _land), \
         mock.patch.object(sn, "_observe"):
        r = sn.attack()

    assert r["ok"] is True
    assert r["applied"] is False
    assert "dagsloft" in str(r["reason"])
    assert _conf(hyp) == pytest.approx(0.8), "en afvist landing må ikke have flyttet noget"


def test_forslaget_beregnes_stadig_og_rapporteres(hyp):
    """Forslaget er stadig information — det er bare ikke længere ALT der sker."""
    with mock.patch("core.services.central_consequence.land_confidence",
                    lambda *_a, **_k: {"applied": False, "reason": "switch"}), \
         mock.patch.object(sn, "_observe"):
        r = sn.attack()
    assert r["confidence_before"] == pytest.approx(0.8)
    assert r["proposed_confidence"] == pytest.approx(0.4)


def test_uden_hypotese_angribes_intet(monkeypatch):
    def _connect():
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute(
            """CREATE TABLE central_hypotheses (
                hyp_id TEXT, source TEXT, statement TEXT, confidence REAL,
                status TEXT, resolved_at TEXT)"""
        )
        return conn

    monkeypatch.setattr(sn, "connect", _connect)
    r = sn.attack()
    assert r["ok"] is False
    assert "ingen hypotese" in str(r["reason"])
