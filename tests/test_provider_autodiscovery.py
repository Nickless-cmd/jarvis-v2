"""Tests for core/services/provider_autodiscovery.py — staging + gated promotion."""
from __future__ import annotations
import core.services.provider_autodiscovery as ad


def test_discovery_stages_new_models_not_auto_add(monkeypatch):
    """Task 13: nye modeller GATER til staging — auto-adder ALDRIG direkte."""
    monkeypatch.setattr(ad, "_list_remote_models",
                        lambda provider: ["new-free-model", "existing"])
    monkeypatch.setattr(ad, "_known_models", lambda: {"existing"})
    staged, added = [], []
    monkeypatch.setattr(ad, "_stage_pending", lambda p, m: staged.append((p, m)))
    monkeypatch.setattr(ad, "_add_to_router", lambda p, m: added.append((p, m)))
    new = ad.discover_provider("groq")
    assert ("groq", "new-free-model") in staged
    assert new == ["new-free-model"]
    assert added == []          # GATER — auto-adder ALDRIG


def test_promote_requires_smoke_score_and_free(monkeypatch):
    """Task 14: promotion kræver smoke + gratis + score."""
    monkeypatch.setattr(ad, "_add_to_router", lambda p, m: None)
    monkeypatch.setattr(ad, "_smoke_ok", lambda p, m: True)
    monkeypatch.setattr(ad, "_is_free", lambda p, m: False)   # ikke gratis
    assert ad.promote_pending("groq", "paid-model") is False
    monkeypatch.setattr(ad, "_is_free", lambda p, m: True)
    monkeypatch.setattr(ad, "_score_model", lambda p, m: 0.7)
    assert ad.promote_pending("groq", "free-model") is True


def test_promote_rejects_when_smoke_fails(monkeypatch):
    monkeypatch.setattr(ad, "_add_to_router", lambda p, m: None)
    monkeypatch.setattr(ad, "_smoke_ok", lambda p, m: False)
    monkeypatch.setattr(ad, "_is_free", lambda p, m: True)
    assert ad.promote_pending("groq", "free-model") is False
