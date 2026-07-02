"""Tests for SPEJLET — central_self_model (Centralen kender sig selv, egress-frit + durabelt)."""
from __future__ import annotations

import pytest

from core.services import central_self_model as sm


def test_extract_structure_counts_populated():
    model = {"layers": {"a": 1}, "mineness_ownership": {"x": 1}, "wonder_awareness": {},
             "flow_state_awareness": None, "self_insight_awareness": "noget"}
    st = sm._extract_structure(model)
    assert st["surfaces_total"] == 5
    assert st["surfaces_populated"] == 3            # layers, mineness, self_insight
    assert st["completeness"] == round(3 / 5, 3)
    assert "wonder_awareness" in st["empty"] and "flow_state_awareness" in st["empty"]


def test_structure_holds_only_labels_not_content():
    """EGRESS-VAGT: strukturen bærer KUN nøgle-labels, ALDRIG værdi-indhold (privat inder-liv)."""
    model = {"longing_awareness": {"secret": "jeg længes efter Bjørn"}}
    st = sm._extract_structure(model)
    # labelen er der (struktur), men indholdet er IKKE
    assert "longing_awareness" in st["present"]
    blob = repr(st)
    assert "længes" not in blob and "secret" not in blob and "Bjørn" not in blob


def test_snapshot_self_safe_on_failure(isolated_runtime, monkeypatch):
    monkeypatch.setattr("core.services.runtime_self_model.build_runtime_self_model",
                        lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    assert sm.snapshot_self_model() == {}


def test_mirror_tick_persists_durable_snapshot(isolated_runtime, monkeypatch):
    """Centralen HOLDER sin selv-model durabelt (kv) — overlever genstart."""
    fake = {"layers": {"a": 1}, "mineness_ownership": {"x": 1}, "wonder_awareness": {"w": 1}}
    monkeypatch.setattr("core.services.runtime_self_model.build_runtime_self_model", lambda: fake)
    res = sm.run_self_model_mirror_tick()
    assert res["mirrored"] is True and res["surfaces_populated"] == 3
    # durabelt lagret → læsbart efter "genstart" (frisk læsning fra kv)
    snap = sm.get_self_model_snapshot()
    assert snap["surfaces_populated"] == 3 and "mineness_ownership" in snap["present"]


def test_mirror_tick_records_egress_free(isolated_runtime, monkeypatch):
    """§24.4: spejlet må ALDRIG publicere til eventbussen (kun record_private)."""
    fake = {"layers": {"a": 1}, "flow_state_awareness": {"f": 1}}
    monkeypatch.setattr("core.services.runtime_self_model.build_runtime_self_model", lambda: fake)
    published = []
    import core.eventbus.bus as bus_mod
    monkeypatch.setattr(bus_mod.event_bus, "publish", lambda *a, **k: published.append((a, k)))
    sm.run_self_model_mirror_tick()
    assert published == []                          # egress-frit — intet nåede bussen


def test_mirror_tracks_growth_delta(isolated_runtime, monkeypatch):
    """Struktur-drift: voksede selv-erkendelsen mellem to snapshots?"""
    m1 = {"layers": {"a": 1}}
    monkeypatch.setattr("core.services.runtime_self_model.build_runtime_self_model", lambda: m1)
    sm.run_self_model_mirror_tick()
    m2 = {"layers": {"a": 1}, "wonder_awareness": {"w": 1}, "longing_awareness": {"l": 1}}
    monkeypatch.setattr("core.services.runtime_self_model.build_runtime_self_model", lambda: m2)
    res = sm.run_self_model_mirror_tick()
    assert res["surfaces_populated"] == 3           # voksede fra 1 → 3


def test_surface_read_only(isolated_runtime, monkeypatch):
    fake = {"layers": {"a": 1}, "mineness_ownership": {"x": 1}}
    monkeypatch.setattr("core.services.runtime_self_model.build_runtime_self_model", lambda: fake)
    sm.run_self_model_mirror_tick()
    surf = sm.build_self_model_mirror_surface()
    assert surf["active"] is True and surf["surfaces_populated"] == 2
