"""publish_file: adressen skal virke DER HVOR BRUGEREN ER.

To fejl laa oven i hinanden og gjorde funktionen ubrugelig uden at nogen af
dem saa ud som en fejl.

1. URL'en var hardkodet `http://localhost:8080/...`. Filen blev udgivet helt
   korrekt — og brugeren fik en adresse der kun virker paa den maskine Jarvis
   selv koerer paa. Paa en telefon er `localhost` telefonen.

2. Hallucinations-vagten hentede den URL UDEN Authorization. Ruten kraever
   godkendelse, saa svaret var 401, vagten satte url_verified=False og skrev
   «Praesenter IKKE URL'en for brugeren — den virker ikke». Hver eneste gang.

Funktionen virkede. Vagten maalte et ubeskyttet kald mod en beskyttet rute og
kaldte det et nedbrud.
"""
from __future__ import annotations

from urllib import error as urllib_error

import pytest


def _publish(monkeypatch, tmp_path, *, base="", svar=200, fejl=None):
    from core.tools import simple_tools_native as N
    monkeypatch.setattr(N, "JARVIS_HOME", tmp_path, raising=False)
    import core.runtime.config as C
    monkeypatch.setattr(C, "JARVIS_HOME", tmp_path, raising=False)
    import core.runtime.secrets as S
    monkeypatch.setattr(S, "read_runtime_key", lambda k, e=None, **kw: base)

    class _Svar:
        status = svar
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def _open(req, timeout=5):
        if fejl is not None:
            raise fejl
        return _Svar()
    monkeypatch.setattr(N.urllib_request, "urlopen", _open)
    return N._exec_publish_file({"filename": "x.html", "content": "<h1>hej</h1>"})


def test_adressen_kommer_fra_konfigurationen(monkeypatch, tmp_path):
    r = _publish(monkeypatch, tmp_path, base="https://api.example.dk")
    assert r["url"] == "https://api.example.dk/files/x.html"
    assert "localhost" not in r["url"]
    assert not r.get("kun_lokal")


def test_uden_konfiguration_siges_det_HOEJT(monkeypatch, tmp_path):
    """En localhost-adresse er ikke en fejl paa maskinen, men den kan ikke
    deles. Uden denne besked ville svaret se fuldt gyldigt ud."""
    r = _publish(monkeypatch, tmp_path, base="")
    assert r["url"].startswith("http://localhost:8080/")
    assert r["kun_lokal"] is True
    assert "runtime.json" in r["warning"]


def test_401_betyder_at_ruten_LEVER(monkeypatch, tmp_path):
    """DEN afgoerende. Ruten kraever godkendelse; et afvist ubeskyttet kald er
    bevis paa at noget lytter og beskytter filen — ikke paa at den er brudt."""
    fejl = urllib_error.HTTPError("u", 401, "Unauthorized", {}, None)
    r = _publish(monkeypatch, tmp_path, base="https://api.example.dk", fejl=fejl)
    assert r["url_verified"] is True
    assert "warning" not in r


def test_404_betyder_stadig_at_noget_er_galt(monkeypatch, tmp_path):
    """Kontrolarm. Uden den ville en vagt der accepterede ALT bestaa ovenfor."""
    fejl = urllib_error.HTTPError("u", 404, "Not Found", {}, None)
    r = _publish(monkeypatch, tmp_path, base="https://api.example.dk", fejl=fejl)
    assert r["url_verified"] is False
    assert "404" in r.get("url_verify_error", "")


def test_serveren_nede_er_ogsaa_en_fejl(monkeypatch, tmp_path):
    r = _publish(monkeypatch, tmp_path, base="https://api.example.dk",
                 fejl=OSError("connection refused"))
    assert r["url_verified"] is False
