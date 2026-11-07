"""Tests for /central/memory-state — owner-gated, self-safe."""
from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

import apps.api.jarvis_api.routes.central as central
from core.services import memory_state_surface as agg


def test_route_is_registered_under_central():
    paths = {(r.path, tuple(sorted(r.methods))) for r in central.router.routes}
    assert ("/central/memory-state", ("GET",)) in paths


def test_owner_gate_blocks(monkeypatch):
    def deny() -> None:
        raise HTTPException(status_code=403, detail="nope")

    monkeypatch.setattr(central, "_require_owner", deny)
    with pytest.raises(HTTPException) as ei:
        asyncio.run(central.central_memory_state())
    assert ei.value.status_code == 403


def test_route_returns_all_keys(monkeypatch):
    monkeypatch.setattr(central, "_require_owner", lambda: None)
    out = asyncio.run(central.central_memory_state())
    assert out["mode"] == "memory-state-v1"
    assert list(out["surfaces"]) == agg.producer_names()


def test_route_survives_failing_surface(monkeypatch):
    import core.services.memory_graph as mg

    monkeypatch.setattr(central, "_require_owner", lambda: None)
    monkeypatch.setattr(mg, "build_memory_graph_surface",
                        lambda: (_ for _ in ()).throw(ValueError("kaput")))
    out = asyncio.run(central.central_memory_state())
    assert out["surfaces"]["memory_graph"] == {"active": False, "reason": "ValueError: kaput"}
    assert list(out["surfaces"]) == agg.producer_names()
