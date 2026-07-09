"""Smoke tests for db_runtime_dream.py — exercise the read/write paths against an isolated DB."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def test_db_runtime_dream_read_paths_are_callable(isolated_runtime):
    import core.runtime.db_runtime_dream as m

    # LIST functions on the empty isolated DB must return empty lists.
    assert m.list_runtime_dream_hypothesis_signals() == []
    assert m.list_runtime_dream_adoption_candidates() == []
    assert m.list_runtime_dream_influence_proposals() == []

    # GET functions on absent ids must return None.
    assert m.get_runtime_dream_hypothesis_signal("missing") is None
    assert m.get_runtime_dream_adoption_candidate("missing") is None
    assert m.get_runtime_dream_influence_proposal("missing") is None

    # Status-update on an absent id must return None (no row to update).
    now = datetime.now(UTC).isoformat()
    assert (
        m.update_runtime_dream_hypothesis_signal_status(
            "missing", status="stale", updated_at=now
        )
        is None
    )
    assert (
        m.update_runtime_dream_adoption_candidate_status(
            "missing", status="stale", updated_at=now
        )
        is None
    )
    assert (
        m.update_runtime_dream_influence_proposal_status(
            "missing", status="stale", updated_at=now
        )
        is None
    )

    # Supersede on an empty domain must return 0 rows affected.
    assert (
        m.supersede_runtime_dream_hypothesis_signals_for_domain(
            domain_key="workspace-search",
            exclude_signal_id="none",
            updated_at=now,
            status_reason="nothing to supersede",
        )
        == 0
    )
    assert (
        m.supersede_runtime_dream_adoption_candidates_for_domain(
            domain_key="workspace-search",
            exclude_candidate_id="none",
            updated_at=now,
            status_reason="nothing to supersede",
        )
        == 0
    )
    assert (
        m.supersede_runtime_dream_influence_proposals_for_domain(
            domain_key="workspace-search",
            exclude_proposal_id="none",
            updated_at=now,
            status_reason="nothing to supersede",
        )
        == 0
    )


def test_db_runtime_dream_hypothesis_signal_round_trip(isolated_runtime):
    import core.runtime.db_runtime_dream as m

    now = datetime.now(UTC).isoformat()
    signal_id = f"dream-hypothesis-signal-{uuid4().hex}"
    persisted = m.upsert_runtime_dream_hypothesis_signal(
        signal_id=signal_id,
        signal_type="dream-hypothesis",
        canonical_key="dream-hypothesis:hypothesis-worthy:workspace-search",
        status="active",
        title="Dream hypothesis support: workspace search",
        summary="Bounded dream hypothesis support marking a carry-forward thread.",
        rationale="Validation dream hypothesis runtime layer",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="dream hypothesis evidence",
        support_summary="Derived from bounded dream support.",
        status_reason="Validation bounded dream hypothesis support.",
        run_id="test-run",
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )
    assert persisted["signal_id"] == signal_id
    assert persisted["status"] == "active"

    # GET returns the same row.
    fetched = m.get_runtime_dream_hypothesis_signal(signal_id)
    assert fetched is not None
    assert fetched["signal_id"] == signal_id
    assert fetched["title"] == "Dream hypothesis support: workspace search"

    # LIST now sees exactly the one signal we wrote.
    listed = m.list_runtime_dream_hypothesis_signals()
    assert [row["signal_id"] for row in listed] == [signal_id]

    # Status update round-trips.
    updated = m.update_runtime_dream_hypothesis_signal_status(
        signal_id, status="stale", updated_at=now, status_reason="aged out"
    )
    assert updated is not None
    assert updated["status"] == "stale"
    assert updated["status_reason"] == "aged out"
