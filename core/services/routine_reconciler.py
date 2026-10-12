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
        return len(outcomes)

    def sweep_retention(self, now: datetime | None = None) -> dict[str, int]:
        return RoutineService().archive_stopped_before(now=now or datetime.now(UTC))
