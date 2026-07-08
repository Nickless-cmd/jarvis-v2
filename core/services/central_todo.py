"""Central TODO — ÉN prioriteret, pollbar huskeliste på tværs af ALLE clusters. I stedet for
at læse 10 steder aggregerer den hvad der skal fikses og rangerer det efter vigtighed.

Pollbar af Claude (når på Bjørns maskine i tomgang) + grundlag for at afgøre hvilke todos
Jarvis kan få autonomt (når adaptiv læring kan vurdere hans stabilitet pr. opgavetype).

Aggregerer (best-effort, self-safe): severe incidents · knækkede runs · config-drift ·
fejlende daemons · døde DB-tabeller · døde endpoints · dark edges. Read-only — handler ALDRIG
selv; foreslår.
"""
from __future__ import annotations

from typing import Any

# Prioritet: lavere tal = vigtigere.
_P_CRITICAL = 1   # severe incident / sikkerhed
_P_HIGH = 2       # knækket run / config-drift
_P_MEDIUM = 3     # fejlende daemon / dark edge
_P_CLEANUP = 5    # døde tools/endpoints/tabeller (oprydning)

# En severe incident der har stået uløst i mere end dette er ikke længere "frisk arbejde
# Jarvis bevæger sig mod" — den ville ellers fastlåse agendaens next_intention (fx en 2-dage-
# gammel rolle-deny på operator_bash). Gamle severe forbliver SYNLIGE i diagnostik/incidents;
# de bliver bare ikke elekteret som Jarvis' selv-rettede intention.
_INCIDENT_TODO_MAX_AGE_H = 24


def _incident_is_fresh(inc: dict[str, Any], *, max_age_h: int = _INCIDENT_TODO_MAX_AGE_H) -> bool:
    """True hvis incidentens ts er inden for max_age_h. Ukendt/uparsbar ts → True (fail-open:
    hellere vise end tabe). Self-safe."""
    from datetime import UTC, datetime
    ts = str(inc.get("ts") or "").strip()
    if not ts:
        return True
    try:
        age_s = datetime.now(UTC).timestamp() - datetime.fromisoformat(ts).timestamp()
        return age_s <= max_age_h * 3600
    except Exception:
        return True


def _item(priority: int, source: str, what: str, **extra: Any) -> dict[str, Any]:
    return {"priority": priority, "source": source, "what": what, **extra}


def build_todo(*, max_items: int = 60) -> list[dict[str, Any]]:
    """Saml + ranger todos fra alle clusters. Self-safe — en kilde der fejler udelades."""
    items: list[dict[str, Any]] = []

    # 1. Severe uløste incidents (KRITISK)
    try:
        from core.runtime.db_central_incidents import list_central_incidents
        for inc in list_central_incidents(limit=30, min_severity="severe", unresolved_only=True):
            if not _incident_is_fresh(inc):
                continue  # for gammel til at være en agenda-todo (stadig synlig som incident)
            items.append(_item(_P_CRITICAL, "incident",
                               f"{inc.get('cluster')}/{inc.get('nerve')}: {inc.get('message')}",
                               cluster=inc.get("cluster"), incident_id=inc.get("id")))
    except Exception:
        pass

    # 2. Nyligt knækkede runs (HØJ) — med fil-reference via korrelation
    try:
        from core.services.central_correlate import recent_broken_runs
        for b in recent_broken_runs()[:15]:
            items.append(_item(_P_HIGH, "broken_run",
                               f"run {b['run_id']} knækkede i {b['cluster']}/{b['nerve']}: {b['reason']}",
                               run_id=b["run_id"], file=b.get("file"), cluster=b.get("cluster")))
    except Exception:
        pass

    # 3. Config-drift (HØJ)
    try:
        from core.services.config_drift import check_port_drift
        d = check_port_drift()
        if d.get("drift"):
            items.append(_item(_P_HIGH, "config_drift",
                               f"port-drift: declared={d['declared_port']} men API på {d['actual_port']}",
                               file="core/runtime/settings.py"))
    except Exception:
        pass

    # 4. Fejlende daemons (MEDIUM)
    try:
        from core.services.daemon_health import daemon_health_summary
        for daemon, n in (daemon_health_summary().get("failing_daemons") or {}).items():
            items.append(_item(_P_MEDIUM, "daemon",
                               f"daemon {daemon} fejlede {n}× i seneste trace", daemon=daemon))
    except Exception:
        pass

    # (Dark edges fra kartografen er bevidst UDELADT her — den fulde analyse er tung og
    # kartografen flager dem allerede via sin egen observe/auto-task. Hent dem on-demand.)

    # 5. Døde DB-tabeller (OPRYDNING — review, ikke drop)
    try:
        from core.services.db_sentinel import dead_table_candidates
        dead = dead_table_candidates()
        if dead:
            items.append(_item(_P_CLEANUP, "db",
                               f"{len(dead)} tomme tabeller til review: {', '.join(dead[:8])}"
                               + ("…" if len(dead) > 8 else ""), tables=dead))
    except Exception:
        pass

    # 7. Døde endpoints (OPRYDNING)
    try:
        from core.services.endpoint_usage_store import dead_endpoints
        dead = dead_endpoints()
        if dead:
            items.append(_item(_P_CLEANUP, "endpoint",
                               f"{len(dead)} endpoints aldrig kaldt (oprydnings-kandidater)",
                               endpoints=dead[:20]))
    except Exception:
        pass

    # §6 lærings-forslag (deterministiske, reviewbare — aldrig auto): rod-årsager +
    # degraderings-undersøgelser + autonomi-vurdering. Prioritet fra forslagets egen.
    try:
        from core.services.central_learning import propose_adjustments
        _PRI = {1: _P_CRITICAL, 2: _P_HIGH, 3: _P_MEDIUM, 4: _P_CLEANUP}
        for p in propose_adjustments():
            items.append(_item(_PRI.get(int(p.get("priority") or 3), _P_MEDIUM),
                               "learning", str(p.get("action") or ""),
                               kind=p.get("kind"), target=p.get("target")))
    except Exception:
        pass

    items.sort(key=lambda it: (it["priority"], it["source"]))
    return items[:max_items]


def poll(*, limit: int = 20) -> dict[str, Any]:
    """Pollbar af Claude i tomgang: top-prioriterede todos + tælling pr. prioritet."""
    todo = build_todo()
    from collections import Counter
    by_pri = Counter(it["priority"] for it in todo)
    return {
        "total": len(todo),
        "critical": by_pri.get(_P_CRITICAL, 0), "high": by_pri.get(_P_HIGH, 0),
        "medium": by_pri.get(_P_MEDIUM, 0), "cleanup": by_pri.get(_P_CLEANUP, 0),
        "top": todo[:limit],
    }


def build_central_todo_surface() -> dict[str, object]:
    """MC-surface — read-only prioriteret huskeliste."""
    p = poll(limit=40)
    return {"active": True, "mode": "central_todo", **p,
            "authority": "derived-read-only — foreslår, handler ALDRIG selv"}
