"""Autonom run-supervision (#3) — Centralen følger HVERT autonomt run, korrelerer det på tværs
af clusters, og vurderer: kørte det rent, løj Jarvis (truth-gate fyrede RED = konfabulation),
loopede han, eller var det en forbindelsesfejl (retryable)? → observe + flag.

Bygger på cross-cluster korrelation (#1) + de eksisterende gates (truth/loop fyrer ALLEREDE
under runnet — supervisionen LÆSER deres verdikter via korrelationen i stedet for at duplikere
logik). Verificerer dermed at Jarvis udførte arbejdet uden at lyve/loope.

Phase 1: VURDÉR + FLAG (+ markér retryable). Phase 2 (auto-retry ved forbindelsesfejl, auto-
reaktion) er bevidst udskudt — bidirektional reaktion ud i clusterne kræver tillid + data.
Self-safe.
"""
from __future__ import annotations

from typing import Any

_CONNECTION_PATTERNS = (
    "connection", "timeout", "timed out", "urlopen", "httperror", "socket", "reset",
    "refused", "broken pipe", "502", "503", "504", "econn", "ssl",
)


def supervise(run_id: str, outcome: str, error: str = "") -> dict[str, Any]:
    """Vurdér ét autonomt run. outcome ∈ {completed, failed, interrupted}. Returnér verdict +
    retryable + om Jarvis løj/loopede + break-point. Self-safe."""
    rid = str(run_id or "")
    err = str(error or "")
    rep: dict[str, Any] = {"run_id": rid, "outcome": str(outcome or ""), "verdict": "unknown",
                           "retryable": False, "lied": False, "looped": False, "break_point": None}
    try:
        from core.services.central_correlate import correlate
        corr = correlate(rid)
    except Exception:
        corr = {"timeline": [], "break_point": None}
    timeline = corr.get("timeline") or []
    # Gate-signaler fra runnet (truth-RED = konfabulation/løgn; loop-RED = looped).
    lied = any(t.get("cluster") == "truth" and t.get("decision") == "red" for t in timeline)
    looped = any(t.get("cluster") == "loop" and t.get("decision") == "red" for t in timeline)
    is_conn = (str(outcome) in ("failed", "interrupted")
               and any(p in err.lower() for p in _CONNECTION_PATTERNS))
    if lied:
        verdict = "lied"
    elif looped:
        verdict = "looped"
    elif is_conn:
        verdict = "connection_error"
    elif str(outcome) == "completed":
        verdict = "clean"
    else:
        verdict = "failed"
    rep.update({"verdict": verdict, "retryable": is_conn, "lied": lied, "looped": looped,
                "break_point": corr.get("break_point")})

    # observe supervisions-verdiktet
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "autonomous", "nerve": "supervision", "run_id": rid,
            "verdict": verdict, "retryable": is_conn, "lied": lied, "looped": looped,
        })
    except Exception:
        pass

    # flag hvis ikke rent — løgn er ALVORLIGST (sikkerheds-relevant for tillid til autonomi)
    if verdict != "clean":
        sev = "severe" if lied else "error"
        bp = corr.get("break_point") or {}
        try:
            from core.runtime.db_central_incidents import record_central_incident
            record_central_incident(
                cluster="autonomous", nerve="supervision", kind=verdict, severity=sev,
                run_id=rid,
                message=(f"autonomt run {rid}: {verdict}"
                         + (f" (knæk: {bp.get('cluster')}/{bp.get('nerve')})" if bp else "")
                         + (f" — {err[:120]}" if err else "")),
            )
        except Exception:
            pass
    return rep
