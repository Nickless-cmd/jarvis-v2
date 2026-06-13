"""Self-wakeup — Jarvis' equivalent of Claude Code's ScheduleWakeup.

Jarvis already has schedule_task (one-shot future work) and the periodic
job scheduler (recurring), but neither matches the conversational wake-up
pattern: "in 90 seconds, re-enter THIS line of thought with prompt X".

This module adds that capability. Three operations:

- schedule_self_wakeup(delay_seconds, prompt, reason) — set a future
  self-message
- list_self_wakeups() — see what's queued
- cancel_self_wakeup(wakeup_id) — abort a pending one

When a wakeup's time arrives:
- Surfaces in prompt awareness on the next visible run/heartbeat tick
  (NOT injected magically — Jarvis sees "⏰ You scheduled yourself to
  resume X — go" and decides what to do)
- After he acts, mark_wakeup_consumed() clears it so it doesn't
  re-surface forever

Persistent: survives restarts via state_store. Audit trail in eventbus
(self_wakeup.scheduled, self_wakeup.fired, self_wakeup.consumed,
self_wakeup.cancelled).

Bounds:
- delay clamped to [60, 86400] (1 min to 24 hours) — anything longer
  should be a real scheduled task
- max 20 pending wakeups at once (don't let it become a backlog)
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)


_STATE_KEY = "self_wakeups"
_MIN_DELAY_SECONDS = 60
_MAX_DELAY_SECONDS = 86400  # 24 hours
_MAX_PENDING = 20


def _load() -> list[dict[str, Any]]:
    raw = load_json(_STATE_KEY, [])
    if not isinstance(raw, list):
        return []
    return [r for r in raw if isinstance(r, dict)]


def _save(records: list[dict[str, Any]]) -> None:
    save_json(_STATE_KEY, records)


def schedule_self_wakeup(
    *,
    delay_seconds: int,
    prompt: str,
    reason: str = "",
    channel: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Queue a self-wakeup. Returns the wakeup record."""
    prompt = (prompt or "").strip()
    reason = (reason or "").strip()
    if not prompt:
        return {"status": "error", "error": "prompt is required"}
    delay = int(max(_MIN_DELAY_SECONDS, min(_MAX_DELAY_SECONDS, delay_seconds)))

    records = _load()
    pending = [r for r in records if r.get("status") == "pending"]
    if len(pending) >= _MAX_PENDING:
        return {
            "status": "error",
            "error": f"max {_MAX_PENDING} pending wakeups; cancel one first",
        }

    fire_at = datetime.now(UTC) + timedelta(seconds=delay)
    wakeup_id = f"wake-{uuid4().hex[:10]}"
    record = {
        "wakeup_id": wakeup_id,
        "scheduled_at": datetime.now(UTC).isoformat(),
        "fire_at": fire_at.isoformat(),
        "delay_seconds": delay,
        "prompt": prompt[:1000],
        "reason": reason[:200],
        "status": "pending",
        "fired_at": None,
        "consumed_at": None,
        # Leverings-destination. Default "app" (jarvis-desk) — wakeups må ALDRIG
        # default'e til Discord (Bjørn 2026-06-13). Dispatcheren guarder mod det.
        "channel": (channel or "app").strip().lower(),
        "session_id": (session_id or "").strip() or None,
    }
    records.append(record)
    _save(records)

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "self_wakeup.scheduled",
            {"wakeup_id": wakeup_id, "fire_at": record["fire_at"],
             "reason": reason[:80], "delay_seconds": delay},
        )
    except Exception:
        pass

    return {"status": "ok", "wakeup": record}


def due_wakeups(*, include_fired_unconsumed: bool = True) -> list[dict[str, Any]]:
    """Return wakeups whose fire_at has passed and not yet consumed."""
    records = _load()
    now_iso = datetime.now(UTC).isoformat()
    out: list[dict[str, Any]] = []
    changed = False
    for r in records:
        status = str(r.get("status") or "")
        if status == "pending" and str(r.get("fire_at", "")) <= now_iso:
            r["status"] = "fired"
            r["fired_at"] = now_iso
            changed = True
            try:
                from core.eventbus.bus import event_bus
                event_bus.publish(
                    "self_wakeup.fired",
                    {"wakeup_id": r.get("wakeup_id"),
                     "reason": str(r.get("reason", ""))[:80]},
                )
            except Exception:
                pass
            out.append(r)
        elif status == "fired" and include_fired_unconsumed:
            out.append(r)
    if changed:
        _save(records)
    return out


def mark_wakeup_consumed(wakeup_id: str) -> dict[str, Any]:
    """Clear a fired wakeup once Jarvis has acted on it."""
    records = _load()
    record = next((r for r in records if r.get("wakeup_id") == wakeup_id), None)
    if record is None:
        return {"status": "error", "error": "wakeup not found"}
    if record.get("status") not in ("pending", "fired"):
        return {"status": "error", "error": f"wakeup status={record.get('status')}, can't consume"}
    record["status"] = "consumed"
    record["consumed_at"] = datetime.now(UTC).isoformat()
    _save(records)
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("self_wakeup.consumed", {"wakeup_id": wakeup_id})
    except Exception:
        pass
    return {"status": "ok", "wakeup_id": wakeup_id}


def cancel_wakeup(wakeup_id: str) -> dict[str, Any]:
    """Cancel a pending wakeup before it fires."""
    records = _load()
    record = next((r for r in records if r.get("wakeup_id") == wakeup_id), None)
    if record is None:
        return {"status": "error", "error": "wakeup not found"}
    if record.get("status") != "pending":
        return {"status": "error", "error": f"can't cancel wakeup with status={record.get('status')}"}
    record["status"] = "cancelled"
    _save(records)
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("self_wakeup.cancelled", {"wakeup_id": wakeup_id})
    except Exception:
        pass
    return {"status": "ok", "wakeup_id": wakeup_id}


def list_wakeups(*, status: str | None = None, limit: int = 30) -> list[dict[str, Any]]:
    records = _load()
    if status:
        records = [r for r in records if r.get("status") == status]
    records.sort(key=lambda r: str(r.get("scheduled_at", "")), reverse=True)
    return records[:limit]


def cleanup_old_wakeups(
    *,
    consumed_age_hours: int = 168,  # 7 days
    cancelled_age_hours: int = 168,
    stale_fired_age_hours: int = 24,
) -> dict[str, int]:
    """Ryd op i gamle consumed/cancelled/stale-fired wakeups.

    Args:
        consumed_age_hours: remove consumed entries older than this (default 7 dage)
        cancelled_age_hours: remove cancelled entries older than this (default 7 dage)
        stale_fired_age_hours: remove fired-but-never-consumed entries older than this (default 24h)

    Returns:
        {removed, remaining} — antal fjernede og tilbageværende wakeups
    """
    records = _load()
    now = datetime.now(UTC)
    kept: list[dict[str, Any]] = []
    removed = 0

    for r in records:
        status = str(r.get("status") or "")
        if status == "consumed":
            consumed_at = r.get("consumed_at")
            if consumed_at:
                try:
                    age = (now - datetime.fromisoformat(consumed_at)).total_seconds() / 3600
                    if age >= consumed_age_hours:
                        removed += 1
                        continue
                except (ValueError, TypeError):
                    pass
        elif status == "cancelled":
            # Brug scheduled_at som proxy hvis cancelled_at ikke findes
            cancelled_ref = r.get("cancelled_at") or r.get("scheduled_at") or ""
            if cancelled_ref:
                try:
                    age = (now - datetime.fromisoformat(cancelled_ref)).total_seconds() / 3600
                    if age >= cancelled_age_hours:
                        removed += 1
                        continue
                except (ValueError, TypeError):
                    pass
        elif status == "fired" and not r.get("consumed_at"):
            fired_at = r.get("fired_at") or ""
            if fired_at:
                try:
                    age = (now - datetime.fromisoformat(fired_at)).total_seconds() / 3600
                    if age >= stale_fired_age_hours:
                        removed += 1
                        continue
                except (ValueError, TypeError):
                    pass
        kept.append(r)

    _save(kept)
    logger.info("cleanup_old_wakeups: removed=%d, remaining=%d", removed, len(kept))
    return {"removed": removed, "remaining": len(kept)}


def tick_wakeup_cleanup() -> dict[str, int]:
    """Daemon tick — ryd op i gamle wakeups.

    Kører periodisk (default 60 min) for at forhindre wakeup-bloat.
    Returnerer antal fjernede og tilbageværende.
    """
    return cleanup_old_wakeups()


def self_wakeup_section() -> str | None:
    """Awareness section showing fired-but-not-consumed wakeups."""
    fired = due_wakeups(include_fired_unconsumed=True)
    fired = [r for r in fired if str(r.get("status") or "") == "fired"]
    if not fired:
        return None
    lines = [f"⏰ Du planlagde {len(fired)} self-wakeup(s) der nu er klar:"]
    for r in fired[:3]:
        wid = str(r.get("wakeup_id", ""))
        prompt = str(r.get("prompt", ""))[:200]
        reason = str(r.get("reason", ""))
        reason_part = f" ({reason})" if reason else ""
        lines.append(f"  • {wid}{reason_part}: {prompt}")
    lines.append(
        "Når du har handlet på en af dem, brug `mark_wakeup_consumed(wakeup_id)` "
        "så den ikke gentager sig i din awareness."
    )
    return "\n".join(lines)


# ── Tools ──────────────────────────────────────────────────────


def _exec_schedule_self_wakeup(args: dict[str, Any]) -> dict[str, Any]:
    return schedule_self_wakeup(
        delay_seconds=int(args.get("delay_seconds") or 60),
        prompt=str(args.get("prompt") or ""),
        reason=str(args.get("reason") or ""),
    )


def _exec_list_self_wakeups(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "ok",
        "wakeups": list_wakeups(
            status=args.get("status"),
            limit=int(args.get("limit") or 30),
        ),
    }


def _exec_cancel_self_wakeup(args: dict[str, Any]) -> dict[str, Any]:
    return cancel_wakeup(str(args.get("wakeup_id") or ""))


def _exec_mark_wakeup_consumed(args: dict[str, Any]) -> dict[str, Any]:
    return mark_wakeup_consumed(str(args.get("wakeup_id") or ""))


SELF_WAKEUP_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "schedule_self_wakeup",
            "description": (
                "Schedule a self-wakeup: when delay_seconds passes, the prompt "
                "surfaces in your awareness so you can resume that line of "
                "thought. Equivalent to Claude Code's ScheduleWakeup but "
                "persistent across restarts. Use for: 'wait 5 min then check X', "
                "'remind me to ask the user Y in 1 hour'. Bounded to "
                "60-86400 seconds (1 min - 24 hours)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "delay_seconds": {"type": "integer"},
                    "prompt": {"type": "string", "description": "What to resume / do when waking."},
                    "reason": {"type": "string", "description": "Short label for telemetry."},
                },
                "required": ["delay_seconds", "prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_self_wakeups",
            "description": "List your queued/fired/consumed self-wakeups. Optional status filter.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["pending", "fired", "consumed", "cancelled"]},
                    "limit": {"type": "integer"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_self_wakeup",
            "description": "Cancel a pending wakeup before it fires.",
            "parameters": {
                "type": "object",
                "properties": {"wakeup_id": {"type": "string"}},
                "required": ["wakeup_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mark_wakeup_consumed",
            "description": "Mark a fired wakeup as consumed so it doesn't re-surface in awareness.",
            "parameters": {
                "type": "object",
                "properties": {"wakeup_id": {"type": "string"}},
                "required": ["wakeup_id"],
            },
        },
    },
]
