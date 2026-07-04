"""Internal loopback endpoint for canonical error reports (Fase 0).

Del af Canonical Error System
(docs/superpowers/specs/2026-07-04-canonical-error-system-REVIEW.md §4, §9).

TYND ADAPTER — IKKE en ny ingestion-pipeline og IKKE en ny store. Modtager én
canonical fejl (fra enhver proces/flade) og router den direkte ind i den
EKSISTERENDE Central-maskineri:

    canonical fejl ─▶ envelope_from_kind() ─▶ ErrorEnvelope (dansk bruger-form)
                   ├─▶ central_anomaly.record_anomaly()  (klassificér + dedup + eskalér)
                   ├─▶ central().observe()                (trace-sink telemetri)
                   └─▶ record_central_incident()          (kun error/critical)

Loopback-only som alle /api/internal/-ruter. FAIL-OPEN (§9): en fejl UNDER
fejl-rapportering må ALDRIG kaskade — enhver intern exception → stadig 202.
RATE-LIMIT: ingen ny her — genbruger record_anomaly's eksisterende cooldown/dedup.
DESK-PROXY (Fase 2): desk rapporterer via /api/internal/errors/report; desk-klienten
røres IKKE nu.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/api/internal/errors", tags=["internal"])

_LOCALHOST_HOSTS = {"127.0.0.1", "::1", "localhost"}

# Canonical severity → incident severity. record_central_incident accepterer kun
# ("info","error","severe"); canonical "critical" → "severe".
_INCIDENT_SEVERITY = {
    "critical": "severe", "error": "error",
    "warning": "info", "info": "info", "debug": "info",
}
_ESCALATE_SEVERITIES = {"error", "critical"}
_UNKNOWN_KIND = "ui.unknown"


class _Origin(BaseModel):
    file: str = ""
    function: str = ""


class ErrorReport(BaseModel):
    """Canonical fejl-wire-form (REVIEW §4 / impl-plan §3). Kun kind/severity/
    recoverable/message/source er obligatoriske. Ukendt kind coerces til ui.unknown."""
    kind: str
    severity: str
    recoverable: str
    message: str
    origin: _Origin = Field(default_factory=_Origin)
    scope: str = ""
    session_id: Optional[str] = None
    run_id: Optional[str] = None
    context: Optional[dict[str, Any]] = None
    source: str


def _build_envelope(*, kind: str, origin_cluster: str, run_id: str, detail: str,
                    scope: str):
    """Byg en ErrorEnvelope fra kind. Foretrækker Fase-0-udvidelsen envelope_from_kind
    (som UDLEDER severity/recoverable fra KIND_MAP — de gives IKKE som args). Falder tilbage
    til legacy build_envelope hvis udvidelsen ikke er merget endnu. Self-safe (kalder wrapper)."""
    from core.services import central_error_envelope as cee
    fn = getattr(cee, "envelope_from_kind", None)
    if callable(fn):
        return fn(kind, origin_cluster=origin_cluster, run_id=run_id,
                  detail=detail, scope=scope)
    return cee.build_envelope(code=kind, origin_cluster=origin_cluster,
                              run_id=run_id, detail=detail)


def _route_into_central(report: ErrorReport) -> str:
    """Router én canonical fejl ind i eksisterende Central-maskineri. Returnerer
    correlation_id. Hvert trin er self-safe; fejl i ét springer ikke de øvrige over
    og propagerer aldrig ud (fail-open §9)."""
    run_id = str(report.run_id or "")
    session_id = str(report.session_id or "")
    origin = report.origin or _Origin()
    location = origin.file
    if origin.function:
        location = f"{location}::{origin.function}" if location else origin.function

    correlation_id = run_id
    # Severity til eskalering: canonical KIND_MAP-udledt (fra envelopen); fald tilbage
    # til rapportens egen severity hvis envelope-build fejlede.
    escalate_severity = str(report.severity or "").lower()

    # 1) Byg bruger-vendt envelope (giver correlation_id + dansk form + kanonisk severity).
    try:
        env = _build_envelope(
            kind=report.kind, origin_cluster=str(report.source or ""),
            run_id=run_id, detail=report.message, scope=str(report.scope or ""))
        correlation_id = str(getattr(env, "correlation_id", "") or run_id)
        escalate_severity = str(getattr(env, "severity", "") or escalate_severity).lower()
    except Exception:
        logger.debug("internal-errors: envelope build failed", exc_info=True)

    # 2) Klassificér + dedup + (selv-)eskalér via eksisterende anomaly-maskineri.
    try:
        from core.services.central_anomaly import record_anomaly
        record_anomaly(
            source=str(report.source or "internal_errors"),
            exc_type=str(report.kind or _UNKNOWN_KIND),
            message=str(report.message or ""),
            module=str(report.scope or ""), location=location)
    except Exception:
        logger.debug("internal-errors: record_anomaly failed", exc_info=True)

    # 3) Observér ind i trace-sinken (skalar-sikker telemetri, kaster aldrig).
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": str(report.scope or "system"), "nerve": "canonical_error",
            "kind": str(report.kind or _UNKNOWN_KIND), "severity": escalate_severity,
            "recoverable": str(report.recoverable or ""),
            "source": str(report.source or ""), "run_id": run_id,
            "session_id": session_id})
    except Exception:
        logger.debug("internal-errors: observe failed", exc_info=True)

    # 4) Persistér en incident KUN for error/critical (record_anomaly kan også eskalere
    #    ved første høj/kritisk-sigtning; begge self-safe, incident-rækker billige).
    if escalate_severity in _ESCALATE_SEVERITIES:
        try:
            from core.runtime.db_central_incidents import record_central_incident
            sev = _INCIDENT_SEVERITY.get(escalate_severity, "error")
            _loc = f" @ {location}" if location else ""
            record_central_incident(
                cluster=str(report.scope or "system"), nerve="canonical_error",
                kind=str(report.kind or _UNKNOWN_KIND), severity=sev,
                message=f"[{report.kind}]{_loc}: {report.message}"[:400],
                run_id=run_id, session_id=session_id)
        except Exception:
            logger.debug("internal-errors: incident record failed", exc_info=True)

    return correlation_id


@router.post("/report")
async def report_error(report: ErrorReport, request: Request) -> JSONResponse:
    """Modtag én canonical fejl og router den ind i Central. Returnerer 202.
    Loopback-only (non-local/proxy-forwarded → 403). Manglende felt → 422 (Pydantic).
    Ukendt kind → coerces til ui.unknown, stadig 202. Intern fejl → stadig 202 (§9)."""
    client_host = request.client.host if request.client else ""
    if client_host not in _LOCALHOST_HOSTS:
        logger.warning("internal-errors: rejected non-localhost host=%s", client_host)
        raise HTTPException(status_code=403, detail="loopback-only")
    if request.headers.get("x-forwarded-for") or request.headers.get("forwarded"):
        logger.warning("internal-errors: rejected proxy-forwarded request")
        raise HTTPException(status_code=403, detail="loopback-only (proxy-forwarded)")

    if not str(report.kind or "").strip():
        report.kind = _UNKNOWN_KIND

    correlation_id = ""
    try:
        correlation_id = _route_into_central(report)
    except Exception:
        logger.debug("internal-errors: routing failed (fail-open)", exc_info=True)

    return JSONResponse(
        {"status": "accepted", "correlation_id": correlation_id}, status_code=202)
