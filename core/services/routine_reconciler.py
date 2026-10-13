"""Crash reconciliation and retention sweeps for Routine work."""
from __future__ import annotations

from datetime import UTC, datetime

from core.runtime import db_routines
from core.services.routine_service import RoutineService


class RoutineReconciler:
    def __init__(self, *, repository=None):
        if repository is None:
            from core.services.routine_runner import RoutineRunRepository

            repository = RoutineRunRepository()
        self.repository = repository

    def reconcile_once(self, now: datetime | None = None) -> int:
        outcomes = db_routines.reconcile_expired_runs(now=now or datetime.now(UTC))
        for outcome in outcomes:
            if outcome.get("status") != "failed":
                continue
            run_id = str(outcome["run_id"])
            run = db_routines.get_run(run_id)
            if run is None:
                continue
            from core.services.routine_inbox import project_event_to_inbox
            from core.services.routine_runner import RoutineRunner, publish_operational_failure

            project_event_to_inbox({
                "owner_user_id": run["owner_user_id"],
                "routine_id": run["routine_id"],
                "event_id": f"{run_id}:failed",
                "event_type": "failed",
            })
            publish_operational_failure(
                routine_id=str(run["routine_id"]), run_id=run_id, component="tool",
            )
            RoutineRunner().record_execution_failure(
                str(run["routine_id"]), run_id=run_id,
            )
        return len(outcomes)

    def sweep_retention(self, now: datetime | None = None) -> dict[str, int]:
        return RoutineService().archive_stopped_before(now=now or datetime.now(UTC))
