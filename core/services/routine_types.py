"""Value objects shared by the Routine domain.

These types intentionally contain no session identifier.  A routine execution is
owned and scoped directly; it is never authorized through a chat session.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping


class RoutineStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ARCHIVED = "archived"
    DELETED = "deleted"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class AccessScope(StrEnum):
    USER_PRIVATE = "user_private"
    SYSTEM_OWNER = "system_owner"


@dataclass(frozen=True)
class RoutinePrincipal:
    canonical_user_id: str
    role: str = "member"
    actor_kind: str = "user"

    @property
    def user_id(self) -> str:
        return self.canonical_user_id


@dataclass(frozen=True)
class RoutineExecutionContext:
    run_id: str
    routine_id: str
    routine_version: int
    owner_user_id: str
    access_scope: AccessScope
    instruction_ref: str
    instruction_hash: str
    trigger_inputs: dict[str, object]
    workspace_name: str
    workspace_kind: str
    workspace_root: str
    capability_scope: str
    permission_policy: dict[str, object]
    approval_policy: dict[str, object]
    provider: str
    model: str
    lease_generation: int


@dataclass(frozen=True)
class RoutineCreate:
    name: str
    instruction: bytes
    capability_scope: str
    trigger_kind: str
    trigger_config: Mapping[str, object] = field(default_factory=dict)
    permission_policy: Mapping[str, object] = field(default_factory=dict)
    delivery_policy: Mapping[str, object] = field(default_factory=dict)
    inbox_policy: Mapping[str, object] = field(default_factory=dict)
    retention_policy: Mapping[str, object] = field(default_factory=dict)
    failure_policy: Mapping[str, object] = field(default_factory=dict)
    access_scope: AccessScope = AccessScope.USER_PRIVATE
    created_by: str = "user"
    workspace_name: str = ""
    workspace_kind: str = ""
    workspace_root: str = ""
    jarvis_restart_allowed: bool = False


@dataclass(frozen=True)
class RoutinePatch:
    name: str | None = None
    instruction: bytes | None = None
    capability_scope: str | None = None
    trigger_kind: str | None = None
    trigger_config: Mapping[str, object] | None = None
    permission_policy: Mapping[str, object] | None = None
    delivery_policy: Mapping[str, object] | None = None
    inbox_policy: Mapping[str, object] | None = None
    retention_policy: Mapping[str, object] | None = None
    failure_policy: Mapping[str, object] | None = None
    workspace_name: str | None = None
    workspace_kind: str | None = None
    workspace_root: str | None = None
    jarvis_restart_allowed: bool | None = None

    def changes(self) -> dict[str, Any]:
        return {key: value for key, value in self.__dict__.items() if value is not None}
