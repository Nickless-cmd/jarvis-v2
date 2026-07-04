"""Bölge 2 (privat-indre → Central): private_temporal_curiosity_state pulser egress-frit."""
from __future__ import annotations

import inspect

import core.memory.private_temporal_curiosity_state as mod


def test_module_imports():
    assert hasattr(mod, "build_private_temporal_curiosity_state")


def test_uses_record_private_egress_free():
    src = inspect.getsource(mod)
    assert "record_private" in src
    assert "central().observe" not in src
    assert "event_bus" not in src
    assert "_emit(" not in src


def test_inactive_and_active_contract():
    empty = mod.build_private_temporal_curiosity_state(
        private_state=None,
        private_temporal_promotion_signal=None,
        private_development_state=None,
    )
    assert empty["active"] is False
    active = mod.build_private_temporal_curiosity_state(
        private_state={"curiosity": "medium", "confidence": "medium"},
        private_temporal_promotion_signal={"rhythm_state": "steady", "signal_id": "s1"},
        private_development_state={"preferred_direction": "observe"},
    )
    assert active["active"] is True
    assert active["current"]["curiosity_level"] == "medium"
