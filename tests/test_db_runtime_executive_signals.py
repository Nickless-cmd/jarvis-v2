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


def _upsert(m, *, candidate_id: str, summary: str = "candidate summary"):
    return m.upsert_runtime_contract_candidate(
        candidate_id=candidate_id,
        candidate_type="memory_promotion",
        target_file="MEMORY.md",
        status="proposed",
        source_kind="observed",
        source_mode="auto",
        actor="jarvis",
        session_id="sess-1",
        run_id="run-1",
        canonical_key="workspace-memory:stable-context:key",
        summary=summary,
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


def test_afgjort_noegle_genopstaar_ikke(isolated_runtime):
    """Regression (2/10-2026): 21.258 af 21.460 stable-context-rækker var dette.

    Opslaget så før kun `proposed`/`approved`. En `applied` nøgle var dermed
    USYNLIG, så den samme kendsgerning blev indsat på ny — og dræbt på ny som
    `superseded`. Køen kunne derfor kun vokse: ~130 oprettet mod ~30 gennemløbet
    pr. dag.
    """
    m = _load_module()

    first = _upsert(m, candidate_id="cand-1")
    assert first["was_created"] is True

    m.update_runtime_contract_candidate_status(
        "cand-1", status="approved", updated_at="2026-07-09T00:00:01Z"
    )
    m.update_runtime_contract_candidate_status(
        "cand-1", status="applied", updated_at="2026-07-09T00:00:02Z"
    )

    again = _upsert(m, candidate_id="cand-2")

    assert again["candidate_id"] == "cand-1", "en afgjort nøgle skal give den eksisterende række"
    assert again["was_created"] is False
    assert again["was_updated"] is False
    assert again["merge_state"] == "duplicate-terminal"
    assert len(m.list_runtime_contract_candidates(candidate_type="memory_promotion")) == 1


def test_afvist_noegle_genopstaar_ikke(isolated_runtime):
    """Også `rejected` er terminal — et afvist svar skal ikke spørges om igen."""
    m = _load_module()

    _upsert(m, candidate_id="cand-1")
    m.update_runtime_contract_candidate_status(
        "cand-1", status="rejected", updated_at="2026-07-09T00:00:01Z"
    )

    again = _upsert(m, candidate_id="cand-2")

    assert again["was_created"] is False
    assert again["merge_state"] == "duplicate-terminal"
    assert len(m.list_runtime_contract_candidates(candidate_type="memory_promotion")) == 1


def test_aktiv_noegle_flettes_stadig(isolated_runtime):
    """Fixet må ikke dræbe den normale flet-vej for en kandidat der lever."""
    m = _load_module()

    _upsert(m, candidate_id="cand-1", summary="first")
    second = _upsert(m, candidate_id="cand-2", summary="second")

    assert second["candidate_id"] == "cand-1"
    assert second["was_created"] is False
    assert second["merge_state"] == "merged"
    assert len(m.list_runtime_contract_candidates(candidate_type="memory_promotion")) == 1


def test_status_opslag_gaar_paa_noeglen(isolated_runtime):
    """A-bis: gaten skal slå op på nøglen, ikke scanne et vindue af nyeste rækker.

    Vinduet var defekten: for `user-preference:reminders:assumption-caution`
    lå den `applied`-række på id 82615, mens vinduets yngste grænse var 92229.
    """
    m = _load_module()

    assert (
        m.runtime_contract_candidate_status_for_key(
            candidate_type="memory_promotion",
            target_file="MEMORY.md",
            canonical_key="findes-ikke",
        )
        is None
    )

    _upsert(m, candidate_id="cand-1")

    assert (
        m.runtime_contract_candidate_status_for_key(
            candidate_type="memory_promotion",
            target_file="MEMORY.md",
            canonical_key="workspace-memory:stable-context:key",
        )
        == "proposed"
    )
