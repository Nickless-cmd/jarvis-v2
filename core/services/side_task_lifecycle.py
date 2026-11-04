"""Pure lifecycle rules for durable side tasks.

The storage service owns persistence; this module owns the vocabulary and the
legal state machine.  Keeping the rules pure makes every entry point (Desk,
tools, autonomous dispatcher and crash reconciliation) answer the same way.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Final


VALID_STATUSES: Final[tuple[str, ...]] = (
    "pending", "queued", "activated", "running", "paused", "blocked",
    "failed", "completed", "dismissed",
)
OPEN_STATUSES: Final[frozenset[str]] = frozenset(VALID_STATUSES[:-2])
TERMINAL_STATUSES: Final[frozenset[str]] = frozenset({"completed", "dismissed"})
ACTIVE_STATUSES: Final[frozenset[str]] = frozenset({"activated", "running"})
REASON_REQUIRED: Final[frozenset[str]] = frozenset(
    {"paused", "blocked", "failed", "dismissed"}
)

_ALLOWED: Final[dict[str, frozenset[str]]] = {
    "pending": frozenset({"queued", "activated", "running", "paused", "blocked", "failed",
                          "completed", "dismissed"}),
    "queued": frozenset({"pending", "activated", "running", "paused", "blocked", "failed",
                         "completed", "dismissed"}),
    "activated": frozenset({"queued", "running", "paused", "blocked", "failed",
                            "completed", "dismissed"}),
    "running": frozenset({"queued", "paused", "blocked", "failed", "completed", "dismissed"}),
    "paused": frozenset({"queued", "activated", "running", "blocked", "failed",
                         "completed", "dismissed"}),
    "blocked": frozenset({"queued", "activated", "running", "paused", "failed",
                          "completed", "dismissed"}),
    "failed": frozenset({"queued", "activated", "running", "paused", "blocked", "dismissed"}),
    "completed": frozenset(),
    "dismissed": frozenset(),
}


def validate_transition(old: str, new: str, *, reason: str = "") -> str | None:
    """Return a user-facing error, or ``None`` when the transition is legal."""
    if new not in VALID_STATUSES:
        return "unknown side-task decision"
    if old not in VALID_STATUSES:
        return f"side task has unknown current status {old!r}"
    if old in TERMINAL_STATUSES:
        return f"side task is already {old} and cannot be reopened"
    if new == old:
        return None
    if new not in _ALLOWED[old]:
        return f"side task cannot move from {old} to {new}"
    if new in REASON_REQUIRED and not str(reason or "").strip():
        return f"{new} kræver en konkret grund"
    return None


def apply_transition(record: dict[str, Any], new: str, *, reason: str = "",
                     actor: str = "", now: datetime | None = None) -> None:
    """Mutate one record with timestamps and a bounded, auditable history."""
    moment = (now or datetime.now(UTC)).astimezone(UTC).isoformat()
    old = str(record.get("status") or "pending")
    record["status"] = new
    record["updated_at"] = moment

    stamp = {
        "queued": "queued_at", "activated": "activated_at", "running": "running_at",
        "paused": "paused_at", "blocked": "blocked_at", "failed": "failed_at",
    }.get(new)
    if stamp:
        record[stamp] = moment
    if new == "running":
        record["last_progress_at"] = moment
    if new in TERMINAL_STATUSES:
        record["resolved_at"] = moment
    if reason:
        record["state_reason"] = str(reason).strip()[:1000]
    elif new in {"queued", "activated", "running"}:
        record.pop("state_reason", None)

    history = list(record.get("transition_history") or [])
    history.append({
        "from": old, "to": new, "at": moment,
        "reason": str(reason or "").strip()[:500],
        "actor": str(actor or "")[:80],
    })
    record["transition_history"] = history[-50:]

