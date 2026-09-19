"""Enhedsregistret og reglen «code mode kræver tilføjet enhed» (19/9-2026)."""
from __future__ import annotations

import pytest

import core.identity.workspace_context as wc
from core.identity.kode_adgang import kode_tilladt
from core.runtime import db_devices as dd


@pytest.fixture
def reg(isolated_runtime):
    return dd


def test_telefon_registreres_listes_og_fjernes(reg):
    t = dd.registrer_telefon("u1", navn="Pixel 9", platform="android")
    assert [e["navn"] for e in dd.liste("u1")] == ["Pixel 9"]
    assert dd.telefon_status(t["id"]) == "aktiv"
    assert dd.fjern(t["id"], "andre") is False  # kun brugerens egen
    assert dd.fjern(t["id"], "u1") is True
    assert dd.telefon_status(t["id"]) == "fjernet"
    assert dd.liste("u1") == []


def test_computer_er_idempotent_og_telefonens_app_id_afvises(reg):
    a = dd.registrer_computer("u1", "app-uuid-1", navn="CheifOne")
    b = dd.registrer_computer("u1", "app-uuid-1")
    assert a["id"] == b["id"]
    with pytest.raises(ValueError):
        dd.registrer_computer("u1", dd.TELEFON_APP_ID)
    with pytest.raises(ValueError):
        dd.registrer_computer("u1", "")


def test_maa_bruge_kode_kun_for_aktiv_post_og_samme_bruger(reg):
    t = dd.registrer_telefon("u1")
    dd.registrer_computer("u1", "app-1")
    assert dd.maa_bruge_kode("u1", enhed=t["id"]) is True
    assert dd.maa_bruge_kode("u2", enhed=t["id"]) is False
    assert dd.maa_bruge_kode("u1", app_id="app-1") is True
    assert dd.maa_bruge_kode("u1", app_id=dd.TELEFON_APP_ID) is False
    dd.fjern(t["id"], "u1")
    assert dd.maa_bruge_kode("u1", enhed=t["id"]) is False


def _som(monkeypatch, uid, enhed="", app_id=""):
    monkeypatch.setattr(wc, "current_user_id", lambda: uid)
    monkeypatch.setattr(wc, "current_token_enhed", lambda: (enhed, app_id))


def test_reglen_slukket_er_alt_som_foer(reg, monkeypatch):
    _som(monkeypatch, "u1")
    assert kode_tilladt() is True


def test_reglen_taendt_kraever_en_tilfoejet_enhed(reg, monkeypatch):
    dd.saet_kraev(True, af="u1")
    t = dd.registrer_telefon("u1")
    _som(monkeypatch, "u1")                       # gammelt token uden enhed
    assert kode_tilladt() is False
    _som(monkeypatch, "u1", enhed=t["id"])        # parret telefon
    assert kode_tilladt() is True
    _som(monkeypatch, "u1", app_id="app-ukendt")  # uregistreret desk
    assert kode_tilladt() is False
    _som(monkeypatch, "", enhed="")               # internt kald
    assert kode_tilladt() is True


def test_en_fjernet_telefons_token_afvises_overalt(reg):
    from core.runtime.jarvisx_auth import AuthError, issue_token, verify_token
    t = dd.registrer_telefon("u1")
    tok = issue_token(user_id="u1", role="member", extra_claims={"jti": "j1", "enhed": t["id"]})["token"]
    assert verify_token(tok)["enhed"] == t["id"]
    dd.fjern(t["id"], "u1")
    with pytest.raises(AuthError, match="device removed"):
        verify_token(tok)


def test_fornyelsen_baerer_enheden_videre_og_nægter_en_fjernet(reg, monkeypatch):
    from core.runtime import token_renewal as tr
    from core.runtime.jarvisx_auth import issue_token, verify_token
    monkeypatch.setattr(tr, "_gemt_bruger", lambda uid: {"role": "member"})
    monkeypatch.setattr(tr, "_husk_jti", lambda uid, jti: None)
    t = dd.registrer_telefon("u1")
    tok = issue_token(user_id="u1", role="member", extra_claims={"jti": "j1", "enhed": t["id"]})["token"]
    ny = tr.renew(tok)
    assert ny.get("ok") is not False, ny
    nyt_token = ny.get("token") or ny.get("access_token")
    assert verify_token(nyt_token)["enhed"] == t["id"]
    dd.fjern(t["id"], "u1")
    assert tr.renew(nyt_token) == {"ok": False, "reason": "device removed"}
