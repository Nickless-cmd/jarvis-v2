"""Authorized lifecycle service for versioned Routine definitions and runs."""
from __future__ import annotations

import hashlib
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
    idempotency_key: str
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

_DEFAULT_INBOX_POLICY = {
    "created": True,
    "edited": True,
    "paused": True,
    "stopped": True,
    "archived": True,
    "deleted": True,
    "failed": True,
    "cancelled": True,
    "action_required": True,
    "delivery_failed": True,
    "succeeded": True,
    "retention": True,
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
        idempotency_key=str(row["idempotency_key"]),
        created_at=str(row["created_at"]),
        definition_snapshot=row.get("definition_snapshot"),
        execution_context=row.get("execution_context"),
    )


def _command_values(command: RoutineCreate | Mapping[str, object]) -> dict[str, Any]:
    values = asdict(command) if isinstance(command, RoutineCreate) else dict(command)
    scope = values.get("access_scope", AccessScope.USER_PRIVATE)
    values["access_scope"] = scope.value if isinstance(scope, AccessScope) else str(scope)
    return values


def _apply_classification(values: dict[str, Any]) -> dict[str, Any]:
    """Validér oprettelsens valg og læg den udledte klassifikation i policy'en.

    `execution_mode` og `importance` er *kommando*-felter: de beskriver valget
    ved oprettelsen. De hører ikke i `routines`-tabellen som egne kolonner —
    den persisterede form er `delivery_policy['classification']`, som runneren
    og indbakken læser. Derfor fjernes de fra `values` her; ellers ville
    `db_routines.create_routine(**values)` fejle på ukendte kwargs.

    En ukendt værdi kaster `ValueError` (se `routine_classification`), så en
    tastefejl stopper oprettelsen frem for at blive en usynlig `normal`.
    """
    from core.services.routine_classification import classify_routine

    klassifikation = classify_routine(
        execution_mode=values.pop("execution_mode", "") or "",
        importance=values.pop("importance", "") or "",
    )
    delivery = dict(values.get("delivery_policy") or {})
    delivery["classification"] = klassifikation.as_dict()
    values["delivery_policy"] = delivery
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

    @staticmethod
    def _project(view: RoutineView, event_type: str) -> None:
        from core.services.routine_inbox import project_event_to_inbox

        project_event_to_inbox({
            "owner_user_id": view.owner_user_id,
            "routine_id": view.routine_id,
            "event_id": f"{view.routine_id}:{event_type}:{view.updated_at}",
            "event_type": event_type,
        })

    def create_and_activate(self, *args: Any) -> RoutineView:
        actor, rest = self._actor_and_rest(args)
        if len(rest) != 1:
            raise TypeError("create_and_activate expects a RoutineCreate command")
        values = _command_values(rest[0])
        if values["access_scope"] == AccessScope.SYSTEM_OWNER.value and actor.role != "owner":
            raise RoutineForbidden("system-owner routines require the owner role")
        values = _apply_classification(values)
        values["inbox_policy"] = {
            **_DEFAULT_INBOX_POLICY,
            **db_routines.get_inbox_preference(actor.canonical_user_id),
            **dict(values.get("inbox_policy") or {}),
        }
        row = db_routines.create_routine(
            owner_user_id=actor.canonical_user_id,
            status="active",
            **values,
        )
        view = _routine_view(row)
        self._project(view, "created")
        return view

    def create_proposal(
        self, principal: RoutinePrincipal, *, for_owner: RoutinePrincipal,
        command: RoutineCreate | Mapping[str, object],
    ) -> RoutineView:
        actor = self._actor(principal)
        if actor.actor_kind != "jarvis":
            raise RoutineForbidden("only Jarvis may create a routine proposal")
        values = _command_values(command)
        values["created_by"] = "jarvis"
        values = _apply_classification(values)
        values["inbox_policy"] = {
            **_DEFAULT_INBOX_POLICY,
            **db_routines.get_inbox_preference(for_owner.canonical_user_id),
            **dict(values.get("inbox_policy") or {}),
        }
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
        view = _routine_view(updated)
        self._project(view, "edited")
        return view

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
        view = _routine_view(
            db_routines.get_routine(routine_id, decrypt_for=actor.canonical_user_id)
        )
        self._project(view, {
            "pause": "paused", "resume": "resumed",
            "archive": "archived", "restore": "restored",
        }[operation])
        return view

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
        view = _routine_view(
            db_routines.get_routine(routine_id, decrypt_for=actor.canonical_user_id)
        )
        self._project(view, "stopped")
        return view

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
        view = _routine_view(updated)
        self._project(view, "restarted")
        return view

    def delete(self, *args: Any) -> bool:
        actor, rest = self._actor_and_rest(args)
        if len(rest) != 1:
            raise TypeError("delete expects routine_id")
        routine_id = str(rest[0])
        row = db_routines.get_routine(routine_id)
        if row is None:
            return False
        require_authorized(actor, Action.DELETE, row)
        private = _routine_view(db_routines.get_routine(
            routine_id, decrypt_for=actor.canonical_user_id,
        ))
        self._project(private, "deleted")
        return db_routines.delete_routine_content(routine_id)

    def enqueue_run(
        self, *args: Any, trigger_key: str,
        execution_context: Mapping[str, object] | None = None,
    ) -> RunView:
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
            execution_context=execution_context,
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
        cancelled = db_routines.cancel_run(str(rest[0]))
        from core.services.routine_inbox import project_event_to_inbox

        project_event_to_inbox({
            "owner_user_id": row["owner_user_id"],
            "routine_id": row["routine_id"],
            "event_id": f"{row['run_id']}:cancelled",
            "event_type": "cancelled",
        })
        return _run_view(cancelled)

    def list(self, *args: Any) -> list[RoutineView]:
        actor, rest = self._actor_and_rest(args)
        if rest:
            raise TypeError("list expects no arguments")
        rows = db_routines.list_routines(
            owner_user_id=actor.canonical_user_id,
            decrypt_for=actor.canonical_user_id,
        )
        return [_routine_view(row) for row in rows]

    def list_runs(self, *args: Any) -> list[RunView]:
        actor, rest = self._actor_and_rest(args)
        if len(rest) != 1:
            raise TypeError("list_runs expects routine_id")
        routine_id = str(rest[0])
        row = db_routines.get_routine(routine_id)
        if row is None:
            raise KeyError(routine_id)
        require_authorized(actor, Action.READ_CONTENT, row)
        return [_run_view(item) for item in db_routines.list_runs(routine_id)]

    def list_run_events(self, *args: Any) -> list[dict[str, Any]]:
        actor, rest = self._actor_and_rest(args)
        if len(rest) != 1:
            raise TypeError("list_run_events expects run_id")
        run_id = str(rest[0])
        row = db_routines.get_run(run_id)
        if row is None:
            raise KeyError(run_id)
        require_authorized(actor, Action.READ_CONTENT, row)
        return db_routines.read_run_events(
            run_id, decrypt_for=actor.canonical_user_id,
        )

    def get_inbox_defaults(self, *args: Any) -> dict[str, object]:
        actor, rest = self._actor_and_rest(args)
        if rest:
            raise TypeError("get_inbox_defaults expects no arguments")
        return db_routines.get_inbox_preference(actor.canonical_user_id)

    def set_inbox_defaults(
        self, policy: Mapping[str, object], *args: Any,
    ) -> dict[str, object]:
        actor, rest = self._actor_and_rest(args)
        if rest:
            raise TypeError("set_inbox_defaults expects a policy only")
        return db_routines.set_inbox_preference(
            actor.canonical_user_id, policy=policy,
        )

    def get_redacted_diagnostic(self, *args: Any) -> dict[str, object] | None:
        actor, rest = self._actor_and_rest(args)
        if len(rest) != 1:
            raise TypeError("get_redacted_diagnostic expects run_id")
        run_id = str(rest[0])
        row = db_routines.get_run(run_id)
        if row is None:
            return None
        require_authorized(actor, Action.READ_REDACTED_FAILURE, row)
        if str(row.get("status") or "") != "failed":
            return None
        opaque = lambda prefix, value: (
            f"{prefix}_{hashlib.sha256(str(value).encode('utf-8')).hexdigest()[:16]}"
        )
        return {
            "opaque_routine_ref": opaque("routine", row["routine_id"]),
            "opaque_run_ref": opaque("run", row["run_id"]),
            "occurred_at": str(row.get("finished_at") or row.get("updated_at") or ""),
            "component": "runner",
            "error_code": str(row.get("diagnostic_code") or "routine_execution_failed"),
            "health_classification": "unknown",
        }

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
                self._project(_routine_view(row), "retention")
                if db_routines.delete_routine_content(
                    str(row["routine_id"]), reason_code="retention_auto_delete"
                ):
                    deleted += 1
                continue
            archive_days = int(policy.get("archive_stopped_days", 30))
            if stopped_at <= current - timedelta(days=archive_days):
                db_routines.transition_routine(str(row["routine_id"]), to_status="archived")
                self._project(_routine_view(row), "retention")
                archived += 1
        return {"archived": archived, "deleted": deleted}
