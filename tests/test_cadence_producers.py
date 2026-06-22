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
