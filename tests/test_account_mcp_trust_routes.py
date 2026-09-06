"""MCP-tillid over API: uden disse ruter var registeret en blindgyde.

Man kunne tilfoeje en server i UI'et og ALDRIG godkende den derfra — altsaa
tilfoeje noget der aldrig kunne bruges.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def klient():
    from apps.api.jarvis_api.app import app
    return TestClient(app)


def _som(monkeypatch, rolle: str) -> None:
    monkeypatch.setattr("apps.api.jarvis_api.routes.account._current_role",
                        lambda uid: rolle)


def test_trust_kan_laeses(klient):
    r = klient.get("/account/mcp/trust")
    assert r.status_code == 200
    assert "servere" in r.json()


def test_godkendelse_er_owner_only(klient, monkeypatch):
    """Samme graense som operator-kanalen: en fremmed server faar lov at handle."""
    _som(monkeypatch, "member")
    assert klient.post("/account/mcp/vejr/allow").status_code == 403
    assert klient.post("/account/mcp/vejr/revoke").status_code == 403


def test_owner_kan_godkende_og_tilbagekalde(klient, monkeypatch):
    _som(monkeypatch, "owner")
    a = klient.post("/account/mcp/rute-proeve/allow")
    assert a.status_code == 200
    assert "rute-proeve" in a.json()["allowlist"]

    t = klient.post("/account/mcp/rute-proeve/revoke")
    assert t.status_code == 200
    assert "rute-proeve" not in t.json()["allowlist"]
