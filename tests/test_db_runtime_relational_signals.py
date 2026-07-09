"""Smoke tests for db_runtime_relational_signals.py — exercise the read/write paths against an isolated DB."""
from __future__ import annotations


def test_db_runtime_relational_signals_read_paths_are_callable(isolated_runtime):
    import core.runtime.db_runtime_relational_signals as m

    # Every family's LIST returns [] and every GET returns None on a fresh DB.
    # This forces each ensure-table + SELECT to actually run against the schema.
    assert m.list_runtime_user_md_update_proposals() == []
    assert m.get_runtime_user_md_update_proposal("missing") is None

    assert m.list_runtime_user_understanding_signals() == []
    assert m.get_runtime_user_understanding_signal("missing") is None

    assert m.list_runtime_inner_visible_support_signals() == []
    assert m.get_runtime_inner_visible_support_signal("missing") is None

    assert m.list_runtime_relation_state_signals() == []
    assert m.get_runtime_relation_state_signal("missing") is None

    assert m.list_runtime_relation_continuity_signals() == []
    assert m.get_runtime_relation_continuity_signal("missing") is None

    assert m.list_runtime_attachment_topology_signals() == []
    assert m.get_runtime_attachment_topology_signal("missing") is None

    assert m.list_runtime_loyalty_gradient_signals() == []
    assert m.get_runtime_loyalty_gradient_signal("missing") is None

    # status filter path (adds a WHERE clause) must also run cleanly.
    assert m.list_runtime_relation_state_signals(status="active") == []

    # update_status on a non-existent row returns None (no raise).
    assert (
        m.update_runtime_relation_state_signal_status(
            "missing", status="stale", updated_at="2026-07-09T00:00:00Z"
        )
        is None
    )

    # supersede against an empty table touches zero rows.
    assert (
        m.supersede_runtime_relation_state_signals_for_focus(
            focus_key="focus",
            exclude_signal_id="none",
            updated_at="2026-07-09T00:00:00Z",
            status_reason="test",
        )
        == 0
    )


def test_db_runtime_relational_signals_upsert_roundtrip(isolated_runtime):
    import core.runtime.db_runtime_relational_signals as m

    ts = "2026-07-09T00:00:00Z"
    signal = m.upsert_runtime_relation_state_signal(
        signal_id="rel-1",
        signal_type="relation-state",
        canonical_key="relation-state:x:focus",
        status="active",
        title="Warm and trusting",
        summary="Relationship reads as warm",
        rationale="observed in chat",
        source_kind="observation",
        confidence="medium",
        evidence_summary="friendly tone",
        support_summary="single session",
        created_at=ts,
        updated_at=ts,
    )
    assert signal["signal_id"] == "rel-1"
    assert signal["status"] == "active"

    # It is now retrievable by id.
    fetched = m.get_runtime_relation_state_signal("rel-1")
    assert fetched is not None
    assert fetched["title"] == "Warm and trusting"

    # And it shows up in the list.
    rows = m.list_runtime_relation_state_signals()
    assert any(r["signal_id"] == "rel-1" for r in rows)

    # Status update round-trips.
    updated = m.update_runtime_relation_state_signal_status(
        "rel-1", status="stale", updated_at=ts, status_reason="aged out"
    )
    assert updated is not None
    assert updated["status"] == "stale"
    assert updated["status_reason"] == "aged out"
