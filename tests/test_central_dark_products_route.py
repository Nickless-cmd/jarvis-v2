"""Tests for /central/dark-products — owner-gated projektion af mørke daemon-produkter.

Verifies:
  - owner-gated: gate raising 403 propagates.
  - per-signal absorb i RETTE naturlige cluster (integrity/cognition/memory/
    governance/channel) med korrekt nerve.
  - self-safe: proxy raising → tomt digest, stadig 200-shape.
  - ingen tekst-lækage: kun signals-dict + tællere returneres.
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

import apps.api.jarvis_api.routes.central_absorb_routes as car


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_owner_gate_propagates(monkeypatch):
    def deny() -> None:
        raise HTTPException(status_code=403, detail="nope")

    monkeypatch.setattr(car, "require_central_owner", deny)
    with pytest.raises(HTTPException) as ei:
        _run(car.get_dark_products())
    assert ei.value.status_code == 403


def test_per_signal_absorb_in_natural_cluster(monkeypatch):
    monkeypatch.setattr(car, "require_central_owner", lambda: None)

    digest = {
        "signals": {
            "apophenia": {"liveness": True, "count": 3},
            "dream_consolidation": {"liveness": True, "count": 2},
            "deep_reflection": {"liveness": False, "count": 0},
            "semantic_memory": {"liveness": True, "count": 1},
            "rule_engine": {"liveness": True, "count": 12},
            "voice_daemon": {"liveness": True, "count": 0},
        },
        "live_count": 5,
        "total": 6,
    }

    import apps.api.jarvis_api.routes.central_absorb_routes as mod
    monkeypatch.setattr(
        "core.services.central_runtime_proxy.proxy_or_local",
        lambda name, builder: digest,
    )

    calls: list[tuple] = []
    monkeypatch.setattr(
        mod, "absorb",
        lambda cluster, nerve, value, **k: calls.append((cluster, nerve, value, k)),
    )

    out = _run(car.get_dark_products())

    routed = {(c, n) for c, n, _, _ in calls}
    assert ("integrity", "apophenia") in routed
    assert ("cognition", "dream_consolidation") in routed
    assert ("cognition", "deep_reflection") in routed
    assert ("memory", "semantic") in routed
    assert ("governance", "rule_engine") in routed
    assert ("channel", "voice") in routed

    # learn_key passed per signal
    lks = {k.get("learn_key") for _, _, _, k in calls}
    assert "integrity:apophenia" in lks
    assert "channel:voice" in lks

    # per-signal absorb carries ONLY liveness+count
    for _, _, v, _ in calls:
        assert set(v.keys()) <= {"liveness", "count"}

    # returned body carries only signals + counters (no raw content)
    assert out["signals"] == digest["signals"]
    assert out["live_count"] == 5 and out["total"] == 6


def test_unknown_signal_skipped(monkeypatch):
    monkeypatch.setattr(car, "require_central_owner", lambda: None)
    monkeypatch.setattr(
        "core.services.central_runtime_proxy.proxy_or_local",
        lambda name, builder: {
            "signals": {"mystery": {"liveness": True, "count": 9}},
            "live_count": 1, "total": 1,
        },
    )
    calls: list[tuple] = []
    monkeypatch.setattr(car, "absorb", lambda c, n, v, **k: calls.append((c, n)))
    out = _run(car.get_dark_products())
    # unknown signal has no natural route → not absorbed
    assert calls == []
    assert out["total"] == 1


def test_self_safe_when_proxy_raises(monkeypatch):
    monkeypatch.setattr(car, "require_central_owner", lambda: None)

    def boom(name, builder):
        raise RuntimeError("proxy down")

    monkeypatch.setattr(
        "core.services.central_runtime_proxy.proxy_or_local", boom
    )
    monkeypatch.setattr(car, "absorb", lambda *a, **k: None)

    out = _run(car.get_dark_products())
    assert out == {"signals": {}, "live_count": 0, "total": 0}


def test_absorb_failure_isolated(monkeypatch):
    """En kastende absorb må aldrig vælte routen."""
    monkeypatch.setattr(car, "require_central_owner", lambda: None)
    monkeypatch.setattr(
        "core.services.central_runtime_proxy.proxy_or_local",
        lambda name, builder: {"signals": {"apophenia": {"liveness": True, "count": 1}},
                               "live_count": 1, "total": 1},
    )

    def boom(*a, **k):
        raise RuntimeError("absorb boom")

    monkeypatch.setattr(car, "absorb", boom)
    out = _run(car.get_dark_products())
    assert out["total"] == 1 and out["live_count"] == 1
