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
                 degrading: list, anomaly_counts: dict | None = None) -> str:
    """🔴 red / 🟡 yellow / 🟢 green — værst-vinder."""
    ac = anomaly_counts or {}
    severe = [i for i in incidents if str(i.get("severity")) == "severe"]
    fail_open = [i for i in incidents if str(i.get("kind")) == "fail_open"]
    if open_breakers or severe or fail_open or int(ac.get("critical") or 0) > 0:
        return "red"
    errors = [i for i in incidents if str(i.get("severity")) in ("error", "severe")]
    if (diag.get("degraded") or errors or degrading or (drift or {}).get("drift")
            or int(ac.get("high") or 0) > 0):
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
    # Config-drift: udled fra de PERSISTEREDE incidents (config_drift-cadence-produceren
    # skriver dem) — KALD IKKE observe_config_drift() live: dens port-probe blokerer ~10s
    # (connect-timeout mod port 80), og panelet poller hvert 2s → ville hænge endpointet.
    drift: dict[str, Any] = {}
    try:
        _drift_inc = next((i for i in incidents
                           if str(i.get("nerve")) == "config_drift"), None)
        if _drift_inc:
            drift = {"drift": True}
            snap["config_drift"] = {"message": str(_drift_inc.get("message") or "")[:120]}
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

    # ── Anomalier: de udefinerede fejl Centralen fangede (uden for de 113 nerver) ──
    try:
        from core.services.central_anomaly import anomaly_summary
        snap["anomalies"] = anomaly_summary(limit=6)
    except Exception:
        snap["anomalies"] = {"counts": {"total": 0}, "recent": []}

    # ── Cluster-grid: grøn/gul/rød/idle pr. cluster (se når ét cluster brækker/går offline)
    try:
        snap["clusters"] = _cluster_grid(snap["feed"], incidents, snap["open_breakers"], degrading)
    except Exception:
        snap["clusters"] = []

    snap["status"] = _status_from(diag, incidents, snap["open_breakers"], drift, degrading,
                                  snap.get("anomalies", {}).get("counts", {}))
    return snap


def _cluster_grid(feed: list, incidents: list, open_breakers: list,
                  degrading: list) -> list[dict[str, Any]]:
    """Pr. cluster: grøn (fyrer), gul (fejl/degraderer), rød (breaker/severe/fail-open),
    idle (stille). Lader owner se ÉT cluster brække/gå offline med ét blik."""
    from core.services import central_catalog as cc
    from core.services.central_catalog import nerve_cluster
    clusters = sorted(cc.clusters())
    # breaker-nerver → deres cluster
    broken = {nerve_cluster(b) for b in open_breakers if nerve_cluster(b)}
    red_clusters: set = set(broken)
    yellow_clusters: set = set()
    for i in incidents:
        c = str(i.get("cluster") or "")
        if str(i.get("severity")) == "severe" or str(i.get("kind")) == "fail_open":
            red_clusters.add(c)
        elif str(i.get("severity")) in ("error",):
            yellow_clusters.add(c)
    for d in degrading:
        yellow_clusters.add(str(d.get("cluster") or ""))
    active = {str(f.get("cluster") or "") for f in feed}
    out = []
    for c in clusters:
        if c in red_clusters:
            st = "red"
        elif c in yellow_clusters:
            st = "yellow"
        elif c in active:
            st = "green"
        else:
            st = "idle"
        out.append({"cluster": c, "status": st,
                    "security": bool(_safe(cc.is_security_cluster, c))})
    # rød/gul først (så de mest kritiske er øverst i grid'et)
    _order = {"red": 0, "yellow": 1, "green": 2, "idle": 3}
    out.sort(key=lambda x: (_order.get(x["status"], 9), x["cluster"]))
    return out


def _safe(fn, *a):
    try:
        return fn(*a)
    except Exception:
        return None
