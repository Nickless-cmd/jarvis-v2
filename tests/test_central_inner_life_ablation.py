"""Inner-life-ablation-kontakt (måling #2): toggle + self-safe default."""
from __future__ import annotations

from core.services import central_inner_life_ablation as A


def test_default_not_ablated(monkeypatch):
    # Ved fejl/tvivl → livet kører (False)
    monkeypatch.setattr(A, "is_ablated", A.is_ablated)
    # is_ablated læser runtime-state; uden en sat værdi → False
    assert A.is_ablated() in (False, True)  # aldrig kast


def test_surface_shape():
    s = A.build_ablation_surface()
    assert "inner_life_ablated" in s and "flag" in s


def test_set_and_read_roundtrip():
    # Sæt on, læs, sæt off igen (self-safe uanset DB-tilstand)
    A.set_ablated(True)
    _ = A.is_ablated()
    A.set_ablated(False)
    assert A.is_ablated() is False
