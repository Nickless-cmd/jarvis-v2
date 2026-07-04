"""Bölge 2 (privat-indre → Central): private_operational_preference pulser egress-frit."""
from __future__ import annotations

import inspect

import core.memory.private_operational_preference as mod


def test_module_imports():
    assert hasattr(mod, "build_private_operational_preference")


def test_uses_record_private_egress_free():
    src = inspect.getsource(mod)
    assert "record_private" in src
    assert "central().observe" not in src
    assert "event_bus" not in src
    assert "_emit(" not in src


def test_inactive_and_active_contract():
    empty = mod.build_private_operational_preference(
        private_initiative_tension=None,
        private_temporal_curiosity_state=None,
        private_relation_state=None,
    )
    assert empty["active"] is False
    active = mod.build_private_operational_preference(
        private_initiative_tension={"tension_kind": "curiosity-pull", "confidence": "medium"},
        private_temporal_curiosity_state={"curiosity_carry": "carried"},
        private_relation_state={"interaction_mode": "user-tool-work"},
    )
    assert active["active"] is True
    assert active["current"]["preferred_lane"] in ("coding", "cheap")
