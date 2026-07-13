"""Tests for core.services.shadow_experiment_registry.

Durabelt (KV via db_core) shadow-eksperiment-register + surfacing. Tiden injiceres
(now_ts/started_ts) så testene er deterministiske. KV mockes med en in-memory dict
så vi ikke rører den rigtige runtime-DB.
"""
from __future__ import annotations

import pytest

from core.runtime import db_core
from core.services import shadow_experiment_registry as reg


@pytest.fixture
def mem_kv(monkeypatch):
    """In-memory erstatning for runtime_state_kv (deterministisk, isoleret)."""
    store: dict[str, object] = {}

    def _get(key, default=None):
        return store.get(str(key), default)

    def _set(key, value, **kw):
        store[str(key)] = value

    monkeypatch.setattr(db_core, "get_runtime_state_value", _get)
    monkeypatch.setattr(db_core, "set_runtime_state_value", _set)
    return store


def test_register_then_list_fresh_not_ripe(mem_kv):
    reg.register_experiment("exp_a", review_after_hours=24, note="n", started_ts=1000.0)
    items = reg.list_experiments(now_ts=1000.0 + 3600.0)  # 1t senere
    assert len(items) == 1
    it = items[0]
    assert it["name"] == "exp_a"
    assert it["reviewed"] is False
    assert it["ripe"] is False
    assert 0.9 < it["hours_running"] < 1.1


def test_becomes_ripe_after_window(mem_kv):
    reg.register_experiment("exp_a", review_after_hours=24, started_ts=1000.0)
    # 25t senere → forbi vinduet
    items = reg.list_experiments(now_ts=1000.0 + 25 * 3600.0)
    assert items[0]["ripe"] is True


def test_register_idempotent_keeps_started_ts(mem_kv):
    reg.register_experiment("exp_a", review_after_hours=24, started_ts=1000.0)
    # gen-registrér senere med anden started_ts → må IKKE nulstille
    reg.register_experiment("exp_a", review_after_hours=24, started_ts=999999.0)
    items = reg.list_experiments(now_ts=1000.0 + 25 * 3600.0)
    assert len(items) == 1
    assert items[0]["started_ts"] == 1000.0
    assert items[0]["ripe"] is True


def test_ready_for_review_only_ripe_unreviewed(mem_kv):
    reg.register_experiment("ripe_one", review_after_hours=1, started_ts=1000.0)
    reg.register_experiment("fresh_one", review_after_hours=100, started_ts=1000.0)
    now = 1000.0 + 5 * 3600.0
    ready = reg.ready_for_review(now_ts=now)
    names = [r["name"] for r in ready]
    assert "ripe_one" in names
    assert "fresh_one" not in names


def test_mark_reviewed_removes_from_ripe(mem_kv):
    reg.register_experiment("exp_a", review_after_hours=1, started_ts=1000.0)
    now = 1000.0 + 5 * 3600.0
    assert [r["name"] for r in reg.ready_for_review(now_ts=now)] == ["exp_a"]
    reg.mark_reviewed("exp_a")
    assert reg.ready_for_review(now_ts=now) == []
    # og list markerer reviewed + ikke-ripe
    it = reg.list_experiments(now_ts=now)[0]
    assert it["reviewed"] is True
    assert it["ripe"] is False


def test_durability_survives_simulated_restart(mem_kv):
    reg.register_experiment("exp_a", review_after_hours=1, started_ts=1000.0)
    # "restart": ny læsning fra samme KV-store (intet in-proces state)
    now = 1000.0 + 5 * 3600.0
    items = reg.list_experiments(now_ts=now)
    assert len(items) == 1 and items[0]["name"] == "exp_a"
    # KV-nøglen findes durabelt
    raw = db_core.get_runtime_state_value("shadow_experiments")
    assert isinstance(raw, dict) and "exp_a" in raw


def test_build_surface_shape_and_ripe_count(mem_kv, monkeypatch):
    # Isolér surface-logikken fra auto-seeding af de kendte live shadows.
    monkeypatch.setattr(reg, "register_known_shadows", lambda: None)
    reg.register_experiment("ripe_one", review_after_hours=1, started_ts=1000.0)
    reg.register_experiment("fresh_one", review_after_hours=100, started_ts=1000.0)
    now = 1000.0 + 5 * 3600.0
    surf = reg.build_shadow_review_surface(now_ts=now)
    assert set(surf.keys()) >= {"experiments", "ripe", "ripe_count"}
    assert surf["ripe_count"] == 1
    assert [r["name"] for r in surf["ripe"]] == ["ripe_one"]
    assert len(surf["experiments"]) == 2


def test_build_surface_self_safe_on_error(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("kv down")

    monkeypatch.setattr(db_core, "get_runtime_state_value", _boom)
    surf = reg.build_shadow_review_surface(now_ts=1234.0)
    assert surf == {"experiments": [], "ripe": [], "ripe_count": 0}
