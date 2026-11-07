"""Tests for den samlede værktøjs-infra-flade (7/11-2026).

Fladen findes fordi de 12 lag ellers var mørke: hver havde en ``build_*_surface``,
men ingen rute kaldte dem. Testene måler derfor KOBLINGEN — at aggregatoren
faktisk kalder hver producent — ikke bare at den returnerer en dict.
"""
from __future__ import annotations

import pytest

from core.services import central_tool_infra_surface as agg


def test_surface_calls_every_registered_producer():
    """Alle 12 producenter skal have et resultat — ikke 11 og en tavs."""
    out = agg.build_tool_infra_surface()
    assert out["mode"] == "tool-infra-v1"
    assert set(out["surfaces"]) == set(agg.producer_names())
    assert len(out["surfaces"]) == 12


def test_every_producer_is_actually_invoked(monkeypatch):
    """Koblingen: fjernes et modul fra registry, forsvinder netop det fra fladen.

    Uden denne kunne aggregatoren returnere 12 tomme dicts og testen ovenfor
    stadig bestå.
    """
    import core.services.tool_tagger as tt
    calls: list[str] = []
    monkeypatch.setattr(tt, "build_tool_tagger_surface",
                        lambda: calls.append("tool_tagger") or {"active": True, "signals": {}})
    out = agg.build_tool_infra_surface()
    assert calls == ["tool_tagger"], "aggregatoren kaldte ikke producenten"
    assert "tool_tagger" in out["live"]


def test_failing_producer_is_isolated_not_fatal(monkeypatch):
    """Én kastende producent må ikke skjule de øvrige 11."""
    import core.services.tool_tagger as tt

    def _boom():
        raise RuntimeError("tagger exploded")

    monkeypatch.setattr(tt, "build_tool_tagger_surface", _boom)
    out = agg.build_tool_infra_surface()
    assert out["surfaces"]["tool_tagger"]["active"] is False
    assert "tagger exploded" in out["surfaces"]["tool_tagger"]["reason"]
    assert "tool_tagger" in out["silent"]
    # de øvrige skal stadig være kaldt
    assert len(out["surfaces"]) == 12
    assert len([n for n in out["surfaces"] if n != "tool_tagger"]) == 11


def test_summary_names_the_silent_layers():
    """Opsummeringen skal navngive de tavse lag — ellers skjuler den dem."""
    out = agg.build_tool_infra_surface()
    assert "lag melder data" in out["summary"]
    for name in out["silent"]:
        assert name in out["summary"]


@pytest.mark.parametrize("name", ["agent_approval_gate", "cache_telemetry", "tool_usage_store"])
def test_known_producers_return_a_dict(name):
    """Stikprøve: de producerer faktisk dicts med en 'active'-nøgle, ikke None."""
    out = agg.build_tool_infra_surface()
    surface = out["surfaces"][name]
    assert isinstance(surface, dict)
    assert "active" in surface
