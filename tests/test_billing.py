"""Tests for billing-skelet (§21.6)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from apps.api.jarvis_api.routes.billing import router


def _client(monkeypatch, configured: bool):
    import apps.api.jarvis_api.routes.billing as b
    monkeypatch.setattr(b, "_stripe_key", lambda: ("sk_test_x" if configured else ""))
    app = FastAPI(); app.include_router(router)
    return TestClient(app)


def test_status_unconfigured(monkeypatch) -> None:
    c = _client(monkeypatch, configured=False)
    d = c.get("/billing/status").json()
    assert d["configured"] is False and "plus" in d["tiers"]


def test_checkout_503_when_unconfigured(monkeypatch) -> None:
    c = _client(monkeypatch, configured=False)
    r = c.post("/billing/checkout", json={"tier": "plus", "user_id": "d-mikkel"})
    assert r.status_code == 503


def test_checkout_invalid_tier(monkeypatch) -> None:
    c = _client(monkeypatch, configured=True)
    r = c.post("/billing/checkout", json={"tier": "gratis", "user_id": "x"})
    assert r.status_code == 400
