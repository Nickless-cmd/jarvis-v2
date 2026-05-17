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
    "signal_surface_gc": timedelta(hours=1),   # hourly trim of stale/old signal surfaces
    "decision_review": timedelta(hours=24),    # daily LLM-led self-review of active decisions
}


def _extract_last_time(item: dict[str, Any]) -> datetime | None:
    """Pick the most relevant timestamp from a job record."""
    for key in ("completed_at", "started_at", "enqueued_at"):
        v = item.get(key)
        if not v:
            continue
        try:
            return datetime.fromisoformat(str(v))
        except ValueError:
            continue
    return None


def check_and_enqueue_due_periodic_jobs() -> dict[str, Any]:
    """Idempotent — enqueue any periodic jobs whose cadence is exceeded.

    Returns {"enqueued": [job_types]}. Empty list = nothing was due.
    Skips a job_type if there's already a pending one (avoid pile-up).

    2026-05-17 perf fix: tidligere blev jobs_engine._load() (16 MB JSON-parse,
    ~235 ms) kaldt op til 36× pr. 30s heartbeat-poll — 2× pr. job_type via
    _has_pending + _last_job_time. py-spy viste 76-79% inclusive CPU på den
    path. Daemons "kogede" fordi scheduleren ikke nåede at enqueue dem
    rettidigt. Fix: ÉN list_jobs() øverst, in-memory filtering bagefter.
    """
    enqueued: list[str] = []
    skipped: list[str] = []
    now = datetime.now(UTC)

    try:
        from core.services.jobs_engine import enqueue_job, list_jobs
    except Exception as exc:
        logger.debug("periodic_jobs_scheduler: jobs_engine import failed: %s", exc)
        return {"enqueued": [], "skipped": [], "error": str(exc)}

    # Load ONE gang — herfra arbejder vi på in-memory data
    try:
        all_items = list_jobs(limit=200)
    except Exception as exc:
        logger.warning("periodic_jobs_scheduler: list_jobs failed: %s", exc)
        all_items = []

    # Byg pending-set + last-time map i én pass
    pending_types: set[str] = set()
    last_times: dict[str, datetime] = {}
    for item in all_items:
        jt = item.get("job_type")
        if not jt:
            continue
        if item.get("status") == "pending":
            pending_types.add(jt)
        ts = _extract_last_time(item)
        if ts is not None:
            existing = last_times.get(jt)
            if existing is None or ts > existing:
                last_times[jt] = ts

    for job_type, cadence in _SCHEDULE.items():
        if job_type in pending_types:
            skipped.append(f"{job_type} (already pending)")
            continue
        last = last_times.get(job_type)
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
