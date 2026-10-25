"""Authenticated, owner-scoped Routine lifecycle API."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from core.services.routine_authorization import RoutineForbidden
from core.services.routine_service import (
    InvalidRoutineTransition,
    RoutineService,
    StaleRoutineVersion,
)
from core.services.routine_types import AccessScope, RoutineCreate, RoutinePrincipal


router = APIRouter(prefix="/api/routines", tags=["routines"])


class RoutineCreateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    instruction: str = Field(min_length=1, max_length=100_000)
    capability_scope: Literal["chat", "code", "system"]
    trigger_kind: Literal["manual", "schedule", "interval", "event", "system"]
    #: Hvor opgaven udføres — valgt ved oprettelsen (Bjørn 19/10-2026).
    #: ``background`` = isoleret run, rapportér til indbakken.
    #: ``session`` = udfør hvor brugeren sidst var aktiv, med cool-down.
    execution_mode: Literal["background", "session"] = "background"
    #: Hvor vigtigt resultatet er. ``high``/``critical`` fremhæves i indbakken;
    #: kun ``critical`` må blokere en mutation.
    importance: Literal["low", "normal", "high", "critical"] = "normal"
    trigger_config: dict[str, object] = {}
    permission_policy: dict[str, object] = {}
    delivery_policy: dict[str, object] = {}
    inbox_policy: dict[str, object] = {}
    retention_policy: dict[str, object] = {}
    failure_policy: dict[str, object] = {}
    access_scope: AccessScope = AccessScope.USER_PRIVATE
    workspace_name: str = ""
    workspace_kind: str = ""
    workspace_root: str = ""
    jarvis_restart_allowed: bool = False


class RoutinePatchBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=0)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    instruction: str | None = Field(default=None, min_length=1, max_length=100_000)
    capability_scope: Literal["chat", "code", "system"] | None = None
    trigger_kind: Literal["manual", "schedule", "interval", "event", "system"] | None = None
    trigger_config: dict[str, object] | None = None
    permission_policy: dict[str, object] | None = None
    delivery_policy: dict[str, object] | None = None
    inbox_policy: dict[str, object] | None = None
    retention_policy: dict[str, object] | None = None
    failure_policy: dict[str, object] | None = None
    workspace_name: str | None = None
    workspace_kind: str | None = None
    workspace_root: str | None = None
    jarvis_restart_allowed: bool | None = None
    reactivate: bool = False


class InboxPolicyBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    created: bool | None = None
    edited: bool | None = None
    paused: bool | None = None
    stopped: bool | None = None
    archived: bool | None = None
    deleted: bool | None = None
    failed: bool | None = None
    cancelled: bool | None = None
    action_required: bool | None = None
    delivery_failed: bool | None = None
    retention: bool | None = None


class EmptyBody(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _principal() -> RoutinePrincipal:
    from core.identity.workspace_context import current_role, current_user_id
    from core.services.routine_identity import (
        AmbiguousRoutineIdentity,
        UnresolvedRoutinePrincipal,
        resolve_principal,
    )

    user_id = str(current_user_id() or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="not authenticated")
    try:
        return resolve_principal(
            user_id, role_hint=str(current_role() or "member")
        )
    except (UnresolvedRoutinePrincipal, AmbiguousRoutineIdentity) as exc:
        raise HTTPException(status_code=401, detail="unresolved routine identity") from exc


def _service() -> RoutineService:
    return RoutineService(_principal())


def _routine(value) -> dict[str, Any]:
    from core.identity.workspace_context import current_user_id

    data = asdict(value)
    data["instruction"] = value.instruction.decode("utf-8", errors="replace")
    data["canonical_owner_user_id"] = data["owner_user_id"]
    if data["access_scope"] == "user_private":
        # Ældre desktop-builds sammenligner med login-tokenet (fx Discord-id),
        # mens Routine-laget gemmer et kanonisk database-id. Listen er allerede
        # owner-scopet af servicen, så kompatibilitets-aliaset udvider ikke adgang.
        data["owner_user_id"] = str(current_user_id() or data["owner_user_id"])
    return data


def _run(value) -> dict[str, Any]:
    data = asdict(value)
    snapshot = data.get("definition_snapshot")
    if isinstance(snapshot, dict) and isinstance(snapshot.get("instruction"), bytes):
        snapshot["instruction"] = snapshot["instruction"].decode(
            "utf-8", errors="replace"
        )
    return data


def _not_found(exc: Exception) -> HTTPException:
    return HTTPException(status_code=404, detail="routine not found")


@router.get("")
def list_routines() -> list[dict[str, Any]]:
    return [_routine(item) for item in _service().list()]


@router.post("")
def create_routine(body: RoutineCreateBody) -> dict[str, Any]:
    values = body.model_dump()
    values["instruction"] = body.instruction.encode("utf-8")
    return _routine(_service().create_and_activate(RoutineCreate(**values)))


@router.get("/inbox-defaults")
def get_inbox_defaults() -> dict[str, object]:
    return _service().get_inbox_defaults()


@router.put("/inbox-defaults")
def set_inbox_defaults(body: InboxPolicyBody) -> dict[str, object]:
    return _service().set_inbox_defaults(body.model_dump(exclude_none=True))


@router.get("/{routine_id}")
def get_routine(routine_id: str) -> dict[str, Any]:
    try:
        item = _service().get(routine_id)
    except (RoutineForbidden, KeyError) as exc:
        raise _not_found(exc) from exc
    if item is None:
        raise HTTPException(status_code=404, detail="routine not found")
    return _routine(item)


@router.patch("/{routine_id}")
def patch_routine(routine_id: str, body: RoutinePatchBody) -> dict[str, Any]:
    values = body.model_dump(exclude={"expected_version", "reactivate"}, exclude_none=True)
    if "instruction" in values:
        values["instruction"] = str(values["instruction"]).encode("utf-8")
    try:
        item = _service().update(
            routine_id, expected_version=body.expected_version,
            reactivate=body.reactivate, **values,
        )
    except StaleRoutineVersion as exc:
        raise HTTPException(status_code=409, detail="stale routine version") from exc
    except InvalidRoutineTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (RoutineForbidden, KeyError) as exc:
        raise _not_found(exc) from exc
    return _routine(item)


@router.delete("/{routine_id}")
def delete_routine(routine_id: str) -> dict[str, bool]:
    try:
        deleted = _service().delete(routine_id)
    except (RoutineForbidden, KeyError) as exc:
        raise _not_found(exc) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="routine not found")
    return {"deleted": True}


@router.post("/{routine_id}/actions/{action}")
def lifecycle_action(
    routine_id: str,
    action: Literal["pause", "resume", "stop", "restart", "archive", "restore"],
) -> dict[str, Any]:
    try:
        return _routine(getattr(_service(), action)(routine_id))
    except InvalidRoutineTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (RoutineForbidden, KeyError) as exc:
        raise _not_found(exc) from exc


@router.post("/{routine_id}/runs")
def run_now(routine_id: str, body: EmptyBody | None = None) -> dict[str, Any]:
    _ = body
    try:
        run = _service().enqueue_run(
            routine_id, trigger_key=f"manual:{uuid4().hex}",
        )
    except RoutineForbidden as exc:
        if "inactive" in str(exc):
            raise HTTPException(status_code=409, detail="routine is inactive") from exc
        raise _not_found(exc) from exc
    except KeyError as exc:
        raise _not_found(exc) from exc
    return _run(run)


@router.get("/{routine_id}/runs")
def list_runs(routine_id: str) -> list[dict[str, Any]]:
    try:
        return [_run(item) for item in _service().list_runs(routine_id)]
    except (RoutineForbidden, KeyError) as exc:
        raise _not_found(exc) from exc


@router.get("/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    try:
        item = _service().get_run(run_id, decrypt=True)
    except (RoutineForbidden, KeyError) as exc:
        raise _not_found(exc) from exc
    if item is None:
        raise HTTPException(status_code=404, detail="run not found")
    return _run(item)


@router.get("/runs/{run_id}/events")
def get_run_events(run_id: str) -> list[dict[str, Any]]:
    try:
        return _service().list_run_events(run_id)
    except (RoutineForbidden, KeyError) as exc:
        raise _not_found(exc) from exc


@router.post("/runs/{run_id}/cancel")
def cancel_run(run_id: str) -> dict[str, Any]:
    try:
        return _run(_service().cancel_run(run_id))
    except (RoutineForbidden, KeyError) as exc:
        raise _not_found(exc) from exc


@router.get("/diagnostics/runs/{run_id}")
def get_redacted_diagnostic(run_id: str) -> dict[str, object]:
    try:
        item = _service().get_redacted_diagnostic(run_id)
    except (RoutineForbidden, KeyError) as exc:
        raise _not_found(exc) from exc
    if item is None:
        raise HTTPException(status_code=404, detail="diagnostic not found")
    return item
