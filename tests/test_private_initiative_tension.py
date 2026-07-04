"""Bölge 2 (privat-indre → Central): private_initiative_tension pulser egress-frit."""
from __future__ import annotations

import inspect

import core.memory.private_initiative_tension as mod


def test_module_imports():
    assert hasattr(mod, "build_private_initiative_tension")


def test_uses_record_private_egress_free():
    src = inspect.getsource(mod)
    assert "record_private" in src
    assert "central().observe" not in src
    assert "event_bus" not in src
    assert "_emit(" not in src


def test_inactive_and_active_contract():
    empty = mod.build_private_initiative_tension(
        private_state=None,
        protected_inner_voice=None,
        private_development_state=None,
        private_reflective_selection=None,
        private_temporal_promotion_signal=None,
        private_temporal_curiosity_state=None,
        private_retained_memory_projection=None,
    )
    assert empty["active"] is False
    active = mod.build_private_initiative_tension(
        private_state={"curiosity": "medium", "frustration": "low", "confidence": "medium"},
        protected_inner_voice={"current_pull": "x", "current_concern": "y"},
        private_development_state={"retained_pattern": "p"},
        private_reflective_selection={"selection_kind": "retain"},
        private_temporal_promotion_signal={"promotion_action": "promote", "signal_id": "s1"},
        private_temporal_curiosity_state={"curiosity_carry": "carried"},
        private_retained_memory_projection=None,
    )
    assert active["active"] is True
    assert active["current"]["tension_level"] in ("low", "medium", "high")
