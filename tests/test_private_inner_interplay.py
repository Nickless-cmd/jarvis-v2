"""Bölge 2 (privat-indre → Central): private_inner_interplay pulser egress-frit."""
from __future__ import annotations

import inspect

import core.memory.private_inner_interplay as mod


def test_module_imports():
    assert hasattr(mod, "build_private_inner_interplay")


def test_uses_record_private_egress_free():
    src = inspect.getsource(mod)
    assert "record_private" in src
    assert "central().observe" not in src
    assert "event_bus" not in src
    assert "_emit(" not in src


def test_inactive_and_active_contract():
    empty = mod.build_private_inner_interplay(
        private_state=None,
        protected_inner_voice=None,
        private_development_state=None,
        private_reflective_selection=None,
    )
    assert empty["active"] is False
    active = mod.build_private_inner_interplay(
        private_state={"confidence": "medium", "state_id": "st1"},
        protected_inner_voice={"mood_tone": "steady", "voice_id": "v1"},
        private_development_state={"retained_pattern": "p"},
        private_reflective_selection={"selection_kind": "retain"},
    )
    assert active["active"] is True
    assert active["current"]["mood_tone"] == "steady"
