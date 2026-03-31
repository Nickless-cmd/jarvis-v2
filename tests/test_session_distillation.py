"""Tests for the session distillation service — private brain persistence,
workspace memory classification, and distillation record creation."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from core.runtime.db import (
    insert_private_brain_record,
    list_private_brain_records,
    get_private_brain_record,
    insert_session_distillation_record,
    list_session_distillation_records,
    get_session_distillation_record,
)


@pytest.fixture()
def _ensure_tables():
    """Touch the DB so tables exist."""
    list_private_brain_records(limit=1)
    list_session_distillation_records(limit=1)


# ---------------------------------------------------------------------------
# Private brain record persistence
# ---------------------------------------------------------------------------


def test_private_brain_record_insert_and_retrieve(_ensure_tables) -> None:
    """Insert a private brain record and retrieve it by ID."""
    now = datetime.now(UTC).isoformat()
    record_id = f"pb-test-{uuid4().hex[:8]}"
    record = insert_private_brain_record(
        record_id=record_id,
        record_type="inner-note-carry",
        layer="private_brain",
        session_id="test-session",
        run_id="test-run",
        focus="Test focus",
        summary="A private inner note about something observed.",
        detail="Some detail text.",
        source_signals="inner-note:abc123",
        confidence="high",
        created_at=now,
    )

    assert record["record_id"] == record_id
    assert record["layer"] == "private_brain"
    assert record["record_type"] == "inner-note-carry"
    assert record["summary"] == "A private inner note about something observed."
    assert record["status"] == "active"

    retrieved = get_private_brain_record(record_id)
    assert retrieved is not None
    assert retrieved["record_id"] == record_id


def test_private_brain_records_are_append_only(_ensure_tables) -> None:
    """Inserting with the same record_id should not overwrite (OR IGNORE)."""
    now = datetime.now(UTC).isoformat()
    record_id = f"pb-dup-{uuid4().hex[:8]}"
    insert_private_brain_record(
        record_id=record_id,
        record_type="self-model-carry",
        layer="private_brain",
        session_id="s1",
        run_id="r1",
        focus="Focus A",
        summary="First version.",
        detail="",
        source_signals="",
        confidence="medium",
        created_at=now,
    )
    insert_private_brain_record(
        record_id=record_id,
        record_type="self-model-carry",
        layer="private_brain",
        session_id="s2",
        run_id="r2",
        focus="Focus B",
        summary="Second version should be ignored.",
        detail="",
        source_signals="",
        confidence="high",
        created_at=now,
    )

    record = get_private_brain_record(record_id)
    assert record is not None
    # First version should persist (INSERT OR IGNORE)
    assert record["summary"] == "First version."
    assert record["session_id"] == "s1"


def test_list_private_brain_records_filters_by_session(_ensure_tables) -> None:
    """list_private_brain_records can filter by session_id."""
    now = datetime.now(UTC).isoformat()
    session_a = f"session-a-{uuid4().hex[:6]}"
    session_b = f"session-b-{uuid4().hex[:6]}"

    insert_private_brain_record(
        record_id=f"pb-a-{uuid4().hex[:8]}",
        record_type="diary-carry",
        layer="private_brain",
        session_id=session_a,
        run_id="r1",
        focus="A",
        summary="Session A record.",
        detail="",
        source_signals="",
        confidence="medium",
        created_at=now,
    )
    insert_private_brain_record(
        record_id=f"pb-b-{uuid4().hex[:8]}",
        record_type="diary-carry",
        layer="private_brain",
        session_id=session_b,
        run_id="r2",
        focus="B",
        summary="Session B record.",
        detail="",
        source_signals="",
        confidence="medium",
        created_at=now,
    )

    records_a = list_private_brain_records(session_id=session_a, limit=10)
    records_b = list_private_brain_records(session_id=session_b, limit=10)

    assert all(r["session_id"] == session_a for r in records_a)
    assert all(r["session_id"] == session_b for r in records_b)


# ---------------------------------------------------------------------------
# Session distillation records
# ---------------------------------------------------------------------------


def test_session_distillation_record_insert_and_retrieve(_ensure_tables) -> None:
    """Insert a distillation record and retrieve it."""
    now = datetime.now(UTC).isoformat()
    distill_id = f"distill-test-{uuid4().hex[:8]}"

    record = insert_session_distillation_record(
        distillation_id=distill_id,
        session_id="test-session",
        run_id="test-run",
        private_brain_count=3,
        workspace_memory_count=1,
        discard_count=2,
        summary="Session distillation: 3 private, 1 workspace, 2 discarded.",
        detail="inner-note-inactive:x | diary-inactive:y",
        created_at=now,
    )

    assert record["distillation_id"] == distill_id
    assert record["private_brain_count"] == 3
    assert record["workspace_memory_count"] == 1
    assert record["discard_count"] == 2

    retrieved = get_session_distillation_record(distill_id)
    assert retrieved is not None
    assert retrieved["summary"] == record["summary"]


# ---------------------------------------------------------------------------
# Integration: distill_session_carry
# ---------------------------------------------------------------------------


def test_distill_session_carry_produces_records_from_runtime_evidence() -> None:
    """distill_session_carry should create private brain records from
    active inner notes and other private signals, and produce a
    distillation record."""
    from apps.api.jarvis_api.services.session_distillation import (
        distill_session_carry,
        build_private_brain_surface,
        build_session_distillation_surface,
    )

    session_id = f"distill-session-{uuid4().hex[:8]}"
    run_id = f"distill-run-{uuid4().hex[:8]}"

    # Seed some active inner notes so distillation finds them
    from core.runtime.db import upsert_runtime_private_inner_note_signal
    now = datetime.now(UTC).isoformat()
    upsert_runtime_private_inner_note_signal(
        signal_id=f"inner-{uuid4().hex[:8]}",
        signal_type="inner-note",
        canonical_key=f"inner-note:test-carry:{uuid4().hex[:6]}",
        status="active",
        title="Test inner note",
        summary="I noticed something interesting about the user's approach.",
        rationale="This is a private observation worth carrying.",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="inner note evidence",
        support_summary="inner note support",
        status_reason="Test",
        run_id=run_id,
        session_id=session_id,
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )

    result = distill_session_carry(
        session_id=session_id,
        run_id=run_id,
    )

    assert result["private_brain_count"] >= 1
    assert result["distillation_id"]

    # Verify surfaces reflect the new records
    brain_surface = build_private_brain_surface()
    assert brain_surface["active"] is True
    assert brain_surface["total_records"] >= 1

    distill_surface = build_session_distillation_surface()
    assert distill_surface["active"] is True
    assert distill_surface["total_records"] >= 1


def test_distill_session_carry_discards_inactive_signals() -> None:
    """Inactive signals should be classified as discard, not persisted
    to private brain."""
    from apps.api.jarvis_api.services.session_distillation import (
        distill_session_carry,
    )
    from core.runtime.db import upsert_runtime_private_inner_note_signal

    session_id = f"distill-inactive-{uuid4().hex[:8]}"
    run_id = f"distill-inactive-run-{uuid4().hex[:8]}"
    now = datetime.now(UTC).isoformat()

    upsert_runtime_private_inner_note_signal(
        signal_id=f"inner-stale-{uuid4().hex[:8]}",
        signal_type="inner-note",
        canonical_key=f"inner-note:stale:{uuid4().hex[:6]}",
        status="stale",
        title="Stale inner note",
        summary="This is stale and should be discarded.",
        rationale="Test",
        source_kind="runtime-derived-support",
        confidence="low",
        evidence_summary="",
        support_summary="",
        status_reason="Stale test",
        run_id=run_id,
        session_id=session_id,
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )

    result = distill_session_carry(
        session_id=session_id,
        run_id=run_id,
    )

    # Stale signal should count as discard
    assert result["discard_count"] >= 1
    assert result["distillation_id"]
