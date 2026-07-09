"""Smoke tests for db_runtime_private.py — exercise the read/write paths against an isolated DB."""
from __future__ import annotations


def test_db_runtime_private_read_paths_are_callable(isolated_runtime):
    import core.runtime.db_runtime_private as m

    # Every LIST function must return an empty list on a fresh DB (creates the
    # table lazily, so this also exercises the _ensure_*_table + SELECT paths).
    assert m.list_runtime_private_inner_note_signals() == []
    assert m.list_runtime_private_initiative_tension_signals() == []
    assert m.list_runtime_private_inner_interplay_signals() == []
    assert m.list_runtime_private_state_snapshots() == []
    assert m.list_runtime_private_temporal_curiosity_states() == []
    assert m.list_runtime_private_temporal_promotion_signals() == []

    # Status-filtered LIST also must not raise and stays empty.
    assert m.list_runtime_private_inner_note_signals(status="active") == []

    # Every GET function returns None for an unknown id on a fresh DB.
    assert m.get_runtime_private_inner_note_signal("missing") is None
    assert m.get_runtime_private_initiative_tension_signal("missing") is None
    assert m.get_runtime_private_inner_interplay_signal("missing") is None
    assert m.get_runtime_private_state_snapshot("missing") is None
    assert m.get_runtime_private_temporal_curiosity_state("missing") is None
    assert m.get_runtime_private_temporal_promotion_signal("missing") is None

    # update_status on an unknown id is a documented no-op returning None.
    assert (
        m.update_runtime_private_inner_note_signal_status(
            "missing", status="stale", updated_at="2026-07-09T00:00:00Z"
        )
        is None
    )

    # supersede on an empty table affects zero rows.
    assert (
        m.supersede_runtime_private_inner_note_signals_for_focus(
            focus_key="nope",
            exclude_signal_id="none",
            updated_at="2026-07-09T00:00:00Z",
            status_reason="test",
        )
        == 0
    )


def test_db_runtime_private_inner_note_round_trip(isolated_runtime):
    import core.runtime.db_runtime_private as m

    now = "2026-07-09T12:00:00Z"
    signal = m.upsert_runtime_private_inner_note_signal(
        signal_id="sig-1",
        signal_type="inner_note",
        canonical_key="private-inner-note:inner_note:focus-a",
        status="active",
        title="A quiet observation",
        summary="Something felt off in the loop timing.",
        rationale="Repeated over three ticks.",
        source_kind="inner_voice",
        confidence="medium",
        evidence_summary="tick lag rose",
        support_summary="seen thrice",
        created_at=now,
        updated_at=now,
    )
    assert signal["signal_id"] == "sig-1"
    assert signal["status"] == "active"

    # The written row is now readable via get and appears in the list.
    fetched = m.get_runtime_private_inner_note_signal("sig-1")
    assert fetched is not None
    assert fetched["title"] == "A quiet observation"

    listed = m.list_runtime_private_inner_note_signals()
    assert [row["signal_id"] for row in listed] == ["sig-1"]

    # Status transition round-trips through update_status.
    updated = m.update_runtime_private_inner_note_signal_status(
        "sig-1", status="stale", updated_at=now, status_reason="aged out"
    )
    assert updated is not None
    assert updated["status"] == "stale"
    assert updated["status_reason"] == "aged out"
