"""Tests for /central/affect — owner-gated affektiv fordelings-route (rådets #4)."""
from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

import apps.api.jarvis_api.routes.central_affect as ca


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_owner_gate_propagates(monkeypatch):
    def deny() -> None:
        raise HTTPException(status_code=403, detail="nope")

    monkeypatch.setattr(ca, "_require_owner", deny)
    with pytest.raises(HTTPException) as ei:
        _run(ca.get_affect())
    assert ei.value.status_code == 403


def test_returns_distribution(monkeypatch):
    monkeypatch.setattr(ca, "_require_owner", lambda: None)
    out = _run(ca.get_affect())
    for k in ("tryk", "varme", "uro", "ro", "dominant", "ts"):
        assert k in out
    assert isinstance(out["dominant"], str)


def test_self_safe_when_surface_raises(monkeypatch):
    monkeypatch.setattr(ca, "_require_owner", lambda: None)

    import core.services.central_affect as caff
    monkeypatch.setattr(
        caff, "build_affect_surface",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    out = _run(ca.get_affect())
    # route must not raise — falls back to neutral distribution
    assert out["dominant"] == "ro"
    assert "ts" in out
