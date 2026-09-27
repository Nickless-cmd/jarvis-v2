"""Quota and adaptive health calculations for cheap-lane candidates."""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Callable


_ACCOUNT_BLOCK_CODES = frozenset({"credits-exhausted", "provider-blocked"})
_ACCOUNT_BLOCK_SECONDS = 6 * 3600


def _account_block_key(provider: str, auth_profile: str) -> str:
    return f"cheap_lane:account_block:{provider}:{auth_profile or 'default'}"


def record_account_block(
    provider: str, auth_profile: str, code: str, retry_after_seconds: int,
) -> None:
    """Pause every model on a profile when the provider rejects that account."""
    if code not in _ACCOUNT_BLOCK_CODES:
        return
    from core.runtime.db_core import set_runtime_state_value

    duration = retry_after_seconds if retry_after_seconds > 0 else _ACCOUNT_BLOCK_SECONDS
    set_runtime_state_value(_account_block_key(provider, auth_profile), {
        "until": (datetime.now(UTC) + timedelta(seconds=duration)).isoformat(),
        "reason": code,
    })


def clear_account_block(provider: str, auth_profile: str) -> None:
    """A real success proves that the account can be used again."""
    from core.runtime.db_core import set_runtime_state_value

    set_runtime_state_value(_account_block_key(provider, auth_profile), None)


def _account_block_until(provider: str, auth_profile: str) -> str:
    from core.runtime.db_core import get_runtime_state_value

    value = get_runtime_state_value(_account_block_key(provider, auth_profile))
    return str(value.get("until") or "") if isinstance(value, dict) else ""


def account_block_active(provider: str, auth_profile: str, now_epoch: float) -> bool:
    """Whether this provider account is in its temporary shared cooldown."""
    until = _account_block_until(provider, auth_profile)
    if not until:
        return False
    try:
        return datetime.fromisoformat(until).timestamp() > now_epoch
    except ValueError:  # Malformed optional block state must not stop routing.
        return False


def quota_snapshot(
    candidate: dict[str, object], *,
    get_state: Callable[..., dict[str, object] | None],
    count_invocations: Callable[..., int],
    decode_metadata: Callable[[dict[str, object]], dict[str, object]],
    cache_prefix: str,
    cache_ttl_seconds: float,
    reset_hours: int,
) -> dict[str, object]:
    from core.services import shared_cache

    provider = str(candidate["provider"])
    model = str(candidate["model"])
    auth_profile = str(candidate.get("auth_profile") or "default")
    cache_key = f"{cache_prefix}{provider}/{model}/{auth_profile}"
    cached = shared_cache.get(cache_key)
    if isinstance(cached, dict):
        return cached

    state = get_state(provider=provider, model=model) or {}
    metadata = decode_metadata(state)
    profile_cooldowns = metadata.get("profile_cooldowns") or {}
    profile_until = (profile_cooldowns.get(auth_profile) if isinstance(profile_cooldowns, dict)
                     else None)
    cooldown_until_raw = str(profile_until or state.get("cooldown_until") or "").strip()
    now = datetime.now(UTC)
    cooldown_active = False
    for until in (profile_until, state.get("cooldown_until")):
        if not until:
            continue
        try:
            if datetime.fromisoformat(str(until)) > now:
                cooldown_active = True
                cooldown_until_raw = str(until)
        except ValueError:  # Ignore malformed persisted cooldown and keep routing.
            continue

    account_cooldown_active = False
    account_until = _account_block_until(provider, auth_profile)
    if account_until:
        try:
            account_cooldown_active = datetime.fromisoformat(account_until) > now
        except ValueError:  # Ignore malformed account block and keep routing.
            pass

    requests_last_minute = count_invocations(
        provider=provider, since=(now - timedelta(minutes=1)).isoformat(),
        auth_profile=auth_profile,
    )
    requests_last_day = count_invocations(
        provider=provider, since=(now - timedelta(hours=reset_hours)).isoformat(),
        auth_profile=auth_profile,
    )
    rpm_limit = candidate.get("rpm_limit")
    daily_limit = candidate.get("daily_limit")
    rpm_exhausted = isinstance(rpm_limit, int) and requests_last_minute >= rpm_limit
    daily_exhausted = isinstance(daily_limit, int) and requests_last_day >= daily_limit
    status = ("account-cooldown" if account_cooldown_active else
              "cooldown-active" if cooldown_active else
              "rpm-exhausted" if rpm_exhausted else
              "daily-exhausted" if daily_exhausted else "ready")
    snapshot = {
        "status": status,
        "blocked": account_cooldown_active or cooldown_active or rpm_exhausted or daily_exhausted,
        "cooldown_active": cooldown_active,
        "cooldown_until": account_until if account_cooldown_active else cooldown_until_raw or None,
        "requests_last_minute": requests_last_minute,
        "requests_last_day": requests_last_day,
        "rpm_limit": rpm_limit,
        "daily_limit": daily_limit,
        "daily_neurons": candidate.get("daily_neurons"),
    }
    shared_cache.set(cache_key, snapshot, ttl_seconds=cache_ttl_seconds)
    return snapshot


def adaptive_snapshot(
    candidate: dict[str, object], *,
    state: dict[str, object] | None,
    get_state: Callable[..., dict[str, object] | None],
    decode_metadata: Callable[[dict[str, object]], dict[str, object]],
) -> dict[str, object]:
    current_state = state or get_state(
        provider=str(candidate["provider"]), model=str(candidate["model"]),
    ) or {}
    metadata = decode_metadata(current_state)
    base_priority = int(candidate.get("priority") or 9999)
    success_count = int(metadata.get("success_count") or 0)
    failure_count = int(metadata.get("failure_count") or 0)
    smoke_success_count = int(metadata.get("smoke_success_count") or 0)
    smoke_failure_count = int(metadata.get("smoke_failure_count") or 0)
    avg_latency_ms = float(metadata.get("avg_latency_ms") or 0.0)
    avg_quality_score = float(metadata.get("avg_quality_score") or 1.0)
    total_runs = success_count + failure_count
    success_ratio = 1.0 if total_runs <= 0 else success_count / total_runs
    total_smokes = smoke_success_count + smoke_failure_count
    smoke_success_ratio = 1.0 if total_smokes <= 0 else smoke_success_count / total_smokes
    quality_penalty = max(0.0, (1.0 - avg_quality_score) * 8.0)
    reliability_penalty = max(0.0, (1.0 - success_ratio) * 10.0)
    smoke_penalty = max(0.0, (1.0 - smoke_success_ratio) * 8.0)
    latency_penalty = min(6.0, avg_latency_ms / 1200.0)
    adaptive_penalty = int(round(quality_penalty + reliability_penalty + smoke_penalty + latency_penalty))
    return {
        "base_priority": base_priority,
        "effective_priority": base_priority + adaptive_penalty,
        "adaptive_penalty": adaptive_penalty,
        "success_count": success_count,
        "failure_count": failure_count,
        "smoke_success_count": smoke_success_count,
        "smoke_failure_count": smoke_failure_count,
        "success_ratio": round(success_ratio, 4),
        "smoke_success_ratio": round(smoke_success_ratio, 4),
        "avg_latency_ms": round(avg_latency_ms, 2),
        "avg_quality_score": round(avg_quality_score, 4),
    }


def decode_state_metadata(state: dict[str, object]) -> dict[str, object]:
    raw = state.get("metadata_json")
    if not raw:
        return {}
    try:
        decoded = json.loads(str(raw))
    except (TypeError, ValueError):  # Malformed optional metadata must not block routing.
        return {}
    return decoded if isinstance(decoded, dict) else {}


def rolling_average(*, current_avg: float, current_count: int, new_value: float) -> float:
    if current_count <= 0:
        return float(new_value)
    return ((current_avg * current_count) + new_value) / float(current_count + 1)


def normalize_probe_text(value: str) -> str:
    text = str(value or "").strip().strip("\"'`")
    return " ".join(text.lower().split())


def smoke_quality_score(*, expected: str, actual: str) -> float:
    normalized_expected = normalize_probe_text(expected)
    normalized_actual = normalize_probe_text(actual)
    if normalized_actual == normalized_expected:
        return 1.0
    if normalized_expected and normalized_expected in normalized_actual:
        return 0.9
    return 0.4
