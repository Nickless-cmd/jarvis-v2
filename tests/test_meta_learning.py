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


def test_aggregate_curiosity_empty(clean_state):
    from core.services.meta_learning_aggregator import aggregate_curiosity
    from core.services.curiosity_budget import ensure_schema
    ensure_schema()
    now = datetime.now(UTC)
    result = aggregate_curiosity(since=now - timedelta(days=7), until=now)
    assert result["actions_used"] == 0
    assert result["action_distribution"] == {}
    assert result["extreme_samples"] == []


def test_aggregate_curiosity_with_data(clean_state):
    from core.services.curiosity_budget import ensure_schema, record_observation
    from core.services.meta_learning_aggregator import aggregate_curiosity
    ensure_schema()

    obs_short = record_observation("read_dreams", "{}", "short note", None)
    obs_long = record_observation(
        "list_tools", "{}",
        "Very long observation that goes into detail about why this is interesting "
        "and what trail of thought led here, capturing the engaged moment of curiosity.",
        None,
    )

    now = datetime.now(UTC)
    result = aggregate_curiosity(since=now - timedelta(days=7), until=now)
    assert result["actions_used"] == 2
    assert result["action_distribution"]["read_dreams"] == 1
    assert result["action_distribution"]["list_tools"] == 1

    roles = {s["role"]: s["id"] for s in result["extreme_samples"]}
    assert roles.get("longest_observation_text") == obs_long
    assert roles.get("shortest_non_empty_observation") == obs_short


def test_aggregate_skill_chain_phase2_empty(clean_state):
    from core.services.meta_learning_aggregator import aggregate_skill_chain_phase2
    now = datetime.now(UTC)
    result = aggregate_skill_chain_phase2(since=now - timedelta(days=7), until=now)
    assert result["proposals_made"] == 0
    assert result["revisions_made"] == 0
    assert result["revision_context_distribution"] == {"pre_execution": 0, "mid_chain": 0}
    assert result["extreme_samples"] == []


def test_aggregate_skill_chain_phase2_with_data(clean_state):
    from core.runtime.db import connect
    from core.services.meta_learning_aggregator import aggregate_skill_chain_phase2

    now = datetime.now(UTC)
    iso_now = now.isoformat()

    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
              event_id TEXT PRIMARY KEY,
              family TEXT,
              kind TEXT,
              created_at TEXT,
              payload_json TEXT
            )
        """)
        conn.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?)",
            ("e1", "cognitive_skill_chain", "proposed", iso_now,
             json.dumps({"plan": ["a","b"], "confidence": 0.9, "step_count": 2})),
        )
        conn.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?)",
            ("e2", "cognitive_skill_chain", "revised", iso_now,
             json.dumps({"new_plan": ["a","c"], "revision_context": "pre_execution",
                         "reason": "I want to try a different second step entirely, "
                                   "because the first plan ran into issues."})),
        )
        conn.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?)",
            ("e3", "cognitive_skill_chain", "revised", iso_now,
             json.dumps({"new_plan": ["d","e"], "revision_context": "mid_chain",
                         "reason": "step 1 failed"})),
        )
        conn.commit()

    result = aggregate_skill_chain_phase2(since=now - timedelta(days=7), until=now)
    assert result["proposals_made"] == 1
    assert result["revisions_made"] == 2
    assert result["revision_context_distribution"]["pre_execution"] == 1
    assert result["revision_context_distribution"]["mid_chain"] == 1

    roles = {s["role"]: s["id"] for s in result["extreme_samples"]}
    assert roles.get("highest_confidence_proposal") == "e1"
    assert roles.get("longest_reason_revision") == "e2"


def test_aggregate_tool_invention_empty(clean_state):
    from core.services.meta_learning_aggregator import aggregate_tool_invention
    now = datetime.now(UTC)
    result = aggregate_tool_invention(since=now - timedelta(days=7), until=now)
    assert result["proposed"] == 0
    assert result["adopted"] == 0


def test_aggregate_tool_invention_with_data(clean_state, monkeypatch):
    from core.services.meta_learning_aggregator import aggregate_tool_invention
    from core.services import plan_proposals as pp

    now = datetime.now(UTC)
    iso_recent = (now - timedelta(days=1)).isoformat()

    fake_plans = {
        "plan-skill-a": {
            "plan_id": "plan-skill-a",
            "status": "approved",
            "created_at": iso_recent,
            "title": "Install skill foo",
            "skill_data": {"name": "foo", "description": "..."},
        },
        "plan-skill-b": {
            "plan_id": "plan-skill-b",
            "status": "dismissed",
            "created_at": iso_recent,
            "title": "Install skill bar",
            "skill_data": {"name": "bar", "description": "..."},
        },
        "plan-regular": {
            "plan_id": "plan-regular",
            "status": "approved",
            "created_at": iso_recent,
            "title": "Regular plan",
            "skill_data": None,
        },
    }
    monkeypatch.setattr(pp, "_load_all", lambda: fake_plans)

    result = aggregate_tool_invention(since=now - timedelta(days=7), until=now)
    assert result["proposed"] == 2
    assert result["adopted"] == 1
    sample_ids = {s["id"] for s in result["extreme_samples"]}
    assert "plan-skill-a" in sample_ids
