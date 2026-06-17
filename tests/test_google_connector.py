"""Google-pakke-connector: Calendar/Drive/Docs/Sheets/Slides (mocket httpx)."""
from __future__ import annotations

import httpx

import core.services.google_connector as gc


class _Resp:
    def __init__(self, status: int, payload: dict):
        self.status_code = status
        self._payload = payload

    def json(self) -> dict:
        return self._payload


def _ok(monkeypatch, payload):
    monkeypatch.setattr(gc, "get_fresh_token", lambda uid, prov: {"access_token": "tok"})
    monkeypatch.setattr(httpx, "get", lambda url, headers=None, params=None, timeout=None: _Resp(200, payload))


def test_list_events(monkeypatch):
    _ok(monkeypatch, {"items": [
        {"id": "e1", "summary": "Tandlæge", "start": {"dateTime": "2026-06-18T09:00:00Z"},
         "location": "Klinik", "htmlLink": "http://x"},
    ]})
    res = gc.list_events("bjorn", max_results=5)
    assert res["status"] == "ok" and res["count"] == 1
    assert res["events"][0]["summary"] == "Tandlæge"


def test_drive_search(monkeypatch):
    _ok(monkeypatch, {"files": [
        {"id": "f1", "name": "Budget.xlsx", "mimeType": "application/vnd.ms-excel",
         "modifiedTime": "2026-06-01", "webViewLink": "http://d"},
    ]})
    res = gc.drive_search("bjorn", query="budget")
    assert res["status"] == "ok" and res["files"][0]["name"] == "Budget.xlsx"


def test_docs_read_extracts_text(monkeypatch):
    _ok(monkeypatch, {"title": "Notat", "body": {"content": [
        {"paragraph": {"elements": [{"textRun": {"content": "Hej "}}, {"textRun": {"content": "verden\n"}}]}},
    ]}})
    res = gc.docs_read("bjorn", "doc123")
    assert res["status"] == "ok" and res["title"] == "Notat"
    assert res["text"] == "Hej verden"


def test_sheets_read(monkeypatch):
    _ok(monkeypatch, {"range": "Ark1!A1:B2", "values": [["a", "b"], ["1", "2"]]})
    res = gc.sheets_read("bjorn", "sheet123", "Ark1!A1:B2")
    assert res["status"] == "ok" and res["values"] == [["a", "b"], ["1", "2"]]


def test_slides_read_counts_and_text(monkeypatch):
    _ok(monkeypatch, {"title": "Pitch", "slides": [
        {"pageElements": [{"shape": {"text": {"textElements": [{"textRun": {"content": "Forside"}}]}}}]},
        {"pageElements": []},
    ]})
    res = gc.slides_read("bjorn", "pres123")
    assert res["status"] == "ok" and res["slide_count"] == 2
    assert res["slides"][0]["text"] == "Forside"


def test_no_token(monkeypatch):
    monkeypatch.setattr(gc, "get_fresh_token", lambda uid, prov: None)
    assert gc.list_events("bjorn")["error"] == "calendar_not_connected"


def test_403_scope_missing(monkeypatch):
    monkeypatch.setattr(gc, "get_fresh_token", lambda uid, prov: {"access_token": "tok"})
    monkeypatch.setattr(httpx, "get", lambda url, headers=None, params=None, timeout=None: _Resp(403, {}))
    assert gc.drive_search("bjorn")["error"] == "drive_scope_missing"


def test_required_ids(monkeypatch):
    monkeypatch.setattr(gc, "get_fresh_token", lambda uid, prov: {"access_token": "tok"})
    assert gc.docs_read("bjorn", "")["error"] == "document_id_required"
    assert gc.sheets_read("bjorn", "s", "")["error"] == "range_required"
    assert gc.slides_read("bjorn", "")["error"] == "presentation_id_required"
