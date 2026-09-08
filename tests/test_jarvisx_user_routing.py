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
