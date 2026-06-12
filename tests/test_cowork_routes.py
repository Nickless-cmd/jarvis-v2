import pytest
from fastapi.testclient import TestClient
from apps.api.jarvis_api.app import create_app
from apps.api.jarvis_api.routes import cowork as cowork_routes


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(cowork_routes.cowork_feed, "build_queue", lambda **k: [
        {"id": "x", "kind": "initiative", "title": "T", "detail": "", "user_id": "owner", "source": "initiative"},
    ])
    monkeypatch.setattr(cowork_routes.cowork_feed, "list_plans", lambda **k: [])
    monkeypatch.setattr(cowork_routes, "_role_owner", lambda: (True, "owner"))
    return TestClient(create_app())


def test_queue_returns_items(client):
    r = client.get("/cowork/queue")
    assert r.status_code == 200
    assert r.json()["items"][0]["id"] == "x"


def test_plans_returns_list(client):
    r = client.get("/cowork/plans")
    assert r.status_code == 200
    assert r.json()["plans"] == []


def test_channels_owner_ok(monkeypatch, client):
    monkeypatch.setattr(cowork_routes.cowork_feed, "channel_status", lambda: [{"name": "discord", "online": True, "unread": 0}])
    r = client.get("/cowork/channels")
    assert r.status_code == 200
    assert r.json()["channels"][0]["name"] == "discord"


def test_channels_member_403(monkeypatch):
    monkeypatch.setattr(cowork_routes, "_role_owner", lambda: (False, "mikkel"))
    monkeypatch.setattr(cowork_routes.cowork_feed, "channel_status", lambda: [])
    c = TestClient(create_app())
    assert c.get("/cowork/channels").status_code == 403


def test_approve_routes_to_resolver(monkeypatch, client):
    called = {}
    monkeypatch.setattr(cowork_routes, "_resolve_item", lambda item_id, decision: called.update(id=item_id, d=decision) or {"status": "ok"})
    r = client.post("/cowork/queue/x/approve")
    assert r.status_code == 200
    assert called == {"id": "x", "d": "approve"}


def test_reject_routes_to_resolver(monkeypatch, client):
    monkeypatch.setattr(cowork_routes, "_resolve_item", lambda item_id, decision: {"status": "ok", "decision": decision})
    r = client.post("/cowork/queue/x/reject")
    assert r.json()["decision"] == "reject"
