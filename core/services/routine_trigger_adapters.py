"""Single-path adapters from legacy producers to isolated Routine runs."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Mapping

from core.runtime import db_routines
from core.services.routine_service import RunView, RoutineService
from core.services.routine_types import RoutinePrincipal


SYSTEM_PRODUCERS = frozenset(
    {"heartbeat", "heartbeat_runtime", "dream", "council", "wakeup"}
)


class UnmigratedRoutineSource(RuntimeError):
    """The cutover is enabled but this legacy source has no verified Routine."""


class UnknownSystemProducer(ValueError):
    """A producer not present in the explicit system-only registry was requested."""


@dataclass(frozen=True)
class TriggerResult:
    count: int
    run: RunView


def routine_cutover_enabled() -> bool:
    return str(os.environ.get("JARVIS_ROUTINES_CUTOVER") or "").strip().lower() in {
        "1", "true", "yes", "on",
    }


def _runner_principal() -> RoutinePrincipal:
    return RoutinePrincipal("routine-trigger-adapter", role="system", actor_kind="system")


class RoutineTriggerAdapters:
    def __init__(self, *, system_owner_user_id: str | None = None):
        self.system_owner_user_id = str(system_owner_user_id or "").strip()
        self.service = RoutineService(_runner_principal())

    def _enqueue(
        self, routine_id: str, *, trigger_key: str,
        execution_context: Mapping[str, object] | None = None,
    ) -> TriggerResult:
        existed = db_routines.run_exists_for_trigger(
            routine_id=routine_id, idempotency_key=trigger_key,
        )
        run = self.service.enqueue_run(
            routine_id, trigger_key=trigger_key, execution_context=execution_context,
        )
        return TriggerResult(count=0 if existed else 1, run=run)

    def _linked(self, source_kind: str, source_id: str) -> str:
        routine_id = db_routines.get_legacy_routine_id(
            source_kind=source_kind, source_id=source_id,
        )
        if not routine_id:
            raise UnmigratedRoutineSource(
                f"{source_kind} source has no verified Routine migration link"
            )
        return routine_id

    def enqueue_scheduled(self, source_id: str) -> TriggerResult:
        return self._enqueue(
            self._linked("scheduled", source_id),
            trigger_key=f"scheduled:{source_id}",
        )

    def enqueue_recurring(
        self, source_id: str, *, occurrence_id: str | None = None,
    ) -> TriggerResult:
        return self._enqueue(
            self._linked("recurring", source_id),
            trigger_key=f"recurring:{occurrence_id or source_id}",
        )

    def _owner(self) -> str:
        if self.system_owner_user_id:
            return self.system_owner_user_id
        from core.identity.owner_resolver import owner_user_id
        from core.services.routine_migration import resolve_canonical_identity

        owner = resolve_canonical_identity(owner_user_id())
        if not owner:
            raise UnmigratedRoutineSource("system owner has no canonical identity link")
        return owner

    def _system_routine(self, producer: str) -> str:
        if producer not in SYSTEM_PRODUCERS:
            raise UnknownSystemProducer(producer)
        routine_id = f"routine_system_{producer}"
        if db_routines.get_routine(routine_id) is None:
            db_routines.create_routine(
                routine_id=routine_id,
                owner_user_id=self._owner(),
                access_scope="system_owner",
                created_by="system",
                status="active",
                name=f"System · {producer}",
                instruction=b"Execute the bounded system task in trigger inputs.",
                capability_scope="system",
                trigger_kind="system",
                trigger_config={"producer": producer},
                permission_policy={},
                delivery_policy={"channel": "desk"},
                inbox_policy={"failed": True},
                retention_policy={"archive_stopped_days": 30},
                failure_policy={"consecutive_failures": 3},
            )
        return routine_id

    def enqueue_system(
        self, producer: str, source_id: str,
        *, trigger_inputs: Mapping[str, object] | None = None,
    ) -> TriggerResult:
        return self._enqueue(
            self._system_routine(producer),
            trigger_key=f"{producer}:{source_id}",
            execution_context={"trigger_inputs": dict(trigger_inputs or {})},
        )

    def fire(self, producer: str, *, source_id: str) -> TriggerResult:
        if producer == "scheduled":
            return self.enqueue_scheduled(source_id)
        if producer == "recurring":
            return self.enqueue_recurring(source_id)
        return self.enqueue_system(producer, source_id)


def enqueue_scheduled(source_id: str) -> TriggerResult:
    return RoutineTriggerAdapters().enqueue_scheduled(source_id)


def enqueue_recurring(
    source_id: str, *, occurrence_id: str | None = None,
) -> TriggerResult:
    return RoutineTriggerAdapters().enqueue_recurring(
        source_id, occurrence_id=occurrence_id,
    )


def enqueue_system(
    producer: str, source_id: str,
    *, trigger_inputs: Mapping[str, object] | None = None,
) -> TriggerResult:
    return RoutineTriggerAdapters().enqueue_system(
        producer, source_id, trigger_inputs=trigger_inputs,
    )


def dispatch_recurring(
    source_id: str, *, legacy: Callable[[], object],
    adapters: RoutineTriggerAdapters | None = None,
    occurrence_id: str | None = None,
) -> TriggerResult | None:
    if routine_cutover_enabled():
        return (adapters or RoutineTriggerAdapters()).enqueue_recurring(
            source_id, occurrence_id=occurrence_id,
        )
    legacy()
    return None


def dispatch_scheduled(
    source_id: str, *, legacy: Callable[[], object],
    adapters: RoutineTriggerAdapters | None = None,
) -> TriggerResult | None:
    if routine_cutover_enabled():
        return (adapters or RoutineTriggerAdapters()).enqueue_scheduled(source_id)
    legacy()
    return None


def dispatch_system(
    producer: str, source_id: str, *, trigger_inputs: Mapping[str, object],
    legacy: Callable[[], object], adapters: RoutineTriggerAdapters | None = None,
) -> TriggerResult | None:
    if routine_cutover_enabled():
        return (adapters or RoutineTriggerAdapters()).enqueue_system(
            producer, source_id, trigger_inputs=trigger_inputs,
        )
    legacy()
    return None


def dispatch_heartbeat_initiative(
    *, focus: str, initiative_id: str,
) -> TriggerResult | None:
    """Extracted heartbeat execution boundary for the oversized runtime module."""
    def _legacy() -> None:
        from core.services.visible_runs import start_autonomous_run

        start_autonomous_run(focus, origin="heartbeat")

    return dispatch_system(
        "heartbeat", initiative_id,
        trigger_inputs={"focus": focus}, legacy=_legacy,
    )
