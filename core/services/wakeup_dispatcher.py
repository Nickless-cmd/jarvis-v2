"""Wakeup dispatcher — autonomous fire of self-wakeups.

Self-wakeups land in awareness when Jarvis has a turn. Without this
dispatcher, a wakeup that fires when no user is talking just sits in
state forever — the prompt is never built, awareness never renders.

Three actions per fired wakeup (matches user's A+B+C plan):

A) Push to webchat — actively notify the user (wakeup is "loud")
B) Trigger heartbeat phase tick — wakes Jarvis' inner loop
C) Send webchat message FROM Jarvis — quote the wakeup prompt
   so when the user sees it they can engage

Idempotent: each wakeup is only dispatched once. After dispatch, the
wakeup stays in 'fired' status until Jarvis calls mark_wakeup_consumed.
We track dispatched-already in the wakeup record itself.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


def dispatch_due_wakeups() -> dict[str, Any]:
    """Find newly-fired wakeups, push them out via webchat + heartbeat tick."""
    from core.services.self_wakeup import due_wakeups, _load, _save

    fired = due_wakeups(include_fired_unconsumed=True)
    if not fired:
        return {"status": "ok", "dispatched": 0}

    # Load full records to check + mutate dispatched flag
    all_records = _load()
    by_id = {r.get("wakeup_id"): r for r in all_records}

    dispatched: list[str] = []
    for w in fired:
        wid = w.get("wakeup_id")
        record = by_id.get(wid)
        if record is None or record.get("dispatched"):
            continue
        prompt = str(record.get("prompt", ""))
        reason = str(record.get("reason", ""))

        # A: webchat push
        try:
            from core.services.notification_bridge import send_session_notification
            msg = (
                f"⏰ Self-wakeup fyrede ({reason or 'no reason'}):\n"
                f"  {prompt}\n"
                f"_(wakeup_id: {wid})_"
            )
            send_session_notification(msg, source="self-wakeup")
        except Exception as exc:
            logger.warning("wakeup webchat push failed: %s", exc)

        # B: trigger heartbeat phase tick (lets Jarvis' inner loop see it)
        try:
            from core.services.heartbeat_phases import tick_with_phases
            tick_with_phases(name="default", trigger="self-wakeup-fire")
        except Exception as exc:
            logger.debug("wakeup heartbeat trigger failed: %s", exc)

        # Mark dispatched in record
        record["dispatched"] = True
        record["dispatched_at"] = datetime.now(UTC).isoformat()
        dispatched.append(str(wid))

        # Eventbus
        try:
            from core.eventbus.bus import event_bus
            event_bus.publish(
                "self_wakeup.dispatched",
                {"wakeup_id": wid, "reason": reason[:80]},
            )
        except Exception:
            pass

    if dispatched:
        _save(all_records)

    return {"status": "ok", "dispatched": len(dispatched), "dispatched_ids": dispatched}


def _exec_dispatch_due_wakeups(args: dict[str, Any]) -> dict[str, Any]:
    return dispatch_due_wakeups()


WAKEUP_DISPATCHER_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "dispatch_due_wakeups",
            "description": (
                "Manually run the wakeup dispatcher (normally automatic via "
                "periodic_jobs_scheduler every 60s). Pushes any fired-but-undispatched "
                "wakeups to webchat + triggers heartbeat tick."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]
