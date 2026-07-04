"""Bölge 2 (privat-indre → Central): private_reflective_selection pulser egress-frit."""
from __future__ import annotations

import inspect

import core.memory.private_reflective_selection as mod


def test_module_imports():
    assert hasattr(mod, "build_private_reflective_selection_payload")


def test_uses_record_private_egress_free():
    src = inspect.getsource(mod)
    assert "record_private" in src
    assert "central().observe" not in src
    assert "event_bus" not in src
    assert "_emit(" not in src


def test_payload_contract_unchanged():
    payload = mod.build_private_reflective_selection_payload(
        run_id="r1",
        work_id="w1",
        private_growth_note={"learning_kind": "reinforce", "confidence": "high"},
        private_self_model={},
        created_at="2026-07-04T00:00:00+00:00",
    )
    assert payload["signal_id"] == "private-reflective-selection:r1"
    assert payload["selection_kind"] == "retain"
