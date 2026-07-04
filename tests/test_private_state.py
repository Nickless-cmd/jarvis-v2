"""Bölge 2 (privat-indre → Central): private_state pulser egress-frit til Centralen.

Tynd per-fil-test (import-smoke + kilde-assert) der pinner: laget kalder record_private
(den kanoniske egress-fri sink) og ALDRIG central().observe/event_bus/_emit. Kun skalarer/
labels krydser grænsen — aldrig privat tekst.
"""
from __future__ import annotations

import inspect

import core.memory.private_state as mod


def test_module_imports():
    assert hasattr(mod, "build_private_state_payload")


def test_uses_record_private_egress_free():
    src = inspect.getsource(mod)
    assert "record_private" in src
    # egress-invariant: MÅ ALDRIG gå via central().observe / event_bus / _emit
    assert "central().observe" not in src
    assert "event_bus" not in src
    assert "_emit(" not in src


def test_payload_contract_unchanged():
    payload = mod.build_private_state_payload(
        private_inner_note={"focus": "x"},
        private_growth_note={"confidence": "medium"},
        private_self_model={},
        private_reflective_selection={},
        private_development_state={},
        created_at="2026-07-04T00:00:00+00:00",
        updated_at="2026-07-04T00:00:00+00:00",
    )
    assert payload["state_id"] == "private-state:current"
    assert "confidence" in payload
