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
    # Reload modules that cache _SCHEMA_INITIALIZED globals so they re-create
    # tables in the tmp_path DB instead of pointing at a stale prior DB.
    import core.services.curiosity_budget as cb
    importlib.reload(cb)
    import core.services.meta_learning_retrospective as mlr
    importlib.reload(mlr)
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


def test_build_prompt_includes_personality_and_citation_instruction(clean_state):
    from core.services.meta_learning_retrospective import _build_retrospective_prompt

    aggregator_snapshot = {
        "world_model": {"predictions_made": 0, "predictions_resolved": 0,
                        "outcome_distribution": {}, "extreme_samples": []},
        "plan_revision": {"plans_created": 0, "status_distribution": {},
                          "extreme_samples": []},
        "curiosity": {"actions_used": 0, "action_distribution": {},
                      "extreme_samples": []},
        "skill_chain_phase2": {"proposals_made": 0, "revisions_made": 0,
                               "revision_context_distribution": {},
                               "extreme_samples": []},
        "tool_invention": {"proposed": 0, "adopted": 0, "extreme_samples": []},
    }
    prompt = _build_retrospective_prompt(
        period_start="2026-05-05T00:00:00+00:00",
        period_end="2026-05-12T00:00:00+00:00",
        aggregator_snapshot=aggregator_snapshot,
    )
    lo = prompt.lower()
    assert "1.-person" in lo or "1. person" in lo or "1st-person" in lo
    assert "dansk" in lo
    assert "citationsnøgle" in lo or "plan_id" in prompt
    assert "Hypothesis Candidates" in prompt
    assert "tom" in lo or "empty" in lo


def test_parse_memo_with_hypotheses(clean_state):
    from core.services.meta_learning_retrospective import _parse_memo_markdown

    markdown = """Dette er ugentlig prosa-analyse. Jeg har observeret at jeg reviderer plans hurtigt: plan-abc123 blev superseded efter 30 min (12. maj 09:30→10:00).

Mit kalibreringsmønster: confidence 0.9 var contradicted i prediction-xyz789.

## Hypothesis Candidates

### Kandidat 1: Vent 3 min før propose_plan
- **Observation:** Plans superseded inden for 1 time i 80% af tilfældene (plan-abc123, plan-def456)
- **Hypotese:** Hvis jeg venter 3 min med refleksion før propose_plan, stiger approval-rate
- **Success-kriterium:** Approval-rate (approved / proposed) stiger fra X til Y over 4 uger
- **Sample-størrelse:** Mindst 10 plans

### Kandidat 2: Lavere confidence i overraskelser
- **Observation:** Predictions med confidence >0.85 contradicted i 40%
- **Hypotese:** Hvis jeg sætter et cap på max 0.85 confidence, vil overall kalibrering forbedres
- **Success-kriterium:** Brier score lavere efter 20 nye predictions
- **Sample-størrelse:** 20 predictions
"""
    result = _parse_memo_markdown(markdown)
    assert result["status"] == "ok"
    assert "ugentlig prosa-analyse" in result["narrative"]
    assert "plan-abc123" in result["narrative"]
    assert "## Hypothesis Candidates" not in result["narrative"]
    assert len(result["hypothesis_candidates"]) == 2
    cand1 = result["hypothesis_candidates"][0]
    assert cand1["id"] == "hyp-1"
    assert "Vent 3 min" in cand1["statement"]
    assert "plan-abc123" in cand1["observation"]
    assert cand1["sample_size_needed"] == 10


def test_parse_memo_without_hypotheses(clean_state):
    from core.services.meta_learning_retrospective import _parse_memo_markdown

    markdown = """Ugen var rolig. Få events, lille datagrundlag, ingen klare mønstre.

## Hypothesis Candidates

(Ingen hypoteser denne uge — datagrundlaget er for spinkelt.)
"""
    result = _parse_memo_markdown(markdown)
    assert result["status"] == "ok"
    assert "Ugen var rolig" in result["narrative"]
    assert result["hypothesis_candidates"] == []


def test_parse_memo_with_markdown_fence(clean_state):
    from core.services.meta_learning_retrospective import _parse_memo_markdown

    markdown = """```markdown
Prosa-analyse her.

## Hypothesis Candidates

### Kandidat 1: Test
- **Observation:** noget
- **Hypotese:** hvis X så Y
- **Success-kriterium:** måling
- **Sample-størrelse:** 5
```"""
    result = _parse_memo_markdown(markdown)
    assert result["status"] == "ok"
    assert "Prosa-analyse" in result["narrative"]
    assert len(result["hypothesis_candidates"]) == 1


def test_parse_memo_malformed_returns_narrative_only(clean_state):
    from core.services.meta_learning_retrospective import _parse_memo_markdown

    markdown = """Just some text without proper structure.

## Hypothesis Candidates

### Kandidat 1: But fields are missing
"""
    result = _parse_memo_markdown(markdown)
    assert result["status"] == "ok"
    assert "Just some text" in result["narrative"]
    assert isinstance(result["hypothesis_candidates"], list)


def test_persist_memo_inserts_row(clean_state):
    from core.runtime.db import connect
    from core.services.meta_learning_retrospective import (
        ensure_schema, _persist_memo,
    )
    ensure_schema()

    memo_id = _persist_memo(
        memo_id="memo-test-1",
        ts="2026-05-12T04:00:00+00:00",
        period_start="2026-05-05T00:00:00+00:00",
        period_end="2026-05-12T00:00:00+00:00",
        narrative="Test narrative.",
        hypothesis_candidates=[{"id": "hyp-1", "statement": "x"}],
        aggregator_snapshot={"world_model": {}},
        model_used="fake-model",
    )
    assert memo_id == "memo-test-1"
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM learning_memos WHERE memo_id = ?", (memo_id,)
        ).fetchone()
    assert row is not None
    assert row["narrative"] == "Test narrative."
    assert row["model_used"] == "fake-model"
    assert row["acknowledged_at"] is None


def test_fetch_latest_unacknowledged(clean_state):
    from core.services.meta_learning_retrospective import (
        ensure_schema, _persist_memo, fetch_latest_unacknowledged_memo,
    )
    ensure_schema()
    assert fetch_latest_unacknowledged_memo() is None

    _persist_memo(
        memo_id="memo-old", ts="2026-05-01T04:00:00+00:00",
        period_start="x", period_end="y",
        narrative="old", hypothesis_candidates=[], aggregator_snapshot={},
        model_used="m",
    )
    _persist_memo(
        memo_id="memo-new", ts="2026-05-12T04:00:00+00:00",
        period_start="x", period_end="y",
        narrative="newer", hypothesis_candidates=[], aggregator_snapshot={},
        model_used="m",
    )
    result = fetch_latest_unacknowledged_memo()
    assert result is not None
    assert result["memo_id"] == "memo-new"


def test_acknowledge_memo_updates_field(clean_state):
    from core.runtime.db import connect
    from core.services.meta_learning_retrospective import (
        ensure_schema, _persist_memo, acknowledge_memo,
    )
    ensure_schema()
    _persist_memo(
        memo_id="memo-ack", ts="2026-05-12T04:00:00+00:00",
        period_start="x", period_end="y",
        narrative="...", hypothesis_candidates=[], aggregator_snapshot={},
        model_used="m",
    )
    acknowledge_memo("memo-ack")
    with connect() as conn:
        row = conn.execute(
            "SELECT acknowledged_at FROM learning_memos WHERE memo_id = ?",
            ("memo-ack",),
        ).fetchone()
    assert row["acknowledged_at"] is not None


def test_generate_weekly_retrospective_end_to_end(clean_state, monkeypatch):
    from core.services import meta_learning_retrospective as mlr
    from core.runtime.db import connect

    fake_text = """Det var en rolig uge med få events. Plan-abc123 blev superseded efter 30 min.

## Hypothesis Candidates

### Kandidat 1: Vent længere
- **Observation:** Plans hurtigt superseded (plan-abc123)
- **Hypotese:** Vent 3 min før propose_plan
- **Success-kriterium:** Approval-rate stiger
- **Sample-størrelse:** 10
"""

    def fake_cheap_lane(*, message: str) -> dict[str, Any]:
        return {"status": "completed", "text": fake_text, "provider": "fake", "model": "fake-m"}

    monkeypatch.setattr(mlr, "execute_public_safe_cheap_lane", fake_cheap_lane)
    import core.services.meta_learning_aggregator as agg
    monkeypatch.setattr(agg, "aggregate_world_model",
                        lambda *, since, until: {"predictions_made": 0, "predictions_resolved": 0, "outcome_distribution": {}, "confidence_buckets": {}, "extreme_samples": []})
    monkeypatch.setattr(agg, "aggregate_plan_revision",
                        lambda *, since, until: {"plans_created": 0, "status_distribution": {}, "extreme_samples": []})
    monkeypatch.setattr(agg, "aggregate_curiosity",
                        lambda *, since, until: {"actions_used": 0, "action_distribution": {}, "extreme_samples": []})
    monkeypatch.setattr(agg, "aggregate_skill_chain_phase2",
                        lambda *, since, until: {"proposals_made": 0, "revisions_made": 0, "revision_context_distribution": {}, "extreme_samples": []})
    monkeypatch.setattr(agg, "aggregate_tool_invention",
                        lambda *, since, until: {"proposed": 0, "adopted": 0, "extreme_samples": []})

    now = datetime.now(UTC)
    result = mlr.generate_weekly_retrospective(now=now)
    assert result["status"] == "ok"
    assert result["memo_id"].startswith("memo-")
    assert "plan-abc123" in result["narrative"].lower()
    assert len(result["hypothesis_candidates"]) == 1
    assert result["model_used"] == "fake-m"

    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM learning_memos WHERE memo_id = ?", (result["memo_id"],)
        ).fetchone()
    assert row is not None


def test_generate_handles_cheap_lane_failure(clean_state, monkeypatch):
    from core.services import meta_learning_retrospective as mlr

    def failing_cheap_lane(*, message: str) -> dict[str, Any]:
        raise RuntimeError("network down")

    monkeypatch.setattr(mlr, "execute_public_safe_cheap_lane", failing_cheap_lane)
    import core.services.meta_learning_aggregator as agg
    for name in ("aggregate_world_model", "aggregate_plan_revision",
                 "aggregate_curiosity", "aggregate_skill_chain_phase2",
                 "aggregate_tool_invention"):
        monkeypatch.setattr(agg, name,
                            lambda *, since, until: {"extreme_samples": []})

    result = mlr.generate_weekly_retrospective(now=datetime.now(UTC))
    assert result["status"] == "error"
    assert "cheap-lane" in result["reason"].lower()


def test_generate_respects_killswitch(clean_state, monkeypatch):
    from core.services import meta_learning_retrospective as mlr

    class FakeSettings:
        meta_learning_enabled = False

    monkeypatch.setattr(mlr, "load_settings", lambda: FakeSettings())
    result = mlr.generate_weekly_retrospective(now=datetime.now(UTC))
    assert result["status"] == "disabled"


def test_producer_registered(clean_state):
    from core.services.internal_cadence import _producers, _ensure_producers_registered
    _ensure_producers_registered()
    assert "meta_learning_weekly_retrospective" in _producers
    spec = _producers["meta_learning_weekly_retrospective"]
    assert spec.cooldown_minutes == 10080
    assert spec.visible_grace_minutes == 60


def test_producer_skips_when_killswitch_off(clean_state, monkeypatch):
    from core.services import meta_learning_retrospective as mlr
    from core.services.internal_cadence import _producers, _ensure_producers_registered

    class FakeSettings:
        meta_learning_enabled = False

    monkeypatch.setattr(mlr, "load_settings", lambda: FakeSettings())
    _ensure_producers_registered()
    spec = _producers["meta_learning_weekly_retrospective"]
    result = spec.run_fn(trigger="cadence", last_visible_at="")
    assert result["status"] == "skipped"


def test_producer_skips_when_recent_memo_exists(clean_state):
    from core.services.meta_learning_retrospective import (
        ensure_schema, _persist_memo,
    )
    from core.services.internal_cadence import _producers, _ensure_producers_registered

    ensure_schema()
    recent_ts = (datetime.now(UTC) - timedelta(days=3)).isoformat()
    _persist_memo(
        memo_id="memo-recent", ts=recent_ts,
        period_start="x", period_end="y",
        narrative="...", hypothesis_candidates=[], aggregator_snapshot={},
        model_used="m",
    )

    _ensure_producers_registered()
    spec = _producers["meta_learning_weekly_retrospective"]
    result = spec.run_fn(trigger="cadence", last_visible_at="")
    assert result["status"] == "skipped"
    assert "recent" in result["reason"].lower() or "<6.5" in result["reason"]


def test_read_learning_memo_tool_validates_memo_id(clean_state):
    from core.tools.meta_learning_tools import _exec_read_learning_memo
    result = _exec_read_learning_memo({})
    assert result["status"] == "rejected"
    assert "memo_id" in result["reason"].lower()


def test_read_learning_memo_tool_missing_memo(clean_state):
    from core.services.meta_learning_retrospective import ensure_schema
    from core.tools.meta_learning_tools import _exec_read_learning_memo
    ensure_schema()
    result = _exec_read_learning_memo({"memo_id": "memo-nonexistent"})
    assert result["status"] == "error"
    assert "not found" in result["reason"].lower()


def test_read_learning_memo_tool_killswitch(clean_state, monkeypatch):
    from core.tools import meta_learning_tools as m

    class FakeSettings:
        meta_learning_enabled = False

    monkeypatch.setattr(m, "load_settings", lambda: FakeSettings())
    result = m._exec_read_learning_memo({"memo_id": "any"})
    assert result["status"] == "disabled"


def test_read_learning_memo_tool_returns_full_memo_and_acknowledges(clean_state):
    from core.services.meta_learning_retrospective import ensure_schema, _persist_memo
    from core.tools.meta_learning_tools import _exec_read_learning_memo
    from core.runtime.db import connect

    ensure_schema()
    _persist_memo(
        memo_id="memo-read", ts="2026-05-12T04:00:00+00:00",
        period_start="2026-05-05T00:00:00+00:00",
        period_end="2026-05-12T00:00:00+00:00",
        narrative="Full narrative text here.",
        hypothesis_candidates=[{"id": "hyp-1", "statement": "x"}],
        aggregator_snapshot={"world_model": {}},
        model_used="fake",
    )

    result = _exec_read_learning_memo({"memo_id": "memo-read"})
    assert result["status"] == "ok"
    assert result["narrative"] == "Full narrative text here."
    assert result["hypothesis_candidates"][0]["statement"] == "x"

    with connect() as conn:
        row = conn.execute(
            "SELECT acknowledged_at FROM learning_memos WHERE memo_id = ?",
            ("memo-read",),
        ).fetchone()
    assert row["acknowledged_at"] is not None


def test_list_learning_memos_tool(clean_state):
    from core.services.meta_learning_retrospective import ensure_schema, _persist_memo
    from core.tools.meta_learning_tools import _exec_list_learning_memos

    ensure_schema()
    for i in range(3):
        _persist_memo(
            memo_id=f"memo-{i}",
            ts=f"2026-05-{10+i:02d}T04:00:00+00:00",
            period_start="x", period_end="y",
            narrative=f"narr {i}", hypothesis_candidates=[],
            aggregator_snapshot={}, model_used="m",
        )
    result = _exec_list_learning_memos({"limit": 2})
    assert result["status"] == "ok"
    assert len(result["memos"]) == 2
    assert result["memos"][0]["memo_id"] == "memo-2"


def test_meta_learning_tools_registered_via_simple_tools():
    from core.tools.simple_tools import TOOL_DEFINITIONS, _TOOL_HANDLERS
    names = {(e.get("function") or {}).get("name") for e in TOOL_DEFINITIONS if isinstance(e, dict)}
    assert "read_learning_memo" in names
    assert "list_learning_memos" in names
    assert "read_learning_memo" in _TOOL_HANDLERS
    assert "list_learning_memos" in _TOOL_HANDLERS


def test_awareness_empty_when_no_memo(clean_state):
    from core.services.meta_learning_retrospective import (
        ensure_schema, format_latest_unacknowledged_memo_for_awareness,
    )
    ensure_schema()
    assert format_latest_unacknowledged_memo_for_awareness() == ""


def test_awareness_empty_when_killswitch_off(clean_state, monkeypatch):
    from core.services import meta_learning_retrospective as mlr

    class FakeSettings:
        meta_learning_enabled = False

    monkeypatch.setattr(mlr, "load_settings", lambda: FakeSettings())
    assert mlr.format_latest_unacknowledged_memo_for_awareness() == ""


def test_awareness_shows_teaser_with_memo(clean_state):
    from core.services.meta_learning_retrospective import (
        ensure_schema, _persist_memo,
        format_latest_unacknowledged_memo_for_awareness,
    )
    ensure_schema()
    _persist_memo(
        memo_id="memo-teaser",
        ts="2026-05-12T04:00:00+00:00",
        period_start="2026-05-05T00:00:00+00:00",
        period_end="2026-05-12T00:00:00+00:00",
        narrative=(
            "Det har været en interessant uge. Jeg har set at plan-abc123 "
            "blev superseded hurtigt. Mit kalibreringsmønster er stabilt på "
            "tværs af predictions."
        ),
        hypothesis_candidates=[
            {"id": "hyp-1", "statement": "Vent længere før propose_plan"},
            {"id": "hyp-2", "statement": "Cap confidence"},
        ],
        aggregator_snapshot={}, model_used="m",
    )
    out = format_latest_unacknowledged_memo_for_awareness()
    assert "📓" in out
    assert "memo-teaser" in out
    assert (
        "2 hypothesis" in out.lower()
        or "2 hypotheses" in out.lower()
        or "2 hypothesis-kandidater" in out.lower()
    )
    assert "read_learning_memo" in out
    assert "Det har været en interessant uge" in out


def test_awareness_empty_after_acknowledge(clean_state):
    from core.services.meta_learning_retrospective import (
        ensure_schema, _persist_memo, acknowledge_memo,
        format_latest_unacknowledged_memo_for_awareness,
    )
    ensure_schema()
    _persist_memo(
        memo_id="memo-acked", ts="2026-05-12T04:00:00+00:00",
        period_start="x", period_end="y",
        narrative="...", hypothesis_candidates=[],
        aggregator_snapshot={}, model_used="m",
    )
    assert format_latest_unacknowledged_memo_for_awareness() != ""
    acknowledge_memo("memo-acked")
    assert format_latest_unacknowledged_memo_for_awareness() == ""
