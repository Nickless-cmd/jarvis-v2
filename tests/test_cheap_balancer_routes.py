"""Tests for /mc/cheap-balancer endpoints."""
from __future__ import annotations
from fastapi.testclient import TestClient
import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_state_path", lambda: tmp_path / "s.json")
    monkeypatch.setattr(clb, "build_slot_pool", lambda: [])

    from apps.api.jarvis_api.app import create_app
    return TestClient(create_app())


def test_get_state_returns_pool_summary(client):
    r = client.get("/mc/cheap-balancer-state")
    assert r.status_code == 200
    data = r.json()
    assert "pool_size" in data
    assert "slots" in data
    assert "recent_calls" in data


def test_post_reset_slot(client, tmp_path, monkeypatch):
    from core.services import cheap_lane_balancer as clb
    state = clb.SlotState(slot_id="groq::m", breaker_level=2, consecutive_failures=5)
    clb._save_state({"groq::m": state})

    r = client.post("/mc/cheap-balancer/slot/groq::m/reset")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    loaded = clb._load_state()
    assert loaded["groq::m"].breaker_level == 0


def test_post_disable_slot(client):
    r = client.post("/mc/cheap-balancer/slot/groq::m/disable")
    assert r.status_code == 200
    assert r.json()["manually_disabled"] is True


def test_post_enable_slot(client):
    from core.services import cheap_lane_balancer as clb
    clb._save_state({"groq::m": clb.SlotState(slot_id="groq::m", manually_disabled=True)})

    r = client.post("/mc/cheap-balancer/slot/groq::m/enable")
    assert r.status_code == 200
    loaded = clb._load_state()
    assert loaded["groq::m"].manually_disabled is False


def test_post_refresh_pool(client):
    r = client.post("/mc/cheap-balancer/refresh-pool")
    assert r.status_code == 200
    data = r.json()
    assert "pool_size" in data
