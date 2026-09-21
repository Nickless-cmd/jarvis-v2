# tests/test_notifikations_valg_rute.py
from __future__ import annotations

import pytest


@pytest.fixture()
def klient(isolated_runtime, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from apps.api.jarvis_api.routes import notifikations_valg as rute

    monkeypatch.setattr(rute, "_bruger", lambda: "bjorn")
    app = FastAPI()
    app.include_router(rute.router)
    return TestClient(app)


def test_henter_alle_slags_med_standarden_lagt_i(klient) -> None:
    valg = klient.get("/notifikations-valg").json()["valg"]
    assert valg["approval"] == "auto"
    assert valg["release"] == "ingen"


def test_saetter_et_valg(klient) -> None:
    assert klient.post("/notifikations-valg",
                       json={"slags": "release", "kanal": "push"}).json()["ok"] is True
    assert klient.get("/notifikations-valg").json()["valg"]["release"] == "push"


def test_afviser_en_ukendt_kanal(klient) -> None:
    svar = klient.post("/notifikations-valg",
                       json={"slags": "release", "kanal": "duer-ikke"}).json()
    assert svar["ok"] is False
    assert "kanal" in svar["fejl"]
