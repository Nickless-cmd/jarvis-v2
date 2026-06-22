"""Stream-cluster — observabilitet for SSE-lanen. IKKE en blokerende gate: streaming er
en LANE med mange fejl-punkter, ikke en beslutning. Gør lanens livscyklus + fejl synlige
i Den Intelligente Central (central.observe) så hængende streams / manglende message_stop
/ zombie-slots FANGES og flagges — i stedet for at Bjørn opdager dem i blinde.

Historisk levede streaming-bugs her usynligt: ~25 tavse ``except: pass`` i SSE-pipelinen,
ingen central trace. Nu emitterer hver lane-overgang (start/stop/idle/cancel/error/zombie/
subscriber_timeout) et central.observe pr. run_id, og en stall-backstop flagger en stream
der fik message_start men ALDRIG message_stop.

Stall-tærsklen (300s) ligger BEVIDST over translatorens egen idle-oprydning (~180s), så
vi kun flagger ægte zombier (task helt død) — ikke lange legitime runs eller streams som
translatorens finally selv lukker. Incident-severity = 'error' (pollbar, ingen push) for
ikke at vække på en mulig false-positive.

SELV-SIKKER: kaster ALDRIG ind i den hotte SSE-sti.
"""
from __future__ import annotations

import threading
import time
from typing import Any

_CLUSTER = "stream"
_STALL_AFTER_S = 300.0  # message_start uden message_stop i >5 min → ægte zombie → flag

# run_id -> {"start": monotonic, "session_id": str, "meta": dict, "flagged": bool}
_live: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def _observe(nerve: str, run_id: str, session_id: str, **data: Any) -> None:
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": _CLUSTER, "nerve": nerve,
            "run_id": run_id, "session_id": session_id, **data,
        })
    except Exception:
        pass


def note_start(run_id: str, session_id: str = "", **meta: Any) -> None:
    """En SSE-stream sendte message_start. Registrér + observe + opportunistisk stall-sweep."""
    rid = str(run_id or "")
    if not rid:
        return
    try:
        with _lock:
            _live[rid] = {"start": time.monotonic(), "session_id": str(session_id or ""),
                          "meta": dict(meta), "flagged": False}
        _observe("stream_start", rid, str(session_id or ""), **meta)
        _sweep_stalled()  # ryd/flag gamle ved hver ny start (ingen daemon nødvendig)
    except Exception:
        pass


def note_stop(run_id: str, *, reason: str = "done") -> None:
    """En SSE-stream sendte message_stop (reason='done' normalt, 'fallback' = terminal-garanti)."""
    rid = str(run_id or "")
    if not rid:
        return
    try:
        with _lock:
            rec = _live.pop(rid, None)
        if rec is None:
            return  # idempotent: allerede stoppet (fx done før finally-fallback) → ingen dobbelt-emit
        sid = str(rec.get("session_id") or "")
        dur_ms = int((time.monotonic() - rec["start"]) * 1000)
        _observe("stream_stop", rid, sid, reason=reason, duration_ms=dur_ms)
    except Exception:
        pass


def note_event(run_id: str, kind: str, session_id: str = "", **data: Any) -> None:
    """Andre lane-fejl/edge-cases: idle / cancel / error / zombie_slot / subscriber_timeout."""
    try:
        _observe(f"stream_{kind}", str(run_id or ""), str(session_id or ""), kind=kind, **data)
    except Exception:
        pass


def _sweep_stalled(timeout_s: float = _STALL_AFTER_S) -> None:
    """message_start uden message_stop i >timeout_s → ægte zombie → flag ÉN gang pr. run
    (observe + persistent incident severity='error', pollbar af Claude/MC)."""
    now = time.monotonic()
    stalled: list[tuple[str, str, int]] = []
    try:
        with _lock:
            for rid, rec in list(_live.items()):
                if not rec.get("flagged") and (now - rec["start"]) > timeout_s:
                    rec["flagged"] = True
                    stalled.append((rid, str(rec.get("session_id") or ""),
                                    int(now - rec["start"])))
        for rid, sid, age in stalled:
            _observe("stream_stall", rid, sid, age_s=age, reason="message_stop_missing")
            try:
                from core.runtime.db_central_incidents import record_central_incident
                record_central_incident(
                    cluster=_CLUSTER, nerve="stream_stall", kind="stall",
                    severity="error", run_id=rid, session_id=sid,
                    message=f"stream {rid} fik message_start men ALDRIG message_stop i {age}s",
                )
            except Exception:
                pass
    except Exception:
        pass


def sweep() -> int:
    """Eksternt-kaldbar stall-sweep (fx fra heartbeat-kadence). Returnér antal live streams."""
    try:
        _sweep_stalled()
        with _lock:
            return len(_live)
    except Exception:
        return 0


def live_count() -> int:
    with _lock:
        return len(_live)
