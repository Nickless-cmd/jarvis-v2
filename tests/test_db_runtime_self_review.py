"""Smoke tests for db_runtime_self_review.py — exercise the read/write paths against an isolated DB."""
from __future__ import annotations


def test_db_runtime_self_review_read_paths_are_callable(isolated_runtime):
    import core.runtime.db_runtime_self_review as m

    # LIST functions: empty on a fresh DB (lazy _ensure creates the schema, no rows).
    assert m.list_runtime_self_review_signals() == []
    assert m.list_runtime_self_review_records() == []
    assert m.list_runtime_self_review_runs() == []
    assert m.list_runtime_self_review_outcomes() == []
    assert m.list_runtime_self_review_cadence_signals() == []

    # GET functions: None for an unknown id.
    assert m.get_runtime_self_review_signal("missing") is None
    assert m.get_runtime_self_review_record("missing") is None
    assert m.get_runtime_self_review_run("missing") is None
    assert m.get_runtime_self_review_outcome("missing") is None
    assert m.get_runtime_self_review_cadence_signal("missing") is None

    # UPDATE-status on a missing row is a no-op returning None (no raise).
    assert (
        m.update_runtime_self_review_signal_status(
            "missing", status="stale", updated_at="2026-01-01T00:00:00Z"
        )
        is None
    )

    # SUPERSEDE on an empty domain updates zero rows.
    assert (
        m.supersede_runtime_self_review_signals_for_domain(
            domain_key="nope",
            exclude_signal_id="none",
            updated_at="2026-01-01T00:00:00Z",
            status_reason="test",
        )
        == 0
    )


def test_db_runtime_self_review_signal_round_trip(isolated_runtime):
    import core.runtime.db_runtime_self_review as m

    now = "2026-01-01T00:00:00Z"
    persisted = m.upsert_runtime_self_review_signal(
        signal_id="sig-1",
        signal_type="drift",
        canonical_key="self-review:drift:domainA",
        status="active",
        title="Test signal",
        summary="A test summary",
        rationale="because",
        source_kind="observation",
        confidence="medium",
        evidence_summary="evidence",
        support_summary="support",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )
    assert persisted["signal_id"] == "sig-1"

    # It reads back through get and shows up in list.
    fetched = m.get_runtime_self_review_signal("sig-1")
    assert fetched is not None
    assert fetched["signal_type"] == "drift"

    listed = m.list_runtime_self_review_signals(status="active")
    assert any(r["signal_id"] == "sig-1" for r in listed)


def test_db_runtime_self_review_record_round_trip(isolated_runtime):
    import core.runtime.db_runtime_self_review as m

    now = "2026-01-01T00:00:00Z"
    m.upsert_runtime_self_review_record(
        record_id="rec-1",
        record_type="finding",
        canonical_key="self-review-record:finding:domainB",
        status="fresh",
        title="Test record",
        summary="summary",
        rationale="because",
        source_kind="observation",
        confidence="high",
        evidence_summary="evidence",
        support_summary="support",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )

    fetched = m.get_runtime_self_review_record("rec-1")
    assert fetched is not None
    assert fetched["record_type"] == "finding"
    assert any(
        r["record_id"] == "rec-1" for r in m.list_runtime_self_review_records()
    )
