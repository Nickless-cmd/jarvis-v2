"""The single authorization matrix for Routine records."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping

from core.services.routine_types import AccessScope, RoutinePrincipal


class Action(StrEnum):
    LIST = "list"
    READ_METADATA = "read_metadata"
    READ_CONTENT = "read_content"
    MUTATE = "mutate"
    RUN = "run"
    DELETE = "delete"
    EXECUTE_SEALED = "execute_sealed"
    READ_REDACTED_FAILURE = "read_redacted_failure"


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str


class RoutineForbidden(PermissionError):
    """The principal is not allowed to perform a Routine action."""


_OWNER_ACTIONS = frozenset({
    Action.LIST,
    Action.READ_METADATA,
    Action.READ_CONTENT,
    Action.MUTATE,
    Action.RUN,
    Action.DELETE,
    Action.READ_REDACTED_FAILURE,
})
_EXECUTOR_KINDS = frozenset({"jarvis", "runner", "system"})


def _deny(reason: str) -> Decision:
    return Decision(False, reason)


def authorize(
    principal: RoutinePrincipal,
    action: Action | str,
    record: Mapping[str, object],
) -> Decision:
    """Evaluate access without decrypting or including record content in reasons."""
    try:
        requested = action if isinstance(action, Action) else Action(str(action))
    except ValueError:  # Unknown input is an authorization denial, not an operational failure.
        return _deny("unknown routine action or scope")
    try:
        scope = AccessScope(str(record.get("access_scope") or ""))
    except ValueError:  # Unknown input is an authorization denial, not an operational failure.
        return _deny("unknown routine action or scope")

    owner_user_id = str(record.get("owner_user_id") or "").strip()
    actor_user_id = str(principal.canonical_user_id or "").strip()
    if not owner_user_id or not actor_user_id:
        return _deny("routine ownership is unresolved")

    is_record_owner = actor_user_id == owner_user_id
    is_house_owner = principal.role == "owner" and principal.actor_kind == "user"
    is_executor = principal.actor_kind in _EXECUTOR_KINDS

    if requested is Action.READ_REDACTED_FAILURE:
        if is_record_owner or is_house_owner or is_executor:
            return Decision(True, "redacted operational projection")
        return _deny("redacted operational projection is restricted")

    if requested is Action.EXECUTE_SEALED:
        if is_executor:
            return Decision(True, "scoped sealed execution")
        return _deny("sealed execution requires an internal executor")

    if is_executor:
        return _deny("internal executors cannot browse routine content")

    if scope is AccessScope.SYSTEM_OWNER:
        if is_record_owner and is_house_owner and requested in _OWNER_ACTIONS:
            return Decision(True, "system-owner record owner")
        return _deny("system-owner routine is owner-only")

    if is_record_owner and requested in _OWNER_ACTIONS:
        return Decision(True, "record owner")
    return _deny("private routine belongs to another user")


def require_authorized(
    principal: RoutinePrincipal,
    action: Action | str,
    record: Mapping[str, object],
) -> None:
    decision = authorize(principal, action, record)
    if not decision.allowed:
        raise RoutineForbidden(decision.reason)
