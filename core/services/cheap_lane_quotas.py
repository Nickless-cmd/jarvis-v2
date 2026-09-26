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
    observation_id = record_quota_observation(
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
    try:
        from core.eventbus.bus import event_bus

        event_bus.publish("runtime.cheap_lane_quota_observed", {
            "provider": provider,
            "auth_profile": auth_profile or "default",
            "period": str(observation["period"]),
            "unit": str(observation["unit"]),
        })
    except Exception:
        pass
    return observation_id


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


def _active_profiles(provider: str, registry_profile: str, *, multiprofile: bool) -> list[str]:
    """Use the same ready account scan as the cheap-lane router."""
    from core.services.auth_profile_scan import ready_profiles_for

    if not multiprofile:
        return [registry_profile or "default"]
    ready = ready_profiles_for(provider)
    return ready or [registry_profile or "default"]


def _account_group(provider: str, profile: str) -> str:
    """Logical owner of usage; gateway Ollama Cloud uses its own account2 login."""
    from core.services.cheap_provider_catalogue import CHEAP_PROVIDER_DEFAULTS

    if provider == "ollama-a2":
        return "account2"
    if profile.startswith("account") and profile[7:].isdigit():
        return profile
    if str((CHEAP_PROVIDER_DEFAULTS.get(provider) or {}).get("auth_kind") or "") == "none":
        return "shared"
    return "account1"


def _measured_usage(now: datetime) -> dict[str, dict[str, object]]:
    """Calendar-window token accounting, including profiles without policies."""
    result: dict[str, dict[str, object]] = {}
    with connect() as conn:
        _ensure_invocation_schema(conn)
        for period in ("day", "week", "month"):
            start, end = _period_bounds(period, now)
            rows = conn.execute(
                "SELECT provider, COALESCE(NULLIF(auth_profile, ''), 'default') AS profile, "
                "COUNT(*) AS calls, COALESCE(SUM(input_tokens), 0) AS input_tokens, "
                "COALESCE(SUM(output_tokens), 0) AS output_tokens, "
                "SUM(CASE WHEN status = 'completed' AND input_tokens + output_tokens = 0 "
                "THEN 1 ELSE 0 END) AS unmetered_calls "
                "FROM cheap_provider_invocations WHERE lane = 'cheap' "
                "AND created_at >= ? AND created_at < ? GROUP BY provider, profile",
                (start.isoformat(), end.isoformat()),
            ).fetchall()
            profiles = [{
                "provider": str(row["provider"]),
                "auth_profile": str(row["profile"]),
                "account": _account_group(str(row["provider"]), str(row["profile"])),
                "calls": int(row["calls"]),
                "input_tokens": int(row["input_tokens"]),
                "output_tokens": int(row["output_tokens"]),
                "total_tokens": int(row["input_tokens"]) + int(row["output_tokens"]),
                "unmetered_calls": int(row["unmetered_calls"] or 0),
            } for row in rows]
            account_totals: dict[str, dict[str, object]] = {}
            for profile in profiles:
                account = str(profile["account"])
                group = account_totals.setdefault(account, {
                    "account": account, "input_tokens": 0, "output_tokens": 0,
                    "total_tokens": 0, "calls": 0, "unmetered_calls": 0,
                })
                for field in ("input_tokens", "output_tokens", "total_tokens", "calls", "unmetered_calls"):
                    group[field] = int(group[field]) + int(profile[field])
            result[period] = {
                "start_at": start.isoformat(), "end_at": end.isoformat(),
                "input_tokens": sum(p["input_tokens"] for p in profiles),
                "output_tokens": sum(p["output_tokens"] for p in profiles),
                "total_tokens": sum(p["total_tokens"] for p in profiles),
                "calls": sum(p["calls"] for p in profiles),
                "unmetered_calls": sum(p["unmetered_calls"] for p in profiles),
                "profiles": sorted(profiles, key=lambda p: (-p["total_tokens"], p["provider"], p["auth_profile"])),
                "accounts": sorted(account_totals.values(), key=lambda p: str(p["account"])),
            }
    return result


def _estimated_capacity(
    now: datetime, members: set[tuple[str, str]],
    usage: dict[str, dict[str, object]],
) -> dict[str, dict[str, object]]:
    """Upper-bound forecast from configured request caps and observed call size.

    A request cap is not a token quota. The result is deliberately labelled an
    estimate and never added to provider-reported token quotas.
    """
    from core.services.cheap_provider_runtime_adapters import (
        provider_cost_class, provider_runtime_defaults, is_routable_provider,
    )

    since = (now - timedelta(days=7)).isoformat()
    with connect() as conn:
        rows = conn.execute(
            "SELECT provider, COALESCE(NULLIF(auth_profile, ''), 'default') AS profile, "
            "COUNT(*) AS calls, SUM(input_tokens + output_tokens) AS tokens "
            "FROM cheap_provider_invocations WHERE lane = 'cheap' "
            "AND status = 'completed' AND input_tokens + output_tokens > 0 "
            "AND created_at >= ? AND created_at < ? GROUP BY provider, profile",
            (since, now.isoformat()),
        ).fetchall()
    samples = {
        (str(row["provider"]), str(row["profile"])):
        (int(row["calls"]), int(row["tokens"]))
        for row in rows
    }
    observed_7d = sum(
        tokens for (provider, profile), (_, tokens) in samples.items()
        if (provider, profile) in members
        and provider_cost_class(provider) != "paid"
        and is_routable_provider(provider)
    )
    today_calls = {
        (str(row["provider"]), str(row["auth_profile"])): int(row["calls"])
        for row in usage["day"]["profiles"]  # type: ignore[index]
    }
    estimates: dict[str, dict[str, object]] = {}
    for period in ("day", "week", "month"):
        _, end = _period_bounds(period, now)
        future_days = max(0, (end.date() - now.date()).days - 1)
        profiles: list[dict[str, object]] = []
        unknown: list[dict[str, str]] = []
        for provider, profile in sorted(members):
            if provider_cost_class(provider) == "paid" or not is_routable_provider(provider):
                continue
            defaults = provider_runtime_defaults(provider)
            daily_limit = defaults.get("daily_limit")
            sample_calls, sample_tokens = samples.get((provider, profile), (0, 0))
            if not isinstance(daily_limit, int) or daily_limit <= 0 or sample_calls == 0:
                unknown.append({"provider": provider, "auth_profile": profile})
                continue
            remaining_calls_today = max(0, daily_limit - today_calls.get((provider, profile), 0))
            calls = remaining_calls_today + future_days * daily_limit
            estimate = round(calls * sample_tokens / sample_calls)
            profiles.append({
                "provider": provider, "auth_profile": profile,
                "account": _account_group(provider, profile),
                "daily_call_limit": daily_limit,
                "sample_calls": sample_calls,
                "mean_tokens_per_call": round(sample_tokens / sample_calls),
                "remaining_calls": calls,
                "estimated_tokens": estimate,
            })
        estimates[period] = {
            "known_estimate_tokens": sum(int(p["estimated_tokens"]) for p in profiles),
            "complete": not unknown,
            "unknown_members": unknown,
            "profiles": sorted(profiles, key=lambda p: -int(p["estimated_tokens"])),
            "end_at": end.isoformat(),
        }
        if period == "month":
            estimates[period]["observed_7d_tokens"] = observed_7d
            estimates[period]["observed_30d_run_rate"] = round(observed_7d * 30 / 7)
    return estimates


def capacity_snapshot(*, now: datetime | None = None) -> dict[str, object]:
    """Combine configured policy, fresh provider truth, and observed usage."""
    from core.runtime.db_core import get_runtime_state_bool
    from core.runtime.provider_router import load_provider_router_registry

    instant = _utc(now or datetime.now(UTC))
    multiprofile = get_runtime_state_bool("cheap_pool_multiprofile_enabled", False)
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
    provider_keys: dict[tuple[str, str], set[tuple[str, str]]] = {}
    active_members: set[tuple[str, str]] = set()
    for provider_entry in providers:
        provider = str(provider_entry.get("provider") or "")
        registry_profile = str(provider_entry.get("auth_profile") or "default")
        profiles = _active_profiles(provider, registry_profile, multiprofile=multiprofile)
        active_members.update((provider, profile) for profile in profiles)
        for profile in profiles:
            policies = (
                list(provider_entry.get("quota_policy") or [])
                if profile == registry_profile else
                list((provider_entry.get("quota_policies") or {}).get(profile) or [])
            )
            declared = {
                (str(p.get("period") or ""), str(p.get("unit") or ""))
                for p in policies if isinstance(p, dict)
            }
            for (observed_provider, observed_profile, period, unit), observation in latest.items():
                if (observed_provider, observed_profile) != (provider, profile):
                    continue
                if (period, unit) in declared:
                    continue
                if period not in {"minute", "day", "week", "month"}:
                    continue
                if unit not in {"tokens", "requests", "credits_usd"}:
                    continue
                observed_at = _parse_time(observation.get("observed_at"))
                if not (observed_at and timedelta(0) <= instant - observed_at <= _FRESH_OBSERVATION):
                    continue
                if observation.get("limit") is None or observation.get("remaining") is None:
                    continue
                policies.append({"period": period, "unit": unit, "limit": observation["limit"]})
            for policy in policies:
                if not isinstance(policy, dict):
                    continue
                period = str(policy.get("period") or "")
                unit = str(policy.get("unit") or "")
                aggregate_key = (period, unit)
                declared_keys.add(aggregate_key)
                provider_keys.setdefault(aggregate_key, set()).add((provider, profile))
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
    for period, unit in sorted(declared_keys):
        relevant = [w for w in windows if w["period"] == period and w["unit"] == unit]
        known = provider_keys.get((period, unit), set())
        missing = sorted(active_members - known)
        unknown_members.extend(
            {"provider": provider, "auth_profile": profile, "period": period, "unit": unit}
            for provider, profile in missing
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

    usage = _measured_usage(instant)
    return {
        "generated_at": instant.isoformat(),
        "windows": windows,
        "totals": totals,
        "unknown_members": unknown_members,
        "usage": usage,
        "estimated_capacity": _estimated_capacity(instant, active_members, usage),
    }
