"""Public-safe /status endpoint.

Designed for external consumers (the Jarvis home site at 192.168.50.32) to
poll without exposing the full API surface. Returns only the minimum needed
to render an 'online + uptime' badge. No app_name, no environment, no
provider info, no secrets.

Reverse-proxied via nginx on the home site; clients never talk to the
Jarvis API directly.
"""
from __future__ import annotations

import time

from fastapi import APIRouter

router = APIRouter()

_STARTED_AT = time.time()


def _format_uptime(seconds: float) -> str:
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}m"
    h, m = divmod(m, 60)
    if h < 24:
        return f"{h}h {m}m" if m else f"{h}h"
    d, h = divmod(h, 24)
    return f"{d}d {h}h" if h else f"{d}d"


def _daemon_count() -> int:
    try:
        from core.services.daemon_manager import get_all_daemon_states
        return sum(1 for d in get_all_daemon_states() if d.get("enabled"))
    except Exception:
        return 0


def _visible_model_label() -> str:
    try:
        from core.runtime.settings import load_settings
        s = load_settings()
        return s.visible_model_name or "unknown"
    except Exception:
        return "unknown"


@router.get("/status")
def status() -> dict:
    uptime_seconds = max(0.0, time.time() - _STARTED_AT)
    return {
        "online": True,
        "uptime_seconds": int(uptime_seconds),
        "uptime_human": _format_uptime(uptime_seconds),
        "uptime": _format_uptime(uptime_seconds),
        "daemons": _daemon_count(),
        "model": _visible_model_label(),
    }
