"""Smoke tests for db_runtime_temporal_memory_signals.py — exercise the read/write paths against an isolated DB."""
from __future__ import annotations


def test_db_runtime_temporal_memory_signals_read_paths_are_callable(isolated_runtime):
    import core.runtime.db_runtime_temporal_memory_signals as m

    # Every family's LIST returns [] and every GET returns None on a fresh DB.
    # This forces each ensure-table + SELECT to actually run against the schema.
    assert m.list_runtime_temporal_recurrence_signals() == []
    assert m.get_runtime_temporal_recurrence_signal("missing") is None

    assert m.list_runtime_remembered_fact_signals() == []
    assert m.get_runtime_remembered_fact_signal("missing") is None

    assert m.list_runtime_memory_md_update_proposals() == []
    assert m.get_runtime_memory_md_update_proposal("missing") is None

    assert m.list_runtime_release_marker_signals() == []
    assert m.get_runtime_release_marker_signal("missing") is None

    assert m.list_runtime_selective_forgetting_candidates() == []
    assert m.get_runtime_selective_forgetting_candidate("missing") is None

    assert m.list_runtime_regulation_homeostasis_signals() == []
    assert m.get_runtime_regulation_homeostasis_signal("missing") is None

    assert m.list_runtime_temperament_tendency_signals() == []
    assert m.get_runtime_temperament_tendency_signal("missing") is None

    # status filter path (adds a WHERE clause) must also run cleanly.
    assert m.list_runtime_temporal_recurrence_signals(status="active") == []

    # update_status on a non-existent row returns None (no raise).
    assert (
        m.update_runtime_temporal_recurrence_signal_status(
            "missing", status="stale", updated_at="2026-07-09T00:00:00Z"
        )
        is None
    )

    # supersede against an empty table touches zero rows.
    assert (
        m.supersede_runtime_temporal_recurrence_signals_for_domain(
            domain_key="focus",
            exclude_signal_id="none",
            updated_at="2026-07-09T00:00:00Z",
            status_reason="test",
        )
        == 0
    )


def test_db_runtime_temporal_memory_signals_upsert_roundtrip(isolated_runtime):
    import core.runtime.db_runtime_temporal_memory_signals as m

    ts = "2026-07-09T00:00:00Z"
    signal = m.upsert_runtime_remembered_fact_signal(
        signal_id="fact-1",
        signal_type="remembered-fact",
        canonical_key="remembered-fact:x:dim",
        status="active",
        title="Bjørn drinks coffee",
        summary="Observed preference for coffee",
        rationale="stated in chat",
        source_kind="observation",
        confidence="medium",
        evidence_summary="said so once",
        support_summary="single mention",
        support_count=1,
        session_count=1,
        created_at=ts,
        updated_at=ts,
    )
    assert signal["signal_id"] == "fact-1"
    assert signal["status"] == "active"

    # It is now retrievable by id.
    fetched = m.get_runtime_remembered_fact_signal("fact-1")
    assert fetched is not None
    assert fetched["title"] == "Bjørn drinks coffee"

    # And it shows up in the list.
    rows = m.list_runtime_remembered_fact_signals()
    assert any(r["signal_id"] == "fact-1" for r in rows)

    # Status update round-trips.
    updated = m.update_runtime_remembered_fact_signal_status(
        "fact-1", status="stale", updated_at=ts, status_reason="aged out"
    )
    assert updated is not None
    assert updated["status"] == "stale"
    assert updated["status_reason"] == "aged out"
