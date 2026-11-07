"""Tests for den samlede hukommelses-flade (7/11-2026).

Måler KOBLINGEN: at aggregatoren kalder hver producent i listen, og at en
kastende producent isoleres uden at skjule de øvrige.
"""
from __future__ import annotations

import importlib

import pytest

from core.services import memory_state_surface as agg

EXPECTED = [
    "semantic_memory", "memory_emotional_context", "cross_agent_memory",
    "end_of_run_memory_consolidation", "associative_recall", "memory_recall_engine",
    "memory_safeguard", "memory_graph", "memory_hygiene", "memory_resurfacing",
    "memory_breathing", "memory_write_queue", "memory_maintenance", "memory_pruning",
    "memory_recall_telemetry", "memory_density", "visual_memory", "conflict_memory",
    "council_memory",
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
    out = agg.build_memory_state_surface()
    assert calls == [name]
    assert out["surfaces"][name] == sentinel
    assert name in out["live"]


@pytest.mark.parametrize("name,mod,fn", agg._PRODUCERS)
def test_failing_producer_is_isolated(monkeypatch, name, mod, fn):
    module = importlib.import_module(mod)

    def _boom():
        raise RuntimeError("exploded")

    monkeypatch.setattr(module, fn, _boom)
    out = agg.build_memory_state_surface()
    assert out["surfaces"][name]["active"] is False
    assert out["surfaces"][name]["reason"] == "RuntimeError: exploded"
    assert name in out["silent"]
    assert name not in out["live"]
    assert set(out["surfaces"]) == set(EXPECTED)  # de øvrige er stadig med
    assert name in out["summary"]


def test_real_surfaces_return_nonempty_dicts():
    out = agg.build_memory_state_surface()
    assert out["mode"] == "memory-state-v1"
    for name, s in out["surfaces"].items():
        assert isinstance(s, dict) and s, name
    assert set(out["live"]) | set(out["silent"]) == set(EXPECTED)
    assert not set(out["live"]) & set(out["silent"])
