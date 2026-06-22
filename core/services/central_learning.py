"""#4 Adaptiv læring — DETERMINISTISK, for ALLE clusters. Centralen læser de signaler clusterne
producerer (persistente incidents, inkl. supervisions-verdikter) og bygger mønstre over tid:
hvilke clusters/nerver trender mod nedbrud, og hvor stabil Jarvis er pr. run-type.

Mål (Bjørn): over tid afværge FULDE cluster-nedbrud + identificere hver enkelt fejl til roden,
og afgøre hvilke TODO'er Jarvis kan få autonomt. Bidirektional reaktion (Central→cluster:
preemptiv isolering via central_switches/breaker) er Phase 2 — kræver tillid + data.

Bygger på den PERSISTENTE incident-historik → akkumulerer automatisk (fx overnight). Ingen
hot-path-cost; beregnes on-demand + på kadence. Read-only/observe — handler ALDRIG selv endnu.
Self-safe.
"""
from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

# Degradering: recent-rate skal overstige baseline-rate med denne faktor OG have nok samples.
_DEGRADE_FACTOR = 2.0
_DEGRADE_MIN_RECENT = 3


def _load(limit: int = 3000) -> list[dict[str, Any]]:
    try:
        from core.runtime.db_central_incidents import list_central_incidents
        return list_central_incidents(limit=limit)
    except Exception:
        return []


def _within(ts: Any, hours: float, now: datetime) -> bool:
    try:
        t = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if t.tzinfo is None:
            t = t.replace(tzinfo=UTC)
        return (now - t) <= timedelta(hours=hours)
    except Exception:
        return False


def cluster_health(*, hours: float = 24, incidents: list | None = None) -> dict[str, dict[str, int]]:
    """Per-cluster incident-billede i vinduet: total + severe. Self-safe."""
    now = datetime.now(UTC)
    inc = incidents if incidents is not None else _load()
    out: dict[str, dict[str, int]] = {}
    for r in inc:
        if not _within(r.get("ts"), hours, now):
            continue
        c = str(r.get("cluster") or "")
        d = out.setdefault(c, {"total": 0, "severe": 0})
        d["total"] += 1
        if str(r.get("severity")) == "severe":
            d["severe"] += 1
    return out


def degrading(*, recent_hours: float = 6, baseline_hours: float = 48,
              incidents: list | None = None) -> list[dict[str, Any]]:
    """Nerver/clusters hvis incident-rate i de seneste `recent_hours` overstiger baseline-raten
    markant → de trender mod nedbrud. DET er det adaptive afværge-signal (fang FØR fuldt nedbrud)."""
    now = datetime.now(UTC)
    inc = incidents if incidents is not None else _load()
    recent: Counter = Counter()
    base: Counter = Counter()
    for r in inc:
        key = f"{r.get('cluster')}/{r.get('nerve')}"
        if _within(r.get("ts"), recent_hours, now):
            recent[key] += 1
        if _within(r.get("ts"), baseline_hours, now):
            base[key] += 1
    out: list[dict[str, Any]] = []
    for key, rc in recent.items():
        if rc < _DEGRADE_MIN_RECENT:
            continue
        recent_rate = rc / recent_hours
        baseline_rate = base.get(key, rc) / baseline_hours
        if recent_rate > baseline_rate * _DEGRADE_FACTOR:
            cluster, _, nerve = key.partition("/")
            out.append({"cluster": cluster, "nerve": nerve, "recent": rc,
                        "recent_rate_hr": round(recent_rate, 3),
                        "baseline_rate_hr": round(baseline_rate, 3)})
    out.sort(key=lambda d: -d["recent_rate_hr"])
    return out


def autonomous_reliability(*, hours: float = 24, incidents: list | None = None) -> dict[str, Any]:
    """Jarvis' autonome pålidelighed fra supervisions-verdikterne (cluster=autonomous nerve=
    supervision incidents, kind=lied/looped/connection_error/failed). Self-safe."""
    now = datetime.now(UTC)
    inc = incidents if incidents is not None else _load()
    kinds: Counter = Counter()
    for r in inc:
        if (str(r.get("cluster")) == "autonomous" and str(r.get("nerve")) == "supervision"
                and _within(r.get("ts"), hours, now)):
            kinds[str(r.get("kind") or "")] += 1
    total_flagged = sum(kinds.values())
    return {
        "flagged_runs": total_flagged,
        "lied": kinds.get("lied", 0), "looped": kinds.get("looped", 0),
        "connection_error": kinds.get("connection_error", 0),
        "failed": kinds.get("failed", 0),
    }


def assess_autonomy(*, hours: float = 24, incidents: list | None = None) -> dict[str, Any]:
    """DETERMINISTISK vurdering: er Jarvis moden til autonome opgaver? Baseret på pålidelighed.
    Løgn/loop er diskvalificerende; ren netværks-flakiness er OK (retryable)."""
    rel = autonomous_reliability(hours=hours, incidents=incidents)
    dishonest = rel["lied"] > 0 or rel["looped"] > 2
    if rel["lied"] > 0:
        verdict, reason = "ikke_moden", f"løj {rel['lied']}× — autonomi kræver ærlighed"
    elif rel["looped"] > 2:
        verdict, reason = "ikke_moden", f"loopede {rel['looped']}× — ustabil"
    elif rel["failed"] > 5:
        verdict, reason = "forsigtig", f"{rel['failed']} fejl — kun lav-risiko todos"
    else:
        verdict, reason = "moden", "ingen løgn/loop-mønster — kan få autonome todos"
    return {"verdict": verdict, "reason": reason, "reliability": rel, "dishonest": dishonest}


def learning_summary() -> dict[str, Any]:
    inc = _load()
    return {
        "cluster_health_24h": cluster_health(hours=24, incidents=inc),
        "degrading": degrading(incidents=inc),
        "autonomy": assess_autonomy(incidents=inc),
    }


def observe_learning() -> dict[str, Any]:
    """Kadence: beregn læring + observe + flag degraderende clusters. ALDRIG auto-reaktion (Ph2)."""
    summary = learning_summary()
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "system", "nerve": "learning",
            "degrading": summary["degrading"][:15],
            "autonomy_verdict": summary["autonomy"]["verdict"],
        })
    except Exception:
        pass
    for d in summary["degrading"]:
        try:
            from core.runtime.db_central_incidents import record_central_incident
            record_central_incident(
                cluster="system", nerve="learning", kind="degrading", severity="error",
                message=(f"{d['cluster']}/{d['nerve']} trender mod nedbrud: "
                         f"{d['recent_rate_hr']}/t vs baseline {d['baseline_rate_hr']}/t"),
            )
        except Exception:
            pass
    return summary
