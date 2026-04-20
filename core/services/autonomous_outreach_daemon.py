"""Autonomous Outreach Daemon — Jarvis reaches out on his own initiative.

Jarvis' plan #6 (PLAN_PROPRIOCEPTION.md, 2026-04-20): combine signals
(time_since_last_contact, interesting events, unfinished threads) and
send proactive messages when they carry real value — never "are you
there?", always concrete observations.

Safety:
- Rate limit: max 1 outreach per 4 hours
- Quiet hours: 22-07 local time (suppress unless high priority)
- Value gate: must have at least one "interesting" signal OR unpaused
  thread older than 48h
- Channel: ntfy (quiet push). Telegram/Discord can be added later.
- Every decision (sent | skipped) is logged to the outreach log.

Trigger cadence: on heartbeat tick. Internally cooldown-gated.
"""
from __future__ import annotations

import json
import logging
import os
from collections import deque
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Deque

logger = logging.getLogger(__name__)

_STORAGE_REL = "workspaces/default/runtime/outreach_log.json"
_LOG_MAX = 200

_COOLDOWN_HOURS = 4
_QUIET_HOURS_START = 22  # inclusive
_QUIET_HOURS_END = 7     # exclusive
_MIN_CONTACT_GAP_HOURS = 2  # don't reach out if user was active recently


def _storage_path() -> Path:
    base = os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2")
    return Path(base) / _STORAGE_REL


def _load_log() -> list[dict[str, Any]]:
    path = _storage_path()
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception as exc:
        logger.warning("autonomous_outreach: load failed: %s", exc)
    return []


def _save_log(items: list[dict[str, Any]]) -> None:
    if len(items) > _LOG_MAX:
        items = items[-_LOG_MAX:]
    path = _storage_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except Exception as exc:
        logger.warning("autonomous_outreach: save failed: %s", exc)


def _last_outreach_sent() -> datetime | None:
    for entry in reversed(_load_log()):
        if entry.get("outcome") == "sent":
            try:
                return datetime.fromisoformat(str(entry.get("at")).replace("Z", "+00:00"))
            except Exception:
                pass
    return None


def _is_quiet_hours(now_local: datetime) -> bool:
    hour = now_local.hour
    # Quiet = hour >= 22 OR hour < 7
    return hour >= _QUIET_HOURS_START or hour < _QUIET_HOURS_END


def _hours_since_last_user_contact() -> float:
    try:
        from core.runtime.db import recent_visible_runs
        runs = recent_visible_runs(limit=10) or []
        for r in runs:
            ts = str(r.get("started_at") or "")
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                return (datetime.now(UTC) - dt).total_seconds() / 3600
            except Exception:
                continue
    except Exception:
        pass
    return 999.0  # unknown → treat as "long ago"


def _gather_interesting_events() -> list[dict[str, Any]]:
    """Collect potentially noteworthy signals from other services."""
    events: list[dict[str, Any]] = []
    # Avoidance findings
    try:
        from core.services.avoidance_detector import detect_avoidances
        for f in detect_avoidances()[:2]:
            events.append({
                "source": "avoidance",
                "title": f.get("sample_title"),
                "detail": f"stille i {f.get('days_silent')} dage",
                "priority": "low",
            })
    except Exception:
        pass
    # Dream auto-promotions (confirmed insight)
    try:
        from core.services.dream_insight_daemon import get_recent_confirmed_dreams  # type: ignore
        confirmed = get_recent_confirmed_dreams() or []
        for d in confirmed[:1]:
            events.append({
                "source": "dream-insight",
                "title": str(d.get("title") or d.get("summary") or "")[:100],
                "detail": "dream confirmed across sessions",
                "priority": "medium",
            })
    except Exception:
        pass
    # Anticipatory peak incoming
    try:
        from core.services.anticipatory_action_daemon import build_anticipatory_action_surface
        s = build_anticipatory_action_surface() or {}
        for p in (s.get("upcoming_peaks") or [])[:1]:
            if p.get("minutes_until", 999) <= 30 and p.get("confidence", 0) >= 0.8:
                events.append({
                    "source": "anticipation",
                    "title": f"Peak-time om {p['minutes_until']}m",
                    "detail": f"kl {p['hour']:02d} — vil du have noget klar?",
                    "priority": "low",
                })
    except Exception:
        pass
    # Unfinished cross-session threads paused >= 48h
    try:
        from core.services.cross_session_threads import list_threads
        paused = list_threads(status="paused")
        now = datetime.now(UTC)
        for t in paused:
            try:
                paused_at = datetime.fromisoformat(str(t.get("paused_at") or "").replace("Z", "+00:00"))
                if (now - paused_at) >= timedelta(hours=48):
                    events.append({
                        "source": "paused-thread",
                        "title": t.get("topic"),
                        "detail": "pauset i 2+ dage — vil du tage fat igen?",
                        "priority": "medium",
                    })
                    break
            except Exception:
                continue
    except Exception:
        pass
    return events


def _compose_message(events: list[dict[str, Any]]) -> str:
    """Build a concrete, value-carrying outreach message from events."""
    if not events:
        return ""
    top = events[0]
    body_parts: list[str] = [f"{top.get('title', '')} — {top.get('detail', '')}"]
    if len(events) > 1:
        tail = events[1]
        body_parts.append(f"Og: {tail.get('title', '')}")
    return " · ".join(p for p in body_parts if p.strip())


def _highest_priority(events: list[dict[str, Any]]) -> str:
    priorities = {"high": 3, "medium": 2, "low": 1}
    if not events:
        return "low"
    return max(events, key=lambda e: priorities.get(str(e.get("priority") or "low"), 1)).get("priority", "low")


def _log_decision(
    *,
    outcome: str,
    reason: str,
    events: list[dict[str, Any]] | None = None,
    message: str | None = None,
    priority: str | None = None,
    channel: str | None = None,
) -> None:
    log = _load_log()
    log.append({
        "at": datetime.now(UTC).isoformat(),
        "outcome": outcome,
        "reason": reason,
        "event_count": len(events or []),
        "priority": priority,
        "channel": channel,
        "message": (message or "")[:300],
    })
    _save_log(log)


def _send_via_ntfy(message: str, *, priority: str = "default") -> bool:
    """Send outreach via ntfy. Returns True on success."""
    try:
        from core.services.ntfy_gateway import send_notification
        result = send_notification(message, title="Jarvis", priority=priority)
        return bool(result.get("status") == "sent")
    except Exception as exc:
        logger.debug("autonomous_outreach: ntfy send failed: %s", exc)
        return False


def attempt_outreach() -> dict[str, Any]:
    """Consider whether to reach out, do so if appropriate. Returns decision dict."""
    now_local = datetime.now().astimezone()

    # Cooldown gate
    last = _last_outreach_sent()
    if last is not None:
        hours_since_last = (datetime.now(UTC) - last).total_seconds() / 3600
        if hours_since_last < _COOLDOWN_HOURS:
            decision = {
                "outcome": "skipped",
                "reason": f"cooldown ({hours_since_last:.1f}h < {_COOLDOWN_HOURS}h)",
            }
            _log_decision(**decision)
            return decision

    # Contact gap gate — if user was active recently, no need to reach out
    hours_since_user = _hours_since_last_user_contact()
    if hours_since_user < _MIN_CONTACT_GAP_HOURS:
        decision = {
            "outcome": "skipped",
            "reason": f"user-active-recently ({hours_since_user:.1f}h)",
        }
        _log_decision(**decision)
        return decision

    # Gather signals
    events = _gather_interesting_events()
    if not events:
        decision = {
            "outcome": "skipped",
            "reason": "no-interesting-events",
        }
        _log_decision(**decision)
        return decision

    priority = _highest_priority(events)

    # Quiet hours gate
    if _is_quiet_hours(now_local) and priority != "high":
        decision = {
            "outcome": "skipped",
            "reason": f"quiet-hours (priority={priority})",
            "events": events,
        }
        _log_decision(**decision)
        return decision

    # Compose and send
    message = _compose_message(events)
    if not message:
        decision = {
            "outcome": "skipped",
            "reason": "empty-message",
            "events": events,
        }
        _log_decision(**decision)
        return decision

    ntfy_priority = "high" if priority == "high" else "low"
    sent = _send_via_ntfy(message, priority=ntfy_priority)
    if sent:
        decision = {
            "outcome": "sent",
            "reason": "outreach-delivered",
            "events": events,
            "message": message,
            "priority": priority,
            "channel": "ntfy",
        }
        _log_decision(**decision)
        try:
            from core.eventbus.bus import event_bus
            event_bus.publish({
                "kind": "autonomous_outreach.sent",
                "payload": {
                    "message": message[:240],
                    "priority": priority,
                    "channel": "ntfy",
                },
            })
        except Exception:
            pass
        return decision
    decision = {
        "outcome": "skipped",
        "reason": "send-failed",
        "events": events,
        "message": message,
    }
    _log_decision(**decision)
    return decision


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    """Heartbeat hook — evaluate outreach candidacy."""
    try:
        return attempt_outreach()
    except Exception as exc:
        logger.debug("autonomous_outreach.tick failed: %s", exc)
        return {"outcome": "error", "reason": str(exc)}


def recent_log(*, limit: int = 20) -> list[dict[str, Any]]:
    return _load_log()[-limit:][::-1]


def build_autonomous_outreach_surface() -> dict[str, Any]:
    log = _load_log()
    sent = [e for e in log if e.get("outcome") == "sent"]
    skipped = [e for e in log if e.get("outcome") == "skipped"]
    last_sent = sent[-1] if sent else None
    return {
        "active": len(sent) > 0,
        "total_attempts": len(log),
        "sent_count": len(sent),
        "skipped_count": len(skipped),
        "last_sent": last_sent,
        "recent_log": log[-5:][::-1],
        "cooldown_hours": _COOLDOWN_HOURS,
        "quiet_hours": f"{_QUIET_HOURS_START}-{_QUIET_HOURS_END}",
        "summary": _surface_summary(sent, skipped, last_sent),
    }


def _surface_summary(
    sent: list[dict[str, Any]], skipped: list[dict[str, Any]], last: dict[str, Any] | None
) -> str:
    if last:
        last_at = str(last.get("at") or "")[:19]
        return f"{len(sent)} outreach sendt (sidst {last_at}), {len(skipped)} skipped"
    if skipped:
        last_skip = skipped[-1]
        return f"0 sendt, senest skipped: {last_skip.get('reason')}"
    return "Ingen outreach-forsøg endnu"
