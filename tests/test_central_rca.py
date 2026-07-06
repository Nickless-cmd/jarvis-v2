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
