"""Cross-proces trace-tee for Den Intelligente Central.

`central_trace.TraceSink` er per-proces (in-memory ring). jarvis-api og jarvis-runtime
kører hver sin Python-proces med hver sin sink → owner-feed'et i desk så HIDTIL kun
api-processens fyringer. Alt i runtime-processen (daemons, autonome runs, inner-voice,
dreams, heartbeat, scheduled_tasks, supervisor …) var USYNLIGT i det levende vindue.

Denne tee lukker hullet: hver proces publicerer (throttled) sit seneste feed + sin
self-diagnose til `shared_cache` (SQLite, ægte cross-proces) under proces-mærkede nøgler.
`realtime_snapshot` læser sin EGEN in-memory ring + de ANDRE processers publicerede feeds
og fletter dem efter tid → ét komplet vindue der fanger BÅDE runtime og api.

Best-effort, self-safe: en tee-fejl må ALDRIG forstyrre runtime eller den hotte sti.
Publicerede feeds har TTL → en død proces forsvinder af sig selv fra panelet.
"""
from __future__ import annotations

import os
import time
from typing import Any

_FEED_KEY = "central:xproc:feed:"      # + proces-rolle
_HEALTH_KEY = "central:xproc:health:"  # + proces-rolle
_ROLES = ("api", "runtime")            # kendte proces-roller (api kører --workers 1)
_TTL = 30                              # sek. — udløb fjerner en død proces fra panelet
_PUBLISH_EVERY = 2.0                   # throttle: max én skrivning pr. proces pr. 2s
_FEED_CAP = 80                         # seneste N records publiceres

_last_publish = 0.0


def process_role() -> str:
    """'api' (visible-lane, JARVIS_ENABLE_RUNTIME_SERVICES=0) eller 'runtime' (daemons)."""
    raw = str(os.getenv("JARVIS_ENABLE_RUNTIME_SERVICES", "1")).strip().lower()
    return "api" if raw in {"0", "false", "no", "off"} else "runtime"


def maybe_publish() -> None:
    """Throttled publish af denne proces' feed + sundhed. Kaldt fra trace-record (hot path)
    → derfor billig monotonic-throttle + fuld self-safety."""
    global _last_publish
    try:
        now = time.monotonic()
        if now - _last_publish < _PUBLISH_EVERY:
            return
        _last_publish = now
    except Exception:
        return
    try:
        _publish_now()
    except Exception:
        pass


def _publish_now() -> None:
    role = process_role()
    from core.services import shared_cache

    # ── feed ────────────────────────────────────────────────────────────
    try:
        from core.services import central_trace
        recs = central_trace.sink().recent(limit=_FEED_CAP)
        feed = [{
            "cluster": str(getattr(r, "cluster", "") or ""),
            "nerve": str(getattr(r, "nerve", "") or ""),
            "kind": str(getattr(r, "kind", "") or ""),
            "decision": str(getattr(r, "decision", "") or ""),
            "reason": str(getattr(r, "reason", "") or "")[:120],
            "run_id": str(getattr(r, "run_id", "") or ""),
            "ts": float(getattr(r, "ts", 0.0) or 0.0),
        } for r in recs]
        shared_cache.set(_FEED_KEY + role,
                         {"process": role, "ts": time.time(), "feed": feed},
                         ttl_seconds=_TTL)
    except Exception:
        pass

    # ── sundhed (per-proces self-diagnose) ──────────────────────────────
    try:
        from core.services.central_core import central
        diag = central().self_diagnose()
        shared_cache.set(_HEALTH_KEY + role, {
            "process": role, "ts": time.time(),
            "degraded": bool(diag.get("degraded")),
            "decide_ok": bool(diag.get("decide_ok")),
            "observe_ok": bool(diag.get("observe_ok")),
            "open_breakers": [str(b) for b in (diag.get("open_breakers") or [])],
            "trace_records": int(diag.get("trace_records") or 0),
        }, ttl_seconds=_TTL)
    except Exception:
        pass


def foreign_feeds(own_role: str) -> list[dict[str, Any]]:
    """Records fra ALLE andre processer end ens egen (ens egen har vi in-memory, friskere).
    Hver record mærkes med 'process'. Self-safe → []."""
    out: list[dict[str, Any]] = []
    try:
        from core.services import shared_cache
        for role in _ROLES:
            if role == own_role:
                continue
            v = shared_cache.get(_FEED_KEY + role)
            if isinstance(v, dict) and isinstance(v.get("feed"), list):
                for f in v["feed"]:
                    if isinstance(f, dict):
                        out.append({**f, "process": role})
    except Exception:
        pass
    return out


def all_health() -> list[dict[str, Any]]:
    """Per-proces sundhed for hver kendt proces der har publiceret (ikke udløbet). Self-safe."""
    out: list[dict[str, Any]] = []
    try:
        from core.services import shared_cache
        for role in _ROLES:
            v = shared_cache.get(_HEALTH_KEY + role)
            if isinstance(v, dict):
                out.append(v)
    except Exception:
        pass
    return out
