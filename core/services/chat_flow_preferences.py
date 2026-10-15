"""Authenticated per-user presentation preferences for Desk Chat Mode."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from core.identity.workspace_context import current_role, current_user_id
from core.runtime.db_core import connect

VALID_PREFERENCES = frozenset({"living", "calm", "adaptive"})
NATIVE_OWNER_PRINCIPAL = "native-owner"
ONBOARDING_CLAIM_TTL = timedelta(minutes=5)


class ChatFlowIdentityError(RuntimeError):
    """The current execution has no verified stable preference owner."""


def _now(value: datetime | None = None) -> datetime:
    current = value or datetime.now(UTC)
    return current if current.tzinfo else current.replace(tzinfo=UTC)


def _iso(value: datetime | None = None) -> str:
    return _now(value).isoformat(timespec="seconds").replace("+00:00", "Z")


def resolve_chat_flow_principal() -> str:
    """Resolve only token-backed identity; session elevation never changes owner."""
    role = str(current_role() or "").strip().lower()
    user_id = str(current_user_id() or "").strip()
    if role not in {"owner", "partner", "member", "guest"}:
        raise ChatFlowIdentityError("verified authenticated identity required")
    if user_id:
        return f"user:{user_id}"
    if role == "owner":
        return NATIVE_OWNER_PRINCIPAL
    raise ChatFlowIdentityError("stable authenticated user id required")


def _ensure_row(conn, principal_id: str, *, now: datetime | None = None) -> None:
    principal = str(principal_id or "").strip()
    if not principal:
        raise ChatFlowIdentityError("stable authenticated user id required")
    conn.execute(
        "INSERT INTO chat_flow_preferences (principal_id, updated_at) VALUES (?, ?) "
        "ON CONFLICT(principal_id) DO NOTHING",
        (principal, _iso(now)),
    )


def _state_from_row(row) -> dict[str, Any]:
    return {
        "preference": str(row["preference"]),
        "onboarding_seen": bool(row["onboarding_seen"]),
        "explicit_user_choice": bool(row["explicit_user_choice"]),
        "suggestions_enabled": bool(row["suggestions_enabled"]),
        "last_suggestion_kind": row["last_suggestion_kind"],
        "last_suggestion_at": row["last_suggestion_at"],
        "suggestion_rejections": int(row["suggestion_rejections"]),
        "short_direct_runs": int(row["short_direct_runs"]),
        "multi_step_runs": int(row["multi_step_runs"]),
        "work_expansions": int(row["work_expansions"]),
        "living_overrides": int(row["living_overrides"]),
        "calm_overrides": int(row["calm_overrides"]),
        "updated_at": str(row["updated_at"]),
    }


def get_chat_flow_state(principal_id: str) -> dict[str, Any]:
    with connect() as conn:
        _ensure_row(conn, principal_id)
        row = conn.execute(
            "SELECT * FROM chat_flow_preferences WHERE principal_id = ?",
            (principal_id,),
        ).fetchone()
    return _state_from_row(row)


def set_chat_flow_state(
    principal_id: str,
    *,
    preference: str | None = None,
    suggestions_enabled: bool | None = None,
    explicit: bool = False,
) -> dict[str, Any]:
    if preference is not None and preference not in VALID_PREFERENCES:
        raise ValueError(f"invalid chat flow preference: {preference!r}")
    assignments: list[str] = []
    values: list[Any] = []
    if preference is not None:
        assignments.append("preference = ?")
        values.append(preference)
        if explicit:
            assignments.append("explicit_user_choice = 1")
    if suggestions_enabled is not None:
        assignments.append("suggestions_enabled = ?")
        values.append(int(suggestions_enabled))
    with connect() as conn:
        _ensure_row(conn, principal_id)
        if assignments:
            assignments.append("updated_at = ?")
            values.append(_iso())
            values.append(principal_id)
            conn.execute(
                f"UPDATE chat_flow_preferences SET {', '.join(assignments)} WHERE principal_id = ?",
                tuple(values),
            )
    return get_chat_flow_state(principal_id)


def claim_chat_flow_onboarding(
    principal_id: str,
    run_id: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    current = _now(now)
    claim_id = uuid4().hex
    expires = current + ONBOARDING_CLAIM_TTL
    with connect() as conn:
        _ensure_row(conn, principal_id, now=current)
        cursor = conn.execute(
            "UPDATE chat_flow_preferences SET onboarding_claim_id = ?, "
            "onboarding_claim_run = ?, onboarding_claim_until = ?, updated_at = ? "
            "WHERE principal_id = ? AND onboarding_seen = 0 AND "
            "(onboarding_claim_id IS NULL OR onboarding_claim_until <= ?)",
            (claim_id, str(run_id), _iso(expires), _iso(current), principal_id, _iso(current)),
        )
    if cursor.rowcount != 1:
        return {"claimed": False, "claim_id": None, **get_chat_flow_state(principal_id)}
    return {"claimed": True, "claim_id": claim_id, "run_id": str(run_id),
            **get_chat_flow_state(principal_id)}


def ack_chat_flow_onboarding(principal_id: str, claim_id: str) -> dict[str, Any]:
    with connect() as conn:
        _ensure_row(conn, principal_id)
        cursor = conn.execute(
            "UPDATE chat_flow_preferences SET onboarding_seen = 1, "
            "onboarding_claim_id = NULL, onboarding_claim_run = NULL, "
            "onboarding_claim_until = NULL, updated_at = ? "
            "WHERE principal_id = ? AND onboarding_seen = 0 AND onboarding_claim_id = ?",
            (_iso(), principal_id, str(claim_id)),
        )
    if cursor.rowcount != 1:
        raise ValueError("onboarding claim is missing, expired, or already acknowledged")
    return get_chat_flow_state(principal_id)


def record_chat_flow_observation(
    principal_id: str,
    *,
    meaningful_steps: int,
    expanded_work: bool,
    manual_override: str | None,
) -> dict[str, Any]:
    if manual_override not in {None, "living", "calm"}:
        raise ValueError("manual override must be living or calm")
    increments = ["multi_step_runs" if max(0, int(meaningful_steps)) >= 2 else "short_direct_runs"]
    if expanded_work:
        increments.append("work_expansions")
    if manual_override:
        increments.append(f"{manual_override}_overrides")
    with connect() as conn:
        _ensure_row(conn, principal_id)
        clause = ", ".join(f"{name} = {name} + 1" for name in increments)
        conn.execute(
            f"UPDATE chat_flow_preferences SET {clause}, updated_at = ? WHERE principal_id = ?",
            (_iso(), principal_id),
        )
    return get_chat_flow_state(principal_id)


def record_chat_flow_suggestion(
    principal_id: str,
    *,
    kind: str,
    outcome: str,
) -> dict[str, Any]:
    if kind not in {"living", "calm"}:
        raise ValueError("suggestion kind must be living or calm")
    if outcome not in {"accepted", "rejected", "dismissed"}:
        raise ValueError("suggestion outcome must be accepted, rejected, or dismissed")
    with connect() as conn:
        _ensure_row(conn, principal_id)
        conn.execute(
            "UPDATE chat_flow_preferences SET last_suggestion_kind = ?, "
            "last_suggestion_at = ?, suggestion_rejections = suggestion_rejections + ?, "
            "updated_at = ? WHERE principal_id = ?",
            (kind, _iso(), int(outcome in {"rejected", "dismissed"}), _iso(), principal_id),
        )
    return get_chat_flow_state(principal_id)
