from fastapi import FastAPI
from fastapi.testclient import TestClient

import apps.api.jarvis_api.routes.presence as presence_routes
import core.services.device_presence as dp
import core.services.desktop_notifications as dn
import core.services.proactive_router as pr


def _client(monkeypatch):
    monkeypatch.setattr(presence_routes, "_current_user", lambda: "bjorn")
    app = FastAPI()
    app.include_router(presence_routes.router)
    return TestClient(app)


def test_ping_records_presence(monkeypatch):
    monkeypatch.setattr(dp, "_now", lambda: 1000.0)
    dp.reset()
    c = _client(monkeypatch)
    r = c.post("/presence/ping", json={"device_key": "desk", "platform": "desktop",
                                       "foreground": True, "awake": True, "network": "home", "interaction": True})
    assert r.status_code == 200 and r.json()["ok"] is True
    assert "desk" in dp._PRESENCE["bjorn"]


def test_pending_drains_desktop_queue(monkeypatch):
    monkeypatch.setattr(dn, "_now", lambda: 1000.0)
    dn.reset()
    dn.enqueue("bjorn", {"notif_id": "n1", "kind": "answer_ready", "title": "t", "body": "b", "session_id": "s1"})
    c = _client(monkeypatch)
    r = c.get("/notifications/pending")
    assert r.status_code == 200
    assert [i["notif_id"] for i in r.json()["items"]] == ["n1"]


def test_ack_cancels_pending(monkeypatch):
    pr.reset()
    pr._PENDING["n1"] = {"user_id": "bjorn", "payload": {}, "kind": "x", "remaining": [], "timer": None}
    c = _client(monkeypatch)
    r = c.post("/notifications/ack", json={"notif_id": "n1"})
    assert r.status_code == 200 and "n1" not in pr._PENDING
