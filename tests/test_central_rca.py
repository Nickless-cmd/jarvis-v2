import sqlite3
from unittest import mock
import pytest
from core.services import central_rca as rca


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "r.db")

    def _connect():
        c = sqlite3.connect(path); c.row_factory = sqlite3.Row; return c

    with mock.patch("core.services.central_rca.connect", side_effect=_connect), \
            mock.patch("core.services.central_rca._observe"):
        yield


def _inc(i, sev, cluster, nerve, resolved=0, msg="boom"):
    return {"id": i, "severity": sev, "cluster": cluster, "nerve": nerve,
            "resolved": resolved, "message": msg}


def test_pick_incident_highest_severity(db):
    rows = [_inc(1, "warning", "a", "x"), _inc(2, "severe", "b", "y"), _inc(3, "error", "c", "z")]
    with mock.patch("core.runtime.db_central_incidents.list_central_incidents", return_value=rows):
        pick = rca.pick_incident()
    assert pick["id"] == 2 and pick["severity"] == "severe"


def test_investigate_detects_recurring_pattern(db):
    rows = [_inc(i, "error", "loop", "veto") for i in range(1, 5)]   # 4 på samme nerve
    with mock.patch("core.runtime.db_central_incidents.list_central_incidents", return_value=rows):
        r = rca.investigate()
    assert r["ok"] and r["recurring"] is True
    assert "tilbagevendende" in r["probable_cause"]
    assert "central_surgery" in r["recommendation"]


def test_investigate_single_event(db):
    rows = [_inc(9, "severe", "net", "health")]
    with mock.patch("core.runtime.db_central_incidents.list_central_incidents", return_value=rows):
        r = rca.investigate()
    assert r["ok"] and r["recurring"] is False and "enkeltstående" in r["probable_cause"]


def test_investigate_persists_and_lists(db):
    rows = [_inc(5, "error", "c", "n")]
    with mock.patch("core.runtime.db_central_incidents.list_central_incidents", return_value=rows):
        rca.investigate()
    lst = rca.list_rca()
    assert lst and lst[0]["incident_id"] == 5 and lst[0]["status"] == "draft"


def test_no_incident_is_safe(db):
    with mock.patch("core.runtime.db_central_incidents.list_central_incidents", return_value=[]):
        assert rca.investigate()["ok"] is False


# ── Gentaget mønster → bindende forpligtelse (13/11-2026) ────────────────────
#
# Målt i drift: 15 uløste incidents, hvoraf 6 lå på `proactivity/verification`
# og 4 på `privacy/cross_user_share`. `pick_incident()` valgte ÉN og kiggede
# aldrig på at de øvrige var samme fejl — så hver undersøgelse startede forfra,
# og `record_rca` observerede kun et tal. En nerve der fejler seks gange er ikke
# seks hændelser, det er én systemisk fejl.


def test_recurring_nerves_finder_kun_de_gentagne(db):
    rows = ([_inc(i, "info", "proactivity", "verification") for i in range(1, 7)]
            + [_inc(i, "info", "privacy", "cross_user_share") for i in range(10, 14)]
            + [_inc(20, "error", "net", "health")])
    with mock.patch("core.runtime.db_central_incidents.list_central_incidents", return_value=rows):
        rec = rca.recurring_nerves()
    assert len(rec) == 2, "en enkeltstaaende nerve er ikke et moenster"
    assert rec[0]["nerve"] == "verification" and rec[0]["unresolved"] == 6
    assert rec[1]["nerve"] == "cross_user_share" and rec[1]["unresolved"] == 4


def test_recurring_nerves_taersklen_er_tre(db):
    rows = [_inc(1, "info", "a", "b"), _inc(2, "info", "a", "b")]
    with mock.patch("core.runtime.db_central_incidents.list_central_incidents", return_value=rows):
        assert rca.recurring_nerves() == [], "to er ikke et moenster"


def test_record_rca_lader_moenstret_lande(db):
    """Fundet skal blive en forpligtelse — og evidensen skal bære det målte tal
    OG sin kilde, ellers dømmer støj-vetoet et målt fund som støj."""
    rows = [_inc(i, "info", "proactivity", "verification") for i in range(1, 7)]
    kaldt = []

    def _fake_land(*a, **kw):
        kaldt.append((a, kw))
        return {"applied": True, "decision_id": "dec_x"}

    with mock.patch("core.runtime.db_central_incidents.list_central_incidents", return_value=rows), \
            mock.patch("core.runtime.db_central_incidents.count_unresolved", return_value=6), \
            mock.patch("core.services.central_consequence.land_decision", side_effect=_fake_land):
        out = rca.record_rca()

    assert out["landing"]["applied"] is True, out
    assert kaldt, "et gentaget moenster skal lande — ikke blot observeres"
    cid, directive = kaldt[0][0][0], kaldt[0][0][1]
    assert cid == "rca"
    assert "verification" in directive
    kw = kaldt[0][1]
    assert "uloeste=6" in (kw.get("evidence") or ""), "evidensen skal baere det maalte tal"
    assert kw.get("evidence_source"), "en maaling uden kilde er ikke evidens"
    assert kw.get("subject") == "recurring:proactivity/verification", "idempotens kraever et stabilt emne"


def test_record_rca_lander_ikke_uden_moenster(db):
    rows = [_inc(1, "info", "a", "b"), _inc(2, "info", "c", "d")]
    with mock.patch("core.runtime.db_central_incidents.list_central_incidents", return_value=rows), \
            mock.patch("core.runtime.db_central_incidents.count_unresolved", return_value=2):
        out = rca.record_rca()
    assert "landing" not in out, "to enkeltstaaende incidents er ikke et moenster"
