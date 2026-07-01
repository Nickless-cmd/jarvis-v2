"""Minimal tests for cadence_producers (coverage-gate + B-batch-2 observe smoke).

Den tunge produce_signals_from_run rører DB + mange daemons; her dækker vi import +
hjælpere + at heartbeat-producer-observe-nerven er registreret.
"""
from __future__ import annotations


def test_module_imports():
    from core.services import cadence_producers as cp
    assert hasattr(cp, "produce_signals_from_run")


def test_meaningful_run_topic_is_str():
    from core.services.cadence_producers import _meaningful_run_topic
    out = _meaningful_run_topic("Jarvis kører på localhost nu")
    assert isinstance(out, str)


def test_cadence_producers_nerve_in_catalog():
    from core.services import central_catalog as cc
    names = [n.name for n in cc.by_cluster("stream")]
    assert "cadence_producers" in names
    assert "notification_route" in names


def test_tick_frozen_detectors_cadence(isolated_runtime):
    # LivingNeuron Fase B: emergence hver 30., contradiction hver 20., ellers no-op. Self-safe.
    from core.services.cadence_producers import tick_frozen_detectors
    off = tick_frozen_detectors(7)   # hverken 20 el. 30
    assert off == {"emergence": 0, "contradiction": 0}
    both = tick_frozen_detectors(60)  # både 20 og 30
    assert set(both) == {"emergence", "contradiction"}
    # må aldrig kaste selv på skæve tal
    tick_frozen_detectors(0)
    tick_frozen_detectors(20)
    tick_frozen_detectors(30)
