"""Tests for counterfactual_tools (Phase 4 — read-only exposition)."""
from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from core.tools import counterfactual_tools as ct


def _setup_db(monkeypatch):
    """Replace connect() with a populated :memory: connection."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE counterfactuals (
            cf_id TEXT PRIMARY KEY,
            cf_key TEXT NOT NULL UNIQUE,
            workspace_id TEXT NOT NULL,
            cluster_id TEXT NOT NULL,
            trigger_event_ids_json TEXT NOT NULL,
            trigger_types_json TEXT NOT NULL,
            what_if TEXT NOT NULL,
            likely_difference TEXT,
            reasoning TEXT,
            llm_confidence REAL DEFAULT 0.0,
            apophenia_score REAL DEFAULT 1.0,
            final_confidence REAL DEFAULT 0.0,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    now = datetime.now(UTC)
    rows = [
        ("cf-a", "key-a", "default", "c1", json.dumps([1]), json.dumps(["conflict.detected"]),
         "Hvad hvis vi havde gjort X?", "diff", "reason", 0.7, 0.9, 0.7, "promoted",
         now.isoformat(), now.isoformat()),
        ("cf-b", "key-b", "default", "c2", json.dumps([2]), json.dumps(["self_review_outcome.created"]),
         "Hvad hvis Y?", None, None, 0.4, 0.5, 0.4, "generated",
         (now - timedelta(days=2)).isoformat(), now.isoformat()),
        ("cf-c", "key-c", "default", "c3", json.dumps([3]), json.dumps(["conflict.detected"]),
         "TODO", None, None, 0.0, 0.0, 0.0, "generated",
         (now - timedelta(days=40)).isoformat(), now.isoformat()),
    ]
    for r in rows:
        conn.execute(
            "INSERT INTO counterfactuals VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", r
        )
    conn.commit()

    class _CtxConn:
        def __enter__(self):
            return conn
        def __exit__(self, *a):
            pass

    monkeypatch.setattr(ct, "connect", lambda: _CtxConn())
    return conn


def test_list_returns_recent(monkeypatch):
    _setup_db(monkeypatch)
    r = ct._exec_list_counterfactuals({"lookback_days": 7})
    assert r["status"] == "ok"
    assert r["count"] == 2  # cf-c is 40d old, outside window
    ids = [cf["cf_id"] for cf in r["counterfactuals"]]
    assert "cf-a" in ids and "cf-b" in ids
    assert "cf-c" not in ids


def test_list_filters_by_status(monkeypatch):
    _setup_db(monkeypatch)
    r = ct._exec_list_counterfactuals({"status": "promoted", "lookback_days": 7})
    assert r["count"] == 1
    assert r["counterfactuals"][0]["cf_id"] == "cf-a"


def test_list_filters_by_trigger_type(monkeypatch):
    _setup_db(monkeypatch)
    r = ct._exec_list_counterfactuals({
        "trigger_type": "conflict.detected", "lookback_days": 7
    })
    assert r["count"] == 1  # only cf-a matches within window
    assert r["counterfactuals"][0]["cf_id"] == "cf-a"


def test_list_min_final_confidence(monkeypatch):
    _setup_db(monkeypatch)
    r = ct._exec_list_counterfactuals({
        "min_final_confidence": 0.5, "lookback_days": 7
    })
    assert r["count"] == 1
    assert r["counterfactuals"][0]["cf_id"] == "cf-a"


def test_list_text_field_present(monkeypatch):
    _setup_db(monkeypatch)
    r = ct._exec_list_counterfactuals({"lookback_days": 90})
    assert "Counterfactuals" in r["text"]
    assert "cf-a" in r["text"]


def test_read_returns_single(monkeypatch):
    _setup_db(monkeypatch)
    r = ct._exec_read_counterfactual({"cf_id": "cf-a"})
    assert r["status"] == "ok"
    assert r["counterfactual"]["cf_id"] == "cf-a"
    assert r["counterfactual"]["what_if"] == "Hvad hvis vi havde gjort X?"


def test_read_missing_cf_id(monkeypatch):
    _setup_db(monkeypatch)
    r = ct._exec_read_counterfactual({})
    assert r["status"] == "error"
    assert "cf_id is required" in r["error"]


def test_read_unknown_cf_id(monkeypatch):
    _setup_db(monkeypatch)
    r = ct._exec_read_counterfactual({"cf_id": "cf-doesnotexist"})
    assert r["status"] == "error"
    assert "unknown" in r["error"]


def test_summary_aggregates(monkeypatch):
    _setup_db(monkeypatch)
    r = ct._exec_counterfactual_summary({"lookback_days": 90})
    assert r["status"] == "ok"
    assert r["total"] == 3
    assert r["by_status"]["promoted"] == 1
    assert r["by_status"]["generated"] == 2
    assert r["promoted_rate"] == pytest.approx(1 / 3, abs=0.01)
    assert "conflict.detected" in r["by_trigger"]
    assert r["by_trigger"]["conflict.detected"] == 2


def test_summary_text_contains_breakdown(monkeypatch):
    _setup_db(monkeypatch)
    r = ct._exec_counterfactual_summary({"lookback_days": 90})
    assert "by_status" in r["text"]
    assert "top trigger types" in r["text"]


def test_list_caps_limit(monkeypatch):
    _setup_db(monkeypatch)
    r = ct._exec_list_counterfactuals({"limit": 999, "lookback_days": 365})
    assert r["count"] <= ct._MAX_LIMIT
