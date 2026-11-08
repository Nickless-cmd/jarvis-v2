"""Lækage-tjek — k-anonymitet og de tilstande der ikke må forveksles.

Den bærende pointe er ikke at opslaget virker, men at de tre udfald holdes
adskilt: *lækket*, *ikke lækket* og *ikke afgjort*. En manglende nøgle eller
et netværksnedbrud må aldrig returnere ``breached: False`` — det ville være
en fallback der ser ud som succes, og brugeren ville tro sin kode var ren.
"""
from __future__ import annotations

import hashlib

import pytest

from core.tools import breach_check_tools as b


class _FakeResponse:
    def __init__(self, status_code: int, text: str = "", payload=None):
        self.status_code = status_code
        self.text = text
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("ikke JSON")
        return self._payload


def test_kun_fem_tegn_forlader_maskinen(monkeypatch) -> None:
    """K-anonymitet: præfikset er de første fem hex-tegn, intet andet sendes."""
    set_kald: list[str] = []

    def fake_get(url, **kwargs):
        set_kald.append(url)
        return _FakeResponse(200, "")

    monkeypatch.setattr("httpx.get", fake_get)
    r = b._exec_check_password_breach({"password": "password"})

    assert r["status"] == "ok"
    forventet = hashlib.sha1(b"password").hexdigest().upper()[:5]
    assert set_kald == [b._RANGE_URL + forventet]
    # Kun de fem tegn sendes. (At strengen "password" optræder i domænet
    # pwnedpasswords.com er ikke et læk — derfor måles længden, ikke ordet.)
    sendt = set_kald[0][len(b._RANGE_URL):]
    assert len(sendt) == 5
    assert all(c in "0123456789ABCDEF" for c in sendt)
    assert sendt == forventet


def test_laekket_password_tælles_lokalt(monkeypatch) -> None:
    """Serveren svarer med mange suffixes; kun vores eget tælles."""
    digest = hashlib.sha1(b"hunter2").hexdigest().upper()
    suffiks = digest[5:]
    krop = f"0000000000000000000000000000000000A:99\n{suffiks}:42\n"

    monkeypatch.setattr("httpx.get", lambda url, **kw: _FakeResponse(200, krop))
    r = b._exec_check_password_breach({"password": "hunter2"})

    assert r["status"] == "ok"
    assert r["breached"] is True
    assert r["count"] == 42


def test_urent_password_er_ikke_laekket(monkeypatch) -> None:
    monkeypatch.setattr("httpx.get",
                        lambda url, **kw: _FakeResponse(200, "AAA:1\nBBB:2\n"))
    r = b._exec_check_password_breach({"password": "et-helt-nyt-password"})

    assert r["status"] == "ok"
    assert r["breached"] is False
    assert r["count"] == 0


def test_netvaerksfejl_er_ikke_det_samme_som_rent(monkeypatch) -> None:
    """Den vigtigste vagt: nedbrud må ikke ligne et rent password."""
    def boom(url, **kw):
        raise ConnectionError("nede")

    monkeypatch.setattr("httpx.get", boom)
    r = b._exec_check_password_breach({"password": "password"})

    assert r["status"] == "error"
    assert "breached" not in r, "en fejl må ikke bære en breached-vaerdi"
    assert "IKKE det samme" in r["note"]


def test_http_fejl_er_ikke_rent(monkeypatch) -> None:
    monkeypatch.setattr("httpx.get", lambda url, **kw: _FakeResponse(503, ""))
    r = b._exec_check_password_breach({"password": "password"})

    assert r["status"] == "error"
    assert "breached" not in r


def test_sha1_hash_accepteres_uden_klartekst(monkeypatch) -> None:
    """Den sikre vej: hash selv, så passwordet aldrig står i værktøjskaldet."""
    digest = hashlib.sha1(b"password").hexdigest().upper()
    monkeypatch.setattr("httpx.get",
                        lambda url, **kw: _FakeResponse(200, f"{digest[5:]}:7\n"))

    r = b._exec_check_password_breach({"sha1_hash": digest})

    assert r["status"] == "ok"
    assert r["count"] == 7


def test_ugyldig_hash_afvises() -> None:
    r = b._exec_check_password_breach({"sha1_hash": "ikke-en-hash"})
    assert r["status"] == "error"


def test_hverken_password_eller_hash_afvises() -> None:
    r = b._exec_check_password_breach({})
    assert r["status"] == "error"


def test_email_uden_noegle_er_no_key_ikke_rent(monkeypatch) -> None:
    """Uden nøgle blev opslaget ALDRIG udført — og det skal siges eksplicit."""
    monkeypatch.setattr(b, "_runtime_key", lambda name: "")
    r = b._exec_check_email_breach({"email": "test@example.com"})

    assert r["status"] == "no_key"
    assert "breached" not in r, "et ikke-udført opslag må ikke se rent ud"
    assert "IKKE udført" in r["note"]


def test_email_404_betyder_rent(monkeypatch) -> None:
    monkeypatch.setattr(b, "_runtime_key", lambda name: "noegle")
    monkeypatch.setattr("httpx.get", lambda url, **kw: _FakeResponse(404))
    r = b._exec_check_email_breach({"email": "test@example.com"})

    assert r["status"] == "ok"
    assert r["breached"] is False


def test_email_med_brud_returnerer_detaljer(monkeypatch) -> None:
    monkeypatch.setattr(b, "_runtime_key", lambda name: "noegle")
    payload = [{"Name": "Adobe", "Title": "Adobe", "BreachDate": "2013-10-04",
                "DataClasses": ["Email addresses", "Passwords"],
                "PwnCount": 152445165, "IsSensitive": False}]
    monkeypatch.setattr("httpx.get",
                        lambda url, **kw: _FakeResponse(200, payload=payload))
    r = b._exec_check_email_breach({"email": "test@example.com"})

    assert r["status"] == "ok"
    assert r["breached"] is True
    assert r["count"] == 1
    assert r["breaches"][0]["name"] == "Adobe"
    assert "Passwords" in r["breaches"][0]["data_classes"]


def test_email_401_er_fejl_ikke_rent(monkeypatch) -> None:
    monkeypatch.setattr(b, "_runtime_key", lambda name: "daarlig")
    monkeypatch.setattr("httpx.get", lambda url, **kw: _FakeResponse(401))
    r = b._exec_check_email_breach({"email": "test@example.com"})

    assert r["status"] == "error"
    assert "breached" not in r


def test_ugyldig_email_afvises() -> None:
    r = b._exec_check_email_breach({"email": "ikke-en-mail"})
    assert r["status"] == "error"


def test_begge_er_registreret_som_vaerktoejer() -> None:
    """Definition og handler skal begge findes — ellers er værktøjet tavst."""
    from core.tools.simple_tools import TOOL_DEFINITIONS, _TOOL_HANDLERS

    navne = {t["function"]["name"] for t in TOOL_DEFINITIONS}
    for n in ("check_password_breach", "check_email_breach"):
        assert n in navne, f"{n} mangler i TOOL_DEFINITIONS"
        assert n in _TOOL_HANDLERS, f"{n} mangler i _TOOL_HANDLERS"
