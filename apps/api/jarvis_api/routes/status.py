"""Status-endpoints til forsiden — én rig og én offentlig.

## To ruter, to målgrupper (25/10-2026)

``/status`` er den RIGE status: den bærer ``model`` og ``daemons``. Den kræver
token (den står ikke i ``_PUBLIC_PATHS``), fordi modelnavnet og antallet af
aktive daemons er intern drift-information.

Docstringen her påstod indtil 25/10 at ``/status`` var «public-safe» og «kun
online + uptime». Det passede ikke: ruten returnerede både ``model`` og
``daemons``, mens vhosten på forsiden proxyede ``/api/status`` dertil uden
token — og fik 401. Kommentaren og koden var uenige, og kommentaren var den
der blev læst.

``/status/public`` er den offentlige: kun ``online`` og uptime. Den står i
``_PUBLIC_PATHS`` og proxies af forsiden. Den bærer intet der fortæller
noget om hvad der kører — kun at noget kører, og hvor længe.

Reverse-proxied via Apache på webserveren; klienter taler aldrig direkte med
Jarvis-API'et (det lytter kun på loopback).
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
    """Den RIGE status. Kræver token — bærer model og daemons."""
    uptime_seconds = max(0.0, time.time() - _STARTED_AT)
    return {
        "online": True,
        "uptime_seconds": int(uptime_seconds),
        "uptime_human": _format_uptime(uptime_seconds),
        "uptime": _format_uptime(uptime_seconds),
        "daemons": _daemon_count(),
        "model": _visible_model_label(),
    }


@router.get("/status/public")
def status_public() -> dict:
    """Den OFFENTLIGE status: online + uptime, intet andet.

    Bevidst smallere end ``/status``. Feltlisten er en kontrakt: tilføjer
    nogen ``model``, ``daemons`` eller et versionstal her, bliver det
    læsbart for alle på internettet uden token — det er hele grunden til at
    ruten findes separat i stedet for at nogen bare lemper på ``/status``.
    """
    uptime_seconds = max(0.0, time.time() - _STARTED_AT)
    return {
        "online": True,
        "uptime_seconds": int(uptime_seconds),
        "uptime_human": _format_uptime(uptime_seconds),
    }
