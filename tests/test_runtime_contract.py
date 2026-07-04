"""Bölge 2 (identitet → Central): runtime_contract pulser egress-frit til Centralen.

KUN present/expected/pending/capability-tællinger + bootstrap-label krydser —
ALDRIG fil-indhold.
"""
from __future__ import annotations

import inspect

import core.identity.runtime_contract as mod


def test_module_imports():
    assert hasattr(mod, "build_runtime_contract_state")
    assert hasattr(mod, "_observe_runtime_contract")


def test_uses_record_private_egress_free():
    src = inspect.getsource(mod)
    assert "record_private" in src
    assert "central().observe" not in src
    assert "event_bus" not in src
    assert "_emit(" not in src


def test_observe_is_self_safe(monkeypatch):
    # Selv hvis record_private kaster, må observe-helperen aldrig kaste videre.
    import core.services.central_private_observe as cpo

    def _boom(*a, **k):
        raise RuntimeError("central down")

    monkeypatch.setattr(cpo, "record_private", _boom)
    # Skal returnere None uden at kaste.
    assert mod._observe_runtime_contract(
        canonical_present=4,
        canonical_expected=8,
        pending_write_count=0,
        capabilities_available=3,
        capabilities_gated=1,
        bootstrap_status="retired",
    ) is None
