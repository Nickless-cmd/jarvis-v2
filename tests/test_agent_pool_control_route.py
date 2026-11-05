"""Styrings-ruter for agent-puljen: samme service som agent-værktøjerne, owner-only,
og modelruten afgøres af backend — ikke af UI'et."""
from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import apps.api.jarvis_api.routes.agent_pool_control as ctl
import apps.api.jarvis_api.routes.central_auth as auth


@pytest.fixture
def kald(monkeypatch):
    """(client, kald-log). Ejeren er tilladt og kendt; servicen er en optager."""
    log: list[tuple[str, dict]] = []

    class FakeSvc:
        def dispatch_agent(self, **kw):
            log.append(("dispatch", kw))
            return {"status": "accepted", "agent_id": "agent-1", "assignment_id": "a-1"}

        def followup_agent(self, **kw):
            log.append(("followup", kw))
            return {"status": "accepted", "agent_id": kw["agent_id"]}

        def interrupt_agent(self, **kw):
            log.append(("interrupt", kw))
            return {"status": "stop_requested", "agent_id": kw["agent_id"]}

        def close_agent(self, **kw):
            log.append(("close", kw))
            return {"status": "accepted", "agent_id": kw["agent_id"], "lifecycle_status": "closing"}

    monkeypatch.setattr(auth, "require_central_owner", lambda: None)
    monkeypatch.setattr(ctl, "_svc", lambda: FakeSvc())
    monkeypatch.setattr(ctl, "_owner_id", lambda: "bjorn")
    app = FastAPI()
    app.include_router(ctl.router)
    return TestClient(app), log


def test_start_kalder_dispatch_med_haard_modelrute(kald):
    client, log = kald
    r = client.post("/mc/agent-pool/agents", json={
        "rolle": "researcher", "opgave": "find noget", "model_route": "claude-cli/default"})
    assert r.status_code == 200 and r.json()["agent_id"] == "agent-1"
    navn, kw = log[0]
    assert navn == "dispatch"
    assert kw["model"] == "claude-cli/default" and kw["model_required"] is True
    assert kw["owner_user_id"] == "bjorn" and kw["goal"] == "find noget"


def test_start_uden_route_er_ikke_et_haardt_krav(kald):
    client, log = kald
    client.post("/mc/agent-pool/agents", json={"opgave": "x"})
    assert log[0][1]["model_required"] is False


def test_ugyldig_udbyder_afvises_med_brugbar_fejl(kald):
    client, log = kald
    r = client.post("/mc/agent-pool/agents", json={"opgave": "x", "model_route": "bogus/gpt"})
    assert r.status_code == 422
    assert "bogus" in r.json()["detail"]["fejl"] and "claude-cli" in r.json()["detail"]["fejl"]
    assert log == []          # intet blev dispatched


def test_politikkens_afvisning_bliver_til_422_med_aarsager(kald, monkeypatch):
    client, log = kald

    class Afviser:
        def dispatch_agent(self, **kw):
            return {"status": "error", "code": "MODEL_UNAVAILABLE",
                    "error": "modelkravet deepseek/x er ikke tilladt for ejeren",
                    "reasons": [{"stage": "explicit", "reason": "deepseek_er_kun_for_platformens_ejer"}]}

    monkeypatch.setattr(ctl, "_svc", lambda: Afviser())
    r = client.post("/mc/agent-pool/agents", json={"opgave": "x", "model_route": "deepseek/x"})
    assert r.status_code == 422
    d = r.json()["detail"]
    assert d["kode"] == "MODEL_UNAVAILABLE" and d["aarsager"][0]["reason"].startswith("deepseek")


def test_tom_opgave_afvises_af_servicen_som_422(kald, monkeypatch):
    client, _ = kald
    monkeypatch.setattr(ctl, "_svc", lambda: type("S", (), {
        "dispatch_agent": lambda self, **kw: {"status": "error", "code": "INVALID_SCOPE",
                                              "error": "goal mangler"}})())
    assert client.post("/mc/agent-pool/agents", json={"opgave": "  "}).status_code == 422


def test_interrupt_close_followup_kalder_servicen(kald):
    client, log = kald
    assert client.post("/mc/agent-pool/agents/agent-1/interrupt", json={"note": "stop"}).json()["status"] == "stop_requested"
    assert client.post("/mc/agent-pool/agents/agent-1/close").json()["lifecycle_status"] == "closing"
    assert client.post("/mc/agent-pool/agents/agent-1/followup", json={"opgave": "næste"}).status_code == 200
    assert [n for n, _ in log] == ["interrupt", "close", "followup"]
    assert log[2][1]["goal"] == "næste" and log[2][1]["agent_id"] == "agent-1"


def test_ukendt_agent_giver_422(kald, monkeypatch):
    client, _ = kald
    monkeypatch.setattr(ctl, "_svc", lambda: type("S", (), {
        "close_agent": lambda self, **kw: {"status": "error", "code": "INVALID_SCOPE",
                                           "error": "ukendt agent"}})())
    r = client.post("/mc/agent-pool/agents/nope/close")
    assert r.status_code == 422 and r.json()["detail"]["fejl"] == "ukendt agent"


def test_ruter_udledes_og_efterproeves(kald):
    """Listen må ikke være håndskrevet: den udledes af politikken, og hver rute er målt.

    Den tidligere version hævdede at `ollama` SKULLE stå i listen. `ollama` findes ikke
    som udbyder noget sted i politikken — testen vogtede altså en løgn, ikke en kontrakt.
    """
    client, _ = kald
    ruter = {x["udbyder"]: x for x in client.get("/mc/agent-pool/routes").json()["ruter"]}

    from core.services.agent_cli_backend import DEFAULT_MODELS
    from core.services.agent_model_policy import OWNER_ONLY_PROVIDERS
    assert set(ruter) == set(DEFAULT_MODELS) | set(OWNER_ONLY_PROVIDERS)

    # En opdigtet udbyder må ikke kunne snige sig ind i det UI'et tilbyder.
    assert "ollama" not in ruter

    for r in ruter.values():
        assert isinstance(r["tilgaengelig"], bool)
        assert r["kun_ejer"] == (r["udbyder"] in OWNER_ONLY_PROVIDERS)
        if not r["tilgaengelig"]:
            assert r["aarsag"], f"{r['udbyder']} er utilgaengelig uden en aarsag"

    assert ruter["deepseek"]["kun_ejer"] and ruter["claude-cli"]["kun_ejer"]


@pytest.mark.parametrize("metode,sti,body", [
    ("get", "/mc/agent-pool/routes", None),
    ("post", "/mc/agent-pool/agents", {"opgave": "x"}),
    ("post", "/mc/agent-pool/agents/a/interrupt", {}),
    ("post", "/mc/agent-pool/agents/a/close", None),
    ("post", "/mc/agent-pool/agents/a/followup", {"opgave": "x"}),
])
def test_ikke_owner_faar_403_og_servicen_roeres_ikke(monkeypatch, metode, sti, body):
    def nej():
        raise HTTPException(status_code=403, detail="Centralen er kun for owner")

    kaldt = []
    monkeypatch.setattr(auth, "require_central_owner", nej)
    monkeypatch.setattr(ctl, "_svc", lambda: kaldt.append(1))
    app = FastAPI()
    app.include_router(ctl.router)
    r = getattr(TestClient(app), metode)(sti, **({"json": body} if body is not None else {}))
    assert r.status_code == 403
    assert kaldt == []
