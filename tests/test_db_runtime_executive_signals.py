"""Smoke tests for db_runtime_executive_signals.py — exercise the read/write paths against an isolated DB."""
from __future__ import annotations

import importlib


def _load_module():
    # db_runtime_executive_signals binds `connect` from core.runtime.db_core at
    # import time. isolated_runtime reloads db_core under a tmp HOME, so reload
    # this module too to rebind `connect` to the isolated DB.
    import core.runtime.db_runtime_executive_signals as m

    return importlib.reload(m)


def test_executive_signals_read_paths_are_callable(isolated_runtime):
    m = _load_module()

    # Every LIST function returns [] on a fresh DB (tables auto-ensured lazily).
    assert m.list_runtime_goal_signals() == []
    assert m.list_runtime_world_model_signals() == []
    assert m.list_runtime_development_focuses() == []
    assert m.list_runtime_autonomy_pressure_signals() == []
    assert m.list_runtime_open_loop_signals() == []
    assert m.list_runtime_open_loop_closure_proposals() == []
    assert m.list_runtime_contract_candidates() == []
    assert m.list_runtime_proactive_loop_lifecycle_signals() == []
    assert m.list_runtime_proactive_question_gates() == []

    # GET functions return None for a missing id.
    assert m.get_runtime_goal_signal("nope") is None
    assert m.get_runtime_world_model_signal("nope") is None
    assert m.get_runtime_development_focus("nope") is None
    assert m.get_runtime_autonomy_pressure_signal("nope") is None
    assert m.get_runtime_open_loop_signal("nope") is None
    assert m.get_runtime_open_loop_closure_proposal("nope") is None
    assert m.get_runtime_contract_candidate("nope") is None
    assert m.get_runtime_proactive_loop_lifecycle_signal("nope") is None
    assert m.get_runtime_proactive_question_gate("nope") is None

    # The COUNT aggregate is empty on a fresh DB.
    assert m.runtime_contract_candidate_counts() == {}


def test_goal_signal_upsert_then_list_and_get(isolated_runtime):
    m = _load_module()

    created = m.upsert_runtime_goal_signal(
        goal_id="goal-1",
        goal_type="focus",
        canonical_key="goal:focus:test",
        status="active",
        title="Test goal",
        summary="A smoke-test goal",
        rationale="because",
        source_kind="observed",
        confidence="medium",
        evidence_summary="ev",
        support_summary="sup",
        support_count=1,
        session_count=1,
        created_at="2026-07-09T00:00:00Z",
        updated_at="2026-07-09T00:00:00Z",
    )
    assert created["goal_id"] == "goal-1"
    assert created["was_created"] is True

    fetched = m.get_runtime_goal_signal("goal-1")
    assert fetched is not None
    assert fetched["title"] == "Test goal"

    listed = m.list_runtime_goal_signals()
    assert [row["goal_id"] for row in listed] == ["goal-1"]


def test_contract_candidate_roundtrip_and_counts(isolated_runtime):
    m = _load_module()

    m.upsert_runtime_contract_candidate(
        candidate_id="cand-1",
        candidate_type="identity",
        target_file="workspace/identity.md",
        status="proposed",
        source_kind="observed",
        source_mode="auto",
        actor="jarvis",
        session_id="sess-1",
        run_id="run-1",
        canonical_key="identity:workspace/identity.md:key",
        summary="candidate summary",
        reason="candidate reason",
        evidence_summary="ev",
        support_summary="sup",
        confidence="medium",
        evidence_class="direct",
        support_count=1,
        session_count=1,
        created_at="2026-07-09T00:00:00Z",
        updated_at="2026-07-09T00:00:00Z",
    )

    listed = m.list_runtime_contract_candidates(candidate_type="identity")
    assert [row["candidate_id"] for row in listed] == ["cand-1"]

    counts = m.runtime_contract_candidate_counts()
    assert counts.get("identity:proposed") == 1
