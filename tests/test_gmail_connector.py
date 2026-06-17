"""Gmail-connector: search/list via brugerens egen token (mocket httpx)."""
from __future__ import annotations

import httpx

import core.services.gmail_connector as gc


class _Resp:
    def __init__(self, status: int, payload: dict):
        self.status_code = status
        self._payload = payload

    def json(self) -> dict:
        return self._payload


def _mock_http(monkeypatch, list_payload, detail_payload, *, list_status=200, detail_status=200):
    calls = {"n": 0}

    def fake_get(url, headers=None, params=None, timeout=None):
        calls["n"] += 1
        if "/messages/" in url:  # detail-kald
            return _Resp(detail_status, detail_payload)
        return _Resp(list_status, list_payload)  # liste-kald

    monkeypatch.setattr(httpx, "get", fake_get)
    return calls


def test_search_returns_enriched_messages(monkeypatch):
    monkeypatch.setattr(gc, "get_fresh_token", lambda uid, prov: {"access_token": "tok"})
    _mock_http(
        monkeypatch,
        {"messages": [{"id": "m1"}]},
        {"snippet": "Hej Bjørn", "labelIds": ["UNREAD"],
         "payload": {"headers": [
             {"name": "Subject", "value": "Møde i morgen"},
             {"name": "From", "value": "chef@firma.dk"},
             {"name": "Date", "value": "Tue, 17 Jun 2026"},
         ]}},
    )
    res = gc.search("bjorn", "is:unread", max_results=5)
    assert res["status"] == "ok"
    assert res["count"] == 1
    m = res["messages"][0]
    assert m["subject"] == "Møde i morgen"
    assert m["from"] == "chef@firma.dk"
    assert m["unread"] is True
    assert m["snippet"] == "Hej Bjørn"


def test_no_token_is_not_connected(monkeypatch):
    monkeypatch.setattr(gc, "get_fresh_token", lambda uid, prov: None)
    res = gc.list_inbox("bjorn")
    assert res == {"status": "error", "error": "gmail_not_connected"}


def test_403_maps_to_scope_missing(monkeypatch):
    monkeypatch.setattr(gc, "get_fresh_token", lambda uid, prov: {"access_token": "tok"})
    _mock_http(monkeypatch, {}, {}, list_status=403)
    res = gc.list_inbox("bjorn")
    assert res["status"] == "error" and res["error"] == "gmail_scope_missing"


def test_empty_query_rejected(monkeypatch):
    monkeypatch.setattr(gc, "get_fresh_token", lambda uid, prov: {"access_token": "tok"})
    assert gc.search("bjorn", "   ")["error"] == "query_required"


def test_max_results_clamped(monkeypatch):
    monkeypatch.setattr(gc, "get_fresh_token", lambda uid, prov: {"access_token": "tok"})
    seen = {}

    def fake_get(url, headers=None, params=None, timeout=None):
        if "/messages/" not in url:
            seen["maxResults"] = params.get("maxResults")
        return _Resp(200, {"messages": []})

    monkeypatch.setattr(httpx, "get", fake_get)
    gc.list_inbox("bjorn", max_results=999)
    assert seen["maxResults"] == 25  # klemt til 25
