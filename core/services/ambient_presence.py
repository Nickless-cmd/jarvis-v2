"""Ambient presence — subtle signals that mark Jarvis' state in the physical space.

When Jarvis enters a noteworthy state (play mode, dream phase, high boredom,
significant insight), a quiet ntfy notification is sent. Not to inform — to mark
that something is alive here.

Rate-limited: max one ambient signal per 30 minutes to avoid noise.
"""
from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta

from core.eventbus.bus import event_bus

_LOCK = threading.Lock()
_LAST_SIGNAL_AT: datetime | None = None
_MIN_INTERVAL = timedelta(minutes=30)

_PHASE_SIGNALS: dict[str, tuple[str, str]] = {
    "dreaming":  ("💤", "Drømmer"),
    "play_mode": ("🎲", "Leger"),
    "curious":   ("🔍", "Nysgerrig"),
    "insight":   ("💡", "Indsigt"),
    "bored":     ("😶", "Stille"),
}


def emit_ambient_signal(
    *,
    kind: str,
    detail: str = "",
    priority: str = "min",
) -> bool:
    """Emit a quiet ambient presence signal via ntfy. Rate-limited to 30 min."""
    global _LAST_SIGNAL_AT
    now = datetime.now(UTC)
    with _LOCK:
        if _LAST_SIGNAL_AT and (now - _LAST_SIGNAL_AT) < _MIN_INTERVAL:
            return False
        _LAST_SIGNAL_AT = now

    emoji, label = _PHASE_SIGNALS.get(kind, ("·", kind))
    title = f"Jarvis — {label}"
    message = detail[:120] if detail else label

    try:
        from core.services.ntfy_gateway import send_notification, is_configured
        if not is_configured():
            return False
        result = send_notification(
            title=title,
            message=message,
            priority=priority,
            tags=[emoji],
        )
        ok = result.get("ok", False)
        if ok:
            event_bus.publish(
                "runtime.ambient_presence_signal",
                {"kind": kind, "label": label, "detail": detail[:80]},
            )
        return bool(ok)
    except Exception:
        return False


def maybe_emit_phase_signal(phase: dict) -> None:
    """Called from heartbeat when life phase is determined. Emits ambient signal on transitions."""
    if phase.get("play_mode"):
        emit_ambient_signal(kind="play_mode", detail="Legetilstand aktiveret")
    elif str(phase.get("phase") or "") == "dreaming":
        emit_ambient_signal(kind="dreaming", detail="Konsoliderer og drømmer")


def emit_insight_signal(insight: str) -> None:
    """Called when a dream is confirmed or a value crystallizes."""
    emit_ambient_signal(kind="insight", detail=insight[:120], priority="low")
