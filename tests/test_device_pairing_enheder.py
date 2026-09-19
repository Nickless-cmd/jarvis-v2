"""Parring kræver totrinskode og registrerer telefonen som enhed (19/9-2026)."""
from __future__ import annotations

import pytest

import core.identity.users as users
from core.runtime import db_devices as dd
from core.services import device_pairing as dp
from core.services import totp_verifier as tv


@pytest.fixture
def seed(isolated_runtime, monkeypatch):
    s = tv.generate_seed()
    monkeypatch.setattr(users, "get_totp_seed", lambda discord_id: s if discord_id == "u1" else "")
    tv._ATTEMPTS.clear()
    return s


def test_uden_totp_nøgle_kan_der_ikke_parres(seed):
    with pytest.raises(dp.TotpFejl) as e:
        dp.kraev_totp("u2", "123456")
    assert e.value.kode == 412 and "totrinsbekræftelse" in str(e.value)


def test_forkert_kode_og_for_mange_forsøg(seed):
    with pytest.raises(dp.TotpFejl) as e:
        dp.kraev_totp("u1", "000000")
    assert e.value.kode == 403
    for _ in range(2):
        with pytest.raises(dp.TotpFejl):
            dp.kraev_totp("u1", "000000")
    with pytest.raises(dp.TotpFejl) as e:
        dp.kraev_totp("u1", tv.generate_code(seed))
    assert e.value.kode == 429


def test_rigtig_kode_og_indløsning_registrerer_telefonen(seed):
    from core.runtime.jarvisx_auth import verify_token
    dp.kraev_totp("u1", tv.generate_code(seed))
    kode = dp.create_pairing("u1", "owner")["code"]
    svar = dp.redeem(kode, navn="Bjørns Pixel", platform="android")
    assert svar and svar["enhed"]
    assert verify_token(svar["token"])["enhed"] == svar["enhed"]
    assert [e["navn"] for e in dd.liste("u1")] == ["Bjørns Pixel"]
    assert dp.status(kode)["navn"] == "Bjørns Pixel"
    assert dp.redeem(kode) is None  # engangs
