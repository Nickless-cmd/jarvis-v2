"""«Brug denne besked som hukommelse» — smalt endpoint, faste valg."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.jarvis_api.routes import mobile_memory as MM


@pytest.fixture
def klient(monkeypatch):
    kald = {}

    def falsk(**kw):
        kald.update(kw)
        return {"status": "ok", "id": 42}

    monkeypatch.setattr("core.tools.jarvis_brain_tools.remember_this", falsk)
    app = FastAPI()
    app.include_router(MM.router)
    c = TestClient(app)
    c.kald = kald  # type: ignore[attr-defined]
    return c


def test_gemmer_med_faste_valg_saa_et_tryk_ikke_bliver_en_formular(klient):
    r = klient.post("/mobile/memory", json={"content": "Broen tabte sit WAN-ben."})
    assert r.status_code == 200 and r.json()["status"] == "ok"
    k = klient.kald  # type: ignore[attr-defined]
    assert k["kind"] == "observation"       # det BLEV sagt, ikke en konklusion
    assert k["visibility"] == "personal"    # en samtale er ikke public_safe
    assert k["domain"] == "samtale"


def test_titlen_udledes_saa_man_ikke_skal_navngive_en_huskeseddel(klient):
    klient.post("/mobile/memory", json={"content": "# Overskrift\n\nresten af teksten"})
    assert klient.kald["title"] == "Overskrift"  # type: ignore[attr-defined]


def test_brugerens_note_kommer_FOERST_den_siger_hvorfor(klient):
    klient.post("/mobile/memory", json={"content": "det tekniske", "note": "husk til i morgen"})
    k = klient.kald  # type: ignore[attr-defined]
    assert k["content"].startswith("husk til i morgen")
    assert "det tekniske" in k["content"]
    assert k["title"] == "husk til i morgen"


def test_tom_besked_afvises(klient):
    assert klient.post("/mobile/memory", json={"content": "   "}).status_code == 400


def test_lang_besked_afkortes_frem_for_at_fylde_hjernen(klient):
    klient.post("/mobile/memory", json={"content": "x" * 9000})
    assert "…(afkortet)" in klient.kald["content"]  # type: ignore[attr-defined]
    assert len(klient.kald["content"]) < 4100       # type: ignore[attr-defined]


def test_session_og_besked_id_foelger_med_saa_posten_kan_spores(klient):
    klient.post("/mobile/memory", json={"content": "x", "session_id": "s1", "message_id": "m9"})
    k = klient.kald  # type: ignore[attr-defined]
    assert k["session_id"] == "s1" and k["turn_id"] == "m9"


def test_fejl_fra_hjernen_bliver_en_fejl_ikke_en_tavs_succes(monkeypatch):
    monkeypatch.setattr(
        "core.tools.jarvis_brain_tools.remember_this",
        lambda **kw: {"status": "error", "error": "validation_failed"},
    )
    app = FastAPI()
    app.include_router(MM.router)
    r = TestClient(app).post("/mobile/memory", json={"content": "x"})
    assert r.status_code == 502


def test_titel_falder_tilbage_naar_teksten_ikke_har_en_linje(klient):
    klient.post("/mobile/memory", json={"content": "ab"})
    assert klient.kald["title"] == "Fra en samtale"  # type: ignore[attr-defined]
