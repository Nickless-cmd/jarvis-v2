"""`central_query` — Jarvis' direkte adgang til Den Intelligente Central (pull on-demand).

Bjørns HÅRDE invariant (spec 2026-06-23): tool'et MÅ ALDRIG fejle Jarvis eller Centralen.
Det returnerer ALTID et struktureret svar med eksplicit status=ok/error — aldrig stille
fejl, aldrig trunkeret output uden `meta.truncated`, aldrig null/'' uden forklaring. Self-
safe: enhver exception fanges og returneres som status=error. Kalder Python-modulerne
DIREKTE (same-process) — ingen HTTP/port-drift/auth.

Read-actions altid tilladt; toggle-actions håndhæves owner-only af central_switches
(sikkerheds-nerver/-clusters kan ALDRIG slås fra).
"""
from __future__ import annotations

import json
import time
from typing import Any

_BUDGET_CHARS = 4000  # pr. response (Bjørn: ikke 2000 — Jarvis skal kunne læse incidents)
_MAX_LIMIT = 100

_READ_ACTIONS = {"status", "incidents", "trace", "cluster_health", "nerve_detail",
                 "autonomy", "learning", "drift", "breakers", "instrument", "known_signals"}
_TOGGLE_ACTIONS = {"toggle_nerve", "toggle_cluster"}
# Muterende skrive-actions — Jarvis' skrive-kanal til Centralen (§10). ALLE owner-gatet
# (R2): kun ejeren (eller unbound legacy) må mutere control-planet. member/guest fail-closer.
_WRITE_ACTIONS = {"resolve_and_route", "depromote", "resolve_incident",
                  "nerve_observe", "note"}


def _envelope(status: str, action: str, data: Any, error: str | None,
              source: str, t0: float, **meta_extra: Any) -> dict[str, Any]:
    meta = {"latency_ms": int((time.monotonic() - t0) * 1000), "source": source,
            "truncated": False}
    meta.update(meta_extra)
    return {"status": status, "action": action, "data": data, "error": error, "meta": meta}


def _paginate(items: list, offset: int, limit: int) -> tuple[list, dict]:
    """Returnér en side + pagina-meta. ALDRIG trunkér en linje midt over: vi dropper
    HELE elementer indtil under budget. Bjørn: trunkering ulovlig uden truncated=true."""
    total = len(items)
    offset = max(0, offset)
    sel = items[offset:offset + limit]
    budget_trim = False
    while sel and len(json.dumps(sel, ensure_ascii=False, default=str)) > _BUDGET_CHARS:
        sel = sel[:-1]
        budget_trim = True
    has_more = (offset + len(sel)) < total
    meta: dict[str, Any] = {"total_count": total, "has_more": has_more,
                            "truncated": bool(budget_trim or has_more)}
    if has_more:
        meta["next_offset"] = offset + len(sel)
    return sel, meta


def _nerve_klass(nerve: str):
    """NerveSpec.klass for en nerve (til sikker toggle). Defaulter SECURITY-SIKKERT:
    hvis nerven ligger i et sikkerheds-cluster behandles den som SECURITY."""
    from core.services.gate_kernel import GateClass
    from core.services import central_catalog as cc
    try:
        for c in cc.clusters():
            for n in cc.by_cluster(c):
                if n.name == nerve:
                    return n.klass
        # ukendt nerve men i et sikkerheds-cluster? → behandl som security
        if cc.is_security_cluster(cc.nerve_cluster(nerve) or ""):
            return GateClass.SECURITY
    except Exception:
        pass
    return GateClass.COGNITIVE


def central_query(args: dict[str, Any]) -> dict[str, Any]:
    """Eneste indgang. Returnerer ALTID en envelope (status ok/error). Kaster aldrig."""
    t0 = time.monotonic()
    action = str((args or {}).get("action") or "").strip()
    try:
        limit = int((args or {}).get("limit") or 20)
    except Exception:
        limit = 20
    limit = min(max(limit, 1), _MAX_LIMIT)
    try:
        offset = int((args or {}).get("offset") or 0)
    except Exception:
        offset = 0
    cluster = str((args or {}).get("cluster") or "").strip()
    nerve = str((args or {}).get("nerve") or "").strip()
    enabled = bool((args or {}).get("enabled"))
    # §10 skrive-params
    signature = str((args or {}).get("signature") or "").strip()
    action_type = str((args or {}).get("action_type") or "route_to_nerve").strip()
    notes = str((args or {}).get("notes") or "")
    text = str((args or {}).get("text") or "")
    importance = str((args or {}).get("importance") or "medium").strip()
    category = str((args or {}).get("category") or "").strip()
    try:
        incident_id = int((args or {}).get("incident_id") or 0)
    except Exception:
        incident_id = 0

    _all_actions = _READ_ACTIONS | _TOGGLE_ACTIONS | _WRITE_ACTIONS
    if not action:
        return _envelope("error", "", None, "manglende 'action'", "central_query", t0)
    if action not in _all_actions:
        return _envelope("error", action, None,
                         f"ukendt action '{action}' (gyldige: "
                         f"{', '.join(sorted(_all_actions))})",
                         "central_query", t0)
    # R2 — owner-gating: kun ejeren (eller unbound legacy '') må MUTERE Centralen.
    # central_query er ikke i OWNER_ONLY_TOOLS, og central_switches håndhæver kun
    # sikkerheds-invarianten — så gaten SKAL ligge her. Read-actions forbliver åbne.
    if action in (_TOGGLE_ACTIONS | _WRITE_ACTIONS):
        try:
            from core.identity.workspace_context import effective_role
            _role = effective_role()
        except Exception:
            _role = ""
        if _role not in ("owner", ""):
            return _envelope("error", action, None,
                             "owner-only: kun ejeren må mutere Centralen", "central_query", t0)

    try:
        # ── status: kompakt snapshot ─────────────────────────────────────
        if action == "status":
            from core.services.central_realtime import realtime_snapshot
            s = realtime_snapshot(trace_limit=8)
            _anom = s.get("anomalies") or {}
            # §3.7 — vis de FAKTISKE seneste anomalier (signatur+lokation+count), ikke kun "16".
            _recent = [
                {"signature": a.get("signature"), "category": a.get("category"),
                 "importance": a.get("importance"), "count": a.get("count"),
                 "location": a.get("location"), "last_seen": a.get("last_seen")}
                for a in (_anom.get("recent") or [])[:6]
            ]
            data = {
                "status": s.get("status"),
                "coverage": s.get("coverage"),
                "diagnose": {k: s.get("diagnose", {}).get(k)
                             for k in ("decide_ok", "observe_ok", "degraded")},
                "open_breakers": len(s.get("open_breakers") or []),
                "unresolved_incidents": len(s.get("incidents") or []),
                "anomalies": {"counts": _anom.get("counts", {}), "recent": _recent},
                "known_signals": s.get("known_signals") or [],
                "config_drift": bool(s.get("config_drift")),
                "clusters": {c["cluster"]: c["status"] for c in (s.get("clusters") or [])},
            }
            return _envelope("ok", action, data, None, "central_realtime", t0)

        # ── incidents (paginer) ──────────────────────────────────────────
        if action == "incidents":
            from core.runtime.db_central_incidents import list_central_incidents
            items = list_central_incidents(unresolved_only=True, limit=200)
            page, pmeta = _paginate(items, offset, limit)
            return _envelope("ok", action, {"items": page}, None, "db_central_incidents",
                             t0, **pmeta)

        # ── trace (seneste fyringer, paginer) ────────────────────────────
        if action == "trace":
            from core.services import central_trace
            recs = central_trace.sink().recent(limit=200)
            items = [{"cluster": r.cluster, "nerve": r.nerve, "kind": r.kind,
                      "decision": r.decision, "reason": str(r.reason or "")[:160],
                      "run_id": r.run_id} for r in reversed(recs)]
            if cluster:
                items = [i for i in items if i["cluster"] == cluster]
            page, pmeta = _paginate(items, offset, limit)
            return _envelope("ok", action, {"items": page}, None, "central_trace", t0, **pmeta)

        # ── cluster_health (pr. cluster) ─────────────────────────────────
        if action == "cluster_health":
            from core.services import central_learning as cl
            inc = cl._load()
            health = cl.cluster_health(incidents=inc)
            degr = {f"{d['cluster']}/{d['nerve']}" for d in cl.degrading(incidents=inc)}
            if cluster:
                health = {cluster: health.get(cluster, {"total": 0, "severe": 0})}
            items = [{"cluster": c, "incidents": v.get("total", 0),
                      "severe": v.get("severe", 0),
                      "degrading": any(k.startswith(c + "/") for k in degr)}
                     for c, v in sorted(health.items())]
            page, pmeta = _paginate(items, offset, limit)
            return _envelope("ok", action, {"items": page}, None, "central_learning", t0, **pmeta)

        # ── nerve_detail (én nerve dybt) ─────────────────────────────────
        if action == "nerve_detail":
            if not nerve:
                return _envelope("error", action, None, "manglende 'nerve'", "central_query", t0)
            from core.services import central_trace, central_switches
            from core.services.central_catalog import nerve_cluster, nerve_location, is_security_cluster
            recs = [r for r in central_trace.sink().recent(limit=400) if r.nerve == nerve]
            cl_name = nerve_cluster(nerve) or ""
            data = {
                "nerve": nerve, "cluster": cl_name,
                "security": bool(is_security_cluster(cl_name)) if cl_name else False,
                "location": nerve_location(nerve) or "",
                "enabled": central_switches.is_enabled("nerve", nerve),
                "recent": [{"kind": r.kind, "decision": r.decision,
                            "reason": str(r.reason or "")[:160], "run_id": r.run_id}
                           for r in list(reversed(recs))[:limit]],
            }
            return _envelope("ok", action, data, None, "central_trace+switches", t0,
                             total_recent=len(recs))

        # ── autonomy ─────────────────────────────────────────────────────
        if action == "autonomy":
            from core.services import central_learning as cl
            return _envelope("ok", action, cl.assess_autonomy(), None, "central_learning", t0)

        # ── learning ─────────────────────────────────────────────────────
        if action == "learning":
            from core.services import central_learning as cl
            inc = cl._load()
            data = {
                "degrading": cl.degrading(incidents=inc)[:limit],
                "root_causes": cl.root_causes(incidents=inc)[:limit],
                "proposals": cl.propose_adjustments(incidents=inc)[:limit],
            }
            # budget: hvis for stor, beskær proposals/root_causes
            truncated = False
            while (len(json.dumps(data, ensure_ascii=False, default=str)) > _BUDGET_CHARS
                   and (data["proposals"] or data["root_causes"])):
                if data["proposals"]:
                    data["proposals"] = data["proposals"][:-1]
                else:
                    data["root_causes"] = data["root_causes"][:-1]
                truncated = True
            return _envelope("ok", action, data, None, "central_learning", t0, truncated=truncated)

        # ── drift ────────────────────────────────────────────────────────
        if action == "drift":
            from core.services.config_drift import observe_config_drift
            rep = observe_config_drift() or {}
            data = {"drift": bool(rep.get("drift")),
                    "declared_port": rep.get("declared_port"),
                    "actual_port": rep.get("actual_port")}
            return _envelope("ok", action, data, None, "config_drift", t0)

        # ── breakers ─────────────────────────────────────────────────────
        if action == "breakers":
            from core.services.central_core import central
            from core.services.central_catalog import nerve_cluster
            try:
                open_n = central()._breaker.open_nerves()
            except Exception:
                open_n = (central().self_diagnose() or {}).get("open_breakers", [])
            data = {"open": [{"nerve": n, "cluster": nerve_cluster(n) or ""} for n in open_n]}
            return _envelope("ok", action, data, None, "central_switches", t0,
                             count=len(open_n))

        # ── instrument: selv-instrumenterings-fund (on-demand scan) ──────
        if action == "instrument":
            from core.runtime import db_instrument as dbi
            do_scan = bool((args or {}).get("scan"))
            scan_rep = None
            if do_scan:
                from core.services.central_instrument import run_instrument_scan
                scan_rep = run_instrument_scan(trigger="central_query", changed_only=True)
            items = dbi.list_findings(status="open", min_score=0, limit=limit)
            paged, meta = _paginate(items, offset, limit)
            data = {"summary": dbi.summary(), "findings": paged,
                    "scanned": (scan_rep or {}).get("scanned") if scan_rep else None}
            return _envelope("ok", action, data, None, "central_instrument", t0, **meta)

        # ── toggle_nerve (owner-only, security låst) ─────────────────────
        if action == "toggle_nerve":
            if not nerve:
                return _envelope("error", action, None, "manglende 'nerve'", "central_query", t0)
            from core.services import central_switches
            res = central_switches.set_enabled("nerve", nerve, enabled,
                                               klass=_nerve_klass(nerve))
            if not res.get("ok"):
                return _envelope("error", action, res, str(res.get("reason") or "afvist"),
                                 "central_switches", t0)
            return _envelope("ok", action, res, None, "central_switches", t0)

        # ── toggle_cluster (owner-only, security låst) ───────────────────
        if action == "toggle_cluster":
            if not cluster:
                return _envelope("error", action, None, "manglende 'cluster'", "central_query", t0)
            from core.services import central_switches
            res = central_switches.set_cluster_enabled(cluster, enabled)
            if not res.get("ok"):
                return _envelope("error", action, res, str(res.get("reason") or "afvist"),
                                 "central_switches", t0)
            return _envelope("ok", action, res, None, "central_switches", t0)

        # ── known_signals (read): promoverede signaler ───────────────────
        if action == "known_signals":
            from core.runtime.db_anomalies import list_known_signals
            items = list_known_signals(limit=limit)
            page, pmeta = _paginate(items, offset, limit)
            return _envelope("ok", action, {"items": page}, None, "db_anomalies", t0, **pmeta)

        # ── resolve_and_route (write): rout signatur til nerve + resolve ──
        if action == "resolve_and_route":
            if not signature:
                return _envelope("error", action, None, "manglende 'signature'", "central_query", t0)
            if not nerve:
                return _envelope("error", action, None, "manglende 'nerve'", "central_query", t0)
            from core.runtime.db_anomalies import route_anomaly_to_nerve, resolve_anomaly
            ok = route_anomaly_to_nerve(signature=signature, cluster=cluster, nerve=nerve,
                                        action=action_type, notes=notes, promoted_by="manual")
            resolve_anomaly(signature)
            return _envelope("ok" if ok else "error", action, {"routed": ok},
                             None if ok else "routing fejlede", "db_anomalies", t0)

        # ── depromote (write): angre en promotion ────────────────────────
        if action == "depromote":
            if not signature:
                return _envelope("error", action, None, "manglende 'signature'", "central_query", t0)
            from core.runtime.db_anomalies import depromote_known_signal
            ok = depromote_known_signal(signature)
            return _envelope("ok" if ok else "error", action, {"depromoted": ok},
                             None if ok else "ingen known-række slettet", "db_anomalies", t0)

        # ── resolve_incident (write): luk en incident ────────────────────
        if action == "resolve_incident":
            if incident_id <= 0:
                return _envelope("error", action, None, "manglende/ugyldig 'incident_id'", "central_query", t0)
            from core.runtime.db_central_incidents import resolve_central_incident
            ok = resolve_central_incident(incident_id)
            return _envelope("ok" if ok else "error", action, {"resolved": ok, "incident_id": incident_id},
                             None if ok else "resolve fejlede", "db_central_incidents", t0)

        # ── nerve_observe (write): injicér en observation til en nerve ───
        if action == "nerve_observe":
            if not nerve:
                return _envelope("error", action, None, "manglende 'nerve'", "central_query", t0)
            from core.services.central_core import central
            central().observe({"cluster": cluster or "anomaly", "nerve": nerve,
                               "importance": importance, "source": "jarvis_write",
                               "category": category or "manual", "text": text[:500],
                               "manual": True})
            return _envelope("ok", action, {"observed": True, "nerve": nerve,
                                            "cluster": cluster or "anomaly"},
                             None, "central_core", t0)

        # ── note (write): fri-tekst note ind i Centralens bevidsthed ─────
        if action == "note":
            if not text.strip():
                return _envelope("error", action, None, "manglende 'text'", "central_query", t0)
            from core.services.central_core import central
            central().observe({"cluster": "central", "nerve": "owner_note",
                               "text": text[:500], "source": "jarvis_write", "manual": True})
            return _envelope("ok", action, {"noted": True}, None, "central_core", t0)

        return _envelope("error", action, None, "uimplementeret action", "central_query", t0)
    except Exception as exc:
        # HÅRD invariant: aldrig stille fejl — altid struktureret error med besked.
        return _envelope("error", action, None,
                         f"{action} failed: {type(exc).__name__}: {exc}"[:300],
                         "central_query", t0)
