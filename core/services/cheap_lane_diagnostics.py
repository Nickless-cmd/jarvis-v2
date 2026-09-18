"""Read-only, deterministic diagnostics over Cheap Lane source-of-truth data."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from core.services.cheap_lane_balancer import balancer_snapshot
from core.services.cheap_lane_quotas import capacity_snapshot
from core.services.provider_registry_admin import fuld_registrering


def _parse_time(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
    except (TypeError, ValueError):
        return None


def recent_invocations(*, since: datetime, limit: int = 500) -> list[dict[str, object]]:
    from core.runtime.db_cheap_lane_control import list_cheap_lane_invocations

    return list_cheap_lane_invocations(
        since=since.isoformat(), limit=limit
    )["items"]  # type: ignore[return-value]


def central_evidence(*, limit: int = 100) -> list[dict[str, object]]:
    from core.runtime.db_central_incidents import list_central_incidents

    incidents = list_central_incidents(limit=limit, unresolved_only=False)
    markers = ("cheap", "provider", "quota", "balancer", "route")
    return [
        incident for incident in incidents
        if any(marker in " ".join(str(incident.get(field) or "").lower()
                                  for field in ("cluster", "nerve", "kind", "message"))
               for marker in markers)
    ]


def route_integrity(*, since: datetime) -> list[dict[str, object]]:
    from core.runtime.db_cheap_lane_control import _ensure_control_schema
    from core.runtime.db_cheap_provider import _ensure_invocation_schema
    from core.runtime.db_core import connect

    with connect() as conn:
        _ensure_control_schema(conn)
        _ensure_invocation_schema(conn)
        routes = conn.execute(
            "SELECT r.route_decision_id, r.correlation_id, r.created_at "
            "FROM cheap_lane_route_decisions r LEFT JOIN cheap_provider_invocations i "
            "ON i.route_decision_id = r.route_decision_id "
            "WHERE r.created_at >= ? AND i.id IS NULL LIMIT 100",
            (since.isoformat(),),
        ).fetchall()
        invocations = conn.execute(
            "SELECT i.invocation_id, i.route_decision_id, i.created_at "
            "FROM cheap_provider_invocations i LEFT JOIN cheap_lane_route_decisions r "
            "ON r.route_decision_id = i.route_decision_id "
            "WHERE i.created_at >= ? AND i.route_decision_id <> '' "
            "AND r.route_decision_id IS NULL LIMIT 100",
            (since.isoformat(),),
        ).fetchall()
    return [
        {"kind": "route-without-invocation", **dict(row)} for row in routes
    ] + [
        {"kind": "invocation-without-route", **dict(row)} for row in invocations
    ]


def _finding(
    code: str,
    severity: str,
    now: datetime,
    evidence: dict[str, object],
    *,
    provider: str = "",
    slot_id: str = "",
) -> dict[str, object]:
    return {
        "code": code,
        "severity": severity,
        "evidence": evidence,
        "first_observed_at": now.isoformat(),
        "last_observed_at": now.isoformat(),
        "provider": provider or None,
        "slot_id": slot_id or None,
        "central_incident_id": None,
    }


def diagnose_cheap_lane(now: datetime | None = None) -> dict[str, object]:
    instant = now or datetime.now(UTC)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=UTC)
    balancer = balancer_snapshot()
    capacity = capacity_snapshot(now=instant)
    registry = fuld_registrering()
    invocations = recent_invocations(since=instant - timedelta(hours=24))
    integrity = route_integrity(since=instant - timedelta(hours=24))
    findings: list[dict[str, object]] = []
    slots = list(balancer.get("slots") or [])
    eligible_slots = [slot for slot in slots if float(slot.get("weight") or 0) > 0]

    if int(balancer.get("eligible_now") or 0) == 0:
        findings.append(_finding(
            "no-eligible-slot", "critical", instant,
            {"pool_size": len(slots), "blocked": int(balancer.get("blocked_now") or len(slots))},
        ))

    for field, code in (("provider", "provider-starvation"),
                        ("auth_profile", "auth-profile-starvation")):
        groups = {str(slot.get(field) or "default") for slot in slots}
        for group in sorted(groups):
            members = [slot for slot in slots if str(slot.get(field) or "default") == group]
            if members and not any(float(slot.get("weight") or 0) > 0 for slot in members):
                findings.append(_finding(
                    code, "high", instant,
                    {field: group, "slots": len(members)},
                    provider=group if field == "provider" else "",
                ))

    if len(eligible_slots) > 1:
        providers = {str(slot.get("provider") or "") for slot in eligible_slots}
        egresses = {str(slot.get("egress") or "") for slot in eligible_slots}
        if len(providers) == 1 or len(egresses) == 1:
            findings.append(_finding(
                "capacity-concentrated", "medium", instant,
                {"eligible_slots": len(eligible_slots), "providers": sorted(providers),
                 "egresses": sorted(egresses)},
            ))

    saved_at = _parse_time(balancer.get("saved_at"))
    if saved_at and instant - saved_at > timedelta(minutes=5):
        findings.append(_finding(
            "balancer-stale", "medium", instant,
            {"saved_at": saved_at.isoformat()},
        ))

    for window in list(capacity.get("windows") or []):
        provider = str(window.get("provider") or "")
        if window.get("freshness") == "stale":
            findings.append(_finding(
                "quota-stale", "medium", instant,
                {"period": window.get("period"), "unit": window.get("unit")},
                provider=provider,
            ))
        limit = float(window.get("limit") or 0)
        remaining = float(window.get("remaining") or 0)
        if limit > 0 and remaining / limit <= 0.1:
            findings.append(_finding(
                "quota-near-exhaustion", "high", instant,
                {"period": window.get("period"), "unit": window.get("unit"),
                 "remaining": remaining, "limit": limit},
                provider=provider,
            ))
        observed = float(window.get("observed_usage") or 0)
        reported = float(window.get("used") or 0)
        if limit > 0 and abs(observed - reported) / limit >= 0.2:
            findings.append(_finding(
                "quota-mismatch", "medium", instant,
                {"observed_usage": observed, "reported_usage": reported, "limit": limit},
                provider=provider,
            ))

    for slot in slots:
        if int(slot.get("breaker_level") or 0) >= 2 or int(
            slot.get("consecutive_failures") or 0
        ) >= 3:
            findings.append(_finding(
                "breaker-repeated", "high", instant,
                {"breaker_level": slot.get("breaker_level"),
                 "consecutive_failures": slot.get("consecutive_failures")},
                provider=str(slot.get("provider") or ""),
                slot_id=str(slot.get("slot_id") or ""),
            ))

    for provider in list(registry.get("udbydere") or []):
        if not bool(provider.get("credentials_ready", False)):
            findings.append(_finding(
                "credentials-missing", "high", instant,
                {"auth_profile": provider.get("auth_profile")},
                provider=str(provider.get("provider") or ""),
            ))

    if len(invocations) >= 5:
        failures = sum(1 for row in invocations if str(row.get("status")) == "failed")
        latencies = sorted(int(row.get("latency_ms") or 0) for row in invocations)
        p95 = latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))]
        if failures / len(invocations) >= 0.25 or p95 >= 10_000:
            findings.append(_finding(
                "runtime-regression", "high", instant,
                {"requests": len(invocations), "failures": failures, "p95_latency_ms": p95},
            ))
    bypass = [
        row for row in invocations
        if str(row.get("status") or "") not in {"smoke-ok"}
        and not str(row.get("route_decision_id") or "")
    ]
    if bypass:
        findings.append(_finding(
            "route-bypassed", "medium", instant,
            {"count": len(bypass), "sample_invocation_id": bypass[0].get("invocation_id")},
        ))
    if integrity:
        findings.append(_finding(
            "route-trace-mismatch", "high", instant,
            {"count": len(integrity), "samples": integrity[:5]},
        ))

    incidents = central_evidence(limit=100)
    for finding in findings:
        provider = str(finding.get("provider") or "").lower()
        code = str(finding["code"]).replace("-", " ")
        for incident in incidents:
            haystack = " ".join(str(incident.get(field) or "").lower()
                                for field in ("cluster", "nerve", "kind", "message"))
            if (provider and provider in haystack) or any(word in haystack for word in code.split()):
                finding["central_incident_id"] = incident.get("id")
                break

    severity_rank = {"critical": 3, "high": 2, "medium": 1, "low": 0}
    findings.sort(key=lambda item: (-severity_rank.get(str(item["severity"]), 0),
                                    str(item["code"]), str(item.get("provider") or "")))
    return {
        "generated_at": instant.isoformat(),
        "status": "healthy" if not findings else "degraded",
        "findings": findings,
    }
