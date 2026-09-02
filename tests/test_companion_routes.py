"""Companion-ruterne — og især owner-gaten på Sansernes Arkiv.

Jarvis skrev: «Grænsen skal ligge i auth-laget (owner-verifikation), ikke kun
ved at skjule UI'et.» Derfor testes RUTEN, ikke en klient. En fane kan skiftes
ud; en dependency kan ikke omgås af en anden app.
"""
from __future__ import annotations

import pytest


# ── 2. SANSERNES ARKIV — OWNER-ONLY ─────────────────────────────────────────
#
# Jarvis skrev: «Grænsen skal ligge i auth-laget (owner-verifikation), ikke kun
# ved at skjule UI'et.» Derfor testes RUTEN, ikke en klient. En fane kan skiftes
# ud; en dependency kan ikke omgås af en anden app.

def _client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from apps.api.jarvis_api.routes.companion import router
    app = FastAPI()
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


def _token(role: str) -> str:
    from core.runtime.jarvisx_auth import issue_token
    return issue_token(user_id="tester", role=role)["token"]


def test_senses_kraever_token():
    r = _client().get("/companion/senses")
    assert r.status_code == 401


def test_senses_afviser_member_med_403():
    r = _client().get("/companion/senses",
                      headers={"Authorization": f"Bearer {_token('member')}"})
    assert r.status_code == 403
    assert "owner" in r.json()["detail"].lower()


def test_senses_afviser_guest_med_403():
    r = _client().get("/companion/senses",
                      headers={"Authorization": f"Bearer {_token('guest')}"})
    assert r.status_code == 403


def test_senses_afviser_forfalsket_token():
    r = _client().get("/companion/senses",
                      headers={"Authorization": "Bearer ikke.et.token"})
    assert r.status_code == 401


def test_senses_slipper_owner_ind(monkeypatch):
    import core.services.visual_memory as vm
    monkeypatch.setattr(vm, "get_visual_memories",
                        lambda **kw: [{"description": "lys på bordet"}], raising=False)
    r = _client().get("/companion/senses",
                      headers={"Authorization": f"Bearer {_token('owner')}"})
    assert r.status_code == 200
    assert r.json()["count"] == 1


def test_gaten_sidder_paa_ruten_ikke_i_handleren(monkeypatch):
    """Selv hvis arkivet var utilgængeligt, må en member ALDRIG nå handleren.
    403 skal komme før noget som helst forsøg på at læse data."""
    import core.services.visual_memory as vm

    def _boom(**kw):
        raise AssertionError("handleren blev kørt for en ikke-owner")

    monkeypatch.setattr(vm, "get_visual_memories", _boom, raising=False)
    r = _client().get("/companion/senses",
                      headers={"Authorization": f"Bearer {_token('member')}"})
    assert r.status_code == 403
