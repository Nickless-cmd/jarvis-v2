"""Ruterne for enheder og reglen — og at kode-panelet afviser (19/9-2026)."""
from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

import core.identity.users as users
import core.identity.workspace_context as wc
from apps.api.jarvis_api.routes import auth_enheder as ae
from core.runtime import db_devices as dd
from core.services import totp_verifier as tv


@pytest.fixture
def ejer(isolated_runtime, monkeypatch):
    s = tv.generate_seed()
    monkeypatch.setattr(users, "get_totp_seed", lambda discord_id: s)
    tv._ATTEMPTS.clear()

    def som(uid="u1", rolle="owner", enhed="", app_id="desk-uuid-1"):
        monkeypatch.setattr(wc, "current_user_id", lambda: uid)
        monkeypatch.setattr(wc, "current_role", lambda: rolle)
        monkeypatch.setattr(wc, "current_token_enhed", lambda: (enhed, app_id))
    som()
    return s, som


def test_ejeren_taender_reglen_og_desken_tilfoejes_selv(ejer):
    seed, _ = ejer
    ae.saet_enheds_krav(ae.KravReq(aktiv=True, totp=tv.generate_code(seed), navn="CheifOne"))
    assert dd.kraev_aktivt() is True
    svar = ae.enheder()
    assert [e["navn"] for e in svar["enheder"]] == ["CheifOne"]
    assert svar["denne"] == {"type": "computer", "tilfoejet": True, "kode_tilladt": True}


def test_kun_ejeren_og_kun_med_kode(ejer):
    seed, som = ejer
    som(rolle="member")
    with pytest.raises(HTTPException) as e:
        ae.saet_enheds_krav(ae.KravReq(aktiv=True, totp=tv.generate_code(seed)))
    assert e.value.status_code == 403
    som()
    with pytest.raises(HTTPException) as e:
        ae.saet_enheds_krav(ae.KravReq(aktiv=True, totp="000000"))
    assert e.value.status_code == 403
    assert dd.kraev_aktivt() is False


def test_reglen_kan_ikke_taendes_fra_en_telefon(ejer):
    """Så ville ejeren låse sig ude af code mode på sin computer."""
    seed, som = ejer
    som(app_id=dd.TELEFON_APP_ID)
    with pytest.raises(HTTPException) as e:
        ae.saet_enheds_krav(ae.KravReq(aktiv=True, totp=tv.generate_code(seed)))
    assert e.value.status_code == 400
    assert dd.kraev_aktivt() is False


def test_fjern_kun_min_egen(ejer):
    t = dd.registrer_telefon("u2")
    with pytest.raises(HTTPException) as e:
        ae.fjern_enhed(t["id"])
    assert e.value.status_code == 404
    mine = dd.registrer_telefon("u1")
    assert ae.fjern_enhed(mine["id"]) == {"ok": True}


def test_kode_panelet_afviser_en_ikke_tilfoejet_enhed(ejer):
    from apps.api.jarvis_api.routes import chat as rute
    _, som = ejer
    dd.saet_kraev(True, af="u1")
    som(app_id="uregistreret")
    with pytest.raises(HTTPException) as e:
        asyncio.run(rute.chat_tree())
    assert e.value.status_code == 403 and "tilføjet i desk" in e.value.detail


def test_v2_streamen_afviser_code_mode_foer_noget_koerer(ejer, monkeypatch):
    """Code mode fra en ikke-tilføjet enhed stopper med 403 FØR en kørsel startes."""
    from apps.api.jarvis_api.routes import chat_stream_v2 as mod
    from apps.api.jarvis_api.routes.chat import ChatStreamRequest
    _, som = ejer
    dd.saet_kraev(True, af="u1")
    som(app_id="uregistreret")
    startet: list = []
    monkeypatch.setattr(mod, "start_or_attach_user_run", lambda **k: startet.append(k) or ("r", False), raising=False)
    with pytest.raises(HTTPException) as e:
        from core.services.chat_sessions import create_chat_session
        sid = create_chat_session(title="kode")["id"]
        asyncio.run(mod.chat_stream_v2(ChatStreamRequest(message="ret login.py", mode="code", session_id=sid)))
    assert e.value.status_code == 403
    assert startet == []


# ── Desk uden app_id-claim i tokenet (Bjørn 20/9-2026) ──────────────────────
def test_desk_uden_claim_kan_taende_reglen_med_sit_eget_app_id(ejer):
    """Han sad i desk på sin computer og kunne ikke tænde reglen.

    Svaret var «Denne klient er ikke en desk-installation (intet app_id) —
    tænd reglen fra desk på din computer, så den selv bliver tilføjet.» Han
    VAR i desk på sin computer. Målt på hans token: claims er
    `exp, iat, iss, role, sub` — claim'en sættes kun af Google-login-flowet,
    og hans token er ældre. Uden en fallback var reglen permanent utændelig.
    """
    seed, som = ejer
    som(app_id="")                                   # tokenet bærer INTET app_id
    ae.saet_enheds_krav(ae.KravReq(
        aktiv=True, totp=tv.generate_code(seed), navn="CheifOne",
        app_id="desk-uuid-fra-broen",
    ))
    assert dd.kraev_aktivt() is True
    assert [e["navn"] for e in ae.enheder()["enheder"]] == ["CheifOne"]


def test_uden_baade_claim_og_krop_siger_den_stadig_fra(ejer):
    """Fallbacken må ikke gøre reglen tændelig fra hvad som helst."""
    seed, som = ejer
    som(app_id="")
    with pytest.raises(HTTPException) as e:
        ae.saet_enheds_krav(ae.KravReq(aktiv=True, totp=tv.generate_code(seed)))
    assert e.value.status_code == 400
    assert dd.kraev_aktivt() is False                 # og reglen blev IKKE tændt


def test_claimen_vinder_over_kroppen(ejer):
    """Et token-bundet desk må ikke kunne omskrive sin egen identitet.

    Registret nøgles på app_id'et (`noegle`), så påstanden kan måles direkte:
    efter en registrering hvor tokenet siger ét og kroppen noget andet, skal
    rækken bære TOKENETS værdi.
    """
    seed, som = ejer
    som(app_id="fra-token")
    ae.registrer_denne_computer(ae.TotpReq(
        totp=tv.generate_code(seed), navn="X", app_id="paastaaet-af-klienten"))
    # `liste()` viser ikke nøglen (den er app_id'et), så vi spørger registret
    # direkte — det er dér påstanden kan efterprøves.
    with dd.connect() as conn:
        noegler = [r[0] for r in conn.execute(
            "SELECT noegle FROM enheder WHERE user_id = 'u1'").fetchall()]
    assert noegler == ["fra-token"]


def test_koden_kraeves_FOER_app_id_overhovedet_laeses(ejer):
    """Fallbacken hviler på at totrinskoden er den anden faktor."""
    seed, som = ejer
    som(app_id="")
    with pytest.raises(HTTPException) as e:
        ae.registrer_denne_computer(ae.TotpReq(totp="000000", app_id="hvad-som-helst"))
    assert e.value.status_code in (400, 401, 403, 429)
    assert ae.enheder()["enheder"] == []


# ── Tokenet skal BAERE app_id bagefter (29/9-2026) ──────────────────────────
#
# Registreringen har haft en fallback siden 20/9: findes der intet
# `app_id`-claim, tages det fra kroppen. Den blev tilfoejet fordi Bjoerns token
# er aeldre end Google-login-flowet og kun har `exp, iat, iss, role, sub`.
#
# Men KONTROLLEN (`kode_adgang` -> `maa_bruge_kode`) laeser kun claim'et. Maalt
# paa CT105 29/9 med enheden registreret og AKTIV:
#
#     maa_bruge_kode(app_id="e74bd42a-…")  -> True    (det registreringen gemte)
#     maa_bruge_kode(app_id="")            -> False   (det tokenet gav)
#
# Enheden kunne tilfoejes, men aldrig genkendes. Hullet blev lukket den ene vej
# og glemt den anden. Bjoern: «min computer er tilføjet men kan ikk få lov at
# starte en kode session».


def _claims(token: str) -> dict:
    from core.runtime.jarvisx_auth import verify_token
    return verify_token(f"Bearer {token}")


def test_registreringen_giver_et_token_der_BAERER_app_id(ejer):
    """Uden claim'et er enheden tilfoejet og usynlig. Tokenet er rettelsen."""
    seed, som = ejer
    som(app_id="")                       # som Bjoerns token: ingen claim
    svar = ae.registrer_denne_computer(
        ae.TotpReq(totp=tv.generate_code(seed), navn="CheifOne", app_id="desk-abc"))
    assert svar.get("token"), "intet token — enheden ville forblive usynlig"
    assert _claims(svar["token"])["app_id"] == "desk-abc"


def test_tokenet_giver_ALDRIG_mere_end_kalderen_havde(ejer):
    """Ruten udsteder et token. Den maa ikke kunne loefte en rolle."""
    seed, som = ejer
    som(uid="u9", rolle="member", app_id="")
    # en member maa gerne tilfoeje sin egen computer
    svar = ae.registrer_denne_computer(
        ae.TotpReq(totp=tv.generate_code(seed), navn="Laptop", app_id="desk-m"))
    c = _claims(svar["token"])
    assert c["role"] == "member"
    assert c["sub"] == "u9"


def test_reglen_kan_taendes_OG_giver_tokenet_med(ejer):
    seed, som = ejer
    som(app_id="")
    svar = ae.saet_enheds_krav(
        ae.KravReq(aktiv=True, totp=tv.generate_code(seed), navn="CheifOne", app_id="desk-x"))
    assert svar["kraev_aktivt"] is True
    assert _claims(svar["token"])["app_id"] == "desk-x"


def test_at_SLUKKE_reglen_udsteder_ikke_et_token(ejer):
    """Kun naar en enhed faktisk blev registreret. Et token uden grund er en
    credential der flyder rundt uden formaal."""
    seed, som = ejer
    som(app_id="")
    ae.saet_enheds_krav(ae.KravReq(aktiv=True, totp=tv.generate_code(seed),
                                   navn="CheifOne", app_id="desk-x"))
    svar = ae.saet_enheds_krav(ae.KravReq(aktiv=False, totp=tv.generate_code(seed)))
    assert "token" not in svar


def test_claim_vinder_stadig_over_kroppen(ejer):
    """En token-bunden desk maa ikke kunne omskrive sin egen identitet."""
    seed, som = ejer
    som(app_id="fra-claim")
    svar = ae.registrer_denne_computer(
        ae.TotpReq(totp=tv.generate_code(seed), navn="C", app_id="fra-kroppen"))
    assert _claims(svar["token"])["app_id"] == "fra-claim"


def test_KAEDEN_hele_vejen_registrér_saa_maa_man_bruge_kode(ejer, monkeypatch):
    """Det er hele fejlen samlet: foer gav den her False til sidst."""
    from core.identity import kode_adgang
    seed, som = ejer
    som(app_id="")
    ae.saet_enheds_krav(ae.KravReq(aktiv=True, totp=tv.generate_code(seed),
                                   navn="CheifOne", app_id="desk-kaede"))
    svar = ae.registrer_denne_computer(
        ae.TotpReq(totp=tv.generate_code(seed), navn="CheifOne", app_id="desk-kaede"))
    # klienten gemmer tokenet; naeste anmodning baerer claim'et
    ny = _claims(svar["token"])
    som(app_id=str(ny["app_id"]))
    assert kode_adgang.kode_tilladt() is True


def test_en_fejlet_token_udstedelse_vaelter_ikke_registreringen(ejer, monkeypatch):
    """Enheden BLEV tilfoejet. Et halvt nej ville se ud som om den ikke blev."""
    seed, som = ejer
    som(app_id="")
    import core.runtime.jarvisx_auth as ja
    monkeypatch.setattr(ja, "issue_token",
                        lambda **kw: (_ for _ in ()).throw(RuntimeError("noeglen vaek")))
    svar = ae.registrer_denne_computer(
        ae.TotpReq(totp=tv.generate_code(seed), navn="C", app_id="desk-z"))
    assert "token" not in svar
    assert [e["navn"] for e in ae.enheder()["enheder"]] == ["C"]
