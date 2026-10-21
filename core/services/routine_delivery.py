"""Fenced delivery outbox for Routine results.

Delivery retries operate on an existing outbox row and never enqueue work.
This module has no session or notification-bridge dependency.
"""
from __future__ import annotations

import json
import uuid
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
    def __init__(self, *, holder: str | None = None):
        self.repository = _RepositoryView()
        self.holder = holder or f"routine-delivery-{uuid.uuid4().hex}"

    def claim_for_run(self, run_id: str, holder: str) -> DeliveryClaim | None:
        row = db_routines.claim_delivery_for_run(run_id, holder=holder)
        return None if row is None else _claim(row)

    def claim_next(self) -> DeliveryClaim | None:
        row = db_routines.claim_next_delivery(holder=self.holder)
        return None if row is None else _claim(row)

    def deliver_next(self) -> DeliveryView | None:
        """Deliver one due item to its private Routine surface.

        ``desk`` and legacy ``auto`` mean that the encrypted run result is now
        available through the owner-authorized Routine API.  The receipt is a
        content-free pointer; result text is never copied to a chat/session or
        shared inbox. Unknown external channels fail closed until a dedicated
        owner-scoped adapter exists.
        """
        claim = self.claim_next()
        if claim is None:
            return None
        supported = claim.channel in {"desk", "auto"}
        outcome = "delivered" if supported else "failed"
        receipt = None
        if supported:
            receipt = json.dumps({
                "surface": "routine_run",
                "run_id": claim.run_id,
            }, sort_keys=True).encode("utf-8")
        view = self.settle(
            claim.delivery_id, holder=self.holder, outcome=outcome, receipt=receipt,
        )
        from core.services.routine_run_recorder import RoutineRunRecorder

        RoutineRunRecorder().append(
            claim.run_id,
            event_id=f"{claim.delivery_id}:{outcome}",
            kind="delivery_completed" if supported else "delivery_failed",
            payload={"channel": claim.channel, "status": outcome},
        )
        return view

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
        if outcome == "failed":
            run = db_routines.get_run(str(row["run_id"]))
            if run is not None:
                from core.services.routine_inbox import project_event_to_inbox

                project_event_to_inbox({
                    "owner_user_id": run["owner_user_id"],
                    "routine_id": run["routine_id"],
                    "event_id": f"{delivery_id}:delivery-failed",
                    "event_type": "delivery_failed",
                })
        return _view(row)

    def record_terminal_failure(self, *, run_id: str) -> None:
        """Record no execution failure state; delivery owns its retry budget."""
        _ = run_id
