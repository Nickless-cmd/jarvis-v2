"""Bölge 2 (privat-indre → Central): private_self_model pulser egress-frit til Centralen."""
from __future__ import annotations

import inspect

import core.memory.private_self_model as mod


def test_module_imports():
    assert hasattr(mod, "build_private_self_model_payload")


def test_uses_record_private_egress_free():
    src = inspect.getsource(mod)
    assert "record_private" in src
    assert "central().observe" not in src
    assert "event_bus" not in src
    assert "_emit(" not in src


def test_payload_contract_unchanged():
    payload = mod.build_private_self_model_payload(
        run_id="r1",
        private_inner_note={"focus": "x"},
        private_growth_note={"confidence": "high", "learning_kind": "reinforce"},
        created_at="2026-07-04T00:00:00+00:00",
        updated_at="2026-07-04T00:00:00+00:00",
    )
    assert payload["model_id"] == "private-self-model:current"
    assert payload["confidence"] == "high"
