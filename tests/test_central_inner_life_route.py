"""Tests for /central/inner-life (Fase A8+) — owner-gated reduceret digest.

Verificerer:
  - owner-gate: gate der rejser 403 propagerer.
  - to grupper (inner_life 22-agtig + experiment) surfacer i output.
  - hver sektion absorberes som egen nerve: cluster="mind" for living-mind,
    cluster="experiment" for AGI/experiment-laget, + aggregat self:inner_life.
  - self-safe: proxy der kaster → tomme grupper men stadig 200-shape dict.
  - ingen rå tekst-nøgler lækker pr. sektion.
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


def test_inner_life_shape_and_per_section_absorb(monkeypatch):
    monkeypatch.setattr(cs, "require_central_owner", lambda: None)

    fake = {
        "inner_life": {
            "thought_stream": {"liveness": True, "count": 5},
            "dream": {"liveness": False, "count": 0},
        },
        "experiment": {
            "adaptive_learning": {"liveness": True, "count": 3},
            "loop_runtime": {"liveness": True, "count": 9},
        },
        "live_count": 3,
        "total": 4,
    }
    monkeypatch.setattr(proxy_mod, "proxy_or_local", lambda name, builder: fake)

    calls = []
    monkeypatch.setattr(cs, "absorb", lambda *a, **k: calls.append((a, k)))

    out = _run(cs.get_inner_life())
    assert "inner_life" in out and "ts" in out
    body = out["inner_life"]
    assert body["inner_life"] == fake["inner_life"]
    assert body["experiment"] == fake["experiment"]
    assert body["live_count"] == 3
    assert body["total"] == 4

    # Byg map af absorb-kald pr. (cluster, nerve).
    by_key = {(a[0], a[1]): (a, k) for (a, k) in calls}

    # inner-life-sektioner → cluster="mind" med learn_key="mind:<name>"
    assert ("mind", "thought_stream") in by_key
    assert by_key[("mind", "thought_stream")][1].get("learn_key") == "mind:thought_stream"
    assert ("mind", "dream") in by_key

    # experiment-sektioner → cluster="experiment" med learn_key="experiment:<name>"
    assert ("experiment", "adaptive_learning") in by_key
    assert by_key[("experiment", "adaptive_learning")][1].get("learn_key") == "experiment:adaptive_learning"
    assert ("experiment", "loop_runtime") in by_key

    # aggregat-absorb bevaret
    assert ("self", "inner_life") in by_key
    assert by_key[("self", "inner_life")][0][2] == {"live_count": 3, "total": 4}

    # ingen rå tekst-nøgler i nogen sektion
    for grp in ("inner_life", "experiment"):
        for sec in body[grp].values():
            assert set(sec.keys()) <= {"liveness", "count"}


def test_inner_life_self_safe_when_proxy_raises(monkeypatch):
    monkeypatch.setattr(cs, "require_central_owner", lambda: None)

    def boom(name, builder):
        raise RuntimeError("nede")

    monkeypatch.setattr(proxy_mod, "proxy_or_local", boom)
    monkeypatch.setattr(cs, "absorb", lambda *a, **k: None)

    out = _run(cs.get_inner_life())
    assert out["inner_life"]["inner_life"] == {}
    assert out["inner_life"]["experiment"] == {}
    assert out["inner_life"]["live_count"] == 0
    assert "ts" in out
