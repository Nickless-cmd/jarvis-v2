"""Bölge 2 (identitet → Central): runtime_candidates pulser egress-frit til Centralen.

KUN antal foreslåede selv-mutationer (vægt på SOUL/IDENTITY-tryk) krydser —
ALDRIG draft-teksten.
"""
from __future__ import annotations

import inspect

import core.identity.runtime_candidates as mod


def test_module_imports():
    assert hasattr(mod, "build_runtime_candidate_workflows")
    assert hasattr(mod, "_observe_candidate_workflows")


def test_uses_record_private_egress_free():
    src = inspect.getsource(mod)
    assert "record_private" in src
    assert "central().observe" not in src
    assert "event_bus" not in src
    assert "_emit(" not in src


def test_observe_scalars_only_and_self_safe(monkeypatch):
    import core.services.central_private_observe as cpo

    captured = {}

    def _fake(cluster, nerve, *, value=1.0, meta=None, reason=""):
        captured["cluster"] = cluster
        captured["nerve"] = nerve
        captured["meta"] = meta or {}
        return True

    monkeypatch.setattr(cpo, "record_private", _fake)
    mod._observe_candidate_workflows({
        "soul_update:proposed": 1,
        "identity_update:proposed": 2,
        "preference_update:proposed": 3,
    })
    assert captured["cluster"] == "identity"
    assert captured["meta"]["self_mutation_proposed"] == 3
    # Kun skalarer i meta — aldrig tekst-blobs.
    for v in captured["meta"].values():
        assert isinstance(v, (int, float, bool, str))
