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


_CUTOVER_TRUE: frozenset[str] = frozenset({"1", "true", "yes", "on"})


def _cutover_tokens() -> set[str]:
    """Env-værdien som mængde: globale sandheds-ord ELLER ``kind:id``-par.

    Bjørn 19/10-2026: «Tænd Routine-cutover på én enkelt opgave som prøve
    først». Det kræver en forgrening der er smallere end alt-eller-intet —
    uden den ville en prøve på én opgave flytte alle 13 levende recurrings
    plus alle scheduled jobs på én gang.
    """
    raw = str(os.environ.get("JARVIS_ROUTINES_CUTOVER") or "").strip().lower()
    if not raw:
        return set()
    return {part.strip() for part in raw.split(",") if part.strip()}


def routine_cutover_enabled() -> bool:
    """GLOBAL cutover — sand kun når env siger det uden at pege på enkeltkilder.

    Bevarer de seks eksisterende kaldesteder (scheduled, heartbeat) urørt:
    sætter man kun ``recurring:rec-x``, er den globale vej fortsat slukket.
    """
    return bool(_cutover_tokens() & _CUTOVER_TRUE)


def cutover_allows(source_kind: str, source_id: str) -> bool:
    """Må netop DENNE kilde gå Routine-vejen?

    ``1/true/yes/on`` = alle kilder. ``recurring:rec-x,scheduled:y`` = kun de
    nævnte. Ukendt/tom = nej (legacy-vejen, som i dag).
    """
    tokens = _cutover_tokens()
    if not tokens:
        return False
    if tokens & _CUTOVER_TRUE:
        return True
    key = f"{source_kind}:{str(source_id or '').strip()}".lower()
    return key in tokens


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
    if cutover_allows("recurring", source_id):
        return (adapters or RoutineTriggerAdapters()).enqueue_recurring(
            source_id, occurrence_id=occurrence_id,
        )
    legacy()
    return None


def dispatch_scheduled(
    source_id: str, *, legacy: Callable[[], object],
    adapters: RoutineTriggerAdapters | None = None,
) -> TriggerResult | None:
    if cutover_allows("scheduled", source_id):
        return (adapters or RoutineTriggerAdapters()).enqueue_scheduled(source_id)
    legacy()
    return None


def dispatch_system(
    producer: str, source_id: str, *, trigger_inputs: Mapping[str, object],
    legacy: Callable[[], object], adapters: RoutineTriggerAdapters | None = None,
) -> TriggerResult | None:
    # Systemproducenter vælges pr. stabil producent, ikke pr. flygtigt
    # occurrence-id. ``system:heartbeat`` kan derfor piloteres uden samtidig
    # at flytte dream, wakeup eller alle scheduled jobs.
    if cutover_allows("system", producer):
        return (adapters or RoutineTriggerAdapters()).enqueue_system(
            producer, source_id, trigger_inputs=trigger_inputs,
        )
    legacy()
    return None


def dispatch_heartbeat_initiative(
    *, focus: str, initiative_id: str, session_id: str = "",
) -> TriggerResult | None:
    """Extracted heartbeat execution boundary for the oversized runtime module.

    ``session_id`` (14/10-2026): initiativet kan bære den samtale det kom fra
    (fx et scheduled-job der lagde det i køen — se ``initiative_queue``). Tom =
    systemets eget initiativ; der findes ingen samtale at vende tilbage til.
    """
    def _legacy() -> None:
        from core.services.visible_runs import start_autonomous_run

        start_autonomous_run(
            focus, session_id=str(session_id or "") or None, origin="heartbeat",
        )

    return dispatch_system(
        "heartbeat", initiative_id,
        trigger_inputs={"focus": focus}, legacy=_legacy,
    )
