"""Huskesedler-connector: per-bruger add/list/search/delete + isolation."""
from __future__ import annotations

import core.services.notes_connector as nc


def _patch(monkeypatch):
    store: dict = {}
    import core.runtime.db_core as dbc
    monkeypatch.setattr(dbc, "get_runtime_state_value", lambda k, d=None: store.get(k, d))
    monkeypatch.setattr(dbc, "set_runtime_state_value", lambda k, v, **kw: store.__setitem__(k, v))
    return store


def test_add_list_roundtrip(monkeypatch):
    _patch(monkeypatch)
    r = nc.add_note("bjorn", "Køb mælk", now=1000.0)
    assert r["status"] == "ok" and r["id"] == "n1000000"
    nc.add_note("bjorn", "Ring til mor", now=1001.0)
    lst = nc.list_notes("bjorn")
    assert lst["count"] == 2
    assert lst["notes"][0]["text"] == "Ring til mor"  # nyeste først


def test_isolation(monkeypatch):
    _patch(monkeypatch)
    nc.add_note("bjorn", "hemmelig", now=1.0)
    assert nc.list_notes("mikkel")["count"] == 0


def test_search(monkeypatch):
    _patch(monkeypatch)
    nc.add_note("bjorn", "Budget Q3", now=1.0)
    nc.add_note("bjorn", "Tandlæge", now=2.0)
    res = nc.search_notes("bjorn", "budget")
    assert res["count"] == 1 and res["notes"][0]["text"] == "Budget Q3"


def test_delete(monkeypatch):
    _patch(monkeypatch)
    nid = nc.add_note("bjorn", "slet mig", now=1.0)["id"]
    assert nc.delete_note("bjorn", nid)["status"] == "ok"
    assert nc.list_notes("bjorn")["count"] == 0
    assert nc.delete_note("bjorn", nid)["error"] == "not_found"


def test_validation(monkeypatch):
    _patch(monkeypatch)
    assert nc.add_note("bjorn", "  ")["error"] == "text_required"
    assert nc.search_notes("bjorn", "")["error"] == "query_required"
