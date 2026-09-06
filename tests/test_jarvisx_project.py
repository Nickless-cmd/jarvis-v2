"""Ejer-gate på projekt-ruterne.

Ruterne læser og opremser værtens filsystem med en rod der må ligge hvor
som helst. Uden gate kunne enhver indlogget bruger — fx telefonen — opremse
/home/bs og læse filer derfra.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from apps.api.jarvis_api.routes import jarvisx_project as jp
from core.identity import workspace_context as wc


@pytest.mark.parametrize("rolle", ["owner", ""])
def test_ejer_og_ubundet_slipper_igennem(rolle, monkeypatch):
    monkeypatch.setattr(wc, "current_role", lambda: rolle)
    jp._kun_ejer()  # rejser ikke


@pytest.mark.parametrize("rolle", ["member", "guest", "anonymous"])
def test_alle_andre_afvises_med_403(rolle, monkeypatch):
    monkeypatch.setattr(wc, "current_role", lambda: rolle)
    with pytest.raises(HTTPException) as ex:
        jp._kun_ejer()
    assert ex.value.status_code == 403


def test_gaten_daekker_hver_eneste_rute():
    # Router-niveau frem for pr. rute, så et nyt endpoint ikke kan glemme den.
    afhængigheder = [d.dependency for d in jp.router.dependencies]
    assert jp._kun_ejer in afhængigheder

    ruter = [r for r in jp.router.routes if getattr(r, "path", "").startswith("/api/project")]
    assert len(ruter) >= 8, f"forventede alle projekt-ruter, fandt {len(ruter)}"


def test_fastapi_haandhaever_gaten_paa_en_rigtig_forespoergsel(monkeypatch, tmp_path):
    """At afhængigheden står på routeren beviser ikke at den fyrer."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(jp.router)
    klient = TestClient(app)
    url = f"/api/project/list?root={tmp_path}"

    monkeypatch.setattr(wc, "current_role", lambda: "member")
    assert klient.get(url).status_code == 403

    monkeypatch.setattr(wc, "current_role", lambda: "owner")
    assert klient.get(url).status_code == 200
