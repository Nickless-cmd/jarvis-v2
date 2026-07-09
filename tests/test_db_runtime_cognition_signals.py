"""Smoke tests for db_runtime_cognition_signals.py — exercise the read/write paths against an isolated DB."""
from __future__ import annotations


def test_db_runtime_cognition_signals_read_paths_are_callable(isolated_runtime):
    import core.runtime.db_runtime_cognition_signals as m

    # LIST functions on the fresh isolated DB must run against the schema and
    # return an empty list.
    assert m.list_runtime_reflective_critics() == []
    assert m.list_runtime_awareness_signals() == []
    assert m.list_runtime_reflection_signals() == []
    assert m.list_runtime_witness_signals() == []
    assert m.list_runtime_internal_opposition_signals() == []
    assert m.list_runtime_meaning_significance_signals() == []
    assert m.list_runtime_metabolism_state_signals() == []
    assert m.list_runtime_executive_contradiction_signals() == []

    # GET functions for missing ids must return None (not raise).
    assert m.get_runtime_reflective_critic("nope") is None
    assert m.get_runtime_awareness_signal("nope") is None
    assert m.get_runtime_reflection_signal("nope") is None
    assert m.get_runtime_witness_signal("nope") is None
    assert m.get_runtime_internal_opposition_signal("nope") is None
    assert m.get_runtime_meaning_significance_signal("nope") is None
    assert m.get_runtime_metabolism_state_signal("nope") is None
    assert m.get_runtime_executive_contradiction_signal("nope") is None

    # update-status on a missing id must return None (not raise).
    assert (
        m.update_runtime_reflection_signal_status(
            "nope", status="settled", updated_at="2026-01-01T00:00:00Z"
        )
        is None
    )

    # supersede on an empty table must run and report zero rows changed.
    assert (
        m.supersede_runtime_reflection_signals_for_domain(
            domain_key="dk",
            exclude_signal_id="x",
            updated_at="2026-01-01T00:00:00Z",
            status_reason="none",
        )
        == 0
    )


def test_reflective_critic_roundtrip(isolated_runtime):
    import core.runtime.db_runtime_cognition_signals as m

    created = m.upsert_runtime_reflective_critic(
        critic_id="critic-1",
        critic_type="drift",
        canonical_key="reflective-critic:drift:demo",
        status="active",
        title="Demo critic",
        summary="A summary",
        rationale="Because reasons",
        source_kind="observation",
        confidence="medium",
        evidence_summary="evidence",
        support_summary="support",
        support_count=1,
        session_count=1,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    assert created["critic_id"] == "critic-1"
    assert created["was_created"] is True

    fetched = m.get_runtime_reflective_critic("critic-1")
    assert fetched is not None
    assert fetched["title"] == "Demo critic"

    listed = m.list_runtime_reflective_critics()
    assert any(row["critic_id"] == "critic-1" for row in listed)


def test_reflection_signal_roundtrip(isolated_runtime):
    import core.runtime.db_runtime_cognition_signals as m

    m.upsert_runtime_reflection_signal(
        signal_id="refl-1",
        signal_type="pattern",
        canonical_key="reflection-signal:pattern:demo",
        status="active",
        title="Reflection",
        summary="sum",
        rationale="rat",
        source_kind="observation",
        confidence="low",
        evidence_summary="ev",
        support_summary="sup",
        support_count=1,
        session_count=1,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )

    fetched = m.get_runtime_reflection_signal("refl-1")
    assert fetched is not None
    assert fetched["signal_id"] == "refl-1"

    listed = m.list_runtime_reflection_signals()
    assert [row["signal_id"] for row in listed] == ["refl-1"]
