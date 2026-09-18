"""Quota policy and measured capacity for the Cheap Lane control center."""
from __future__ import annotations

import calendar
from datetime import UTC, datetime, timedelta
from typing import Any

from core.runtime.db_cheap_lane_control import (
    list_quota_observations,
    record_quota_observation,
)
from core.runtime.db_cheap_provider import _ensure_invocation_schema
from core.runtime.db_core import connect

_FRESH_OBSERVATION = timedelta(hours=24)


def set_quota_policy(*, provider: str, auth_profile: str,
                     windows: list[dict[str, object]],
                     expected_revision: str = "") -> dict[str, Any]:
    from core.services.provider_registry_admin import saet_kvote_politik

    return saet_kvote_politik(
        provider=provider,
        auth_profile=auth_profile,
        windows=windows,
        expected_revision=expected_revision,
    )


def observe_provider_quota(*, provider: str, auth_profile: str,
                           observation: dict[str, object]) -> int:
    """Persist an adapter's normalized provider quota observation."""
    required = {"period", "unit", "limit", "remaining"}
    if not required <= observation.keys():
        missing = ", ".join(sorted(required - observation.keys()))
        raise ValueError(f"quota observation mangler: {missing}")
    return record_quota_observation(
        provider=provider,
        auth_profile=auth_profile or "default",
        period=str(observation["period"]),
        unit=str(observation["unit"]),
        limit=float(observation["limit"]) if observation["limit"] is not None else None,
        remaining=(float(observation["remaining"])
                   if observation["remaining"] is not None else None),
        reset_at=(str(observation["reset_at"])
                  if observation.get("reset_at") is not None else None),
        observed_at=(str(observation["observed_at"])
                     if observation.get("observed_at") is not None else None),
    )


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _parse_time(value: object) -> datetime | None:
    try:
        return _utc(datetime.fromisoformat(str(value).replace("Z", "+00:00")))
    except (TypeError, ValueError):
        return None


def _period_bounds(period: str, now: datetime) -> tuple[datetime, datetime]:
    now = _utc(now)
    if period == "minute":
        return now - timedelta(minutes=1), now
    if period == "day":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, start + timedelta(days=1)
    if period == "week":
        start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return start, start + timedelta(days=7)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def _monthly_bounds(reset_day: int, now: datetime) -> tuple[datetime, datetime]:
    """Return the current UTC monthly window for a provider reset day."""
    now = _utc(now)

    def boundary(year: int, month: int) -> datetime:
        day = min(reset_day, calendar.monthrange(year, month)[1])
        return datetime(year, month, day, tzinfo=UTC)

    this_month = boundary(now.year, now.month)
    if now >= this_month:
        start = this_month
        year, month = (now.year + 1, 1) if now.month == 12 else (now.year, now.month + 1)
        return start, boundary(year, month)
    year, month = (now.year - 1, 12) if now.month == 1 else (now.year, now.month - 1)
    return boundary(year, month), this_month


def _usage(*, provider: str, auth_profile: str, unit: str,
           start: datetime, end: datetime) -> float:
    expression = {
        "tokens": "COALESCE(SUM(input_tokens + output_tokens), 0)",
        "requests": "COUNT(*)",
        "credits_usd": "COALESCE(SUM(cost_usd), 0)",
    }[unit]
    with connect() as conn:
        _ensure_invocation_schema(conn)
        row = conn.execute(
            f"SELECT {expression} AS usage FROM cheap_provider_invocations "
            "WHERE lane = 'cheap' AND provider = ? AND auth_profile = ? "
            "AND created_at >= ? AND created_at < ?",
            (provider, auth_profile, start.isoformat(), end.isoformat()),
        ).fetchone()
    return float(row["usage"] or 0)


def _cheap_providers(registry: dict[str, object]) -> list[dict[str, object]]:
    models = list(registry.get("models") or [])  # type: ignore[arg-type]
    active = {
        str(model.get("provider") or "")
        for model in models
        if isinstance(model, dict)
        and str(model.get("lane") or "") == "cheap"
        and bool(model.get("enabled", True))
    }
    return [
        provider for provider in list(registry.get("providers") or [])  # type: ignore[arg-type]
        if isinstance(provider, dict)
        and bool(provider.get("enabled", True))
        and str(provider.get("provider") or "") in active
    ]


def capacity_snapshot(*, now: datetime | None = None) -> dict[str, object]:
    """Combine configured policy, fresh provider truth, and observed usage."""
    from core.runtime.provider_router import load_provider_router_registry

    instant = _utc(now or datetime.now(UTC))
    providers = _cheap_providers(load_provider_router_registry())
    observations = list_quota_observations(limit=500)
    latest: dict[tuple[str, str, str, str], dict[str, object]] = {}
    for observation in observations:
        key = tuple(str(observation.get(field) or "") for field in (
            "provider", "auth_profile", "period", "unit"
        ))
        latest.setdefault(key, observation)

    windows: list[dict[str, object]] = []
    declared_keys: set[tuple[str, str]] = set()
    provider_keys: dict[tuple[str, str], set[str]] = {}
    for provider_entry in providers:
        provider = str(provider_entry.get("provider") or "")
        profile = str(provider_entry.get("auth_profile") or "default")
        policies = list(provider_entry.get("quota_policy") or [])
        for policy in policies:
            if not isinstance(policy, dict):
                continue
            period = str(policy.get("period") or "")
            unit = str(policy.get("unit") or "")
            aggregate_key = (period, unit)
            declared_keys.add(aggregate_key)
            provider_keys.setdefault(aggregate_key, set()).add(provider)
            if period == "month" and policy.get("reset_day") is not None:
                start, end = _monthly_bounds(int(policy["reset_day"]), instant)
            else:
                start, end = _period_bounds(period, instant)
            observed_usage = _usage(
                provider=provider, auth_profile=profile, unit=unit,
                start=start, end=end,
            )
            observation = latest.get((provider, profile, period, unit))
            observed_at = _parse_time(observation.get("observed_at")) if observation else None
            fresh = bool(observed_at and instant - observed_at <= _FRESH_OBSERVATION)
            authoritative = bool(
                fresh and observation is not None
                and observation.get("limit") is not None
                and observation.get("remaining") is not None
            )
            if authoritative:
                limit_value = float(observation["limit"])
                remaining = max(float(observation["remaining"]), 0.0)
                used = max(limit_value - remaining, 0.0)
                source = "provider"
                confidence = "high"
                reset_at = observation.get("reset_at") or end.isoformat()
            else:
                limit_value = float(policy.get("limit") or 0)
                used = observed_usage
                remaining = max(limit_value - used, 0.0)
                source = "configured"
                confidence = "measured"
                reset_at = end.isoformat()
            windows.append({
                "provider": provider,
                "auth_profile": profile,
                "period": period,
                "unit": unit,
                "limit": limit_value,
                "used": used,
                "remaining": remaining,
                "reset_at": reset_at,
                "source": source,
                "confidence": confidence,
                "observed_at": observed_at.isoformat() if observed_at else None,
                "freshness": "fresh" if fresh else ("stale" if observed_at else "unknown"),
                "observed_usage": observed_usage,
            })

    totals: dict[str, dict[str, object]] = {}
    unknown_members: list[dict[str, str]] = []
    cheap_names = {str(entry.get("provider") or "") for entry in providers}
    for period, unit in sorted(declared_keys):
        relevant = [w for w in windows if w["period"] == period and w["unit"] == unit]
        known = provider_keys.get((period, unit), set())
        missing = sorted(cheap_names - known)
        unknown_members.extend(
            {"provider": provider, "period": period, "unit": unit}
            for provider in missing
        )
        totals[f"{period}:{unit}"] = {
            "period": period,
            "unit": unit,
            "limit": (None if missing else sum(float(w["limit"]) for w in relevant)),
            "known_limit": sum(float(w["limit"]) for w in relevant),
            "used": sum(float(w["used"]) for w in relevant),
            "remaining": sum(float(w["remaining"]) for w in relevant),
            "complete": not missing,
        }

    return {
        "generated_at": instant.isoformat(),
        "windows": windows,
        "totals": totals,
        "unknown_members": unknown_members,
    }
