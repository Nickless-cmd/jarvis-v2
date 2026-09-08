"""401'erne sagde ikke hvorfor.

Mikkels telefon gav **927 afvisninger på seks timer** fra 87.52.110.16 — og
intet i serverloggen kunne skelne «udløbet» fra «forkert signatur» fra «ingen
token». Grunden stod kun i svaret til klienten. Diagnosen krævede derfor ti
målinger i stedet for ét opslag.
"""

from __future__ import annotations

import logging
from unittest.mock import Mock

import apps.api.jarvis_api.middleware.jarvisx_user_routing as M


def _request(host="1.2.3.4", path="/presence/ping"):
    r = Mock()
    r.client = Mock(host=host)
    r.url = Mock(path=path)
    return r


def _nulstil():
    M._AFVIS_SIDST.clear()


def test_grunden_logges(caplog):
    _nulstil()
    with caplog.at_level(logging.WARNING):
        M._log_auth_afvisning("token expired", _request())
    assert "token expired" in caplog.text


def test_klient_og_sti_kommer_med(caplog):
    """Uden dem kan man ikke se HVEM der hamrer — det var hele problemet."""
    _nulstil()
    with caplog.at_level(logging.WARNING):
        M._log_auth_afvisning("token expired", _request("87.52.110.16", "/mobile/latest"))
    assert "87.52.110.16" in caplog.text and "/mobile/latest" in caplog.text


def test_en_hamrende_klient_giver_ET_signal_ikke_tusind(caplog):
    """927 linjer er ikke et bedre signal end én."""
    _nulstil()
    with caplog.at_level(logging.WARNING):
        for _ in range(50):
            M._log_auth_afvisning("token expired", _request())
    assert caplog.text.count("auth-afvist") == 1


def test_forskellige_grunde_logges_hver_for_sig(caplog):
    _nulstil()
    with caplog.at_level(logging.WARNING):
        M._log_auth_afvisning("token expired", _request())
        M._log_auth_afvisning("invalid token: bad signature", _request())
    assert caplog.text.count("auth-afvist") == 2


def test_forskellige_klienter_logges_hver_for_sig(caplog):
    _nulstil()
    with caplog.at_level(logging.WARNING):
        M._log_auth_afvisning("token expired", _request("1.1.1.1"))
        M._log_auth_afvisning("token expired", _request("2.2.2.2"))
    assert caplog.text.count("auth-afvist") == 2


def test_token_logges_ALDRIG(caplog):
    """Grunden må siges højt; legitimationen må ikke."""
    import inspect

    src = inspect.getsource(M._log_auth_afvisning)
    assert "raw_auth" not in src and "authorization" not in src.lower()


def test_logningen_kan_ikke_vaelte_en_request(caplog):
    _nulstil()
    daarlig = Mock()
    daarlig.client = None
    daarlig.url = None
    M._log_auth_afvisning("token expired", daarlig)  # må ikke kaste


# ── fornyelse skal kunne nås af netop den klient der er låst ude ──────────

def test_fornyelse_er_public():
    """Kræver /auth/renew et gyldigt token, kan den klient der har brug for den
    per definition ikke nå den. Udstedelse er stadig ejer-beskyttet."""
    assert M._is_public_path("/api/auth/renew") is True
    assert M._is_public_path("/api/auth/issue") is False


def _svar_paa(token: str) -> dict:
    """Kør middlewaren med et ægte token og læs 401-kroppen."""
    import asyncio, json
    from unittest.mock import patch

    req = Mock()
    req.method = "GET"
    req.url = Mock(path="/api/chat")
    req.client = Mock(host="9.9.9.9")
    req.state = Mock()
    req.headers = {"authorization": "Bearer " + token}

    async def _next(_r):  # pragma: no cover — nås ikke ved 401
        raise AssertionError("burde have været afvist")

    _nulstil()
    with patch("core.runtime.jarvisx_auth.auth_required", return_value=True):
        svar = asyncio.run(M.jarvisx_user_routing_middleware(req, _next))
    assert svar.status_code == 401
    return json.loads(bytes(svar.body).decode("utf-8"))


def test_401_fortaeller_om_der_er_en_vej_tilbage():
    """`can_renew` er forskellen på «vent, jeg forny'r» og «hent ejeren».

    Et udløbet token kan veksles. En forkert signatur kan ikke — der er intet
    at forny, og en klient der prøver alligevel hamrer bare et nyt sted.
    """
    import os
    os.environ["JARVISX_AUTH_SECRET"] = "m" * 64
    import jwt
    from datetime import UTC, datetime, timedelta

    nu = datetime.now(UTC)
    krav = {"sub": "u-mikkel", "role": "member", "iss": "jarvisx",
            "iat": int((nu - timedelta(days=40)).timestamp()),
            "exp": int((nu - timedelta(days=10)).timestamp())}

    udloebet = jwt.encode(krav, "m" * 64, algorithm="HS256")
    forfalsket = jwt.encode({**krav, "exp": int((nu + timedelta(days=1)).timestamp())},
                            "en-helt-anden-hemmelighed", algorithm="HS256")

    assert _svar_paa(udloebet)["can_renew"] is True
    assert _svar_paa(forfalsket)["can_renew"] is False
