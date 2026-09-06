"""Workbench-ruterne: bygget 6/9, men uden dem kunne ingen app naa dem.

Vigtigst: operator-kanalen. Mens den er aaben koerer bash paa Bjoerns maskine
uden godkendelse pr. kald — han skal kunne SE det og lukke den.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def klient(monkeypatch):
    from apps.api.jarvis_api.app import app
    return TestClient(app)


def _som(monkeypatch, rolle: str) -> None:
    monkeypatch.setattr("apps.api.jarvis_api.routes.workbench._current_role",
                        lambda uid: rolle)


def test_status_kraever_ikke_owner(klient):
    """At spoerge om kanalen er aaben er harmloest — og at gate det ville
    skjule tilstanden for den der har mest brug for at se den."""
    r = klient.get("/workbench/operator-channel?session_id=proeve")
    assert r.status_code == 200
    assert r.json()["open"] in (True, False)


def test_ikke_owner_kan_ikke_aabne_kanalen(klient, monkeypatch):
    _som(monkeypatch, "member")
    r = klient.post("/workbench/operator-channel/open", json={"session_id": "s1"})
    assert r.status_code == 403


def test_owner_kan_aabne_og_lukke(klient, monkeypatch):
    _som(monkeypatch, "owner")
    a = klient.post("/workbench/operator-channel/open", json={"session_id": "rute-proeve"})
    assert a.status_code == 200 and a.json()["open"] is True

    s = klient.get("/workbench/operator-channel?session_id=rute-proeve")
    assert s.json()["open"] is True
    assert s.json()["udloeber_om_s"] > 0

    l = klient.post("/workbench/operator-channel/close", json={"session_id": "rute-proeve"})
    assert l.status_code == 200 and l.json()["open"] is False


def test_checkpoints_kan_listes(klient):
    r = klient.get("/workbench/checkpoints?session_id=findes-ikke")
    assert r.status_code == 200
    assert r.json()["antal"] == 0


def test_rollback_er_owner_only(klient, monkeypatch):
    _som(monkeypatch, "guest")
    assert klient.post("/workbench/checkpoints/rollback", json={}).status_code == 403


def test_kontakter_kan_laeses(klient):
    r = klient.get("/workbench/switches")
    assert r.status_code == 200
    d = r.json()
    assert "bash_sandbox" in d and "env_block" in d
    assert d["bash_sandbox"]["tændt"] is False, "sandboxen skal vaere slukket som standard"


def test_ukendt_kontakt_giver_404(klient, monkeypatch):
    _som(monkeypatch, "owner")
    assert klient.post("/workbench/switches/volapyk", json={"enabled": True}).status_code == 404


def test_kontakt_er_owner_only(klient, monkeypatch):
    _som(monkeypatch, "member")
    r = klient.post("/workbench/switches/bash_sandbox", json={"enabled": True})
    assert r.status_code == 403
