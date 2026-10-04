"""Ruten `/chat/inbox/flag` — Bjørns egen vej ind i indbakken.

Testene går gennem FastAPI's TestClient, altså den rigtige rute og den rigtige
validering. En test der kaldte `flag_fra_bruger` direkte ville ikke måle det
led der oftest brækker: om ruten overhovedet er inkluderet i appen.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

import pytest

from core.runtime import db_inbox

BJORN = "bjorn"


@pytest.fixture
def klient(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    from apps.api.jarvis_api.routes.chat_inbox import router

    sti = tmp_path / "r.db"

    @contextmanager
    def _c():
        k = sqlite3.connect(sti)
        k.row_factory = sqlite3.Row
        try:
            yield k
            k.commit()
        finally:
            k.close()

    monkeypatch.setattr(db_inbox, "connect", _c)
    monkeypatch.setattr(db_inbox, "_skema_klar", False)

    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_ruten_er_INKLUDERET_i_den_rigtige_app():
    """Det led der oftest brækker. Fire gange 3.-4./10 var mekanismen korrekt
    og kalderen manglede — skriveren, læseren i prompten, lukkeren og
    tælleren. En rute i en fil ingen inkluderer er den femte."""
    from apps.api.jarvis_api.app import app
    stier = {getattr(r, "path", "") for r in app.routes}
    assert "/chat/inbox/flag" in stier, \
        "ruten findes men app.py inkluderer den ikke"


def test_et_flag_oprettes_med_den_AUTENTIFICEREDE_bruger(klient, monkeypatch):
    from core.identity import workspace_context as wc
    monkeypatch.setattr(wc, "current_user_id", lambda: BJORN)
    r = klient.post("/chat/inbox/flag", json={"titel": "Desk haenger"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "ok" and d["bloker"] is False
    p = db_inbox.hent(bruger_id=BJORN, kilde_id=d["id"])
    assert p is not None and p["verificeret_ejer"] == db_inbox.EJER_BRUGER


def test_ruten_tager_IKKE_et_bruger_id_fra_kroppen(klient, monkeypatch):
    """Et felt kalderen vælger er en påstand, ikke proveniens. Sendes der et
    `bruger_id`, må det ignoreres — ikke bruges."""
    from core.identity import workspace_context as wc
    monkeypatch.setattr(wc, "current_user_id", lambda: BJORN)
    r = klient.post("/chat/inbox/flag",
                    json={"titel": "x", "bruger_id": "en-anden"})
    assert r.status_code == 200
    assert db_inbox.hent(bruger_id="en-anden", kilde_id=r.json()["id"]) is None
    assert db_inbox.hent(bruger_id=BJORN, kilde_id=r.json()["id"]) is not None


def test_UDEN_autentificeret_bruger_svares_401(klient, monkeypatch):
    from core.identity import workspace_context as wc
    monkeypatch.setattr(wc, "current_user_id", lambda: "")
    monkeypatch.setattr(wc, "current_workspace_name", lambda: "")
    r = klient.post("/chat/inbox/flag", json={"titel": "x"})
    assert r.status_code == 401


def test_TOM_titel_svares_400_og_opretter_intet(klient, monkeypatch):
    from core.identity import workspace_context as wc
    monkeypatch.setattr(wc, "current_user_id", lambda: BJORN)
    for titel in ("", "   "):
        r = klient.post("/chat/inbox/flag", json={"titel": titel})
        assert r.status_code == 400, f"{titel!r} slap igennem"
    assert db_inbox.liste(bruger_id=BJORN, kun_aabne=False) == []


def test_bloker_skal_bedes_om_EKSPLICIT(klient, monkeypatch):
    """«Synlig men gater ikke som standard» — Bjørn 4/10."""
    from core.identity import workspace_context as wc
    monkeypatch.setattr(wc, "current_user_id", lambda: BJORN)
    uden = klient.post("/chat/inbox/flag", json={"titel": "a"}).json()
    med = klient.post("/chat/inbox/flag",
                      json={"titel": "b", "bloker": True}).json()
    assert uden["bloker"] is False
    assert med["bloker"] is True
    assert db_inbox.hent(bruger_id=BJORN, kilde_id=uden["id"])["bloker"] is False
    assert db_inbox.hent(bruger_id=BJORN, kilde_id=med["id"])["bloker"] is True
