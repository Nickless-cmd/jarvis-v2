"""Content-free operational failure projections for owner and Jarvis."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Mapping


@dataclass(frozen=True)
class OperationalFailure:
    opaque_routine_ref: str
    opaque_run_ref: str
    occurred_at: str
    component: str
    error_code: str
    error_class: str
    occurrence_count: int
    retry_count: int
    health_classification: str


_COMPONENTS = frozenset({"runner", "scheduler", "delivery", "migration", "runtime", "tool"})
_HEALTH = frozenset({"degraded", "unavailable", "unknown", "healthy"})


def _opaque(prefix: str, value: object) -> str:
    digest = hashlib.sha256(str(value or "unknown").encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _bounded_count(value: object) -> int:
    try:
        return max(0, min(int(value), 1_000_000))
    except (TypeError, ValueError):  # Untrusted counts degrade to zero; content is never logged.
        return 0


def project_failure(exc: BaseException, metadata: Mapping[str, object]) -> OperationalFailure:
    component = str(metadata.get("trusted_component") or "runtime").lower()
    if component not in _COMPONENTS:
        component = "runtime"
    health = str(metadata.get("trusted_health_classification") or "unknown").lower()
    if health not in _HEALTH:
        health = "unknown"
    occurred_at = metadata.get("occurred_at")
    if not isinstance(occurred_at, str) or "T" not in occurred_at:
        occurred_at = datetime.now(UTC).isoformat()
    return OperationalFailure(
        opaque_routine_ref=_opaque("routine", metadata.get("routine_id")),
        opaque_run_ref=_opaque("run", metadata.get("run_id")),
        occurred_at=occurred_at,
        component=component,
        error_code="routine_execution_failed",
        error_class=type(exc).__name__,
        occurrence_count=_bounded_count(metadata.get("occurrence_count", 1)),
        retry_count=_bounded_count(metadata.get("retry_count", 0)),
        health_classification=health,
    )


def render_projection(projection: OperationalFailure) -> str:
    return (
        "Routinefejl "
        f"{projection.opaque_routine_ref}/{projection.opaque_run_ref} · "
        f"{projection.component} · {projection.error_code} "
        f"({projection.error_class}) · retry {projection.retry_count} · "
        f"health {projection.health_classification} · {projection.occurred_at}"
    )


def publish_failure(projection: OperationalFailure) -> dict[str, str]:
    """Publish the same fixed-schema projection to operational inbox and app chat."""
    from core.identity.owner_resolver import (
        owner_user_id,
        resolve_owner_app_session,
        session_is_external_channel,
    )
    from core.services.inbox_state import registrer_kilde

    owner = str(owner_user_id() or "").strip()
    event_id = f"{projection.opaque_run_ref}:{projection.error_code}"
    inbox_status = "blocked"
    if owner:
        inbox_status = str(registrer_kilde(
            bruger_id=owner,
            kildetype="routine_event",
            kilde_id=event_id,
            kilde_ejer="jarvis",
            beskrivelse=render_projection(projection),
        ).get("status") or "error")

    session_id = str(resolve_owner_app_session() or "").strip()
    session_status = "blocked"
    if session_id and not session_is_external_channel(session_id):
        from core.services.chat_sessions import append_chat_message

        append_chat_message(
            session_id=session_id,
            role="assistant",
            content=render_projection(projection),
            user_id=owner or None,
        )
        session_status = "delivered"
    return {"session": session_status, "inbox": inbox_status}
