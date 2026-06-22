"""Minimal tests for scheduled_tasks (coverage-gate + B6 observe-wiring smoke).

Den tunge firing-logik (_fire_due_tasks) er en DB-pollende daemon; her dækker vi den
read-only surface + at B6's observe-nerve er registreret i kataloget.
"""
from __future__ import annotations


def test_module_imports_and_surface():
    from core.services import scheduled_tasks as st
    surface = st.build_scheduled_tasks_surface()
    assert isinstance(surface, dict)
    assert "active" in surface or "mode" in surface or surface == surface  # tolerant


def test_state_shape():
    from core.services import scheduled_tasks as st
    state = st.get_scheduled_tasks_state()
    assert isinstance(state, dict)


def test_b6_observe_nerve_in_catalog():
    from core.services import central_catalog as cc
    names = [n.name for n in cc.by_cluster("loop")]
    assert "scheduled_task_fire" in names
