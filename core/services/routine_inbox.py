"""User-controlled projections of Routine lifecycle events into durable inbox."""
from __future__ import annotations

from typing import Mapping

from core.runtime import db_routines
from core.services.routine_authorization import Action, require_authorized
from core.services.routine_types import RoutinePrincipal


class RoutineInboxService:
    def set_user_defaults(
        self, principal: RoutinePrincipal, policy: Mapping[str, object]
    ) -> dict[str, object]:
        return db_routines.set_inbox_preference(
            principal.canonical_user_id, policy=dict(policy)
        )

    def set_override(
        self, principal: RoutinePrincipal, routine_id: str,
        override: Mapping[str, object],
    ) -> dict[str, object]:
        row = db_routines.get_routine(routine_id)
        if row is None:
            raise KeyError(routine_id)
        require_authorized(principal, Action.MUTATE, row)
        current = self.effective_policy(principal, routine_id)
        merged = {**current, **dict(override)}
        return db_routines.set_inbox_preference(
            principal.canonical_user_id, routine_id=routine_id, policy=merged
        )

    def effective_policy(
        self, principal: RoutinePrincipal, routine_id: str
    ) -> dict[str, object]:
        row = db_routines.get_routine(routine_id)
        if row is None:
            raise KeyError(routine_id)
        require_authorized(principal, Action.READ_METADATA, row)
        specific = db_routines.get_inbox_preference(
            principal.canonical_user_id, routine_id=routine_id
        )
        if specific:
            return specific
        return db_routines.get_inbox_preference(principal.canonical_user_id)

    def project_event_to_inbox(self, event: Mapping[str, object]) -> dict:
        owner = str(event.get("owner_user_id") or "").strip()
        routine_id = str(event.get("routine_id") or "").strip()
        event_id = str(event.get("event_id") or "").strip()
        event_type = str(event.get("event_type") or "").strip().lower()
        if not owner or not routine_id or not event_id or not event_type:
            return {"status": "invalid"}
        policy = db_routines.get_inbox_preference(owner, routine_id=routine_id)
        if not bool(policy.get(event_type, False)):
            return {"status": "suppressed"}
        from core.services.inbox_state import registrer_kilde

        return registrer_kilde(
            bruger_id=owner,
            kildetype="routine_event",
            kilde_id=event_id,
            kilde_ejer="jarvis",
            beskrivelse=f"Routinehændelse: {event_type}",
        )


def project_event_to_inbox(event: Mapping[str, object]) -> dict:
    return RoutineInboxService().project_event_to_inbox(event)
