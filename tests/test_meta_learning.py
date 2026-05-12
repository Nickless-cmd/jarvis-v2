"""Meta-læring Phase 1 — tests.

AGI track #3. See spec at
docs/superpowers/specs/2026-05-12-meta-learning-phase1-design.md.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest


@pytest.fixture()
def clean_state(tmp_path, monkeypatch):
    """Isolated workspace + DB so meta-learning data doesn't pollute tests."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("JARVIS_WORKSPACES_DIR", str(tmp_path / "workspaces"))
    import core.runtime.config as cfg
    monkeypatch.setattr(cfg, "STATE_DIR", str(tmp_path / "state"))
    import importlib
    import core.runtime.db as db
    importlib.reload(db)
    import core.runtime.state_store as ss
    importlib.reload(ss)
    return None


def test_schema_bootstrap_creates_table(clean_state):
    from core.services.meta_learning_retrospective import ensure_schema
    from core.runtime.db import connect

    ensure_schema()
    with connect() as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='learning_memos'"
        ).fetchone()
        assert row is not None

        idx = {r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='learning_memos'"
        ).fetchall()}
        assert "idx_learning_memos_ts" in idx


def test_schema_bootstrap_idempotent(clean_state):
    from core.services.meta_learning_retrospective import ensure_schema
    ensure_schema()
    ensure_schema()  # should not raise


def test_aggregate_world_model_empty(clean_state):
    from core.services.meta_learning_aggregator import aggregate_world_model
    now = datetime.now(UTC)
    result = aggregate_world_model(since=now - timedelta(days=7), until=now)
    assert result["predictions_made"] == 0
    assert result["predictions_resolved"] == 0
    assert result["outcome_distribution"] == {"supported": 0, "contradicted": 0, "uncertain": 0}
    assert result["extreme_samples"] == []


def test_aggregate_world_model_with_data(clean_state):
    from core.runtime.state_store import save_json
    from core.services.meta_learning_aggregator import aggregate_world_model

    now = datetime.now(UTC)
    iso_now = now.isoformat()
    iso_recent = (now - timedelta(days=1)).isoformat()
    iso_old = (now - timedelta(days=30)).isoformat()  # outside window

    predictions = [
        {"id": "p1", "subject": "x", "expectation": "y", "confidence": 0.9,
         "created_at": iso_recent, "outcome": "contradicted", "resolved_at": iso_now},
        {"id": "p2", "subject": "a", "expectation": "b", "confidence": 0.3,
         "created_at": iso_recent, "outcome": "supported", "resolved_at": iso_now},
        {"id": "p3", "subject": "c", "expectation": "d", "confidence": 0.7,
         "created_at": iso_recent, "outcome": "uncertain", "resolved_at": iso_now},
        {"id": "p4", "subject": "old", "expectation": "outside window",
         "confidence": 0.5, "created_at": iso_old, "outcome": "supported",
         "resolved_at": iso_old},
    ]
    save_json("runtime_world_model_predictions", predictions)

    result = aggregate_world_model(since=now - timedelta(days=7), until=now)
    assert result["predictions_made"] == 3
    assert result["predictions_resolved"] == 3
    assert result["outcome_distribution"]["contradicted"] == 1
    assert result["outcome_distribution"]["supported"] == 1
    assert result["outcome_distribution"]["uncertain"] == 1

    roles = {s["role"]: s["id"] for s in result["extreme_samples"]}
    assert roles.get("highest_confidence_contradicted") == "p1"
    assert roles.get("lowest_confidence_supported") == "p2"


def test_aggregate_plan_revision_empty(clean_state):
    from core.services.meta_learning_aggregator import aggregate_plan_revision
    now = datetime.now(UTC)
    result = aggregate_plan_revision(since=now - timedelta(days=7), until=now)
    assert result["plans_created"] == 0
    assert result["status_distribution"] == {
        "awaiting_approval": 0, "approved": 0, "completed": 0,
        "dismissed": 0, "superseded": 0,
    }
    assert result["extreme_samples"] == []


def test_aggregate_plan_revision_with_data(clean_state, monkeypatch):
    from core.services.meta_learning_aggregator import aggregate_plan_revision
    from core.services import plan_proposals as pp

    now = datetime.now(UTC)
    iso_now = now.isoformat()
    fast_supersede_created = (now - timedelta(days=2)).isoformat()
    fast_supersede_updated = (now - timedelta(days=2) + timedelta(minutes=30)).isoformat()
    long_completion_created = (now - timedelta(days=5)).isoformat()
    long_completion_updated = (now - timedelta(days=1)).isoformat()

    fake_plans = {
        "plan-fast": {
            "plan_id": "plan-fast", "status": "superseded",
            "created_at": fast_supersede_created,
            "updated_at": fast_supersede_updated,
            "title": "Fast superseded", "superseded_by": "plan-other",
        },
        "plan-long": {
            "plan_id": "plan-long", "status": "completed",
            "created_at": long_completion_created,
            "updated_at": long_completion_updated,
            "title": "Long completion",
        },
        "plan-other": {
            "plan_id": "plan-other", "status": "approved",
            "created_at": iso_now, "title": "Replacement",
        },
    }
    monkeypatch.setattr(pp, "_load_all", lambda: fake_plans)

    result = aggregate_plan_revision(since=now - timedelta(days=7), until=now)
    assert result["plans_created"] == 3
    assert result["status_distribution"]["superseded"] == 1
    assert result["status_distribution"]["completed"] == 1
    assert result["status_distribution"]["approved"] == 1

    roles = {s["role"]: s["id"] for s in result["extreme_samples"]}
    assert roles.get("fastest_superseded") == "plan-fast"
    assert roles.get("longest_completion") == "plan-long"
