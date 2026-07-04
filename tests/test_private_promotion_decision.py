"""Bölge 2 (privat-indre → Central): private_promotion_decision pulser egress-frit."""
from __future__ import annotations

import inspect

import core.memory.private_promotion_decision as mod


def test_module_imports():
    assert hasattr(mod, "build_private_promotion_decision_payload")


def test_uses_record_private_egress_free():
    src = inspect.getsource(mod)
    assert "record_private" in src
    assert "central().observe" not in src
    assert "event_bus" not in src
    assert "_emit(" not in src


def test_payload_contract_unchanged():
    payload = mod.build_private_promotion_decision_payload(
        run_id="r1",
        work_id="w1",
        private_temporal_promotion_signal={"promotion_action": "promote"},
        private_development_state={"confidence": "medium"},
        private_growth_note={"learning_kind": "reinforce"},
        created_at="2026-07-04T00:00:00+00:00",
    )
    assert payload["decision_id"] == "private-promotion-decision:r1"
    assert payload["promotion_action"] == "promote"
