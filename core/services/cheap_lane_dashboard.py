"""Composite, partial-safe snapshot for the Cheap Lane control center."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Callable

from core.services.cheap_lane_balancer import balancer_snapshot
from core.services.cheap_lane_diagnostics import central_evidence, diagnose_cheap_lane
from core.services.cheap_lane_quotas import capacity_snapshot
from core.services.provider_registry_admin import fuld_registrering


def invocation_trends(*, window_hours: int) -> dict[str, object]:
    from core.runtime.db_cheap_lane_control import list_cheap_lane_invocations

    since = datetime.now(UTC) - timedelta(hours=window_hours)
    rows = list_cheap_lane_invocations(since=since.isoformat(), limit=500)["items"]
    return {
        "requests": len(rows),
        "tokens": sum(int(row.get("input_tokens") or 0) + int(row.get("output_tokens") or 0)
                      for row in rows),
        "errors": sum(1 for row in rows if str(row.get("status") or "") == "failed"),
        "cost_usd": sum(float(row.get("cost_usd") or 0) for row in rows),
        "truncated": len(rows) == 500,
    }


def _section(source: str, loader: Callable[[], object]) -> dict[str, object]:
    observed_at = datetime.now(UTC).isoformat()
    try:
        data = loader()
        freshness = "stale" if (
            isinstance(data, dict)
            and any(str(item.get("freshness") or "") == "stale"
                    for item in list(data.get("windows") or []))
        ) else "live"
        return {
            "source": source, "observed_at": observed_at,
            "freshness": freshness, "data": data, "error": None,
        }
    except Exception:
        return {
            "source": source, "observed_at": observed_at,
            "freshness": "unknown", "data": None,
            "error": {"code": "source-unavailable", "message": f"{source} unavailable"},
        }


def build_cheap_lane_dashboard(window_hours: int = 24) -> dict[str, object]:
    hours = max(1, min(int(window_hours), 24 * 31))
    sections = {
        "capacity": _section("quota", capacity_snapshot),
        "providers": _section("provider-registry", fuld_registrering),
        "balancer": _section("balancer", balancer_snapshot),
        "trends": _section("invocation-history", lambda: invocation_trends(window_hours=hours)),
        "diagnostics": _section("diagnostics", diagnose_cheap_lane),
        "central": _section("central-incidents", lambda: central_evidence(limit=100)),
    }
    if any(section["error"] for section in sections.values()):
        status = "partial"
    elif any(section["freshness"] == "stale" for section in sections.values()):
        status = "stale"
    else:
        status = "complete"
    trends = sections["trends"]["data"] if isinstance(sections["trends"]["data"], dict) else {}
    balancer = (sections["balancer"]["data"]
                if isinstance(sections["balancer"]["data"], dict) else {})
    diagnostics = (sections["diagnostics"]["data"]
                   if isinstance(sections["diagnostics"]["data"], dict) else {})
    return {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "window_hours": hours,
        "status": status,
        "kpis": {
            "requests": int(trends.get("requests") or 0),
            "tokens": int(trends.get("tokens") or 0),
            "errors": int(trends.get("errors") or 0),
            "cost_usd": float(trends.get("cost_usd") or 0),
            "eligible_slots": int(balancer.get("eligible_now") or 0),
            "active_findings": len(list(diagnostics.get("findings") or [])),
        },
        "sections": sections,
    }
