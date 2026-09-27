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

    rows: list[dict[str, object]] = []
    cursor = ""
    while True:
        page = list_cheap_lane_invocations(
            since=since.isoformat(), limit=limit, cursor=cursor,
        )
        rows.extend(page["items"])
        next_cursor = str(page.get("next_cursor") or "")
        if not next_cursor or next_cursor == cursor:
            return rows
        cursor = next_cursor


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

    # A route is written before dispatch. Let in-flight calls finish before
    # treating the missing invocation as a trace mismatch.
    mature_before = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    with connect() as conn:
        _ensure_control_schema(conn)
        _ensure_invocation_schema(conn)
        routes = conn.execute(
            "SELECT r.route_decision_id, r.correlation_id, r.created_at "
            "FROM cheap_lane_route_decisions r LEFT JOIN cheap_provider_invocations i "
            "ON i.route_decision_id = r.route_decision_id "
            "WHERE r.created_at >= ? AND r.created_at < ? AND i.id IS NULL LIMIT 100",
            (since.isoformat(), mature_before),
        ).fetchall()
        invocations = conn.execute(
            "SELECT i.invocation_id, i.route_decision_id, i.created_at "
            "FROM cheap_provider_invocations i LEFT JOIN cheap_lane_route_decisions r "
            "ON r.route_decision_id = i.route_decision_id "
            "WHERE i.created_at >= ? AND i.route_decision_id <> '' "
            "AND r.route_decision_id IS NULL LIMIT 100",
            (since.isoformat(),),
        ).fetchall()
        restarts = [
            _parse_time(row["created_at"])
            for row in conn.execute(
                "SELECT created_at FROM events WHERE kind = 'runtime.started' "
                "AND created_at >= ?",
                ((since - timedelta(minutes=1)).isoformat(),),
            ).fetchall()
        ]
    return [
        {
            "kind": (
                "route-interrupted-by-restart"
                if created is not None and any(
                    abs((started - created).total_seconds()) <= 60
                    for started in restarts if started is not None
                )
                else "route-without-invocation"
            ),
            **dict(row),
        }
        for row in routes
        for created in [_parse_time(row["created_at"])]
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


def invocation_health(rows: list[dict[str, object]]) -> dict[str, object]:
    """Summarize the full invocation window without merging account outcomes."""
    groups: dict[str, dict[str, list[dict[str, object]]]] = {
        "by_profile": {}, "by_provider_profile": {},
    }
    for row in rows:
        profile = str(row.get("auth_profile") or "default")
        provider = str(row.get("provider") or "")
        groups["by_profile"].setdefault(profile, []).append(row)
        groups["by_provider_profile"].setdefault(f"{provider}::{profile}", []).append(row)

    def metrics(items: list[dict[str, object]]) -> dict[str, int]:
        latencies = sorted(int(item.get("latency_ms") or 0) for item in items)
        return {
            "requests": len(items),
            "failures": sum(str(item.get("status") or "") == "failed" for item in items),
            "p95_latency_ms": latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))]
            if latencies else 0,
        }

    return {
        **metrics(rows),
        **{kind: {key: metrics(items) for key, items in entries.items()}
           for kind, entries in groups.items()},
    }


def unrouted_pool_invocations(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Find missing route IDs only where a cheap-pool route was expected."""
    return [
        row for row in rows
        if str(row.get("provider") or "") != "ollama"  # direct local fallback
        and str(row.get("status") or "") != "smoke-ok"
        and not str(row.get("route_decision_id") or "")
    ]


#: Værdien i `cheap_provider_invocations.status` for et gennemført kald.
#: MÅLT, ikke antaget: kolonnen rummer `completed` og `failed` — aldrig `ok`.
_STATUS_SUCCES = "completed"


def health_divergence(slots: list[dict[str, object]], *,
                      since: datetime) -> list[dict[str, object]]:
    """Slots balanceren holder i cooldown, mens lanen HAR haft succes bagefter.

    FUNDET af codex 27/9-2026: OVHcloud gennemførte et kald kl. 06:58, mens
    balancerens registrerede seneste succes stod på 06:40 og slottet stadig lå
    i cooldown. To bøger over den samme udbyders sundhed, og de stemmer ikke.

    Årsagen er mekanisk: `_register_success` i balanceren rydder cooldown og
    tæller breakeren ned — men den kaldes KUN når kaldet gik gennem
    balanceren. Selection-lanen kan ramme samme udbyder udenom, og den succes
    når aldrig frem. Slottet bliver liggende i en cooldown virkeligheden har
    modbevist.

    DENNE FUNKTION ÆNDRER INGEN RUTNING. Den måler kun uenigheden. Det er med
    vilje: at lade en selection-succes rydde balancerens cooldown ville være en
    adfærdsændring i den varme sti, og de to lag kan have gode grunde til at
    holde hver sin bog (andre konti, andre profiler). Først skal uenigheden
    kunne SES — så kan nogen afgøre hvilken bog der har ret.

    En cooldown uden en nyere succes er ikke en uenighed; den er balanceren der
    gør sit arbejde. Derfor meldes kun de slots hvor lanen beviseligt kom
    igennem bagefter.

    STATUS-VÆRDIEN ER `completed`, IKKE `ok`. Første udgave af denne funktion
    filtrerede på `'ok'` — en værdi jeg selv fandt på — og vagten kunne derfor
    ALDRIG fyre. Målt i produktionen 27/9-2026, sidste døgn:

        completed   5082
        failed       434

    Der findes ingen `ok`. `_STATUS_SUCCES` er derfor pinnet i en test mod den
    ægte kolonne, ikke mod en konstant jeg selv skrev.
    """
    i_cooldown = [s for s in slots
                  if str(s.get("status") or "") == "cooldown"
                  and str(s.get("provider") or "")]
    if not i_cooldown:
        return []

    # Samme funktions-lokale import som `route_integrity` ovenfor: modulet
    # holder ikke en DB-reference paa modulniveau.
    from core.runtime.db_core import connect

    fundet: list[dict[str, object]] = []
    with connect() as conn:
        for slot in i_cooldown:
            provider = str(slot.get("provider") or "")
            profil = str(slot.get("auth_profile") or "default")
            raekke = conn.execute(
                "SELECT MAX(created_at) FROM cheap_provider_invocations "
                "WHERE provider = ? AND COALESCE(NULLIF(auth_profile, ''), 'default') = ? "
                "AND status = ? AND created_at >= ?",
                (provider, profil, _STATUS_SUCCES, since.isoformat()),
            ).fetchone()
            lanens = _parse_time((raekke or [None])[0])
            if lanens is None:
                continue
            balancerens = _parse_time(slot.get("last_success_at"))
            if balancerens is not None and lanens <= balancerens:
                continue
            fundet.append({
                "provider": provider,
                "auth_profile": profil,
                "slot_id": str(slot.get("slot_id") or ""),
                "balancer_last_success": (balancerens.isoformat()
                                          if balancerens else None),
                "lane_last_success": lanens.isoformat(),
                "bagud_s": (round((lanens - balancerens).total_seconds(), 1)
                            if balancerens else None),
                "cooldown_until": slot.get("cooldown_until"),
                "cooldown_reason": slot.get("cooldown_reason"),
            })
    return fundet


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
                parked = all(bool(slot.get("account_block_reason")) for slot in members)
                findings.append(_finding(
                    code, "medium" if parked else "high", instant,
                    {field: group, "slots": len(members), "account_parked": parked},
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

    parked_accounts: dict[tuple[str, str, str], list[dict[str, object]]] = {}
    for slot in slots:
        account_reason = str(slot.get("account_block_reason") or "")
        if account_reason:
            key = (str(slot.get("provider") or ""),
                   str(slot.get("auth_profile") or "default"), account_reason)
            parked_accounts.setdefault(key, []).append(slot)
            continue
        if int(slot.get("breaker_level") or 0) >= 2 or int(
            slot.get("consecutive_failures") or 0
        ) >= 3:
            active_cooldown = (str(slot.get("status") or "") == "cooldown"
                               and float(slot.get("weight") or 0) <= 0)
            findings.append(_finding(
                "breaker-repeated", "high" if active_cooldown else "medium", instant,
                {"breaker_level": slot.get("breaker_level"),
                 "consecutive_failures": slot.get("consecutive_failures"),
                 "status": slot.get("status")},
                provider=str(slot.get("provider") or ""),
                slot_id=str(slot.get("slot_id") or ""),
            ))
    for uenig in health_divergence(slots, since=instant - timedelta(hours=24)):
        findings.append(_finding(
            "health-divergence", "medium", instant,
            {k: v for k, v in uenig.items() if k not in ("provider", "slot_id")},
            provider=str(uenig.get("provider") or ""),
            slot_id=str(uenig.get("slot_id") or ""),
        ))

    for (provider, profile, reason), members in sorted(parked_accounts.items()):
        findings.append(_finding(
            "account-parked", "medium", instant,
            {"auth_profile": profile, "reason": reason,
             "affected_slots": len(members),
             "until": members[0].get("account_block_until")},
            provider=provider,
        ))

    for provider in list(registry.get("udbydere") or []):
        if not bool(provider.get("credentials_ready", False)):
            findings.append(_finding(
                "credentials-missing", "high", instant,
                {"auth_profile": provider.get("auth_profile")},
                provider=str(provider.get("provider") or ""),
            ))

    health = invocation_health(invocations)
    if len(invocations) >= 5:
        failures = int(health["failures"])
        p95 = int(health["p95_latency_ms"])
        if failures / len(invocations) >= 0.25 or p95 >= 10_000:
            findings.append(_finding(
                "runtime-regression", "high", instant,
                health,
            ))
    bypass = unrouted_pool_invocations(invocations)
    if bypass:
        findings.append(_finding(
            "route-bypassed", "medium", instant,
            {"count": len(bypass), "sample_invocation_id": bypass[0].get("invocation_id")},
        ))
    interrupted = [item for item in integrity
                   if item.get("kind") == "route-interrupted-by-restart"]
    mismatches = [item for item in integrity
                  if item.get("kind") != "route-interrupted-by-restart"]
    if interrupted:
        findings.append(_finding(
            "route-interrupted", "medium", instant,
            {"count": len(interrupted), "samples": interrupted[:5]},
        ))
    if mismatches:
        findings.append(_finding(
            "route-trace-mismatch", "high", instant,
            {"count": len(mismatches), "samples": mismatches[:5]},
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
