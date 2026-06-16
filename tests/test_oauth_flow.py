"""OAuth-flow: signeret state + authorize-URL + code-bytte."""
from __future__ import annotations
import core.services.oauth_flow as of


def test_state_roundtrip():
    s = of.sign_state("u1", "github")
    assert of.verify_state(s) == ("u1", "github")


def test_state_tampered_rejected():
    s = of.sign_state("u1", "github")
    body = s.split(".", 1)[0]
    assert of.verify_state(body + "." + "deadbeef" * 4) is None


def test_state_expired_rejected():
    s = of.sign_state("u1", "github", now=1000.0)
    assert of.verify_state(s, now=1000.0 + 10000) is None


def test_build_authorize_url(monkeypatch):
    monkeypatch.setattr(of, "_secret", lambda k, d="": "CID123" if k.endswith("client_id") else d)
    url = of.build_authorize_url("github", "u1")
    assert url and "client_id=CID123" in url and "state=" in url and "response_type=code" in url
    assert "redirect_uri=https%3A%2F%2Fapi.srvlab.dk%2Fapi%2Foauth%2Fgithub%2Fcallback" in url


def test_build_unknown_or_unconfigured(monkeypatch):
    monkeypatch.setattr(of, "_secret", lambda k, d="": "CID")
    assert of.build_authorize_url("nope", "u1") is None
    monkeypatch.setattr(of, "_secret", lambda k, d="": "")
    assert of.build_authorize_url("github", "u1") is None


def test_exchange_code(monkeypatch):
    monkeypatch.setattr(of, "_secret", lambda k, d="": "x")
    import httpx
    class _R:
        status_code = 200
        def json(self): return {"access_token": "gho_y", "scope": "repo"}
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _R())
    assert of.exchange_code("github", "code123")["access_token"] == "gho_y"


def test_exchange_code_failure(monkeypatch):
    monkeypatch.setattr(of, "_secret", lambda k, d="": "x")
    import httpx
    class _R:
        status_code = 401
        def json(self): return {}
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _R())
    assert of.exchange_code("github", "c") is None
