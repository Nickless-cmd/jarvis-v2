"""Bölge 2 (privat-indre → Central): private_development_state pulser egress-frit."""
from __future__ import annotations

import inspect

import core.memory.private_development_state as mod


def test_module_imports():
    assert hasattr(mod, "build_private_development_state_payload")


def test_uses_record_private_egress_free():
    src = inspect.getsource(mod)
    assert "record_private" in src
    assert "central().observe" not in src
    assert "event_bus" not in src
    assert "_emit(" not in src


def test_payload_contract_unchanged():
    payload = mod.build_private_development_state_payload(
        private_growth_note={"confidence": "low"},
        private_self_model={"growth_direction": "reinforce:retain"},
        private_reflective_selection={},
        created_at="2026-07-04T00:00:00+00:00",
        updated_at="2026-07-04T00:00:00+00:00",
    )
    assert payload["state_id"] == "private-development-state:current"
