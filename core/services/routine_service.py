"""Authorized lifecycle service for versioned Routine definitions and runs."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Mapping

from core.runtime import db_routines
from core.services.routine_authorization import (
    Action,
    RoutineForbidden,
    require_authorized,
)
from core.services.routine_types import (
    AccessScope,
    RoutineCreate,
    RoutinePatch,
    RoutinePrincipal,
)


class StaleRoutineVersion(RuntimeError):
    """An edit lost the optimistic version race."""


class InvalidRoutineTransition(RuntimeError):
    """A requested lifecycle transition is not valid from the current state."""


@dataclass(frozen=True)
class RoutineView:
    routine_id: str
    owner_user_id: str
    access_scope: str
    name: str
    instruction: bytes
    capability_scope: str
    trigger_kind: str
    trigger_config: dict[str, object]
    permission_policy: dict[str, object]
    delivery_policy: dict[str, object]
    inbox_policy: dict[str, object]
    retention_policy: dict[str, object]
    failure_policy: dict[str, object]
    jarvis_restart_allowed: bool
    status: str
    version: int
    created_at: str
    updated_at: str
    stopped_at: str | None = None
    archived_at: str | None = None

    @property
    def id(self) -> str:
        return self.routine_id


@dataclass(frozen=True)
class RunView:
    run_id: str
    routine_id: str
    owner_user_id: str
    access_scope: str
    routine_version: int
    status: str
    lease_holder: str | None
    lease_generation: int
    created_at: str
    definition_snapshot: dict[str, object] | None = None
    execution_context: dict[str, object] | None = None


_TRANSITIONS = {
    "pause": {"active": "paused"},
    "resume": {"paused": "active"},
    "archive": {"stopped": "archived", "paused": "archived"},
    "restore": {"archived": "stopped"},
    "restart": {"stopped": "active"},
}


def _routine_view(row: Mapping[str, Any]) -> RoutineView:
    return RoutineView(
        routine_id=str(row["routine_id"]),
        owner_user_id=str(row["owner_user_id"]),
        access_scope=str(row["access_scope"]),
        name=str(row.get("name") or ""),
        instruction=bytes(row.get("instruction") or b""),
        capability_scope=str(row["capability_scope"]),
        trigger_kind=str(row["trigger_kind"]),
        trigger_config=dict(row.get("trigger_config") or {}),
        permission_policy=dict(row.get("permission_policy") or {}),
        delivery_policy=dict(row.get("delivery_policy") or {}),
        inbox_policy=dict(row.get("inbox_policy") or {}),
        retention_policy=dict(row.get("retention_policy") or {}),
        failure_policy=dict(row.get("failure_policy") or {}),
        jarvis_restart_allowed=bool(row.get("jarvis_restart_allowed")),
        status=str(row["status"]),
        version=int(row["version"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        stopped_at=row.get("stopped_at"),
        archived_at=row.get("archived_at"),
    )


def _run_view(row: Mapping[str, Any]) -> RunView:
    return RunView(
        run_id=str(row["run_id"]),
        routine_id=str(row["routine_id"]),
        owner_user_id=str(row["owner_user_id"]),
        access_scope=str(row["access_scope"]),
        routine_version=int(row["routine_version"]),
        status=str(row["status"]),
        lease_holder=row.get("lease_holder"),
        lease_generation=int(row["lease_generation"]),
        created_at=str(row["created_at"]),
        definition_snapshot=row.get("definition_snapshot"),
        execution_context=row.get("execution_context"),
    )


def _command_values(command: RoutineCreate | Mapping[str, object]) -> dict[str, Any]:
    values = asdict(command) if isinstance(command, RoutineCreate) else dict(command)
    scope = values.get("access_scope", AccessScope.USER_PRIVATE)
    values["access_scope"] = scope.value if isinstance(scope, AccessScope) else str(scope)
    return values


class RoutineService:
    def __init__(self, principal: RoutinePrincipal | None = None):
        self.principal = principal

    def _actor(self, supplied: RoutinePrincipal | None = None) -> RoutinePrincipal:
        actor = supplied or self.principal
        if actor is None:
            raise RoutineForbidden("a canonical routine principal is required")
        return actor

    def _actor_and_rest(self, args: tuple[Any, ...]) -> tuple[RoutinePrincipal, tuple[Any, ...]]:
        if args and isinstance(args[0], RoutinePrincipal):
            return self._actor(args[0]), args[1:]
        return self._actor(), args

    def create_and_activate(self, *args: Any) -> RoutineView:
        actor, rest = self._actor_and_rest(args)
        if len(rest) != 1:
            raise TypeError("create_and_activate expects a RoutineCreate command")
        values = _command_values(rest[0])
        if values["access_scope"] == AccessScope.SYSTEM_OWNER.value and actor.role != "owner":
            raise RoutineForbidden("system-owner routines require the owner role")
        row = db_routines.create_routine(
            owner_user_id=actor.canonical_user_id,
            status="active",
            **values,
        )
        return _routine_view(row)

    def create_proposal(
        self, principal: RoutinePrincipal, *, for_owner: RoutinePrincipal,
        command: RoutineCreate | Mapping[str, object],
    ) -> RoutineView:
        actor = self._actor(principal)
        if actor.actor_kind != "jarvis":
            raise RoutineForbidden("only Jarvis may create a routine proposal")
        values = _command_values(command)
        values["created_by"] = "jarvis"
        row = db_routines.create_routine(
            owner_user_id=for_owner.canonical_user_id,
            status="draft",
            **values,
        )
        return _routine_view(row)

    def get(self, *args: Any) -> RoutineView | None:
        actor, rest = self._actor_and_rest(args)
        if len(rest) != 1:
            raise TypeError("get expects routine_id")
        row = db_routines.get_routine(str(rest[0]))
        if row is None:
            return None
        require_authorized(actor, Action.READ_CONTENT, row)
        return _routine_view(
            db_routines.get_routine(str(rest[0]), decrypt_for=actor.canonical_user_id)
        )

    def update(
        self, *args: Any, expected_version: int | None = None,
        patch: RoutinePatch | Mapping[str, object] | None = None,
        reactivate: bool = False, **changes: object,
    ) -> RoutineView:
        actor, rest = self._actor_and_rest(args)
        if not rest:
            raise TypeError("update expects routine_id")
        routine_id = str(rest[0])
        if len(rest) > 1 and expected_version is None:
            expected_version = int(rest[1])
        if len(rest) > 2 and patch is None:
            patch = rest[2]
        if expected_version is None:
            raise TypeError("expected_version is required")
        row = db_routines.get_routine(routine_id)
        if row is None:
            raise KeyError(routine_id)
        require_authorized(actor, Action.MUTATE, row)
        patch_values = patch.changes() if isinstance(patch, RoutinePatch) else dict(patch or {})
        patch_values.update(changes)
        try:
            updated = db_routines.update_routine_definition(
                routine_id,
                expected_version=expected_version,
                changes=patch_values,
                reactivate=reactivate,
            )
        except ValueError as exc:
            if "stale routine version" in str(exc):
                raise StaleRoutineVersion("routine was edited by another writer") from exc
            raise
        return _routine_view(updated)

    def _transition(self, operation: str, *args: Any) -> RoutineView:
        actor, rest = self._actor_and_rest(args)
        if len(rest) != 1:
            raise TypeError(f"{operation} expects routine_id")
        routine_id = str(rest[0])
        row = db_routines.get_routine(routine_id)
        if row is None:
            raise KeyError(routine_id)
        require_authorized(actor, Action.MUTATE, row)
        target = _TRANSITIONS[operation].get(str(row["status"]))
        if target is None:
            raise InvalidRoutineTransition(f"cannot {operation} from {row['status']}")
        db_routines.transition_routine(routine_id, to_status=target)
        return _routine_view(
            db_routines.get_routine(routine_id, decrypt_for=actor.canonical_user_id)
        )

    def pause(self, *args: Any) -> RoutineView:
        return self._transition("pause", *args)

    def resume(self, *args: Any) -> RoutineView:
        return self._transition("resume", *args)

    def archive(self, *args: Any) -> RoutineView:
        return self._transition("archive", *args)

    def restore(self, *args: Any) -> RoutineView:
        return self._transition("restore", *args)

    def stop(self, *args: Any) -> RoutineView:
        actor, rest = self._actor_and_rest(args)
        if len(rest) != 1:
            raise TypeError("stop expects routine_id")
        routine_id = str(rest[0])
        row = db_routines.get_routine(routine_id)
        if row is None:
            raise KeyError(routine_id)
        require_authorized(actor, Action.MUTATE, row)
        db_routines.stop_routine(routine_id)
        return _routine_view(
            db_routines.get_routine(routine_id, decrypt_for=actor.canonical_user_id)
        )

    def restart(self, *args: Any) -> RoutineView:
        actor, rest = self._actor_and_rest(args)
        if len(rest) != 1:
            raise TypeError("restart expects routine_id")
        routine_id = str(rest[0])
        row = db_routines.get_routine(routine_id)
        if row is None:
            raise KeyError(routine_id)
        if actor.actor_kind == "jarvis":
            require_authorized(actor, Action.EXECUTE_SEALED, row)
            if not bool(row["jarvis_restart_allowed"]):
                raise RoutineForbidden("Jarvis restart is not enabled for this routine")
        else:
            require_authorized(actor, Action.MUTATE, row)
        target = _TRANSITIONS["restart"].get(str(row["status"]))
        if target is None:
            raise InvalidRoutineTransition(f"cannot restart from {row['status']}")
        updated = db_routines.transition_routine(routine_id, to_status=target)
        if actor.actor_kind != "jarvis":
            updated = db_routines.get_routine(routine_id, decrypt_for=actor.canonical_user_id)
        return _routine_view(updated)

    def delete(self, *args: Any) -> bool:
        actor, rest = self._actor_and_rest(args)
        if len(rest) != 1:
            raise TypeError("delete expects routine_id")
        routine_id = str(rest[0])
        row = db_routines.get_routine(routine_id)
        if row is None:
            return False
        require_authorized(actor, Action.DELETE, row)
        return db_routines.delete_routine_content(routine_id)

    def enqueue_run(self, *args: Any, trigger_key: str) -> RunView:
        actor, rest = self._actor_and_rest(args)
        if len(rest) != 1:
            raise TypeError("enqueue_run expects routine_id")
        routine_id = str(rest[0])
        row = db_routines.get_routine(routine_id)
        if row is None:
            raise KeyError(routine_id)
        action = Action.EXECUTE_SEALED if actor.actor_kind in {"jarvis", "runner", "system"} else Action.RUN
        require_authorized(actor, action, row)
        if row["status"] != "active":
            raise RoutineForbidden("inactive routines cannot enqueue runs")
        return _run_view(db_routines.create_run(
            routine_id=routine_id,
            idempotency_key=trigger_key,
            trigger_source="system" if actor.actor_kind != "user" else "manual",
        ))

    def get_run(self, *args: Any, decrypt: bool = False) -> RunView | None:
        actor, rest = self._actor_and_rest(args)
        if len(rest) != 1:
            raise TypeError("get_run expects run_id")
        row = db_routines.get_run(str(rest[0]))
        if row is None:
            return None
        require_authorized(actor, Action.READ_CONTENT, row)
        if decrypt:
            row = db_routines.get_run(str(rest[0]), decrypt_for=actor.canonical_user_id)
        return _run_view(row)

    def cancel_run(self, *args: Any) -> RunView:
        actor, rest = self._actor_and_rest(args)
        if len(rest) != 1:
            raise TypeError("cancel_run expects run_id")
        row = db_routines.get_run(str(rest[0]))
        if row is None:
            raise KeyError(str(rest[0]))
        require_authorized(actor, Action.MUTATE, row)
        return _run_view(db_routines.cancel_run(str(rest[0])))

    def archive_stopped_before(self, *, now: datetime | None = None) -> dict[str, int]:
        current = now or datetime.now(UTC)
        candidates = db_routines.list_stopped_routines(before=current.isoformat())
        archived = 0
        deleted = 0
        for row in candidates:
            stopped_at = datetime.fromisoformat(str(row["stopped_at"]))
            policy = dict(row.get("retention_policy") or {})
            delete_days = policy.get("auto_delete_days")
            if delete_days is not None and stopped_at <= current - timedelta(days=int(delete_days)):
                if db_routines.delete_routine_content(
                    str(row["routine_id"]), reason_code="retention_auto_delete"
                ):
                    deleted += 1
                continue
            archive_days = int(policy.get("archive_stopped_days", 30))
            if stopped_at <= current - timedelta(days=archive_days):
                db_routines.transition_routine(str(row["routine_id"]), to_status="archived")
                archived += 1
        return {"archived": archived, "deleted": deleted}
