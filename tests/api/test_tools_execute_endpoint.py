from fastapi.testclient import TestClient
from apps.api.jarvis_api.app import app

client = TestClient(app)


def test_catalog_locked_returns_companions_and_load_more():
    r = client.get("/v1/tools/catalog", params={"unlocked": "false"})
    assert r.status_code == 200
    names = {(d.get("function") or d)["name"] for d in r.json()["tools"]}
    assert "remember_this" in names
    assert "load_more_tools" in names
    assert "runtime_bash" not in names


def test_catalog_unlocked_returns_runtime_aliases():
    r = client.get("/v1/tools/catalog", params={"unlocked": "true"})
    assert r.status_code == 200
    names = {(d.get("function") or d)["name"] for d in r.json()["tools"]}
    assert "runtime_bash" in names
