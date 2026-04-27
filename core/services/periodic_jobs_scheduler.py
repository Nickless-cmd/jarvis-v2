"""Periodic jobs scheduler — enqueues overdue background jobs.

Background: governance_bootstrap registers handlers (chronicle_refresh,
memory_decay_sweep, dream_distillation_sweep, weekly_manifest_refresh)
but historically nothing periodically *enqueued* them. The handlers
slept; chronicle stalled at 17. april (9 days idle); manifest never
got the weekly refresh that was always intended.

This module fixes that with a single idempotent function:
``check_and_enqueue_due_periodic_jobs``. It looks at the most recent
job of each scheduled type and enqueues a new one when the cadence
threshold is exceeded. Safe to call frequently — duplicate-suppressed
by both pending-job check and cadence threshold.

Hooked into ``poll_heartbeat_schedule`` so it runs naturally with the
~30s heartbeat poll. Cheap: a JSON load + a few timestamp comparisons.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


# job_type → cadence (timedelta between scheduled enqueues)
_SCHEDULE: dict[str, timedelta] = {
    "chronicle_refresh": timedelta(hours=24),
    "weekly_manifest_refresh": timedelta(days=7),
    "goal_synthesis": timedelta(days=7),
    "personality_snapshot": timedelta(hours=4),  # 6x/day for stable baseline
    "provider_health_check": timedelta(minutes=5),  # 12x/hour proactive ping
    "auto_improvement_proposals": timedelta(hours=24),  # daily check + propose
    "agent_observation_decay": timedelta(hours=24),  # daily stale-marking
    "wakeup_dispatch": timedelta(seconds=60),  # poll every 60s for fired wakeups
    # Identity formation infrastructure (2026-04-27)
    "crisis_scan": timedelta(hours=24),  # daily — find friction moments
    "identity_drift_proposal": timedelta(days=7),  # weekly — file proposal if drifted
    "monthly_arc": timedelta(days=28),  # monthly narrative
    "quarterly_arc": timedelta(days=91),  # quarterly arc
    "annual_arc": timedelta(days=365),  # annual transformation doc
    # System-intelligence growth (2026-04-27)
    "skill_distillation": timedelta(days=7),  # weekly principle extraction per role
    "arc_rule_extraction": timedelta(days=7),  # weekly rule extraction from new arcs
}


def _last_job_time(job_type: str) -> datetime | None:
    """Most recent enqueued/run job of this type, or None."""
    try:
        from core.services.jobs_engine import list_jobs
        items = list_jobs(limit=200)
    except Exception:
        return None
    matches = [i for i in items if i.get("job_type") == job_type]
    if not matches:
        return None
    times: list[datetime] = []
    for i in matches:
        for key in ("completed_at", "started_at", "enqueued_at"):
            v = i.get(key)
            if not v:
                continue
            try:
                times.append(datetime.fromisoformat(str(v)))
                break
            except ValueError:
                continue
    if not times:
        return None
    return max(times)


def _has_pending(job_type: str) -> bool:
    try:
        from core.services.jobs_engine import list_jobs
        pending = list_jobs(status="pending", limit=200)
    except Exception:
        return False
    return any(i.get("job_type") == job_type for i in pending)


def check_and_enqueue_due_periodic_jobs() -> dict[str, Any]:
    """Idempotent — enqueue any periodic jobs whose cadence is exceeded.

    Returns {"enqueued": [job_types]}. Empty list = nothing was due.
    Skips a job_type if there's already a pending one (avoid pile-up).
    """
    enqueued: list[str] = []
    skipped: list[str] = []
    now = datetime.now(UTC)

    try:
        from core.services.jobs_engine import enqueue_job
    except Exception as exc:
        logger.debug("periodic_jobs_scheduler: jobs_engine import failed: %s", exc)
        return {"enqueued": [], "skipped": [], "error": str(exc)}

    for job_type, cadence in _SCHEDULE.items():
        if _has_pending(job_type):
            skipped.append(f"{job_type} (already pending)")
            continue
        last = _last_job_time(job_type)
        if last is not None and (now - last) < cadence:
            continue
        try:
            jid = enqueue_job(
                job_type=job_type,
                payload={"reason": "periodic-scheduled", "cadence_hours": int(cadence.total_seconds() / 3600)},
                priority=8,  # low — these are background self-maintenance
                max_requests=1,
            )
            enqueued.append(job_type)
            logger.info("periodic_jobs_scheduler: enqueued %s (job %s, last seen %s)",
                        job_type, jid, last.isoformat() if last else "never")
        except Exception as exc:
            logger.warning("periodic_jobs_scheduler: enqueue %s failed: %s", job_type, exc)

    return {"enqueued": enqueued, "skipped": skipped}
