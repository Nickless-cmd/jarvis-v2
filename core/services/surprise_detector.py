"""Surprise detector — anomaly signals for the proactive/autonomous lane.

Reactive Jarvis runs only when prompted. Proactive Jarvis needs to wake
up when something *unexpected* happens. This module scans recent
eventbus activity and publishes ``surprise.detected`` events whenever it
sees one of:

1. **Burst of errors.** N runtime.error or tool.execution_error events in
   a short window — suggests something is broken right now.
2. **Service silence.** A service that normally heartbeats every X
   seconds hasn't published anything in 3X. Could be hung.
3. **First-of-its-kind event.** A new event kind appeared that has never
   been seen before in this session — worth investigating.
4. **Approval starvation.** An approval card has been pending for more
   than 1 hour without resolution.

Each surprise becomes a ``surprise.detected`` event; phase 3's wake-up
digest then surfaces it in the next prompt naturally — no extra plumbing.

Designed to run from heartbeat ticks (called once per minute or so) but
also exposed as a tool the autonomous loop can call on demand.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)

_STATE_KEY = "surprise_detector"
_ERROR_BURST_WINDOW_MIN = 5
_ERROR_BURST_THRESHOLD = 4
_APPROVAL_STARVATION_MIN = 60


def _load_state() -> dict[str, Any]:
    raw = load_json(_STATE_KEY, {})
    return raw if isinstance(raw, dict) else {}


def _save_state(state: dict[str, Any]) -> None:
    save_json(_STATE_KEY, state)


def _publish(kind: str, summary: str, detail: dict[str, Any] | None = None) -> None:
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "surprise.detected",
            {
                "surprise_kind": kind,
                "summary": summary[:240],
                "detail": detail or {},
            },
        )
    except Exception as exc:
        logger.debug("surprise_detector: publish failed: %s", exc)


def _check_error_burst() -> int:
    try:
        from core.eventbus.bus import event_bus
        events = event_bus.recent(limit=120)
    except Exception:
        return 0
    cutoff = (datetime.now(UTC) - timedelta(minutes=_ERROR_BURST_WINDOW_MIN)).isoformat()
    error_kinds = ("runtime.error", "tool.execution_error", "tool.invocation_failed")
    recent_errors = [
        e for e in events
        if str(e.get("kind", "")) in error_kinds
        and str(e.get("created_at", "")) >= cutoff
    ]
    if len(recent_errors) >= _ERROR_BURST_THRESHOLD:
        kinds_seen = sorted({str(e.get("kind", "")) for e in recent_errors})
        _publish(
            "error_burst",
            f"{len(recent_errors)} fejl-events i sidste {_ERROR_BURST_WINDOW_MIN} min",
            {"count": len(recent_errors), "kinds": kinds_seen},
        )
        return 1
    return 0


def _check_first_of_its_kind() -> int:
    """Track every event kind we've ever seen; new ones become surprises."""
    state = _load_state()
    seen_kinds: set[str] = set(state.get("seen_kinds", []))
    try:
        from core.eventbus.bus import event_bus
        events = event_bus.recent(limit=200)
    except Exception:
        return 0
    new_kinds: list[str] = []
    for e in events:
        k = str(e.get("kind", ""))
        if not k or k.startswith("surprise."):
            continue
        if k not in seen_kinds:
            new_kinds.append(k)
            seen_kinds.add(k)
    if new_kinds:
        # Only surface when we have a non-empty seen set already (otherwise
        # every kind looks new on first run, which floods the eventbus).
        if state.get("bootstrapped"):
            for k in new_kinds[:3]:
                _publish("new_event_kind", f"Ny event-type set første gang: {k}")
        state["seen_kinds"] = sorted(seen_kinds)
        state["bootstrapped"] = True
        _save_state(state)
    return len(new_kinds)


def _check_approval_starvation() -> int:
    """Check pending_approvals state for cards older than threshold."""
    pending = load_json("pending_approvals", {})
    if not isinstance(pending, dict) or not pending:
        return 0
    cutoff = datetime.now(UTC) - timedelta(minutes=_APPROVAL_STARVATION_MIN)
    state = _load_state()
    notified = set(state.get("starvation_notified", []))
    fresh: list[str] = []
    for aid, rec in pending.items():
        if not isinstance(rec, dict):
            continue
        created = str(rec.get("created_at", ""))
        if not created:
            continue
        try:
            ts = datetime.fromisoformat(created)
        except Exception:
            continue
        if ts < cutoff and aid not in notified:
            tool = str(rec.get("tool_name", "?"))
            _publish(
                "approval_starvation",
                f"Approval ventet >{_APPROVAL_STARVATION_MIN} min: {tool}",
                {"approval_id": aid, "tool": tool},
            )
            notified.add(aid)
            fresh.append(aid)
    if fresh:
        # Trim notified set to only currently-pending ids so it doesn't grow.
        state["starvation_notified"] = [a for a in notified if a in pending]
        _save_state(state)
    return len(fresh)


def check_surprises() -> dict[str, Any]:
    """Run all anomaly checks; return a summary of what fired."""
    return {
        "error_burst": _check_error_burst(),
        "first_of_its_kind": _check_first_of_its_kind(),
        "approval_starvation": _check_approval_starvation(),
    }


def _exec_check_surprises(_args: dict[str, Any]) -> dict[str, Any]:
    return {"status": "ok", "fired": check_surprises()}


SURPRISE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "check_surprises",
            "description": (
                "Run anomaly detection across recent eventbus activity. "
                "Each surprise found becomes a surprise.detected event "
                "which then surfaces in the next prompt's wake-up digest. "
                "Useful at the start of an autonomous tick or when you "
                "suspect something quiet went wrong."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]
