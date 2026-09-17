"""POST /voice/samtale — billetter til ægte stemme-samtale (17/9-2026).

Ruten udsteder rettigheder, så det der testes er GRÆNSERNE: kun ejeren,
agentens Jarvis-billet går aldrig til telefonen, og LiveKit-billetten giver
kun adgang til ét rum.
"""
import jwt
import pytest
from fastapi import HTTPException

import apps.api.jarvis_api.routes.voice_live as vl


class _Req:
    def __init__(self, auth: str = ""):
        self.headers = {"authorization": auth} if auth else {}


def test_livekit_billet_giver_kun_adgang_til_eet_rum():
    t = vl.livekit_billet("nøgle", "hemmelig" * 5, identitet="bruger-1", rum="stemme-abc")
    krav = jwt.decode(t, "hemmelig" * 5, algorithms=["HS256"])
    assert krav["iss"] == "nøgle" and krav["sub"] == "bruger-1"
    assert krav["video"]["room"] == "stemme-abc" and krav["video"]["roomJoin"] is True
    assert "roomAdmin" not in krav["video"]
    assert krav["exp"] - krav["nbf"] <= vl._BILLET_SEKUNDER + 10


def test_admin_billet_er_kortlivet():
    t = vl.livekit_billet("k", "s" * 40, identitet="jarvis-api", rum="r", admin=True, ttl=60)
    krav = jwt.decode(t, "s" * 40, algorithms=["HS256"])
    assert krav["video"]["roomAdmin"] is True and krav["exp"] - krav["nbf"] <= 70


def test_kun_ejeren(monkeypatch):
    import core.runtime.jarvisx_auth as auth
    monkeypatch.setattr(auth, "verify_token", lambda raw: {"sub": "u", "role": "member"})
    with pytest.raises(HTTPException) as e:
        vl.aabn_samtale(vl.SamtaleRequest(), _Req("Bearer x"))
    assert e.value.status_code == 403
    with pytest.raises(HTTPException) as e:
        vl.aabn_samtale(vl.SamtaleRequest(), _Req())
    assert e.value.status_code == 401


def test_agentens_jarvis_billet_naar_aldrig_telefonen(monkeypatch):
    import core.runtime.jarvisx_auth as auth
    monkeypatch.setattr(auth, "verify_token", lambda raw: {"sub": "ejer-1", "role": "owner", "app_id": "app-9"})
    monkeypatch.setattr(vl, "_livekit_noegler", lambda: ("k", "s" * 40))
    udstedt = {}
    def _issue(**kw):
        udstedt.update(kw)
        return {"token": "HEMMELIG-JARVIS-BILLET"}
    monkeypatch.setattr(auth, "issue_token", _issue)
    sendt = {}
    monkeypatch.setattr(vl, "_send_agent", lambda k, s, rum, meta: sendt.update(rum=rum, meta=meta))

    svar = vl.aabn_samtale(vl.SamtaleRequest(session_id="chat-1"), _Req("Bearer x"))

    assert "HEMMELIG-JARVIS-BILLET" not in str(svar)
    assert sendt["meta"]["jarvis_token"] == "HEMMELIG-JARVIS-BILLET"
    assert sendt["meta"]["session_id"] == "chat-1"
    assert sendt["rum"] == svar["rum"]
    # Kort levetid, samme ejer og samme app-binding.
    assert udstedt["role"] == "owner" and udstedt["user_id"] == "ejer-1"
    assert udstedt["ttl_seconds"] == vl._BILLET_SEKUNDER and udstedt["app_id"] == "app-9"
    krav = jwt.decode(svar["token"], "s" * 40, algorithms=["HS256"])
    assert krav["video"]["room"] == svar["rum"]
