"""Real-time Central-surface til owner-vinduet i jarvis-desk (code mode).

Aggregerer Den Intelligente Centrals live-tilstand til ÉT snapshot som desk-panelet poller:
  Lag 1 (puls):   status-lys + dækning (nerver/clusters) + self-diagnose
  Lag 2 (feed):   de seneste nerve-fyringer (decide/observe) — det levende vindue
  Lag 3 (flag):   uløste incidents + åbne circuit-breakers + config-drift
  Lag 4 (læring): degraderende clusters + autonomi-dom + forslag-antal

ALT er read-only og self-safe — surfacen må ALDRIG kaste eller forstyrre runtime.
NB: central_trace er per-proces (ring-buffer); dette snapshot er jarvis-api-processens
syn (= den synlige lanes fyringer). Incidents/breakers/læring er DB/cross-proces-komplette.
"""
from __future__ import annotations

from typing import Any


def _status_from(diag: dict, incidents: list, open_breakers: list, drift: dict,
                 degrading: list) -> str:
    """🔴 red / 🟡 yellow / 🟢 green — værst-vinder."""
    severe = [i for i in incidents if str(i.get("severity")) == "severe"]
    fail_open = [i for i in incidents if str(i.get("kind")) == "fail_open"]
    if open_breakers or severe or fail_open:
        return "red"
    errors = [i for i in incidents if str(i.get("severity")) in ("error", "severe")]
    if diag.get("degraded") or errors or degrading or (drift or {}).get("drift"):
        return "yellow"
    return "green"


def realtime_snapshot(*, trace_limit: int = 24) -> dict[str, Any]:
    """Ét snapshot af Centralens live-tilstand. Self-safe (delvise data ved fejl)."""
    snap: dict[str, Any] = {
        "status": "green", "coverage": {}, "diagnose": {},
        "feed": [], "incidents": [], "open_breakers": [], "config_drift": None,
        "learning": {},
    }

    # ── Lag 1: puls ──────────────────────────────────────────────────────
    diag: dict[str, Any] = {}
    try:
        from core.services.central_core import central
        diag = central().self_diagnose()
    except Exception:
        diag = {"degraded": True, "decide_ok": False, "observe_ok": False,
                "open_breakers": [], "trace_records": 0}
    snap["diagnose"] = diag
    snap["open_breakers"] = list(diag.get("open_breakers") or [])
    try:
        from core.services import central_catalog as cc
        clusters = sorted(cc.clusters())
        snap["coverage"] = {
            "nerves": sum(len(list(cc.by_cluster(c))) for c in clusters),
            "clusters": len(clusters),
            "security_clusters": sum(1 for c in clusters if cc.is_security_cluster(c)),
            "trace_buffer": int(diag.get("trace_records") or 0),
        }
    except Exception:
        pass

    # ── Lag 2: feed (de seneste fyringer) ────────────────────────────────
    try:
        from core.services import central_trace
        from core.services.central_catalog import is_security_cluster, nerve_location
        recs = central_trace.sink().recent(limit=trace_limit)
        feed = []
        for r in reversed(recs):  # nyeste først
            cluster = str(getattr(r, "cluster", "") or "")
            nerve = str(getattr(r, "nerve", "") or "")
            feed.append({
                "cluster": cluster, "nerve": nerve,
                "kind": str(getattr(r, "kind", "") or ""),       # decide|observe|error
                "decision": str(getattr(r, "decision", "") or ""),  # red|yellow|green|skip
                "reason": str(getattr(r, "reason", "") or "")[:120],
                "run_id": str(getattr(r, "run_id", "") or ""),
                "security": bool(_safe(is_security_cluster, cluster)),
            })
        snap["feed"] = feed
    except Exception:
        pass

    # ── Lag 3: flag ──────────────────────────────────────────────────────
    incidents: list[dict[str, Any]] = []
    try:
        from core.runtime.db_central_incidents import list_central_incidents
        incidents = list_central_incidents(unresolved_only=True, limit=40)
        snap["incidents"] = [
            {"cluster": str(i.get("cluster") or ""), "nerve": str(i.get("nerve") or ""),
             "kind": str(i.get("kind") or ""), "severity": str(i.get("severity") or ""),
             "message": str(i.get("message") or "")[:200], "ts": str(i.get("ts") or "")}
            for i in incidents[:12]
        ]
    except Exception:
        pass
    drift: dict[str, Any] = {}
    try:
        from core.services.config_drift import observe_config_drift
        drift = observe_config_drift() or {}
        if drift.get("drift"):
            snap["config_drift"] = {
                "declared_port": drift.get("declared_port"),
                "actual_port": drift.get("actual_port"),
            }
    except Exception:
        pass

    # ── Lag 4: læring ────────────────────────────────────────────────────
    degrading: list[Any] = []
    try:
        from core.services import central_learning as cl
        inc = cl._load()
        degrading = cl.degrading(incidents=inc)
        autonomy = cl.assess_autonomy(incidents=inc)
        snap["learning"] = {
            "degrading": [{"target": f"{d['cluster']}/{d['nerve']}",
                           "rate_hr": d.get("recent_rate_hr")} for d in degrading[:5]],
            "autonomy": autonomy.get("verdict"),
            "autonomy_reason": autonomy.get("reason"),
            "proposals": len(cl.propose_adjustments(incidents=inc)),
            "root_causes": [{"target": f"{g['cluster']}/{g['nerve']}", "count": g["count"]}
                            for g in cl.root_causes(incidents=inc)[:4]],
        }
    except Exception:
        pass

    snap["status"] = _status_from(diag, incidents, snap["open_breakers"], drift, degrading)
    return snap


def _safe(fn, *a):
    try:
        return fn(*a)
    except Exception:
        return None
