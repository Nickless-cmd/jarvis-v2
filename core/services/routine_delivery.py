"""Fenced delivery outbox for Routine results.

Delivery retries operate on an existing outbox row and never enqueue work.
This module has no session or notification-bridge dependency: result text is
never copied into a chat or a shared inbox.

It DOES wake the owner on their own device (25/10-2026). ``desk`` used to mean
only «the result can be fetched from the Routine API» — so a routine could be
``delivered`` without a single human ever being told. A push carries the
routine's name, not its result: the result still lives only on the Routine
surface.
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass

from core.runtime import db_routines

logger = logging.getLogger(__name__)


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


def _push_owner(claim: DeliveryClaim) -> None:
    """Giv ejeren et push naar resultatet ligger klar paa rutinens egen flade.

    ``desk``-kanalen betyder «resultatet kan hentes via Routine-API'et» — ikke
    at nogen fik besked. Maalt 25/10-2026: Michelles rutine koerte og blev
    ``delivered``, men hendes telefon fik intet, fordi der slet ikke fandtes en
    kobling mellem rutine-delivery og push-stakken.

    Noeglen er ikke den samme i de to lag: rutinen ejes af det KANONISKE
    ``user_id``, mens web-push-abonnementet ligger under Discord-id'et. Uden
    oversaettelsen ville pushen gaa til nul abonnementer og fejle tavst — det
    er praecis den maalefejl der kostede en hel eftermiddag samme dag.

    Self-safe: en fejl her maa aldrig goere en leveret rutine til en fejlet.
    """
    try:
        run = db_routines.get_run(claim.run_id)
        if not run:
            return
        routine_id = str(run.get("routine_id") or "")
        if not routine_id:
            return
        routine = db_routines.get_routine(
            routine_id, decrypt_for=claim.owner_user_id,
        )
        if not routine:
            return
        if str(routine.get("access_scope") or "") == "system_owner":
            # Systemrutiner (heartbeat/dream) er rammer, ikke opgaver. De skal
            # ikke kunne vaekke en telefon kl. 03.
            return
        policy = dict(routine.get("delivery_policy") or {})
        if policy.get("push") is False:
            return
        from core.identity import user_db

        account = user_db.get_user(claim.owner_user_id) or {}
        discord_id = str(account.get("discord_id") or "").strip()
        if not discord_id:
            return
        from core.services.push_dispatcher import _push_to_web

        navn = str(routine.get("name") or "Rutine")
        _push_to_web(discord_id, {
            "title": navn,
            "body": "Dit rutine-resultat er klar i appen.",
            "run_id": claim.run_id,
            "kind": "routine",
        })
    except Exception as exc:  # self-safe: push maa ikke vaelte en levering
        logger.warning(
            "routine push fejlede for run %s: %s", claim.run_id, type(exc).__name__,
        )


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
        if supported:
            _push_owner(claim)
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
