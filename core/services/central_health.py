"""Central self-helbred (§1: "hvem overvåger Centralen?"). Centralen prober SIG SELV på en
kadence og ESKALERER hvis den degraderer — så hvis decide()/observe() selv begynder at fejle,
opdager vi det FØR gates holder op med at virke i stilhed.

Adresserer Bjørns punkter:
  #1 self-check    — central().self_diagnose() (decide+observe-probe, åbne breakers, sink).
  #5 persistence   — circuit-breaker er IN-MEMORY pr. proces → nulstilles ved genstart. Det er
                     BEVIDST (genstart = recovery; en evigt-trippet breaker ville være værre).
                     Gjort eksplicit her + i CircuitBreaker.open_nerves docstring.
  #6 escalation    — degraded / åbne breakers / mange uløste severe incidents → ntfy til Bjørn
                     + persistent self_health-incident (pollbar), ud over ren logging.

Self-safe: kaster aldrig. Bør kaldes på en hyppig kadence (fx hver time).
"""
from __future__ import annotations

from typing import Any

# Tærskler for eskalering (kan kalibreres når vi har data).
_SEVERE_INCIDENT_ALARM = 5


def check() -> dict[str, Any]:
    """Kør Centralens self_diagnose + tilføj uløst-severe-incident-tæller. Self-safe."""
    rep: dict[str, Any] = {"decide_ok": False, "observe_ok": False,
                           "open_breakers": [], "trace_records": 0, "degraded": True}
    try:
        from core.services.central_core import central
        rep.update(central().self_diagnose())
    except Exception:
        pass
    try:
        from core.runtime.db_central_incidents import count_unresolved
        rep["unresolved_severe"] = int(count_unresolved(min_severity="severe"))
    except Exception:
        rep["unresolved_severe"] = 0
    return rep


def _escalation_reasons(rep: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if rep.get("degraded"):
        reasons.append(f"decide_ok={rep.get('decide_ok')} observe_ok={rep.get('observe_ok')}")
    if rep.get("open_breakers"):
        reasons.append(f"åbne circuit-breakers: {rep.get('open_breakers')}")
    if int(rep.get("unresolved_severe") or 0) >= _SEVERE_INCIDENT_ALARM:
        reasons.append(f"{rep.get('unresolved_severe')} uløste severe incidents")
    return reasons


def observe_and_escalate() -> dict[str, Any]:
    """Kør check → observe til Centralen → ESKALÉR (ntfy + persistent incident) hvis degraded.
    Kadence-kaldt. ALDRIG destruktiv."""
    rep = check()
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "system", "nerve": "central_health",
            "decide_ok": rep.get("decide_ok"), "observe_ok": rep.get("observe_ok"),
            "degraded": rep.get("degraded"), "open_breakers": rep.get("open_breakers"),
            "unresolved_severe": rep.get("unresolved_severe"),
        })
    except Exception:
        pass
    reasons = _escalation_reasons(rep)
    if reasons:
        msg = "Den Intelligente Central self-helbred: " + "; ".join(reasons)
        try:
            from core.services.ntfy_gateway import send_notification
            send_notification("⚠ " + msg, title="Central self-helbred", priority="high")
        except Exception:
            pass
        try:
            from core.runtime.db_central_incidents import record_central_incident
            record_central_incident(cluster="system", nerve="central_health",
                                    kind="self_health", severity="severe", message=msg)
        except Exception:
            pass
    return rep


def build_central_health_surface() -> dict[str, object]:
    """MC-surface — read-only self-helbreds-projektion."""
    rep = check()
    return {
        "active": True, "mode": "central_health",
        "decide_ok": rep.get("decide_ok"), "observe_ok": rep.get("observe_ok"),
        "degraded": rep.get("degraded"), "open_breakers": rep.get("open_breakers"),
        "trace_records": rep.get("trace_records"),
        "unresolved_severe": rep.get("unresolved_severe"),
        "note": "circuit-breakers er per-proces in-memory → nulstilles ved genstart (bevidst)",
        "authority": "derived-read-only",
    }
