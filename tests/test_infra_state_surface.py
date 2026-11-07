"""Tests for den samlede drifts-flade (7/11-2026).

Måler KOBLINGEN: at aggregatoren kalder hver producent i listen, at en kastende
producent isoleres uden at skjule de øvrige, og at routen faktisk eksponerer den.

Baggrund: målt på tværs af HELE repoet — ikke kun apps/ — blev 24 flader refereret
fra ingen anden fil end deres egen. De 23 her er maskinrummet: DB-helbred, cache,
ressource-signaler, mail, vision, selv-reparation. Netop den slags der kører
forkert i månedsvis uden at nogen opdager det, fordi ingen ser den.
"""
from __future__ import annotations

import importlib

import pytest

from core.services import infra_state_surface as agg

EXPECTED = [
    "db_sentinel", "shared_cache", "cache_maintenance", "runtime_resource_signal",
    "runtime_action_outcome", "cluster_family_scheduler", "shutdown_window",
    "paid_lane_guard", "self_repair", "session_tool_pin", "skill_relevance",
    "vision_backend", "mail_checker", "ambient_sound", "query_language_bridge",
    "policy_abstraction", "concept_baseline", "repeated_requests",
    "selective_consolidation", "offline_recomposition", "dream_action_executor",
    "inner_dialectic", "self_model_history",
]


def test_registry_is_exactly_the_measured_set():
    assert agg.producer_names() == EXPECTED


@pytest.mark.parametrize("name,mod,fn", agg._PRODUCERS)
def test_every_producer_exists_and_is_called(monkeypatch, name, mod, fn):
    """Hver producent findes (modul+funktion) og aggregatoren kalder netop den."""
    module = importlib.import_module(mod)
    assert callable(getattr(module, fn))
    calls: list[str] = []
    sentinel = {"active": True, "marker": name}
    monkeypatch.setattr(module, fn, lambda: calls.append(name) or sentinel)
    out = agg.build_infra_state_surface()
    assert calls == [name]
    assert out["surfaces"][name] == sentinel
    assert name in out["live"]


@pytest.mark.parametrize("name,mod,fn", agg._PRODUCERS)
def test_failing_producer_is_isolated(monkeypatch, name, mod, fn):
    module = importlib.import_module(mod)

    def _boom():
        raise RuntimeError("exploded")

    monkeypatch.setattr(module, fn, _boom)
    out = agg.build_infra_state_surface()
    assert out["surfaces"][name]["active"] is False
    assert out["surfaces"][name]["reason"] == "RuntimeError: exploded"
    assert name in out["silent"]
    assert name not in out["live"]
    assert set(out["surfaces"]) == set(EXPECTED)  # de øvrige er stadig med
    assert name in out["summary"]


def test_real_surfaces_return_nonempty_dicts():
    out = agg.build_infra_state_surface()
    assert out["mode"] == "infra-state-v1"
    for name, s in out["surfaces"].items():
        assert isinstance(s, dict) and s, name
    assert set(out["live"]) | set(out["silent"]) == set(EXPECTED)
    assert not set(out["live"]) & set(out["silent"])


def test_route_exposes_the_aggregate(monkeypatch):
    """Den ægte kobling: routen Desk kalder skal svare med aggregatets form."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import apps.api.jarvis_api.routes.central as route

    app = FastAPI()
    app.include_router(route.router)
    monkeypatch.setattr(route, "_require_owner", lambda: None)
    res = TestClient(app).get("/central/infra-state")
    assert res.status_code == 200
    body = res.json()
    assert body["mode"] == "infra-state-v1"
    assert set(body["surfaces"]) == set(EXPECTED)


def test_route_is_owner_gated(monkeypatch):
    """Uden ejer-adgang må drifts-tilstanden ikke lække."""
    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient

    import apps.api.jarvis_api.routes.central as route

    def _nej():
        raise HTTPException(status_code=403, detail="owner only")

    app = FastAPI()
    app.include_router(route.router)
    monkeypatch.setattr(route, "_require_owner", _nej)
    assert TestClient(app).get("/central/infra-state").status_code == 403
