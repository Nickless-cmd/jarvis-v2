"""Tests for /central/self (Task 1.4) — owner-gated reduced self-snapshot.

Verifies:
  - owner-gated: gate raising 403 propagates.
  - reduced output only: raw fields never surface, only kept meta.
  - self-safe: a builder raising → that key is {} and route still returns 200-shape.
  - absorb called: absorb() invoked with cluster="self" for each surface.
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

import apps.api.jarvis_api.routes.central_self as cs


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_owner_gate_propagates(monkeypatch):
    def deny() -> None:
        raise HTTPException(status_code=403, detail="nope")

    monkeypatch.setattr(cs, "require_central_owner", deny)
    with pytest.raises(HTTPException) as ei:
        _run(cs.get_self())
    assert ei.value.status_code == 403


def test_reduced_output_only(monkeypatch):
    monkeypatch.setattr(cs, "require_central_owner", lambda: None)

    raw_by_name = {
        "living_executive": {
            "active": True,
            "mode": "experimental-active",
            "summary": {"trace_count": 3, "recent_count": 2},
            "current_focus": "TOP SECRET FOCUS",
            "current_tool_plan": {"tool": "secret"},
            "recent_traces": [{"impulse": "x"}],
            "memory_precedents": ["p1"],
        },
        "self_model": {
            "summary": {"total_layers": 40, "active_count": 12},
            "built_at": "2026-07-05T00:00:00Z",
            "layers": [{"detail": "secret raw layer"}],
            "current_focus": "hidden",
        },
        "world_model": {
            "active": True,
            "summary": {"active_count": 5},
            "items": [{"title": "raw signal"}],
            "prediction_skeleton": {"body": "raw prediction"},
        },
    }

    monkeypatch.setattr(cs, "proxy_or_local", lambda name, builder: raw_by_name[name])
    monkeypatch.setattr(cs, "absorb", lambda *a, **k: None)

    out = _run(cs.get_self())
    assert "self" in out and "ts" in out
    body = out["self"]

    # raw fields must NEVER appear as keys in any reduced surface
    forbidden = (
        "current_focus", "current_tool_plan", "recent_traces",
        "memory_precedents", "items", "prediction_skeleton", "layers",
    )
    for surface in body.values():
        for f in forbidden:
            assert f not in surface, f"raw field {f} leaked as top-level key"
    # raw CONTENT strings must never appear anywhere in the reduced output
    flat = str(body)
    for f in ("TOP SECRET FOCUS", "raw signal", "raw prediction", "secret raw layer"):
        assert f not in flat, f"raw content {f} leaked"

    # derived liveness present per surface
    assert body["living_executive"]["liveness"] is True
    assert body["world_model"]["liveness"] is True
    assert "liveness" in body["self_model"]


def test_self_safe_builder_raises(monkeypatch):
    monkeypatch.setattr(cs, "require_central_owner", lambda: None)

    def proxy(name, builder):
        if name == "self_model":
            raise RuntimeError("boom")
        return {"active": True, "summary": {}}

    monkeypatch.setattr(cs, "proxy_or_local", proxy)
    monkeypatch.setattr(cs, "absorb", lambda *a, **k: None)

    out = _run(cs.get_self())
    assert "self" in out and "ts" in out
    assert out["self"]["self_model"] == {}
    # the surviving surfaces still produced something
    assert isinstance(out["self"]["living_executive"], dict)


def test_absorb_called_for_each_surface(monkeypatch):
    monkeypatch.setattr(cs, "require_central_owner", lambda: None)
    monkeypatch.setattr(
        cs, "proxy_or_local",
        lambda name, builder: {"active": True, "summary": {"n": 1}},
    )

    calls: list[tuple] = []
    monkeypatch.setattr(cs, "absorb", lambda cluster, nerve, value, **k: calls.append((cluster, nerve)))

    _run(cs.get_self())
    clusters = [c for c, _ in calls]
    nerves = [n for _, n in calls]
    assert clusters == ["self"] * 7
    assert set(nerves) == {
        "living_executive", "self_model", "world_model",
        "open_loops", "runtime_awareness", "runtime_self_knowledge",
        "counterfactual",
    }


def test_phase_c_surfaces_present_and_reduced(monkeypatch):
    """Fase C: de 4 private agentur-lag er med i self-dict'en, KUN som
    liveness/summary — intet råt tekst-/liste-indhold slipper igennem."""
    monkeypatch.setattr(cs, "require_central_owner", lambda: None)

    # Simulate the raw producer surfaces (as the light-builders would receive
    # them BEFORE _light reduces). Include raw text/list content that must NEVER
    # surface. proxy_or_local invokes the (light) builder, so we bypass the real
    # producers by patching proxy_or_local to run the builder against fakes.
    raw_producers = {
        "open_loops": {
            "active": True,
            "open_loops": [{"goal": "RAW UNRESOLVED GOAL"}, {"goal": "x"}],
            "top_signal": "RAW SIGNAL TEXT",
            "count": 2,
        },
        "runtime_awareness": {
            "active": True,
            "signals": [{"note": "RAW AWARENESS NOTE"}],
            "score": 0.5,
        },
        "runtime_self_knowledge": {
            "active": False,
            "facts": ["RAW SELF FACT"],
            "map": {"a": 1, "b": 2},
        },
        "counterfactual": {
            "active": True,
            "predictions": [{"body": "RAW PREDICTION TEXT"}],
            "horizon": 3,
        },
    }

    def proxy(name, builder):
        # For the phase-C names, feed the raw producer through the real builder
        # by monkeypatching the underlying producer import is heavy; instead we
        # apply _light directly (mirrors what the builder does).
        if name in raw_producers:
            from apps.api.jarvis_api.routes.internal_runtime_surface import _light
            return _light(raw_producers[name])
        return {"active": True, "summary": {"n": 1}}

    monkeypatch.setattr(cs, "proxy_or_local", proxy)
    monkeypatch.setattr(cs, "absorb", lambda *a, **k: None)

    out = _run(cs.get_self())
    body = out["self"]

    for name in ("open_loops", "runtime_awareness",
                 "runtime_self_knowledge", "counterfactual"):
        assert name in body, f"phase-C surface {name} missing"
        surf = body[name]
        # ONLY liveness + summary kept
        assert set(surf.keys()) <= {"liveness", "summary"}, \
            f"{name} kept extra keys: {surf.keys()}"
        assert "liveness" in surf
        # summary holds ONLY scalars / counters — no raw text/list values
        for sk, sv in (surf.get("summary") or {}).items():
            assert isinstance(sv, (bool, int, float)), \
                f"{name}.summary.{sk} is non-scalar: {sv!r}"

    # liveness derived from `active`
    assert body["open_loops"]["liveness"] is True
    assert body["runtime_self_knowledge"]["liveness"] is False

    # NO raw content string anywhere in the reduced output
    flat = str(body)
    for leak in ("RAW UNRESOLVED GOAL", "RAW SIGNAL TEXT", "RAW AWARENESS NOTE",
                 "RAW SELF FACT", "RAW PREDICTION TEXT"):
        assert leak not in flat, f"raw content leaked: {leak}"
