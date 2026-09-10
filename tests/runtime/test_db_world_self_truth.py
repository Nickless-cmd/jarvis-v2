from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.runtime import db_core
from core.runtime.db_runtime_executive_signals import (
    list_runtime_world_model_signals,
    update_runtime_world_model_signal_status,
    upsert_runtime_world_model_signal,
)
from core.runtime.db_world_self_truth import quarantine_legacy_world_topics


@pytest.fixture
def truth_db(monkeypatch: pytest.MonkeyPatch, tmp_path):
    db_core.close_pooled_connection()
    monkeypatch.setattr(db_core, "DB_PATH", tmp_path / "truth.db")
    yield
    db_core.close_pooled_connection()


def _legacy_signal(index: int, *, signal_type: str = "conversational_context") -> None:
    now = datetime.now(UTC).isoformat()
    upsert_runtime_world_model_signal(
        signal_id=f"legacy-{index}",
        signal_type=signal_type,
        canonical_key=f"legacy:{index}",
        status="active",
        title=f"Legacy {index}",
        summary="historical evidence",
        rationale="test fixture",
        source_kind="visible_run",
        confidence="medium",
        evidence_summary="fixture",
        support_summary="fixture",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def test_quarantine_legacy_topics_is_bounded_and_restart_safe(truth_db):
    for index in range(3):
        _legacy_signal(index)
    _legacy_signal(99, signal_type="workspace-scope-assumption")

    first = quarantine_legacy_world_topics(batch_size=2)
    statuses = {
        item["signal_id"]: item["status"]
        for item in list_runtime_world_model_signals(limit=10)
    }

    assert first["quarantined"] == 2
    assert sum(status == "legacy_quarantined" for status in statuses.values()) == 2
    assert statuses["legacy-99"] == "active"

    second = quarantine_legacy_world_topics(batch_size=2)
    third = quarantine_legacy_world_topics(batch_size=2)

    assert second["quarantined"] == 1
    assert second["completed"] == 1
    assert third["quarantined"] == 0
    assert third["completed"] == 1


def test_quarantine_reopens_for_legacy_rows_inserted_after_completion(truth_db):
    _legacy_signal(1)
    assert quarantine_legacy_world_topics(batch_size=1)["completed"] == 1

    _legacy_signal(2)
    reopened = quarantine_legacy_world_topics(batch_size=1)
    statuses = {
        item["signal_id"]: item["status"]
        for item in list_runtime_world_model_signals(limit=10)
    }

    assert reopened["quarantined"] == 1
    assert statuses["legacy-2"] == "legacy_quarantined"


def test_quarantine_rescans_eligible_rows_below_cursor(truth_db):
    _legacy_signal(1)
    update_runtime_world_model_signal_status(
        "legacy-1",
        status="legacy_quarantined",
        updated_at=datetime.now(UTC).isoformat(),
    )
    _legacy_signal(2)
    assert quarantine_legacy_world_topics(batch_size=1)["completed"] == 1
    update_runtime_world_model_signal_status(
        "legacy-1",
        status="active",
        updated_at=datetime.now(UTC).isoformat(),
    )

    rescanned = quarantine_legacy_world_topics(batch_size=1)
    statuses = {
        item["signal_id"]: item["status"]
        for item in list_runtime_world_model_signals(limit=10)
    }

    assert rescanned["quarantined"] == 1
    assert statuses["legacy-1"] == "legacy_quarantined"
