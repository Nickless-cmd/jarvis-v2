"""Companion-ruterne — og især husstands-gaten på Sansernes Arkiv.

Jarvis skrev: «Grænsen skal ligge i auth-laget ... ikke kun ved at skjule UI'et.»
Derfor testes RUTEN, ikke en klient. En fane kan skiftes ud; en dependency kan
ikke omgås af en anden app — heller ikke af en fremtidig desktop-flade.

Bjørn præciserede grænsen 2026-09-02: arkivet er for ham OG Michelle, som bor i
hjemmet. Mikkel, Rune og Lotte er familie med hver deres samtale, men de bor her
ikke. Testene navngiver derfor rollerne efter mennesker, så det er tydeligt hvad
de faktisk beskytter.
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


def test_familie_afvises_med_403():
    """Mikkel, Rune og Lotte er `member`. Arkivet rager dem ikke."""
    r = _client().get("/companion/senses",
                      headers={"Authorization": f"Bearer {_token('member')}"})
    assert r.status_code == 403
    assert "household" in r.json()["detail"].lower()


def test_michelle_slipper_ind(monkeypatch):
    """Michelle er `partner`: hun deler det rum Jarvis sanser."""
    import core.services.visual_memory as vm
    monkeypatch.setattr(vm, "get_visual_memories",
                        lambda **kw: [{"description": "lys på bordet"}], raising=False)
    r = _client().get("/companion/senses",
                      headers={"Authorization": f"Bearer {_token('partner')}"})
    assert r.status_code == 200
    assert r.json()["count"] == 1


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


def test_partner_faar_ikke_ekstra_magt_af_adgangen():
    """Husstands-adgangen åbner ÉT rum. Michelle må aldrig kunne mere end en
    member ellers — det var Bjørns udtrykkelige betingelse."""
    from core.services.permission_engine import allowed_tools
    assert allowed_tools(role="partner", mode="chat") == allowed_tools(role="member", mode="chat")


def test_gaten_sidder_paa_ruten_ikke_i_handleren(monkeypatch):
    """Selv hvis arkivet var utilgængeligt, må familie ALDRIG nå handleren.
    403 skal komme før noget som helst forsøg på at læse data."""
    import core.services.visual_memory as vm

    def _boom(**kw):
        raise AssertionError("handleren blev kørt for en ikke-owner")

    monkeypatch.setattr(vm, "get_visual_memories", _boom, raising=False)
    r = _client().get("/companion/senses",
                      headers={"Authorization": f"Bearer {_token('member')}"})
    assert r.status_code == 403
