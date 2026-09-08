"""Fornyelse af bearer-tokens.

Baggrunden er målt, ikke gættet: Mikkels telefon fik 927 × 401 på seks timer
med grunden `token expired`, og der var nul forsøg på `/api/auth/refresh` —
fordi ingen klient nogensinde har fået en refresh-token at forsøge med.

Testene her holder på de egenskaber der gør fornyelse forsvarlig. Den vigtige
er ikke at fornyelse VIRKER; det er at den aldrig giver mere end den fik.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest

os.environ.setdefault("JARVISX_AUTH_SECRET", "t" * 64)

from core.runtime import token_renewal as tr  # noqa: E402
from core.runtime.jarvisx_auth import issue_token, verify_token  # noqa: E402


@pytest.fixture(autouse=True)
def _isoleret_state(monkeypatch):
    """Bogføring af jti'er i hukommelsen — ingen test rører runtime-DB'en."""
    butik: dict[str, object] = {}
    monkeypatch.setattr("core.runtime.db.get_runtime_state_value",
                        lambda k, d=None: butik.get(k, d), raising=False)
    monkeypatch.setattr("core.runtime.db.set_runtime_state_value",
                        lambda k, v: butik.__setitem__(k, v), raising=False)
    return butik


def _token(**kw) -> str:
    kw.setdefault("user_id", "u-mikkel")
    kw.setdefault("role", "member")
    return issue_token(**kw)["token"]


def _udloebet(dage_siden: float, *, user_id="u-mikkel", role="member", ttl_dage=365, **ekstra) -> str:
    """Et ÆGTE signeret token der allerede er udløbet for `dage_siden` dage."""
    import jwt
    from core.runtime.jarvisx_auth import _ALGO, _ISSUER, _read_secret
    exp = datetime.now(UTC) - timedelta(days=dage_siden)
    payload = {"sub": user_id, "role": role, "iss": _ISSUER,
               "iat": int((exp - timedelta(days=ttl_dage)).timestamp()),
               "exp": int(exp.timestamp()), **ekstra}
    return jwt.encode(payload, _read_secret(), algorithm=_ALGO)


# ── grundvejen ────────────────────────────────────────────────────────────

def test_gyldigt_token_kan_fornys(monkeypatch):
    monkeypatch.setattr(tr, "_gemt_bruger", lambda uid: None)
    res = tr.renew(_token())
    assert res["ok"] is True
    assert verify_token(res["token"])["sub"] == "u-mikkel"
    assert res["grace"] is False


def test_udloebet_token_i_naadevinduet_kan_stadig_fornys(monkeypatch):
    """Genopretningsvejen — hele grunden til at modulet findes.

    En telefon der har ligget stille skal kunne komme tilbage selv, uden at
    nogen bærer et token over på den i hånden.
    """
    monkeypatch.setattr(tr, "_gemt_bruger", lambda uid: None)
    res = tr.renew(_udloebet(3))
    assert res["ok"] is True
    assert res["grace"] is True
    assert verify_token(res["token"])["sub"] == "u-mikkel"


def test_for_gammelt_token_afvises(monkeypatch):
    monkeypatch.setattr(tr, "_gemt_bruger", lambda uid: None)
    res = tr.renew(_udloebet(tr.GRACE_DAYS + 1))
    assert res["ok"] is False
    assert "too old" in res["reason"]


def test_bearer_praefiks_taales(monkeypatch):
    monkeypatch.setattr(tr, "_gemt_bruger", lambda uid: None)
    assert tr.renew("Bearer " + _token())["ok"] is True


# ── fornyelse giver aldrig mere end den fik ───────────────────────────────

def test_forfalsket_signatur_afvises():
    import jwt
    falsk = jwt.encode({"sub": "u-mikkel", "role": "owner", "iss": "jarvisx",
                        "iat": 1, "exp": 9999999999}, "en-helt-anden-hemmelighed",
                       algorithm="HS256")
    res = tr.renew(falsk)
    assert res["ok"] is False
    assert res["reason"] == "invalid token"


def test_degraderet_bruger_kan_ikke_forny_sig_tilbage_til_owner(monkeypatch):
    """Den vigtigste af dem alle.

    Tokenet siger owner fordi det VAR sandt da det blev udstedt. Kartoteket
    siger member nu. Fornyelse må følge kartoteket.
    """
    monkeypatch.setattr(tr, "_gemt_bruger", lambda uid: {"role": "member", "deleted": False})
    res = tr.renew(_token(user_id="u-x", role="owner"))
    assert res["ok"] is True
    assert res["role"] == "member"
    assert verify_token(res["token"])["role"] == "member"


def test_fornyelse_hæver_aldrig_rollen(monkeypatch):
    """Omvendt vej: et kartotek der siger owner må ikke løfte et member-token."""
    monkeypatch.setattr(tr, "_gemt_bruger", lambda uid: {"role": "owner", "deleted": False})
    res = tr.renew(_token(user_id="u-x", role="member"))
    assert res["role"] == "member"


def test_ukendt_bruger_beholder_token_rollen(monkeypatch):
    """Lotte står i SQLite, Mikkel i users.json. Et opslag der fejler må ikke
    stille degradere nogen — tokenet er signeret af os."""
    monkeypatch.setattr(tr, "_gemt_bruger", lambda uid: None)
    assert tr.renew(_token(user_id="u-ukendt", role="partner"))["role"] == "partner"


def test_slettet_bruger_kan_ikke_forny(monkeypatch):
    monkeypatch.setattr(tr, "_gemt_bruger", lambda uid: {"role": "member", "deleted": True})
    res = tr.renew(_token())
    assert res["ok"] is False
    assert res["reason"] == "user removed"


def test_levetiden_arves_den_forlaenges_ikke(monkeypatch):
    monkeypatch.setattr(tr, "_gemt_bruger", lambda uid: None)
    res = tr.renew(_token(ttl_days=30))
    nyt = verify_token(res["token"])
    dage = (nyt["exp"] - nyt["iat"]) / 86400
    assert 29.5 < dage < 30.5


def test_app_id_overlever_fornyelse(monkeypatch):
    """Desk'ens TOTP-binding hænger på app_id. Tabes den, begynder Bjørns egen
    app at bede om TOTP i sin egen session."""
    monkeypatch.setattr(tr, "_gemt_bruger", lambda uid: None)
    res = tr.renew(_token(app_id="desk-abc"))
    assert verify_token(res["token"])["app_id"] == "desk-abc"


# ── afbryderen ────────────────────────────────────────────────────────────

def test_fornyet_token_faar_en_jti_saa_det_kan_slukkes(monkeypatch):
    """Tokens i brug i dag har INGEN jti og kan derfor kun slukkes ved at
    rotere hemmeligheden — altså ved at smide alle ud."""
    monkeypatch.setattr(tr, "_gemt_bruger", lambda uid: None)
    res = tr.renew(_token())
    assert verify_token(res["token"]).get("jti")


def test_revoke_slukker_brugerens_fornyede_tokens(monkeypatch, _isoleret_state):
    monkeypatch.setattr(tr, "_gemt_bruger", lambda uid: None)
    res = tr.renew(_token(user_id="u-mikkel"))
    jti = verify_token(res["token"])["jti"]

    assert tr.revoke_user_tokens("u-mikkel") == 1

    from core.identity.user_db import _REVOKED_KEY
    assert jti in json.loads(json.dumps(_isoleret_state[_REVOKED_KEY]))
    assert json.loads(_isoleret_state[tr._JTI_INDEX_PREFIX + "u-mikkel"]) == []


def test_sortlistet_token_kan_ikke_forny_sig_videre(monkeypatch):
    """Ellers ville afbryderen ikke virke: et slukket token kunne veksle sig
    til et nyt, uslukket et."""
    monkeypatch.setattr(tr, "_gemt_bruger", lambda uid: None)
    jti = uuid.uuid4().hex
    monkeypatch.setattr("core.identity.user_db.is_api_key_revoked", lambda j: j == jti)
    res = tr.renew(_token(extra_claims={"jti": jti}))
    assert res["ok"] is False
    assert res["reason"] == "token revoked"


def test_bogfoerings_fejl_vaelter_ikke_fornyelsen(monkeypatch):
    """Tokenet er stadig gyldigt hvis kun bogføringen fejler. Det er kun
    afbryderen der mangler for netop dét token — og det er den rigtige pris."""
    monkeypatch.setattr(tr, "_gemt_bruger", lambda uid: None)
    def _braek(*a, **k): raise RuntimeError("DB laast")
    monkeypatch.setattr("core.runtime.db.set_runtime_state_value", _braek, raising=False)
    assert tr.renew(_token())["ok"] is True
