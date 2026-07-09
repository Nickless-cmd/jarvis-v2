"""Smoke tests for db_runtime_self.py — exercise the read/write paths against an isolated DB."""
from __future__ import annotations


def test_db_runtime_self_read_paths_are_callable(isolated_runtime):
    import core.runtime.db_runtime_self as m

    # LIST functions on a fresh DB must return an empty list (this also creates
    # the tables lazily via the _ensure_* helpers).
    assert m.list_runtime_self_model_signals() == []
    assert m.list_runtime_self_authored_prompt_proposals() == []
    assert m.list_runtime_self_narrative_continuity_signals() == []
    assert m.list_runtime_selfhood_proposals() == []

    # GET functions for a nonexistent id must return None, not raise.
    assert m.get_runtime_self_model_signal("does-not-exist") is None
    assert m.get_runtime_self_authored_prompt_proposal("does-not-exist") is None
    assert m.get_runtime_self_narrative_continuity_signal("does-not-exist") is None
    assert m.get_runtime_selfhood_proposal("does-not-exist") is None


def test_db_runtime_self_model_signal_round_trip(isolated_runtime):
    import core.runtime.db_runtime_self as m

    stored = m.upsert_runtime_self_model_signal(
        signal_id="sig-1",
        signal_type="tone",
        canonical_key="self-model:tone:warmth",
        status="active",
        title="warmth",
        summary="tends warm",
        rationale="observed across sessions",
        source_kind="observation",
        confidence="medium",
        evidence_summary="ev",
        support_summary="sup",
        support_count=1,
        session_count=1,
        created_at="2026-07-09T00:00:00Z",
        updated_at="2026-07-09T00:00:00Z",
    )
    assert stored["signal_id"] == "sig-1"
    assert stored["was_created"] is True

    fetched = m.get_runtime_self_model_signal("sig-1")
    assert fetched is not None
    assert fetched["title"] == "warmth"

    rows = m.list_runtime_self_model_signals()
    assert [r["signal_id"] for r in rows] == ["sig-1"]

    updated = m.update_runtime_self_model_signal_status(
        "sig-1",
        status="stale",
        updated_at="2026-07-09T01:00:00Z",
        status_reason="aged out",
    )
    assert updated is not None
    assert updated["status"] == "stale"


def test_db_runtime_selfhood_proposal_round_trip(isolated_runtime):
    import core.runtime.db_runtime_self as m

    stored = m.upsert_runtime_selfhood_proposal(
        proposal_id="prop-1",
        proposal_type="value",
        canonical_key="selfhood-proposal:value:curiosity",
        status="fresh",
        title="curiosity",
        summary="values curiosity",
        rationale="recurring",
        source_kind="observation",
        confidence="low",
        evidence_summary="ev",
        support_summary="sup",
        support_count=1,
        session_count=1,
        created_at="2026-07-09T00:00:00Z",
        updated_at="2026-07-09T00:00:00Z",
    )
    assert stored["proposal_id"] == "prop-1"

    rows = m.list_runtime_selfhood_proposals()
    assert [r["proposal_id"] for r in rows] == ["prop-1"]

    # Supersede-for-domain with an exclusion that is NOT this row → the one live
    # proposal gets superseded; rowcount is 1.
    n = m.supersede_runtime_selfhood_proposals_for_domain(
        domain_key="curiosity",
        exclude_proposal_id="other",
        updated_at="2026-07-09T02:00:00Z",
        status_reason="replaced",
    )
    assert n == 1
    assert m.get_runtime_selfhood_proposal("prop-1")["status"] == "superseded"
