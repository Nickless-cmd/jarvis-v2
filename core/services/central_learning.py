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
        # Degradering = ONGOING trend mod nedbrud. En RESOLVED incident er håndteret (ikke
        # degradering); INFO-niveau er rutine-governance / ekstern-scan-støj / auto-healed
        # (ikke nedbrud). Kun ULØSTE error/severe tæller → normal drift farver IKKE Centralen gul.
        if r.get("resolved"):
            continue
        if str(r.get("severity")) not in ("error", "severe"):
            continue
        key = f"{r.get('cluster')}/{r.get('nerve')}"
        if _within(r.get("ts"), recent_hours, now):
            recent[key] += 1
        if _within(r.get("ts"), baseline_hours, now):
            base[key] += 1
    out: list[dict[str, Any]] = []
    for key, rc in recent.items():
        if rc < _DEGRADE_MIN_RECENT:
            continue
        cluster, _, nerve = key.partition("/")
        # Ekskludér Centralens EGEN meta-observation (system/learning) fra degraderings-
        # analysen: ellers ville lærings-signalet om degradering selv tælle som degradering
        # → selv-forstærkende loop ("learning trender mod nedbrud").
        if cluster == "system" and nerve == "learning":
            continue
        recent_rate = rc / recent_hours
        baseline_rate = base.get(key, rc) / baseline_hours
        if recent_rate > baseline_rate * _DEGRADE_FACTOR:
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


import re

# Rod-årsag: en gentaget fejl-signatur skal optræde mindst så mange gange i vinduet.
_ROOTCAUSE_MIN = 3
_RE_HEXID = re.compile(r"\b[0-9a-f]{8,}\b", re.I)   # run-id'er/hashes
_RE_NUM = re.compile(r"\d+")
_RE_QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"")


def _signature(message: str) -> str:
    """Normalisér en incident-besked til en stabil signatur så GENTAGNE fejl grupperes:
    strip run-id'er/hashes/tal/citerede værdier → kernen tilbage. Det er broen fra
    symptom (mange enkelt-incidents) til ROD (ét mønster)."""
    s = str(message or "")
    s = _RE_HEXID.sub("<id>", s)
    s = _RE_QUOTED.sub("<v>", s)
    s = _RE_NUM.sub("<n>", s)
    return " ".join(s.split())[:160]


def root_causes(*, hours: float = 48, min_count: int = _ROOTCAUSE_MIN,
                incidents: list | None = None) -> list[dict[str, Any]]:
    """Gruppér incidents efter (cluster/nerve/signatur) → rangerede GENTAGNE rod-årsager
    (ikke symptomer). Hver med antal + først/sidst set + et eksempel. Det er "identificér
    den enkelte fejl helt ind ved roden" (Bjørn). Deterministisk."""
    now = datetime.now(UTC)
    inc = incidents if incidents is not None else _load()
    groups: dict[tuple, dict[str, Any]] = {}
    for r in inc:
        if not _within(r.get("ts"), hours, now):
            continue
        sig = _signature(str(r.get("message") or ""))
        key = (str(r.get("cluster") or ""), str(r.get("nerve") or ""), sig)
        g = groups.setdefault(key, {"cluster": key[0], "nerve": key[1], "signature": sig,
                                    "count": 0, "severe": 0, "first": None, "last": None,
                                    "sample": str(r.get("message") or "")[:200]})
        g["count"] += 1
        if str(r.get("severity")) == "severe":
            g["severe"] += 1
        ts = str(r.get("ts") or "")
        if g["first"] is None or ts < g["first"]:
            g["first"] = ts
        if g["last"] is None or ts > g["last"]:
            g["last"] = ts
    out = [g for g in groups.values() if g["count"] >= min_count]
    out.sort(key=lambda d: (-d["severe"], -d["count"]))
    return out


def propose_adjustments(*, incidents: list | None = None) -> list[dict[str, Any]]:
    """DETERMINISTISKE, reviewbare FORSLAG (aldrig auto-anvendt — Bjørn: "forslag ikke
    ændringer"). Udledt af degrading-trends + rod-årsager + autonomi-modenhed. Hver bærer
    en handling Bjørn/Claude/Jarvis kan tage stilling til + hvor i koden roden ligger."""
    inc = incidents if incidents is not None else _load()
    proposals: list[dict[str, Any]] = []

    # 1. Degraderende nerver → foreslå undersøgelse/midlertidig isolering (ikke auto).
    for d in degrading(incidents=inc):
        proposals.append({
            "kind": "investigate_degrading", "priority": 2,
            "target": f"{d['cluster']}/{d['nerve']}",
            "action": (f"{d['cluster']}/{d['nerve']} trender mod nedbrud "
                       f"({d['recent_rate_hr']}/t vs baseline {d['baseline_rate_hr']}/t) — "
                       f"undersøg roden; overvej midlertidig isolering via central_switches "
                       f"hvis det eskalerer (manuelt valg)."),
        })

    # 2. Gentagne rod-årsager → foreslå fix ved kilden (med lokation fra kataloget).
    for g in root_causes(incidents=inc):
        loc = ""
        try:
            from core.services.central_catalog import nerve_location
            loc = nerve_location(g["nerve"]) or ""
        except Exception:
            pass
        proposals.append({
            "kind": "fix_root_cause", "priority": 1 if g["severe"] else 3,
            "target": f"{g['cluster']}/{g['nerve']}",
            "action": (f"Rod-årsag ramt {g['count']}× ({g['severe']} severe): "
                       f"\"{g['signature']}\" — fix ved kilden{f' ({loc})' if loc else ''}."),
            "sample": g["sample"],
        })

    # 3. Autonomi-modenhed → forslag om hvilke todos Jarvis kan få (ingen auto-tildeling).
    a = assess_autonomy(incidents=inc)
    if a["verdict"] == "moden":
        proposals.append({"kind": "autonomy_ready", "priority": 4, "target": "jarvis",
                          "action": "Jarvis viser intet løgn/loop-mønster — kan få lav/middel-risiko "
                                    "autonome todos (manuel tildeling, ikke auto)."})
    elif a["verdict"] in ("ikke_moden", "forsigtig"):
        proposals.append({"kind": "autonomy_hold", "priority": 2, "target": "jarvis",
                          "action": f"Hold autonome todos tilbage: {a['reason']}."})

    proposals.sort(key=lambda p: p["priority"])
    return proposals


def learning_summary() -> dict[str, Any]:
    inc = _load()
    return {
        "cluster_health_24h": cluster_health(hours=24, incidents=inc),
        "degrading": degrading(incidents=inc),
        "root_causes": root_causes(incidents=inc),
        "proposals": propose_adjustments(incidents=inc),
        "autonomy": assess_autonomy(incidents=inc),
    }


def observe_learning() -> dict[str, Any]:
    """Kadence: beregn læring + observe + flag degraderende clusters + emit FORSLAG.
    ALDRIG auto-reaktion/-mutation (Phase 2). Forslag er reviewbare, ikke handlinger."""
    summary = learning_summary()
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "system", "nerve": "learning",
            "degrading": summary["degrading"][:15],
            "root_causes": [{"target": f"{g['cluster']}/{g['nerve']}", "count": g["count"]}
                            for g in summary["root_causes"][:10]],
            "proposals": [{"kind": p["kind"], "target": p["target"]} for p in summary["proposals"][:15]],
            "autonomy_verdict": summary["autonomy"]["verdict"],
        })
    except Exception:
        pass
    # Degradering er en LIVE projektion (beregnet on-demand af degrading() til både panelet
    # og observe()-telemetrien ovenfor). Vi persisterer den IKKE som incidents: at skrive et
    # afledt signal tilbage i kilde-incident-tabellen er dual-truth (MC læser projektioner,
    # opfinder ikke en anden sandhed) OG skabte en feedback-loop (system/learning-incidents
    # hævede learning-raten → learning flaggede sig selv) + ubegrænset ophobning uden dedup.
    return summary


def poll_proposals(*, limit: int = 20) -> list[dict[str, Any]]:
    """Reviewbar liste af deterministiske lærings-forslag (til Bjørn/Claude/MC/Jarvis).
    Pollbar — handler ALDRIG selv. Bjørn: notificér + foreslå, ingen auto-ændringer."""
    try:
        return propose_adjustments()[:limit]
    except Exception:
        return []
