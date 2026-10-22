"""Rate limit skal vaere TAENDT som standard, og skal taelle paa den aegte klient.

Maalt i drift 22/10-2026: `JARVISX_RATE_LIMIT` var ikke sat, saa
`_rate_limit_config()` returnerede enabled=False — nul beskyttelse mod brute
force paa `/api/auth/login` og `/api/auth/register` paa et offentligt API.

Samme maaling viste en faelde mere: Caddy ejer :443 og proxyer til
`127.0.0.1:8080`, og uvicorn koerer UDEN `--proxy-headers`. Derfor er
`request.client.host` 127.0.0.1 for ALLE kald — ogsaa dem fra internettet. En
graense paa socket-IP ville ramme alle klienter som een IP.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.jarvis_api.middleware.security_headers import (
    SimpleRateLimitMiddleware,
    _effektiv_klient_ip,
    _er_lokal_adresse,
    _rate_limit_config,
)


def _app() -> FastAPI:
    app = FastAPI()

    @app.get("/ping")
    def ping():
        return {"ok": True}

    app.add_middleware(SimpleRateLimitMiddleware)
    return app


def test_rate_limit_er_taendt_som_standard(monkeypatch):
    monkeypatch.delenv("JARVISX_RATE_LIMIT", raising=False)
    enabled, max_req, _window = _rate_limit_config()
    assert enabled is True, "en sikkerhedsgraense skal vaere taendt naar ingen har taget stilling"
    assert max_req == 120


def test_rate_limit_kan_slaas_fra(monkeypatch):
    for vaerdi in ("0", "false", "off", "no"):
        monkeypatch.setenv("JARVISX_RATE_LIMIT", vaerdi)
        assert _rate_limit_config()[0] is False


def test_offentlig_klient_rammes(monkeypatch):
    monkeypatch.setenv("JARVISX_RATE_LIMIT_MAX", "3")
    monkeypatch.setenv("JARVISX_RATE_LIMIT_WINDOW", "60")
    c = TestClient(_app())
    h = {"X-Forwarded-For": "8.8.8.8"}
    for _ in range(3):
        assert c.get("/ping", headers=h).status_code == 200
    r = c.get("/ping", headers=h)
    assert r.status_code == 429
    assert r.json()["error"] == "too_many_requests"


def test_privat_klient_slipper_igennem(monkeypatch):
    """Husets egne klienter (desk, runtime) maa ikke 429'es af deres egen polling."""
    monkeypatch.setenv("JARVISX_RATE_LIMIT_MAX", "2")
    c = TestClient(_app())
    for ip in ("10.0.0.20", "127.0.0.1", "192.168.1.5"):
        h = {"X-Forwarded-For": ip}
        for _ in range(5):
            assert c.get("/ping", headers=h).status_code == 200, ip


def test_spoofet_foerste_haab_slipper_ikke(monkeypatch):
    """En angriber kan skrive en privat IP i XFF — men den aegte adresse staar
    SIDST (Caddy tilfoejer den), og det er den vi laeser."""
    monkeypatch.setenv("JARVISX_RATE_LIMIT_MAX", "2")
    c = TestClient(_app())
    h = {"X-Forwarded-For": "10.0.0.5, 8.8.8.8"}
    for _ in range(2):
        assert c.get("/ping", headers=h).status_code == 200
    assert c.get("/ping", headers=h).status_code == 429


def test_effektiv_ip_laeser_sidste_haab():
    class _R:
        headers = {"x-forwarded-for": "1.2.3.4, 5.6.7.8"}
        client = None

    assert _effektiv_klient_ip(_R()) == "5.6.7.8"


def test_effektiv_ip_falder_tilbage_paa_socket():
    class _Klient:
        host = "203.0.113.9"

    class _R:
        headers: dict = {}
        client = _Klient()

    assert _effektiv_klient_ip(_R()) == "203.0.113.9"


def test_lokal_adresse_klassificering():
    assert _er_lokal_adresse("127.0.0.1") is True
    assert _er_lokal_adresse("10.0.0.20") is True
    assert _er_lokal_adresse("192.168.1.5") is True
    assert _er_lokal_adresse("8.8.8.8") is False
    assert _er_lokal_adresse("testclient") is False
