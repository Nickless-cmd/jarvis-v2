"""Tests for /central/soul — owner-gated projektion af mørke sjæle-signaler.

Verifies:
  - owner-gated: gate raising 403 propagates.
  - per-signal absorb with cluster="soul" + aggregat "roster".
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
        _run(car.get_soul())
    assert ei.value.status_code == 403


def test_per_signal_absorb_with_soul_cluster(monkeypatch):
    monkeypatch.setattr(car, "require_central_owner", lambda: None)

    digest = {
        "signals": {
            "longing": {"liveness": True, "count": 3},
            "identity_drift": {"liveness": False, "count": 0},
            "signal_decay": {"liveness": True, "count": 5},
        },
        "live_count": 2,
        "total": 3,
    }

    import apps.api.jarvis_api.routes.central_absorb_routes as mod
    monkeypatch.setattr(
        "core.services.central_runtime_proxy.proxy_or_local",
        lambda name, builder: digest,
    )

    calls: list[tuple] = []
    monkeypatch.setattr(mod, "absorb", lambda cluster, nerve, value, **k: calls.append((cluster, nerve, value)))

    out = _run(car.get_soul())

    # every absorb is cluster="soul"
    assert all(c == "soul" for c, _, _ in calls)
    nerves = [n for _, n, _ in calls]
    assert set(nerves) == {"longing", "identity_drift", "signal_decay", "roster"}

    # per-signal absorb carries ONLY liveness+count
    for c, n, v in calls:
        if n == "roster":
            assert set(v.keys()) == {"live_count", "total"}
        else:
            assert set(v.keys()) <= {"liveness", "count"}

    # returned body carries only signals + counters (no raw content)
    assert out["signals"] == digest["signals"]
    assert out["live_count"] == 2 and out["total"] == 3


def test_self_safe_when_proxy_raises(monkeypatch):
    monkeypatch.setattr(car, "require_central_owner", lambda: None)

    def boom(name, builder):
        raise RuntimeError("proxy down")

    monkeypatch.setattr(
        "core.services.central_runtime_proxy.proxy_or_local", boom
    )
    monkeypatch.setattr(car, "absorb", lambda *a, **k: None)

    out = _run(car.get_soul())
    assert out == {"signals": {}, "live_count": 0, "total": 0}


def test_absorb_failure_isolated(monkeypatch):
    """En kastende absorb må aldrig vælte routen."""
    monkeypatch.setattr(car, "require_central_owner", lambda: None)
    monkeypatch.setattr(
        "core.services.central_runtime_proxy.proxy_or_local",
        lambda name, builder: {"signals": {"longing": {"liveness": True, "count": 1}},
                               "live_count": 1, "total": 1},
    )

    def boom(*a, **k):
        raise RuntimeError("absorb boom")

    monkeypatch.setattr(car, "absorb", boom)
    out = _run(car.get_soul())
    assert out["total"] == 1 and out["live_count"] == 1
