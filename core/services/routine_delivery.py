"""Fenced delivery outbox for Routine results.

Delivery retries operate on an existing outbox row and never enqueue work.
This module has no session or notification-bridge dependency.
"""
from __future__ import annotations

from dataclasses import dataclass

from core.runtime import db_routines


class StaleDeliveryLease(RuntimeError):
    """A worker attempted to settle a delivery it no longer owns."""


@dataclass(frozen=True)
class DeliveryClaim:
    delivery_id: str
    run_id: str
    owner_user_id: str
    channel: str
    status: str
    retry_count: int
    lease_generation: int


@dataclass(frozen=True)
class DeliveryView:
    delivery_id: str
    run_id: str
    owner_user_id: str
    channel: str
    status: str
    retry_count: int
    next_attempt_at: str | None
    lease_generation: int


class _RepositoryView:
    @staticmethod
    def count_runs(routine_id: str) -> int:
        return db_routines.count_runs(routine_id)


def _claim(row: dict) -> DeliveryClaim:
    return DeliveryClaim(
        delivery_id=str(row["delivery_id"]),
        run_id=str(row["run_id"]),
        owner_user_id=str(row["owner_user_id"]),
        channel=str(row["channel"]),
        status=str(row["status"]),
        retry_count=int(row["retry_count"]),
        lease_generation=int(row["lease_generation"]),
    )


def _view(row: dict) -> DeliveryView:
    return DeliveryView(
        delivery_id=str(row["delivery_id"]),
        run_id=str(row["run_id"]),
        owner_user_id=str(row["owner_user_id"]),
        channel=str(row["channel"]),
        status=str(row["status"]),
        retry_count=int(row["retry_count"]),
        next_attempt_at=row.get("next_attempt_at"),
        lease_generation=int(row["lease_generation"]),
    )


class RoutineDeliveryService:
    def __init__(self):
        self.repository = _RepositoryView()

    def claim_for_run(self, run_id: str, holder: str) -> DeliveryClaim | None:
        row = db_routines.claim_delivery_for_run(run_id, holder=holder)
        return None if row is None else _claim(row)

    def settle(
        self, delivery_id: str, *, holder: str, outcome: str,
        next_attempt_at: str | None = None, receipt: bytes | None = None,
    ) -> DeliveryView:
        try:
            row = db_routines.settle_delivery(
                delivery_id,
                holder=holder,
                outcome=outcome,
                next_attempt_at=next_attempt_at,
                receipt=receipt,
            )
        except ValueError as exc:
            if "stale delivery lease" in str(exc):
                raise StaleDeliveryLease("delivery lease is no longer current") from exc
            raise
        return _view(row)

    def record_terminal_failure(self, *, run_id: str) -> None:
        """Record no execution failure state; delivery owns its retry budget."""
        _ = run_id
