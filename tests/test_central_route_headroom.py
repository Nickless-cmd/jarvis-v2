"""Tests for core/services/central_route_headroom.py — proaktiv kvote-rotation."""
from __future__ import annotations
import core.services.central_route_headroom as hr


def test_headroom_deweights_at_80_and_skips_at_95(monkeypatch):
    monkeypatch.setattr(hr, "_usage_fraction", lambda provider: 0.5)  # 50%
    assert hr.headroom_ok("groq") is True
    assert hr.headroom_weight("groq") == 1.0
    monkeypatch.setattr(hr, "_usage_fraction", lambda provider: 0.85)  # 85%
    assert hr.headroom_ok("groq") is True
    assert hr.headroom_weight("groq") < 1.0        # de-vægtet
    monkeypatch.setattr(hr, "_usage_fraction", lambda provider: 0.97)  # 97%
    assert hr.headroom_ok("groq") is False         # skip proaktivt
