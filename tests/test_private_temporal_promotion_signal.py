"""Bölge 2 (privat-indre → Central): private_temporal_promotion_signal pulser egress-frit."""
from __future__ import annotations

import inspect

import core.memory.private_temporal_promotion_signal as mod


def test_module_imports():
    assert hasattr(mod, "build_private_temporal_promotion_signal_payload")


def test_uses_record_private_egress_free():
    src = inspect.getsource(mod)
    assert "record_private" in src
    assert "central().observe" not in src
    assert "event_bus" not in src
    assert "_emit(" not in src


def test_payload_contract_unchanged():
    payload = mod.build_private_temporal_promotion_signal_payload(
        run_id="r1",
        work_id="w1",
        private_state={"confidence": "medium", "fatigue": "low", "frustration": "low"},
        private_reflective_selection={"selection_kind": "retain"},
        private_development_state={},
        protected_inner_voice={"mood_tone": "steady"},
        created_at="2026-07-04T00:00:00+00:00",
    )
    assert payload["signal_id"] == "private-temporal-promotion-signal:r1"
    assert payload["promotion_action"] == "promote"
