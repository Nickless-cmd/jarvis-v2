"""Bölge 2 (identitet → Central): visible_identity pulser egress-frit til Centralen.

KUN aktiv-flag + antal linjer/tegn/present krydser — ALDRIG identitets-teksten selv.
"""
from __future__ import annotations

import inspect

import core.identity.visible_identity as mod


def test_module_imports():
    assert hasattr(mod, "load_visible_identity_summary")


def test_uses_record_private_egress_free():
    src = inspect.getsource(mod)
    assert "record_private" in src
    assert '"identity"' in src  # identity-cluster
    assert "central().observe" not in src
    assert "event_bus" not in src
    assert "_emit(" not in src
