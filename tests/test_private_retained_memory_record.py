"""Bölge 2 (privat-indre → Central): private_retained_memory_record pulser egress-frit.

Vigtigst her: KUN kind/scope/horizon/confidence-labels krydser — ALDRIG retained_value
(det faktiske huskede indhold).
"""
from __future__ import annotations

import inspect

import core.memory.private_retained_memory_record as mod


def test_module_imports():
    assert hasattr(mod, "build_private_retained_memory_record_payload")


def test_uses_record_private_egress_free():
    src = inspect.getsource(mod)
    assert "record_private" in src
    assert "central().observe" not in src
    assert "event_bus" not in src
    assert "_emit(" not in src


def test_payload_contract_unchanged():
    payload = mod.build_private_retained_memory_record_payload(
        run_id="r1",
        work_id="w1",
        private_promotion_decision={"promotion_target": "hemmelig note", "promotion_action": "promote", "confidence": "high"},
        private_development_state={},
        private_growth_note={"learning_kind": "reinforce"},
        private_self_model={},
        created_at="2026-07-04T00:00:00+00:00",
    )
    assert payload["record_id"] == "private-retained-memory-record:r1"
    assert payload["retained_kind"] == "reinforced pattern"
