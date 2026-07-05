"""Verificér at cadence-scheduleren kalder injektions-refreshen pr. tick."""
from __future__ import annotations
import core.services.internal_cadence as ic


def test_scheduler_calls_injection_refresh(monkeypatch):
    called = {"n": 0}
    monkeypatch.setattr(
        "core.services.central_injection_registry.refresh_dirty",
        lambda: called.__setitem__("n", called["n"] + 1))
    ic._run_injection_refresh_tick()
    assert called["n"] == 1
