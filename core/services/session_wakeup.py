"""Eventbus → visible-prompt wake-up digest.

When a visible session starts a new turn, this module assembles a short
"siden vi sidst snakkede" block of *notable* events that fired on the
eventbus while the session was idle (or while another channel was
active). Without this, every turn starts cold — the model has no idea
that Discord crashed twice, an approval card is waiting, or a
recurring task failed in the background.

Pattern lifted from how Claude Code's harness wakes me when a Monitor
fires: the event isn't a user message, but it lands in my context as
a system observation so I can react proactively.

Per-session ``last_seen_event_id`` is persisted via state_store so the
digest doesn't repeat events across restarts.
"""
from __future__ import annotations

import logging
from typing import Any

from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)

_STATE_KEY = "session_wakeup_marks"
_MAX_DIGEST_EVENTS = 5
_LOOKBACK_LIMIT = 200  # how many recent events to scan per turn

# Event kinds worth surfacing to the visible model. Everything else is
# either too noisy (circadian/heartbeat ticks, tool.invoked spam) or
# already implicit in the conversation (the user's own run events).
_NOTABLE_KINDS = (
    "runtime.error",
    "runtime.warning",
    "runtime.crash",
    "runtime.autonomous_run_failed",
    "runtime.api_unhandled_exception",
    "channel.bridge_offline",
    "channel.bridge_recovered",
    "channel.discord_dm_failed_unrecoverable",
    "channel.discord_send_failed",
    "tool.invocation_failed",
    "tool.execution_error",
    "approval.pending",
    "approval.denied",
    "cost.budget_threshold",
    "cost.budget_exceeded",
    "heartbeat.degraded",
    "heartbeat.recovered",
    "self_review.flagged",
    "incident.opened",
    "incident.escalated",
    "surprise.detected",
)


def _is_notable(kind: str) -> bool:
    if not kind:
        return False
    if kind in _NOTABLE_KINDS:
        return True
    # Allow any incident.* and any runtime.*_failed pattern by prefix.
    if kind.startswith("incident."):
        return True
    if kind.startswith("runtime.") and kind.endswith("_failed"):
        return True
    return False


def _load_marks() -> dict[str, int]:
    raw = load_json(_STATE_KEY, {})
    if not isinstance(raw, dict):
        return {}
    out: dict[str, int] = {}
    for k, v in raw.items():
        try:
            out[str(k)] = int(v)
        except Exception:
            continue
    return out


def _save_marks(marks: dict[str, int]) -> None:
    save_json(_STATE_KEY, marks)


def last_seen_event_id(session_id: str) -> int:
    return int(_load_marks().get(str(session_id or "_default"), 0))


def mark_seen(session_id: str, event_id: int) -> None:
    sid = str(session_id or "_default")
    marks = _load_marks()
    if int(event_id) > int(marks.get(sid, 0)):
        marks[sid] = int(event_id)
        _save_marks(marks)


def _format_event(ev: dict[str, Any]) -> str:
    kind = str(ev.get("kind", "?"))
    payload = ev.get("payload") or {}
    # Pick the most informative single field: error > message > summary > focus.
    detail = ""
    for key in ("error", "message", "summary", "focus", "tool", "reason"):
        val = payload.get(key) if isinstance(payload, dict) else None
        if val:
            detail = str(val)[:140]
            break
    ts = str(ev.get("created_at", ""))[11:19]  # HH:MM:SS slice
    if detail:
        return f"- [{ts}] {kind}: {detail}"
    return f"- [{ts}] {kind}"


def wakeup_digest(session_id: str | None) -> str | None:
    """Return a short digest of notable events since this session last saw,
    or None if nothing notable. Updates the per-session mark as a side effect.
    """
    sid = str(session_id or "_default")
    try:
        from core.eventbus.bus import event_bus
    except Exception as exc:
        logger.debug("session_wakeup: eventbus import failed: %s", exc)
        return None

    last_id = last_seen_event_id(sid)
    try:
        if last_id > 0:
            recent = event_bus.recent_since_id(last_id, limit=_LOOKBACK_LIMIT)
        else:
            # First turn ever — only show very recent activity, not full history.
            recent = event_bus.recent(limit=30)
    except Exception as exc:
        logger.debug("session_wakeup: eventbus fetch failed: %s", exc)
        return None

    notable = [e for e in recent if _is_notable(str(e.get("kind", "")))]

    # Always advance the mark to the newest seen event id, even if nothing
    # was notable — otherwise a quiet hour with one boring event would
    # keep replaying it.
    if recent:
        newest = max(int(e.get("id", 0) or 0) for e in recent)
        if newest > last_id:
            mark_seen(sid, newest)

    if not notable:
        return None

    # Newest first, capped.
    notable_sorted = sorted(notable, key=lambda e: int(e.get("id", 0) or 0), reverse=True)
    bullets = [_format_event(e) for e in notable_sorted[:_MAX_DIGEST_EVENTS]]
    header = (
        "Siden vi sidst snakkede er disse hændelser sket i baggrunden "
        "(nævn dem kun hvis relevant for nu):"
    )
    return header + "\n" + "\n".join(bullets)
