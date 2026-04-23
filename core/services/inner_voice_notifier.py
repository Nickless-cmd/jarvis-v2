"""Inner voice notifier — proactive notification when a thought has substance.

Subscribes to `private_inner_note_signal.voice_daemon_produced` events. When
Jarvis produces a private inner-voice note that is substantive (initiative
detected, mode == "pulled", or summary long enough), this notifier pushes a
short message into the active user session via notification_bridge.

Opt-in via setting `inner_voice_notify_enabled` (default False). Respects
quiet hours (22:00–07:00 local, default) and a hard cooldown (120 min
default) so the user never gets spammed with half-baked half-thoughts.
"""
from __future__ import annotations

import logging
import queue
import threading
from datetime import UTC, datetime, timedelta
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db import (
    get_private_brain_record,
    get_runtime_state_value,
    set_runtime_state_value,
)

logger = logging.getLogger(__name__)

_SUPPORTED_KIND = "private_inner_note_signal.voice_daemon_produced"
_STATE_KEY = "inner_voice_notifier.state"
_DEFAULT_COOLDOWN_MINUTES = 120
_DEFAULT_MIN_SUMMARY_CHARS = 80
_DEFAULT_QUIET_START_HOUR = 22
_DEFAULT_QUIET_END_HOUR = 7

_SUBSCRIBER_THREAD: threading.Thread | None = None
_SUBSCRIBER_STOP = threading.Event()
_SUBSCRIBER_QUEUE: queue.Queue[dict[str, Any] | None] | None = None


def start_inner_voice_notifier() -> None:
    global _SUBSCRIBER_THREAD, _SUBSCRIBER_QUEUE
    if _SUBSCRIBER_THREAD and _SUBSCRIBER_THREAD.is_alive():
        return
    _SUBSCRIBER_STOP.clear()
    subscriber = event_bus.subscribe()
    _SUBSCRIBER_QUEUE = subscriber
    thread = threading.Thread(
        target=_subscriber_loop,
        kwargs={"subscriber": subscriber},
        name="jarvis-inner-voice-notifier",
        daemon=True,
    )
    thread.start()
    _SUBSCRIBER_THREAD = thread
    logger.info("inner_voice_notifier: started")


def stop_inner_voice_notifier() -> None:
    global _SUBSCRIBER_THREAD, _SUBSCRIBER_QUEUE
    _SUBSCRIBER_STOP.set()
    subscriber = _SUBSCRIBER_QUEUE
    if subscriber is not None:
        event_bus.unsubscribe(subscriber)
    thread = _SUBSCRIBER_THREAD
    if thread and thread.is_alive():
        thread.join(timeout=1.0)
    _SUBSCRIBER_THREAD = None
    _SUBSCRIBER_QUEUE = None
    logger.info("inner_voice_notifier: stopped")


def _subscriber_loop(*, subscriber: queue.Queue[dict[str, Any] | None]) -> None:
    while not _SUBSCRIBER_STOP.is_set():
        try:
            item = subscriber.get(timeout=0.5)
        except queue.Empty:
            continue
        if item is None:
            break
        if not isinstance(item, dict):
            continue
        if str(item.get("kind") or "") != _SUPPORTED_KIND:
            continue
        try:
            _handle_event(dict(item.get("payload") or {}))
        except Exception as exc:
            logger.warning("inner_voice_notifier: handler failed: %s", exc)


def _handle_event(payload: dict[str, Any]) -> None:
    if not _notifier_enabled():
        return
    if not payload.get("created"):
        return

    record_id = str(payload.get("record_id") or "").strip()
    if not record_id:
        return

    record = get_private_brain_record(record_id) or {}
    summary = str(record.get("summary") or "").strip()
    if not summary:
        return

    mode = str(payload.get("mode") or "").strip()
    initiative = str(payload.get("initiative") or "").strip()
    initiative_detected = bool(payload.get("initiative_detected"))

    if not _is_substantive(
        summary=summary,
        mode=mode,
        initiative=initiative,
        initiative_detected=initiative_detected,
    ):
        return

    now = datetime.now(UTC)
    if _in_quiet_hours(now):
        return
    if _in_cooldown(now):
        return

    message = _format_message(summary=summary, initiative=initiative, mode=mode)

    try:
        from core.services.notification_bridge import send_session_notification
        result = send_session_notification(message, source="inner-voice-notifier")
    except Exception as exc:
        logger.warning("inner_voice_notifier: delivery raised: %s", exc)
        return

    if isinstance(result, dict) and result.get("status") == "ok":
        _record_sent(now, record_id=record_id)
        try:
            event_bus.publish(
                "inner_voice_notifier.delivered",
                {
                    "record_id": record_id,
                    "mode": mode,
                    "at": now.isoformat(),
                },
            )
        except Exception:
            pass
    else:
        logger.debug("inner_voice_notifier: delivery not ok: %s", result)


def _is_substantive(
    *,
    summary: str,
    mode: str,
    initiative: str,
    initiative_detected: bool,
) -> bool:
    if initiative_detected and initiative:
        return True
    if mode == "pulled":
        return True
    if len(summary) >= _min_summary_chars():
        return True
    return False


def _format_message(*, summary: str, initiative: str, mode: str) -> str:
    prefix = f"💭 [inner voice · {mode}]" if mode else "💭 [inner voice]"
    body = summary.strip()
    if initiative:
        body = f"{body}\n→ {initiative}"
    return f"{prefix}: {body}"


def _notifier_enabled() -> bool:
    try:
        from core.runtime.settings import load_settings
        settings = load_settings()
        return bool(settings.extra.get("inner_voice_notify_enabled", False))
    except Exception:
        return False


def _min_summary_chars() -> int:
    try:
        from core.runtime.settings import load_settings
        settings = load_settings()
        value = int(settings.extra.get("inner_voice_notify_min_chars") or _DEFAULT_MIN_SUMMARY_CHARS)
        return max(20, min(value, 1000))
    except Exception:
        return _DEFAULT_MIN_SUMMARY_CHARS


def _cooldown_minutes() -> int:
    try:
        from core.runtime.settings import load_settings
        settings = load_settings()
        value = int(settings.extra.get("inner_voice_notify_cooldown_minutes") or _DEFAULT_COOLDOWN_MINUTES)
        return max(5, min(value, 60 * 24))
    except Exception:
        return _DEFAULT_COOLDOWN_MINUTES


def _quiet_hours() -> tuple[int, int]:
    try:
        from core.runtime.settings import load_settings
        settings = load_settings()
        start = int(settings.extra.get("inner_voice_notify_quiet_start") or _DEFAULT_QUIET_START_HOUR)
        end = int(settings.extra.get("inner_voice_notify_quiet_end") or _DEFAULT_QUIET_END_HOUR)
        return (max(0, min(23, start)), max(0, min(23, end)))
    except Exception:
        return (_DEFAULT_QUIET_START_HOUR, _DEFAULT_QUIET_END_HOUR)


def _in_quiet_hours(now: datetime) -> bool:
    start, end = _quiet_hours()
    hour = now.astimezone().hour
    if start == end:
        return False
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end


def _state() -> dict[str, Any]:
    val = get_runtime_state_value(_STATE_KEY, default={})
    return dict(val) if isinstance(val, dict) else {}


def _in_cooldown(now: datetime) -> bool:
    state = _state()
    last = str(state.get("last_sent_at") or "")
    if not last:
        return False
    try:
        last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
    except Exception:
        return False
    return (now - last_dt) < timedelta(minutes=_cooldown_minutes())


def _record_sent(now: datetime, *, record_id: str) -> None:
    state = _state()
    history = list(state.get("history") or [])
    history.insert(0, {"record_id": record_id, "sent_at": now.isoformat()})
    history = history[:50]
    set_runtime_state_value(
        _STATE_KEY,
        {
            "last_sent_at": now.isoformat(),
            "last_record_id": record_id,
            "history": history,
        },
    )


def get_inner_voice_notifier_state() -> dict[str, Any]:
    state = _state()
    return {
        "enabled": _notifier_enabled(),
        "cooldown_minutes": _cooldown_minutes(),
        "min_summary_chars": _min_summary_chars(),
        "quiet_hours": _quiet_hours(),
        "last_sent_at": state.get("last_sent_at") or "",
        "last_record_id": state.get("last_record_id") or "",
        "history": list(state.get("history") or [])[:10],
    }
