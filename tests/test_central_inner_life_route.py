"""Tests for /central/inner-life (Fase A8) — owner-gated reduceret inner-life-digest.

Verificerer:
  - owner-gate: gate der rejser 403 propagerer.
  - reduceret output: sections/live_count/total surfacer, absorb kaldes med cluster="self".
  - self-safe: proxy der kaster → tomt sections men stadig 200-shape dict.
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

import apps.api.jarvis_api.routes.central_self as cs
import core.services.central_runtime_proxy as proxy_mod


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_owner_gate_propagates(monkeypatch):
    def deny() -> None:
        raise HTTPException(status_code=403, detail="nope")

    monkeypatch.setattr(cs, "require_central_owner", deny)
    with pytest.raises(HTTPException) as ei:
        _run(cs.get_inner_life())
    assert ei.value.status_code == 403


def test_inner_life_shape_and_absorb(monkeypatch):
    monkeypatch.setattr(cs, "require_central_owner", lambda: None)

    fake = {
        "sections": {
            "thought_stream": {"liveness": True, "count": 5},
            "dream": {"liveness": False, "count": 0},
        },
        "live_count": 1,
        "total": 2,
    }
    monkeypatch.setattr(proxy_mod, "proxy_or_local", lambda name, builder: fake)

    calls = []
    monkeypatch.setattr(cs, "absorb", lambda *a, **k: calls.append((a, k)))

    out = _run(cs.get_inner_life())
    assert "inner_life" in out and "ts" in out
    body = out["inner_life"]
    assert body["sections"] == fake["sections"]
    assert body["live_count"] == 1
    assert body["total"] == 2

    # absorb kaldt med cluster="self", nerve="inner_life"
    assert calls, "absorb blev ikke kaldt"
    (args, kwargs) = calls[0]
    assert args[0] == "self"
    assert args[1] == "inner_life"
    assert args[2] == {"live_count": 1, "total": 2}

    # ingen rå tekst-nøgler i sektionerne
    for sec in body["sections"].values():
        assert set(sec.keys()) <= {"liveness", "count"}


def test_inner_life_self_safe_when_proxy_raises(monkeypatch):
    monkeypatch.setattr(cs, "require_central_owner", lambda: None)

    def boom(name, builder):
        raise RuntimeError("nede")

    monkeypatch.setattr(proxy_mod, "proxy_or_local", boom)
    monkeypatch.setattr(cs, "absorb", lambda *a, **k: None)

    out = _run(cs.get_inner_life())
    assert out["inner_life"]["sections"] == {}
    assert out["inner_life"]["live_count"] == 0
    assert "ts" in out
