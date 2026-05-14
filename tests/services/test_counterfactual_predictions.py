"""Tests for counterfactual_predictions binding + frequency-comparison sweep."""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from core.services import counterfactual_predictions as cp


def _seed_events(monkeypatch, kind: str, baseline_count: int, post_count: int, anchor: datetime) -> None:
    """Inject a fake connect() that returns a sqlite :memory: db pre-seeded
    with synthetic events: ``baseline_count`` rows of ``kind`` in
    [anchor-7d, anchor) and ``post_count`` rows in [anchor, anchor+7d)."""
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE events (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "kind TEXT, payload_json TEXT DEFAULT '{}', created_at TEXT)"
    )
    span = timedelta(days=7)
    # Spread events evenly across each window
    for i in range(baseline_count):
        ts = (anchor - span + timedelta(seconds=i + 1)).isoformat()
        conn.execute("INSERT INTO events(kind, created_at) VALUES (?, ?)", (kind, ts))
    for i in range(post_count):
        ts = (anchor + timedelta(seconds=i + 1)).isoformat()
        conn.execute("INSERT INTO events(kind, created_at) VALUES (?, ?)", (kind, ts))
    conn.commit()

    class _Holder:
        def __enter__(self_inner):
            return conn

        def __exit__(self_inner, *a):
            pass

    def fake_connect():
        return _Holder()

    monkeypatch.setattr("core.runtime.db.connect", fake_connect)


def test_frequency_verdict_supported_when_post_declines(monkeypatch):
    anchor = datetime.now(UTC) - timedelta(days=3)
    _seed_events(monkeypatch, "conflict.detected", baseline_count=100, post_count=30, anchor=anchor)
    v = cp._frequency_verdict(event_kind="conflict.detected", created_at=anchor)
    assert v["outcome"] == "supported"
    assert v["baseline"] == 100
    assert v["post"] == 30
    assert v["ratio"] == pytest.approx(0.30, abs=0.01)


def test_frequency_verdict_contradicted_when_post_increases(monkeypatch):
    anchor = datetime.now(UTC) - timedelta(days=3)
    _seed_events(monkeypatch, "decision_revoked", baseline_count=10, post_count=20, anchor=anchor)
    v = cp._frequency_verdict(event_kind="decision_revoked", created_at=anchor)
    assert v["outcome"] == "contradicted"
    assert v["ratio"] == pytest.approx(2.0, abs=0.01)


def test_frequency_verdict_uncertain_when_stable(monkeypatch):
    anchor = datetime.now(UTC) - timedelta(days=3)
    _seed_events(monkeypatch, "stable.kind", baseline_count=10, post_count=11, anchor=anchor)
    v = cp._frequency_verdict(event_kind="stable.kind", created_at=anchor)
    assert v["outcome"] == "uncertain"
    assert "stable" in v["reason"]


def test_frequency_verdict_uncertain_when_baseline_too_small(monkeypatch):
    anchor = datetime.now(UTC) - timedelta(days=3)
    _seed_events(monkeypatch, "rare.kind", baseline_count=1, post_count=5, anchor=anchor)
    v = cp._frequency_verdict(event_kind="rare.kind", created_at=anchor)
    assert v["outcome"] == "uncertain"
    assert "baseline-too-noisy" in v["reason"]


def test_frequency_verdict_uncertain_when_event_kind_missing():
    v = cp._frequency_verdict(event_kind="", created_at=datetime.now(UTC))
    assert v["outcome"] == "uncertain"
    assert v["reason"] == "no-event-kind-tag-on-prediction"


def test_extract_event_kind_from_evidence():
    pred = {"evidence": ["counterfactual:cf-abc", "event_kind:conflict.detected", "anchor-text"]}
    assert cp._extract_event_kind(pred) == "conflict.detected"


def test_extract_event_kind_returns_empty_when_absent():
    pred = {"evidence": ["counterfactual:cf-abc", "anchor-text"]}
    assert cp._extract_event_kind(pred) == ""


def test_is_horizon_expired_true_when_past_horizon_plus_grace():
    pred = {
        "created_at": (datetime.now(UTC) - timedelta(days=cp.HORIZON_DAYS + cp.GRACE_DAYS + 1)).isoformat()
    }
    assert cp._is_horizon_expired(pred, datetime.now(UTC)) is True


def test_is_horizon_expired_false_when_within_window():
    pred = {"created_at": (datetime.now(UTC) - timedelta(days=2)).isoformat()}
    assert cp._is_horizon_expired(pred, datetime.now(UTC)) is False


def test_confidence_band_thresholds():
    assert cp._confidence_band(0.9) == "high"
    assert cp._confidence_band(0.7) == "high"
    assert cp._confidence_band(0.5) == "medium"
    assert cp._confidence_band(0.4) == "medium"
    assert cp._confidence_band(0.2) == "low"
    assert cp._confidence_band(0.0) == "low"
