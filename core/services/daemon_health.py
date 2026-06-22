"""Daemon-helbred (Fase 1) — gør de standalone daemon-tråde + silent eventbus-listeners
synlige i Den Intelligente Central. Deres fejl blev logget (debug/warning) eller SLUGT
(except: pass) men nåede ALDRIG central.observe → deres helbred var usynligt.

De 25 cadence-producers (internal_cadence) + 81 heartbeat-tickede (daemon_manager) er allerede
observable. Dette dækker resten: ~9 standalone-tråde (cartographer/process_watcher m.fl.) +
~16 eventbus-listeners der ellers fejler i stilhed. MEKANISME til inkrementel adoption: kald
note_error i hver daemons except-sti (og evt. note_tick på succes).

Self-safe; kaster aldrig ind i daemon-loopet.
"""
from __future__ import annotations

from typing import Any


def note_error(daemon: str, error: Any, **data: Any) -> None:
    """En daemon/listener fejlede. → observe (cluster=system, nerve=daemon_health, ok=False)."""
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "system", "nerve": "daemon_health",
            "daemon": str(daemon or ""), "ok": False,
            "error": f"{type(error).__name__}: {error}"[:160], **data,
        })
    except Exception:
        pass


def note_tick(daemon: str, *, ok: bool = True, **data: Any) -> None:
    """En daemon kørte en cyklus. Valgfri helbreds-puls (brug sparsomt — fejl er hovedsignalet)."""
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "system", "nerve": "daemon_health",
            "daemon": str(daemon or ""), "ok": bool(ok), **data,
        })
    except Exception:
        pass


def daemon_health_summary(*, window: int = 1000) -> dict[str, Any]:
    """Read-only: hvilke daemons har fejlet i seneste trace (til MC/debug). Self-safe."""
    fails: dict[str, int] = {}
    try:
        from core.services import central_trace
        for r in central_trace.sink().recent()[-window:]:
            if r.cluster == "system" and r.nerve == "daemon_health":
                p = r.payload or {}
                if not p.get("ok"):
                    d = str(p.get("daemon") or "")
                    fails[d] = fails.get(d, 0) + 1
    except Exception:
        pass
    return {"failing_daemons": fails, "failing_count": len(fails)}
