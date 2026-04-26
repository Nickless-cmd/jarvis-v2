"""Unit tests for periodic_jobs_scheduler — chronicle/manifest cadence."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from core.services.periodic_jobs_scheduler import (
    check_and_enqueue_due_periodic_jobs,
)


def _job(job_type: str, hours_ago: float, status: str = "completed"):
    ts = (datetime.now(UTC) - timedelta(hours=hours_ago)).isoformat()
    return {
        "job_type": job_type,
        "status": status,
        "completed_at": ts if status == "completed" else None,
        "enqueued_at": ts,
    }


def test_no_history_enqueues_all():
    enq_calls = []
    def fake_list(**kw):
        return []
    def fake_enqueue(**kw):
        enq_calls.append(kw["job_type"])
        return f"job-{kw['job_type']}-x"
    with patch("core.services.jobs_engine.list_jobs", side_effect=fake_list), \
         patch("core.services.jobs_engine.enqueue_job", side_effect=fake_enqueue):
        result = check_and_enqueue_due_periodic_jobs()
    assert "chronicle_refresh" in result["enqueued"]
    assert "weekly_manifest_refresh" in result["enqueued"]


def test_recent_chronicle_skipped():
    def fake_list(status=None, limit=50):
        return [_job("chronicle_refresh", hours_ago=2)]
    enq_calls = []
    def fake_enqueue(**kw):
        enq_calls.append(kw["job_type"])
        return "job-x"
    with patch("core.services.jobs_engine.list_jobs", side_effect=fake_list), \
         patch("core.services.jobs_engine.enqueue_job", side_effect=fake_enqueue):
        result = check_and_enqueue_due_periodic_jobs()
    assert "chronicle_refresh" not in result["enqueued"]
    assert "weekly_manifest_refresh" in result["enqueued"]


def test_pending_chronicle_skipped():
    def fake_list(status=None, limit=50):
        if status == "pending":
            return [_job("chronicle_refresh", hours_ago=0.1, status="pending")]
        return []
    enq_calls = []
    def fake_enqueue(**kw):
        enq_calls.append(kw["job_type"])
        return "job-x"
    with patch("core.services.jobs_engine.list_jobs", side_effect=fake_list), \
         patch("core.services.jobs_engine.enqueue_job", side_effect=fake_enqueue):
        result = check_and_enqueue_due_periodic_jobs()
    assert "chronicle_refresh" not in result["enqueued"]
    assert any("chronicle_refresh" in s for s in result["skipped"])


def test_old_chronicle_enqueued():
    def fake_list(status=None, limit=50):
        if status == "pending":
            return []
        return [_job("chronicle_refresh", hours_ago=48)]
    enq_calls = []
    def fake_enqueue(**kw):
        enq_calls.append(kw["job_type"])
        return "job-x"
    with patch("core.services.jobs_engine.list_jobs", side_effect=fake_list), \
         patch("core.services.jobs_engine.enqueue_job", side_effect=fake_enqueue):
        result = check_and_enqueue_due_periodic_jobs()
    assert "chronicle_refresh" in result["enqueued"]


def test_recent_weekly_manifest_skipped():
    def fake_list(status=None, limit=50):
        return [_job("weekly_manifest_refresh", hours_ago=24)]
    with patch("core.services.jobs_engine.list_jobs", side_effect=fake_list), \
         patch("core.services.jobs_engine.enqueue_job", return_value="job-x") as enq:
        result = check_and_enqueue_due_periodic_jobs()
    assert "weekly_manifest_refresh" not in result["enqueued"]
