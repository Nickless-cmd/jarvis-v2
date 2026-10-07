"""Smoke tests for db_runtime_chronicle.py — exercise the read/write paths against an isolated DB."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def test_db_runtime_chronicle_read_paths_are_callable(isolated_runtime):
    import core.runtime.db_runtime_chronicle as m

    # LIST functions on the empty isolated DB must return empty lists.
    assert m.list_runtime_consolidation_target_signals() == []
    assert m.list_runtime_chronicle_consolidation_signals() == []
    assert m.list_runtime_chronicle_consolidation_briefs() == []
    assert m.list_runtime_chronicle_consolidation_proposals() == []

    # GET functions on absent ids must return None.
    assert m.get_runtime_consolidation_target_signal("missing") is None
    assert m.get_runtime_chronicle_consolidation_signal("missing") is None
    assert m.get_runtime_chronicle_consolidation_brief("missing") is None
    assert m.get_runtime_chronicle_consolidation_proposal("missing") is None

    # Status-update on an absent id must return None (no row to update).
    now = datetime.now(UTC).isoformat()
    assert (
        m.update_runtime_consolidation_target_signal_status(
            "missing", status="stale", updated_at=now
        )
        is None
    )

    # Supersede on an empty domain must return 0 rows affected.
    assert (
        m.supersede_runtime_chronicle_consolidation_signals_for_domain(
            domain_key="workspace-search",
            exclude_signal_id="none",
            updated_at=now,
            status_reason="nothing to supersede",
        )
        == 0
    )


def test_db_runtime_chronicle_signal_round_trip(isolated_runtime):
    import core.runtime.db_runtime_chronicle as m

    now = datetime.now(UTC).isoformat()
    signal_id = f"chronicle-consolidation-signal-{uuid4().hex}"
    persisted = m.upsert_runtime_chronicle_consolidation_signal(
        signal_id=signal_id,
        signal_type="chronicle-consolidation",
        canonical_key="chronicle-consolidation:consolidation-worthy:workspace-search",
        status="active",
        title="Chronicle consolidation support: workspace search",
        summary="Bounded chronicle/consolidation support marking a carry-forward thread.",
        rationale="Validation chronicle/consolidation runtime layer",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="chronicle consolidation evidence",
        support_summary="Derived from bounded self-review support.",
        status_reason="Validation bounded chronicle/consolidation support.",
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
    fetched = m.get_runtime_chronicle_consolidation_signal(signal_id)
    assert fetched is not None
    assert fetched["signal_id"] == signal_id
    assert fetched["title"] == "Chronicle consolidation support: workspace search"

    # LIST now sees exactly the one signal we wrote.
    listed = m.list_runtime_chronicle_consolidation_signals()
    assert [row["signal_id"] for row in listed] == [signal_id]

    # Status update round-trips.
    updated = m.update_runtime_chronicle_consolidation_signal_status(
        signal_id, status="stale", updated_at=now, status_reason="aged out"
    )
    assert updated is not None
    assert updated["status"] == "stale"
    assert updated["status_reason"] == "aged out"


def test_upsert_brief_dedup_fyrer_for_status_briefed(isolated_runtime):
    """Vagt mod brief-ophobningen (1/10-2026).

    ``cadence_producers`` skriver briefs med status='briefed', men netop den
    status stod IKKE i ``lookup_statuses`` i brief-upserten. ``_upsert_signal``
    finder den eksisterende raekke via ``canonical_key`` + ``status IN (...)``,
    saa opslaget matchede aldrig — og hver tur skrev en ny raekke. Maalt foer
    fixet: 22.103 briefs med 15.468 unikke noegler.

    Testen pinner BEGGE halvdele af fixet: at 'briefed' er foert til
    lookup-listen, og at tre upserts med samme noegle derfor giver praecis én
    raekke. Fjernes 'briefed' igen, fejler den her.
    """
    import core.runtime.db_runtime_chronicle as m

    key = "chronicle-brief:2026-10-01:chat-test"
    now = datetime.now(UTC).isoformat()

    for i in range(3):
        m.upsert_runtime_chronicle_consolidation_brief(
            brief_id=f"brief-{i}",
            brief_type="post_run_brief",
            canonical_key=key,
            status="briefed",
            title=f"Brief {i}",
            summary="Run brief",
            rationale="Post-run carry-forward",
            source_kind="visible_run",
            confidence="medium",
            evidence_summary="evidence",
            support_summary="completed",
            run_id=f"visible-run{i}",
            session_id="chat-test",
            created_at=now,
            updated_at=now,
        )

    rows = [
        row
        for row in m.list_runtime_chronicle_consolidation_briefs()
        if row["canonical_key"] == key
    ]
    assert len(rows) == 1, (
        f"brief-ophobning: {len(rows)} raekker for samme noegle — 'briefed' mangler "
        "sandsynligvis i lookup_statuses i upsert_runtime_chronicle_consolidation_brief"
    )
