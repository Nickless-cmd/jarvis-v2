"""Tests for §20 API-hærdning (security headers, CORS-whitelist, rate limit)."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.jarvis_api.middleware.security_headers import (
    SecurityHeadersMiddleware, SimpleRateLimitMiddleware, cors_allowed_origins,
)


def _app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(SimpleRateLimitMiddleware)

    @app.get("/x")
    def _x():
        return {"ok": True}
    return app


def test_security_headers_present() -> None:
    c = TestClient(_app())
    r = c.get("/x")
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert "Strict-Transport-Security" in r.headers
    assert r.headers["Referrer-Policy"] == "no-referrer"


def test_csp_gated_off_by_default(monkeypatch) -> None:
    monkeypatch.delenv("JARVISX_CSP", raising=False)
    c = TestClient(_app())
    assert "Content-Security-Policy" not in c.get("/x").headers


def test_csp_on_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("JARVISX_CSP", "1")
    c = TestClient(_app())
    assert "default-src 'none'" in c.get("/x").headers.get("Content-Security-Policy", "")


def test_cors_default_is_star(monkeypatch) -> None:
    monkeypatch.delenv("JARVISX_CORS_ORIGINS", raising=False)
    assert cors_allowed_origins() == ["*"]


def test_cors_whitelist_from_env(monkeypatch) -> None:
    monkeypatch.setenv("JARVISX_CORS_ORIGINS", "https://a.dk, http://localhost:5174")
    assert cors_allowed_origins() == ["https://a.dk", "http://localhost:5174"]


def test_rate_limit_off_by_default(monkeypatch) -> None:
    monkeypatch.delenv("JARVISX_RATE_LIMIT", raising=False)
    c = TestClient(_app())
    for _ in range(20):
        assert c.get("/x").status_code == 200


def test_rate_limit_enforced_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("JARVISX_RATE_LIMIT", "1")
    monkeypatch.setenv("JARVISX_RATE_LIMIT_MAX", "3")
    monkeypatch.setenv("JARVISX_RATE_LIMIT_WINDOW", "60")
    c = TestClient(_app())
    codes = [c.get("/x").status_code for _ in range(5)]
    assert codes.count(200) == 3
    assert codes.count(429) == 2


# --- §20.1 HTTP→HTTPS redirect (in-app, X-Forwarded-Proto-gated) ---

from apps.api.jarvis_api.middleware.security_headers import HttpsRedirectMiddleware


def _redirect_app():
    app = FastAPI()
    app.add_middleware(HttpsRedirectMiddleware)

    @app.get("/api/x")
    def _x():
        return {"ok": True}

    @app.get("/health")
    def _h():
        return {"ok": True}
    return app


def test_https_redirect_off_by_default(monkeypatch) -> None:
    monkeypatch.delenv("JARVISX_HTTPS_REDIRECT", raising=False)
    c = TestClient(_redirect_app())
    assert c.get("/api/x").status_code == 200          # ingen redirect


def test_https_redirect_on_plain_http(monkeypatch) -> None:
    monkeypatch.setenv("JARVISX_HTTPS_REDIRECT", "1")
    c = TestClient(_redirect_app())
    r = c.get("/api/x", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"].startswith("https://")


def test_https_redirect_skips_when_forwarded_https(monkeypatch) -> None:
    monkeypatch.setenv("JARVISX_HTTPS_REDIRECT", "1")
    c = TestClient(_redirect_app())
    r = c.get("/api/x", headers={"X-Forwarded-Proto": "https"}, follow_redirects=False)
    assert r.status_code == 200                         # Caddy-proxied → ingen redirect


def test_https_redirect_health_exempt(monkeypatch) -> None:
    monkeypatch.setenv("JARVISX_HTTPS_REDIRECT", "1")
    c = TestClient(_redirect_app())
    assert c.get("/health", follow_redirects=False).status_code == 200
