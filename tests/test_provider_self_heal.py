"""Tests for core/services/provider_self_heal.py — eskalering + model-drift."""
from __future__ import annotations
import core.services.provider_self_heal as sh


def test_escalates_when_three_plus_providers_down(monkeypatch):
    """Task 15: 3+ nede samtidig → eskalér til Bjørn."""
    sent = []
    monkeypatch.setattr(sh, "_notify_bjorn", lambda msg: sent.append(msg))
    monkeypatch.setattr(sh, "_observe_central", lambda payload: None)
    assert sh.check_and_heal(down_providers=["a", "b", "c"]) is True
    assert sent


def test_does_not_escalate_below_threshold(monkeypatch):
    sent = []
    monkeypatch.setattr(sh, "_notify_bjorn", lambda msg: sent.append(msg))
    monkeypatch.setattr(sh, "_observe_central", lambda payload: None)
    assert sh.check_and_heal(down_providers=["a", "b"]) is False
    assert not sent


def test_model_drift_404_auto_removes(monkeypatch):
    """Task 15: 404-model fjernes auto (removal er sikkert)."""
    removed = []
    monkeypatch.setattr(sh, "_remove_from_router", lambda p, m: removed.append((p, m)))
    monkeypatch.setattr(sh, "_observe_central", lambda payload: None)
    assert sh.handle_model_drift(provider="groq", model="gone", status_code=404) is True
    assert ("groq", "gone") in removed


def test_non_404_does_not_remove(monkeypatch):
    removed = []
    monkeypatch.setattr(sh, "_remove_from_router", lambda p, m: removed.append((p, m)))
    monkeypatch.setattr(sh, "_observe_central", lambda payload: None)
    assert sh.handle_model_drift(provider="groq", model="x", status_code=429) is False
    assert removed == []
