"""Cheap Lane Balancer — weighted-random load balancing for daemon LLM calls.

Spreads daemon traffic across all available (provider, model) slots
(excluding local ollama, openai-codex, codex-cli) so that no single
quota gets drained while others sit idle.

Plan: docs/superpowers/plans/2026-05-02-cheap-lane-balancer.md
"""
from __future__ import annotations
import json
import os
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from core.services.egress_routing import resolve_egress


@dataclass(frozen=True)
class BalancerSlot:
    """Immutable identity of a (provider, model) lane."""
    provider: str
    model: str
    auth_profile: str
    base_url: str
    rpm_limit: Optional[int]
    daily_limit: Optional[int]
    is_public_proxy: bool
    egress: str = "home"

    @property
    def slot_id(self) -> str:
        return f"{self.provider}::{self.model}::{self.auth_profile or 'default'}"


@dataclass
class SlotState:
    """Per-slot mutable runtime state. Persisted to JSON (timestamps deque is in-memory only)."""
    slot_id: str
    # RPM tracking — in-memory only; restart resets (acceptable, sub-minute window)
    recent_call_timestamps: deque = field(default_factory=lambda: deque(maxlen=200))
    # Daily quota — reactive (only learned from 429 responses)
    daily_use_count: int = 0
    daily_window_start: str = ""  # ISO date "YYYY-MM-DD"
    # Cooldown
    cooldown_until: Optional[float] = None
    cooldown_reason: str = ""
    # Circuit breaker
    consecutive_failures: int = 0
    last_failure_at: Optional[float] = None
    breaker_level: int = 0  # 0=normal, 1=5min, 2=15min, 3=1h
    # Manual override
    manually_disabled: bool = False
    # Telemetry
    total_calls: int = 0
    total_failures: int = 0
    last_success_at: Optional[float] = None
    # Adaptive quota learning (Task 12) — behind cheap_pool_adaptive_quota_enabled.
    # Learned real daily ceiling; only trusted after ≥2 corroborating genuine
    # daily-quota 429s, floored at a fraction of the config limit. Reset daily.
    daily_observed: Optional[int] = None
    last_429_at: Optional[float] = None
    quota_429_count: int = 0  # corroboration counter within the current day
    # Task 14: anti-jag — set True after ≥3 genuine daily-quota 429s in the
    # current day → weight 0 (skip) until the daily reset. Behind the same flag.
    stale_until_daily_reset: bool = False


# ---------------------------------------------------------------------------
# Pool construction
# ---------------------------------------------------------------------------


_EXCLUDED_PROVIDERS = frozenset({"ollama", "openai-codex", "codex-cli"})
_PUBLIC_PROXIES = frozenset({"ollamafreeapi", "arko", "opencode"})


def _provider_router_path() -> Path:
    return Path(
        os.environ.get("JARVIS_CONFIG_DIR")
        or Path.home() / ".jarvis-v2" / "config"
    ) / "provider_router.json"


def _router_enabled_models() -> list[dict]:
    """Return list of dicts {provider, model, enabled, auth_profile, lane}
    from provider_router.json with auth_profile resolved from providers[].

    Returns empty list if file missing or malformed (best-effort).
    """
    p = _provider_router_path()
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    # Index providers[] by name for auth_profile lookup
    provider_entries = {
        str(item.get("provider") or "").strip(): item
        for item in (data.get("providers") or [])
        if bool(item.get("enabled", True))
    }
    out: list[dict] = []
    for entry in data.get("models") or []:
        provider = str(entry.get("provider") or "").strip()
        # Inherit auth_profile from providers[] if missing on the model entry
        if "auth_profile" not in entry or not entry.get("auth_profile"):
            pe = provider_entries.get(provider, {})
            entry = {**entry, "auth_profile": pe.get("auth_profile") or ""}
        out.append(entry)
    return out


def _credentials_ready(provider: str, auth_profile: str) -> bool:
    """Check if provider has working credentials. Wraps existing helper."""
    try:
        from core.services.cheap_provider_runtime import provider_auth_ready
        return bool(provider_auth_ready(provider=provider, auth_profile=auth_profile or "default"))
    except Exception:
        return False


def _provider_metadata(provider: str) -> dict:
    """Lookup provider's static config (rpm_limit, daily_limit, base_url, etc.)."""
    try:
        from core.services.cheap_provider_runtime import provider_runtime_defaults
        return provider_runtime_defaults(provider) or {}
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------


from datetime import datetime, timezone


def _state_path() -> Path:
    return Path(
        os.environ.get("JARVIS_STATE_ROOT")
        or Path.home() / ".jarvis-v2" / "state"
    ) / "cheap_balancer_state.json"


def _state_to_dict(state: SlotState) -> dict:
    """Serialize SlotState to JSON-safe dict (skips deque)."""
    return {
        "slot_id": state.slot_id,
        "daily_use_count": state.daily_use_count,
        "daily_window_start": state.daily_window_start,
        "cooldown_until": state.cooldown_until,
        "cooldown_reason": state.cooldown_reason,
        "consecutive_failures": state.consecutive_failures,
        "last_failure_at": state.last_failure_at,
        "breaker_level": state.breaker_level,
        "manually_disabled": state.manually_disabled,
        "total_calls": state.total_calls,
        "total_failures": state.total_failures,
        "last_success_at": state.last_success_at,
        "daily_observed": state.daily_observed,
        "last_429_at": state.last_429_at,
        "quota_429_count": state.quota_429_count,
        "stale_until_daily_reset": state.stale_until_daily_reset,
    }


def _state_from_dict(d: dict) -> SlotState:
    return SlotState(
        slot_id=str(d.get("slot_id") or ""),
        daily_use_count=int(d.get("daily_use_count") or 0),
        daily_window_start=str(d.get("daily_window_start") or ""),
        cooldown_until=d.get("cooldown_until"),
        cooldown_reason=str(d.get("cooldown_reason") or ""),
        consecutive_failures=int(d.get("consecutive_failures") or 0),
        last_failure_at=d.get("last_failure_at"),
        breaker_level=int(d.get("breaker_level") or 0),
        manually_disabled=bool(d.get("manually_disabled", False)),
        total_calls=int(d.get("total_calls") or 0),
        total_failures=int(d.get("total_failures") or 0),
        last_success_at=d.get("last_success_at"),
        daily_observed=(int(d["daily_observed"]) if d.get("daily_observed") is not None else None),
        last_429_at=d.get("last_429_at"),
        quota_429_count=int(d.get("quota_429_count") or 0),
        stale_until_daily_reset=bool(d.get("stale_until_daily_reset", False)),
    )


def _load_state() -> dict[str, SlotState]:
    """Load all slot-states from disk. Returns empty dict on missing/corrupt file."""
    p = _state_path()
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out: dict[str, SlotState] = {}
    for slot_id, payload in (data.get("slots") or {}).items():
        try:
            out[slot_id] = _state_from_dict({**payload, "slot_id": slot_id})
        except Exception:
            continue
    return out


def _save_state(states: dict[str, SlotState]) -> None:
    """Atomic write to state file."""
    p = _state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "slots": {sid: _state_to_dict(st) for sid, st in states.items()},
    }
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(p)


# Debounce: at most 1 save per N seconds
_LAST_SAVE_AT: float = 0.0
_SAVE_DEBOUNCE_SECONDS = 5.0


def _save_state_debounced(states: dict[str, SlotState]) -> None:
    global _LAST_SAVE_AT
    import time
    now = time.time()
    if now - _LAST_SAVE_AT < _SAVE_DEBOUNCE_SECONDS:
        return
    _save_state(states)
    _LAST_SAVE_AT = now


def _ensure_state(states: dict[str, SlotState], slot_id: str) -> SlotState:
    """Get-or-create slot state. Mutates `states` in place."""
    if slot_id not in states:
        states[slot_id] = SlotState(slot_id=slot_id)
    return states[slot_id]


# ---------------------------------------------------------------------------
# Selection algorithm — weighted random by headroom × health × proxy_boost
# ---------------------------------------------------------------------------


import random


_PROXY_BOOST = 1.5
_BREAKER_HEALTH = {0: 1.0, 1: 0.5, 2: 0.2, 3: 0.05}


def _today_iso(now: float | None = None) -> str:
    """Returns UTC date string. Override hookable via module-level _datetime_for_today."""
    dt_mod = globals().get("_datetime_for_today", datetime)
    return dt_mod.now(timezone.utc).strftime("%Y-%m-%d")


def _count_recent_calls(timestamps, now: float, window_seconds: int) -> int:
    """Count timestamps falling within [now - window, now]."""
    threshold = now - window_seconds
    return sum(1 for t in timestamps if t >= threshold)


def _daily_used_from_db(provider: str, auth_profile: str = "") -> int:
    """Task 4 / Fund 5: daglig brug fra SQLite cheap_provider_invocations (samme kilde
    som selection). Self-safe → 0 ved fejl (headroom bliver fuld, aldrig falsk-blokerende).

    auth_profile="" tæller alle profiler (bagudkompatibelt); en konkret profil
    tæller kun invocations for netop den (provider, auth_profile)-kombination."""
    try:
        from datetime import datetime, timedelta, UTC
        from core.runtime.db_cheap_provider import count_cheap_provider_invocations
        since = (datetime.now(UTC) - timedelta(hours=24)).isoformat()
        return int(count_cheap_provider_invocations(
            provider=provider, lane="cheap", since=since,
            auth_profile=auth_profile) or 0)
    except Exception:
        return 0


def _daily_headroom_for(slot: BalancerSlot, state: "SlotState | None" = None) -> float:
    """Daily headroom fra SQLite frem for balancerens private JSON daily_use_count.

    Task 13: når den lærte loft (state.daily_observed) er kendt OG flaget er ON,
    bruges min(config daily_limit, daily_observed) som effektivt loft → en slot på/over
    sit lærte loft får headroom 0.0 (→ weight 0 → skippes UDEN try-and-fail round-trip).
    state=None (default) bevarer den rene config-loft-adfærd for andre callers."""
    limit = slot.daily_limit
    if limit and state is not None and _flag_adaptive_quota() and state.daily_observed is not None:
        limit = min(limit, state.daily_observed)
    if not limit:
        return 1.0
    used = _daily_used_from_db(slot.provider, slot.auth_profile)
    return max(0.0, 1.0 - used / limit)


def _observe_central(nerve: str, payload: dict) -> None:
    """Task 5: skriv til Centralens system/<nerve>. Self-safe — observabilitet må
    aldrig bryde routing (mønster fra provider_circuit_breaker._observe_pp)."""
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": nerve, **payload})
    except Exception:
        pass


def _emit_balancer_event(name: str, payload: dict) -> None:
    """Ét sted: emit til eventbus (bagudkompatibelt) + observe fejl-events til Central."""
    try:
        from core.eventbus.events import emit  # type: ignore
        emit(name, payload)
    except Exception:
        pass
    if name in ("cheap_balancer.call_failed", "cheap_balancer.pool_exhausted",
                "cheap_balancer.provider_wide_cooldown"):
        _observe_central("provider_health", {"source": "cheap_lane_balancer",
                                             "event": name, **payload})


def _compute_weight(slot: BalancerSlot, state: SlotState, now: float) -> float:
    """Returns non-negative weight; 0 means slot is ineligible right now.

    weight = headroom_factor × health_multiplier × proxy_boost
    """
    if state.manually_disabled:
        return 0.0
    if state.cooldown_until and now < state.cooldown_until:
        return 0.0
    # Task 14: anti-jag — a slot flagged stale (≥3 daily-quota 429s today) is
    # skipped until the daily reset. Only when the adaptive flag is ON; with the
    # flag OFF the field is ignored entirely (byte-identical to before).
    if _flag_adaptive_quota() and state.stale_until_daily_reset:
        return 0.0

    base = 1.0
    if slot.rpm_limit:
        rpm_used = _count_recent_calls(state.recent_call_timestamps, now, 60)
        rpm_headroom = max(0.0, 1.0 - rpm_used / slot.rpm_limit)
        base *= rpm_headroom
    if slot.daily_limit:
        # Fund 5: daily headroom fra SQLite (én sandhed), ikke privat JSON daily_use_count.
        # Task 13: giv state med → predictive skip mod lært loft (min(config, daily_observed)).
        base *= _daily_headroom_for(slot, state)

    health = _BREAKER_HEALTH.get(state.breaker_level, 0.05)
    preference = _PROXY_BOOST if slot.is_public_proxy else 1.0

    # Pålideligheds-læring (15. jul, Bjørn: "læg de mest fejlende længere ned, fjern dem
    # ikke — det er hele meningen med loaderen"). En slot der fejler intermitterende
    # (breaker'en trigger aldrig nok, consec nulstilles) blev ved med at blive valgt.
    # Nu de-vægtes den efter observeret fejl-rate: reliability = 1 - fejl%, gulvet ved
    # _RELIABILITY_FLOOR så den ALDRIG rammer 0 (bliver stadig prøvet lejlighedsvis →
    # kan komme igen når den begynder at svare). Kun efter nok data (min-sample), så
    # nye/lav-volumen-slots ikke straffes på støj.
    reliability = 1.0
    if state.total_calls >= _MIN_RELIABILITY_SAMPLES:
        fail_rate = min(1.0, state.total_failures / max(1, state.total_calls))
        reliability = max(_RELIABILITY_FLOOR, 1.0 - fail_rate)

    return max(0.0, base * health * preference * reliability)


def _slot_status(slot: BalancerSlot, state: SlotState, now: float) -> str:
    """Single derived status string for a slot, most-severe-wins.

    Severity order (high→low): disabled > cooldown > stale > recovering > healthy.
    - "disabled":   manually_disabled
    - "cooldown":   cooldown_until is in the future (an OPEN breaker also shows
                    here — _register_failure sets cooldown_until alongside the
                    breaker escalation, so an actively-blocking breaker IS a
                    cooldown by this ordering).
    - "stale":      stale_until_daily_reset (anti-jag, ≥3 daily-quota 429s today)
    - "recovering": breaker_level > 0 but the cooldown has ALREADY EXPIRED — the
                    slot is eligible for a trial call again (half-open); the
                    breaker_level only resets to 0 on the next SUCCESS. This is
                    NOT an active breaker — showing it as "breaker" made stale,
                    long-expired trips read as live outages in Mission Control
                    (a dead provider that's simply never re-picked stays flagged
                    forever). It's de-weighted via _BREAKER_HEALTH, not blocked.
    - "healthy":    none of the above
    """
    if state.manually_disabled:
        return "disabled"
    if state.cooldown_until and now < state.cooldown_until:
        return "cooldown"
    if state.stale_until_daily_reset:
        return "stale"
    if state.breaker_level > 0:
        return "recovering"
    return "healthy"


# ---------------------------------------------------------------------------
# Failure / success handling — circuit breaker
# ---------------------------------------------------------------------------


_BREAKER_COOLDOWN_SECONDS = {0: 0, 1: 300, 2: 900, 3: 3600}  # 5min/15min/1h
_CONSECUTIVE_FAILURE_THRESHOLD = 3
_DEFAULT_429_COOLDOWN_SECONDS = 3600
# Pålideligheds-vægtning: kræv ≥ dette antal kald før fejl-rate straffer vægten
# (ellers straffes en ny slot på 1-2 uheldige kald); gulv så de-vægtede slots aldrig
# rammer 0 og kan komme igen.
_MIN_RELIABILITY_SAMPLES = 20
_RELIABILITY_FLOOR = 0.05

# Task 12: adaptive daily-quota learning. Learned ceiling is never allowed below
# this fraction of the known config limit, so a single noisy 429 can't cripple a
# slot to a near-zero ceiling.
_DAILY_FLOOR_FRACTION = 0.5


def _flag_adaptive_quota() -> bool:
    """Learn real daily ceilings from genuine daily-quota 429s. Default OFF.

    When False, _register_failure's adaptive-quota learning is skipped entirely
    and the breaker/cooldown behavior is byte-identical to before Task 12.
    """
    try:
        from core.runtime.db_core import get_runtime_state_bool
        return get_runtime_state_bool("cheap_pool_adaptive_quota_enabled", False)
    except Exception:
        return False


def _maybe_daily_reset(state: SlotState, now: float) -> None:
    """Reset per-day adaptive-quota learning at the UTC day boundary.

    Only touches the learning fields (and stamps daily_window_start with the
    current day). Called exclusively from the flag-gated path so that with the
    flag OFF no state field is mutated relative to pre-Task-12 behavior.
    """
    today = _today_iso(now)
    if state.daily_window_start != today:
        state.daily_window_start = today
        state.daily_observed = None
        state.quota_429_count = 0
        state.stale_until_daily_reset = False  # Task 14: re-learn next day


def _register_failure(
    state: SlotState,
    error_kind: str,
    *,
    retry_after_s: int = 0,
    now: float,
    observed_used: Optional[int] = None,
    config_daily: Optional[int] = None,
) -> None:
    """Update state after a failed call.

    429 with retry-after → use header verbatim, don't escalate breaker.
    429 without retry-after → 1h default cooldown.
    Other errors → escalate breaker after 3 consecutive failures.

    Adaptive daily-quota learning (Task 12) runs only when
    _flag_adaptive_quota() is True; otherwise this function is byte-identical to
    its pre-Task-12 behavior. It learns state.daily_observed ONLY from genuine
    daily-quota-exhausted 429s (error_kind mentions both "quota" and "daily" and
    carries NO retry-after — a retry-after means rate/transient, not exhaustion),
    requires ≥2 corroborating events, and floors the learned value at
    _DAILY_FLOOR_FRACTION of config_daily.
    """
    state.consecutive_failures += 1
    state.last_failure_at = now
    state.total_failures += 1
    state.total_calls += 1   # FIX 15. jul: tæl ALLE forsøg (før: kun succes → fejl% kunne >100%)
    state.cooldown_reason = error_kind

    if _flag_adaptive_quota():
        _maybe_daily_reset(state, now)
        kind = (error_kind or "").lower()
        # Genuine daily exhaustion ONLY: mentions quota AND daily, and NO
        # retry-after present (retry_after_s in (0, None)). A present retry-after
        # → transient/rate limit → NOT a daily exhaustion → no learning.
        is_daily_quota = ("quota" in kind and "daily" in kind and not retry_after_s)
        if is_daily_quota:
            state.quota_429_count += 1
            state.last_429_at = now
            if state.quota_429_count >= 2:  # corroboration required
                floor = int((config_daily or 0) * _DAILY_FLOOR_FRACTION)
                candidate = observed_used if observed_used is not None else (config_daily or 0)
                current = state.daily_observed if state.daily_observed is not None else candidate
                _was_unlearned = state.daily_observed is None
                state.daily_observed = max(floor, min(current, candidate))
                if _was_unlearned:  # Task 15: observe first-time learn (None -> value)
                    _observe_central("cheap_pool", {"event": "quota_learned",
                                                    "slot_id": state.slot_id,
                                                    "daily_observed": state.daily_observed})
            if state.quota_429_count >= 3:  # Task 14: anti-jag → mark stale
                state.stale_until_daily_reset = True
        # Fall through: a quota 429 is still a failure → keep escalating below.

    if "429" in error_kind:
        if retry_after_s > 0:
            state.cooldown_until = now + retry_after_s
        else:
            state.cooldown_until = now + _DEFAULT_429_COOLDOWN_SECONDS
        return

    if state.consecutive_failures >= _CONSECUTIVE_FAILURE_THRESHOLD:
        state.breaker_level = min(state.breaker_level + 1, 3)
    cooldown = _BREAKER_COOLDOWN_SECONDS.get(state.breaker_level, 0)
    if cooldown > 0:
        state.cooldown_until = now + cooldown


def _register_success(state: SlotState, now: float) -> None:
    """Update state after a successful call."""
    state.recent_call_timestamps.append(now)
    state.total_calls += 1
    state.last_success_at = now
    state.consecutive_failures = 0
    state.cooldown_until = None
    if state.breaker_level > 0:
        state.breaker_level = max(0, state.breaker_level - 1)


# Provider-wide cooldown when DNS / connection-level failure detected.
# DNS issues affect ALL slots from the same provider, so circuit-break the
# whole provider rather than burn retries on every slot.
_PROVIDER_WIDE_DNS_COOLDOWN_SECONDS = 600  # 10 min


def _is_dns_or_connection_error(error_kind: str, exc: Exception | None = None) -> bool:
    """True if error indicates network-level (provider-wide) issue, not slot-specific."""
    kind = (error_kind or "").lower()
    if "connection-error" in kind:
        return True
    if "dns" in kind or "gaierror" in kind or "getaddrinfo" in kind:
        return True
    if "name resolution" in kind or "nodename nor servname" in kind:
        return True
    if exc is not None:
        msg = str(exc).lower()
        if any(s in msg for s in ("getaddrinfo", "name or service not known",
                                    "nodename nor servname", "name resolution",
                                    "temporary failure in name resolution")):
            return True
    return False


def _register_provider_wide_failure(
    states: dict[str, SlotState],
    pool: list[BalancerSlot],
    provider: str,
    now: float,
    *,
    reason: str,
    cooldown_s: int = _PROVIDER_WIDE_DNS_COOLDOWN_SECONDS,
) -> int:
    """Apply cooldown to ALL slots from `provider`. Returns number of slots affected.

    Used when a provider-level issue (DNS down, connection refused, etc.) is
    detected — saves us from retrying every slot on a dead provider.
    """
    affected = 0
    for slot in pool:
        if slot.provider != provider:
            continue
        s = _ensure_state(states, slot.slot_id)
        # Don't override an already-longer cooldown
        if s.cooldown_until is None or s.cooldown_until < now + cooldown_s:
            s.cooldown_until = now + cooldown_s
            s.cooldown_reason = f"provider-wide:{reason}"
        affected += 1
    if affected > 0:
        logger.warning(
            "cheap_balancer: provider-wide cooldown applied to %s "
            "(%s slots, %ss) reason=%s",
            provider, affected, cooldown_s, reason,
        )
        try:
            from core.eventbus.events import emit  # type: ignore
            _emit_balancer_event("cheap_balancer.provider_wide_cooldown", {
                "provider": provider,
                "slots_affected": affected,
                "cooldown_seconds": cooldown_s,
                "reason": reason,
            })
        except Exception:
            pass
    return affected


def _select_slot(
    states: dict[str, SlotState],
    pool: list[BalancerSlot],
    now: float,
) -> BalancerSlot | None:
    """Pick a slot via weighted-random; returns None if all blocked."""
    eligible: list[tuple[BalancerSlot, float]] = []
    for slot in pool:
        state = _ensure_state(states, slot.slot_id)
        w = _compute_weight(slot, state, now)
        if w > 0:
            eligible.append((slot, w))
    if not eligible:
        return None

    total = sum(w for _, w in eligible)
    if total <= 0:
        return None
    pick = random.random() * total
    cumulative = 0.0
    for slot, w in eligible:
        cumulative += w
        if pick < cumulative:
            return slot
    return eligible[-1][0]


# ---------------------------------------------------------------------------
# call_balanced — public entry point with retry-on-failure
# ---------------------------------------------------------------------------


import logging
import time as _time

logger = logging.getLogger("cheap_lane_balancer")


# ---------------------------------------------------------------------------
# central_route hook (spec §5.5) — mirror af selection-siden.
# Foren de to gaflede cheap-subsystemer: når central_route_live er ON henter
# BÅDE balancer og selection kandidat-rangeringen fra det Central-ejede
# beslutnings-punkt (central_route). Byte-identisk med gammel sti når begge
# flag er OFF (default). Aldrig-tør bevaret: routes der giver floor/ikke-mapbar
# kandidat falder tilbage til den vægtede-tilfældige pick (og til sidst floor).
# ---------------------------------------------------------------------------


def _central_route_shadow() -> bool:
    """Kør central_route-sammenligning (default OFF → nul overhead)."""
    try:
        from core.runtime.db_core import get_runtime_state_bool
        return get_runtime_state_bool("central_route_shadow", False)
    except Exception:
        return False


def _central_route_live() -> bool:
    """Brug central_route's pick i stedet for den gamle sti (default OFF)."""
    try:
        from core.runtime.db_core import get_runtime_state_bool
        return get_runtime_state_bool("central_route_live", False)
    except Exception:
        return False


def _flag_multiprofile() -> bool:
    """Byg én slot pr. (provider, klar auth-profil) i stedet for kun entry-profilen.

    Default OFF → uændret adfærd (én slot pr. model med entry'ens auth_profile).
    """
    try:
        from core.runtime.db_core import get_runtime_state_bool
        return get_runtime_state_bool("cheap_pool_multiprofile_enabled", False)
    except Exception:
        return False


def _record_route_divergence(old: dict, new: dict) -> None:
    """Shadow-sammenligning: log/observe når central_route ville vælge noget andet
    end balancerens vægtede-tilfældige pick. Data til at beslutte hvornår vi flipper
    til live. Mirror af selection._record_route_divergence."""
    try:
        old_p = (str(old.get("provider") or ""), str(old.get("model") or ""))
        new_p = (str(new.get("provider") or ""), str(new.get("model") or ""))
        if old_p != new_p:
            logger.info("central_route shadow-divergens (balancer): gammel=%s ny=%s",
                        old_p, new_p)
            _observe_central("route_shadow", {"source": "cheap_lane_balancer",
                                              "old_provider": old_p[0],
                                              "new_provider": new_p[0]})
    except Exception:
        pass


def _central_route_slot(
    eligible_pool: list[BalancerSlot],
    tried_slot_ids: set[str],
) -> BalancerSlot | None:
    """Spørg central_route om lane='cheap'-pick og map til en EGNET (untried) slot i
    poolen. None hvis routen giver floor eller (provider, model) ikke findes som en
    kandidat her — så bevarer vi aldrig-tør (kalderen falder til vægtet-random → floor)."""
    try:
        from core.services import central_route
        r = central_route.route(lane="cheap")
        if r.get("is_floor"):
            return None
        p, m = str(r.get("provider") or ""), str(r.get("model") or "")
        for slot in eligible_pool:
            if slot.provider == p and slot.model == m and slot.slot_id not in tried_slot_ids:
                return slot
    except Exception:
        logger.debug("central_route: balancer-slot-map fejlede", exc_info=True)
    return None


def _maybe_central_route_slot(
    weighted_slot: BalancerSlot | None,
    eligible_pool: list[BalancerSlot],
    tried_slot_ids: set[str],
) -> BalancerSlot | None:
    """Hook før slot bruges: shadow-compare (OFF → no-op) + live-apply. Aldrig-tør
    bevaret — live-pick bruges kun når den mapper til en egnet slot, ellers beholdes
    den vægtede-tilfældige pick."""
    if not (_central_route_shadow() or _central_route_live()):
        return weighted_slot
    routed = _central_route_slot(eligible_pool, tried_slot_ids)
    if _central_route_shadow() and weighted_slot is not None:
        _record_route_divergence(
            {"provider": weighted_slot.provider, "model": weighted_slot.model},
            ({"provider": routed.provider, "model": routed.model} if routed else {}),
        )
    if _central_route_live() and routed is not None:
        return routed
    return weighted_slot


def _call_provider_chat(
    *,
    provider: str,
    model: str,
    auth_profile: str,
    base_url: str,
    message: str,
) -> dict:
    """Wrapper around cheap_provider_runtime._execute_provider_chat.

    Override in tests via monkeypatch.
    """
    from core.services.cheap_provider_runtime import _execute_provider_chat
    return _execute_provider_chat(
        provider=provider, model=model,
        auth_profile=auth_profile, base_url=base_url,
        message=message,
    )


# Recent calls ring buffer (in-memory, 75 max)
_RECENT_CALLS: list[dict] = []
_RECENT_CALLS_MAX = 75


def _append_recent_call(
    slot_id: str, daemon: str, status: str, latency_ms: int,
    *, error: str = "",
) -> None:
    entry = {
        "at": datetime.now(timezone.utc).isoformat(),
        "slot_id": slot_id,
        "daemon": daemon,
        "status": status,
        "latency_ms": latency_ms,
    }
    if error:
        entry["error"] = error
    _RECENT_CALLS.append(entry)
    while len(_RECENT_CALLS) > _RECENT_CALLS_MAX:
        _RECENT_CALLS.pop(0)


def recent_calls() -> list[dict]:
    """Returns ring-buffer of last 75 calls (newest first)."""
    return list(reversed(_RECENT_CALLS))


def call_balanced(
    *,
    prompt: str,
    daemon_name: str = "",
    max_retries: int = 3,
) -> dict:
    """Pick a slot via weighted-random; execute; on failure retry next slot.

    Returns: {status, text, provider, model, attempts, ...}
    Raises RuntimeError when all eligible slots exhausted.

    FIX 3 (2026-07-15) — hvorfor 'cheap-balanced'-lanen IKKE er foldet ind i 'cheap':
    Den er IKKE redundant. Denne balancer bærer sin egen distinkte adfærd:
      · vægtet-tilfældigt slot-valg pr. (provider, model) med per-slot succes/fejl-state,
      · retry på tværs af slots + garanteret bund (attempt_floor),
      · credit-assignment-registrering pr. pick.
    central_route-forening (SPEC 7) findes allerede som _maybe_central_route_slot-hook'et,
    men er DEFAULT OFF (central_route_live=False) — migrationen er stadig shadow-først og
    endnu ikke flippet på grundlag af divergens-data. At folde nu ville (a) miste balancerens
    kvote-spredning på tværs af providers og (b) foregribe den igangværende migration. Den
    separate lane-label er bevidst: den adskiller balancer-stien (daemon load-spredning) fra
    selection-stien ('cheap'). Forening sker naturligt når central_route_live flippes.
    """
    from core.services.cheap_provider_runtime import CheapProviderError

    states = _load_state()
    pool = build_slot_pool()
    if not pool:
        # Fund 4: tom pool → garanteret bund, aldrig rejse.
        from core.services.cheap_lane_floor import attempt_floor
        fr = attempt_floor(message=prompt, lane="cheap", reason="empty-pool")
        fr.setdefault("attempts", 0)
        fr.setdefault("output_tokens", int(fr.get("output_tokens") or 0))
        return fr

    tried_slot_ids: set[str] = set()
    last_error: Exception | None = None
    attempts = 0

    while attempts < max_retries:
        eligible_pool = [s for s in pool if s.slot_id not in tried_slot_ids]
        if not eligible_pool:
            break

        now = _time.time()
        slot = _select_slot(states, eligible_pool, now)
        # central_route hook (§5.5): shadow-compare + live-apply. OFF → no-op.
        # Aldrig-tør: routen kan kun bytte til en anden EGNET slot, aldrig fjerne den.
        slot = _maybe_central_route_slot(slot, eligible_pool, tried_slot_ids)
        if slot is None:
            break

        tried_slot_ids.add(slot.slot_id)
        attempts += 1
        state = _ensure_state(states, slot.slot_id)
        call_started = _time.time()

        # ── Lag 1: record provider_routing choice ──────────────────────
        _choice_id: str | None = None
        try:
            from core.runtime.db_credit_assignment import record_choice as _rc
            _choice_id = _rc(
                kind="provider_routing",
                title=f"Provider for {daemon_name or 'daemon'} (attempt {attempts+1})",
                options=[s.slot_id for s in eligible_pool[:5]],
                decision=slot.slot_id,
                why=f"weight={_compute_weight(slot, state, now):.3f}",
            )
        except Exception:
            _choice_id = None

        try:
            result = _call_provider_chat(
                provider=slot.provider,
                model=slot.model,
                auth_profile=slot.auth_profile,
                base_url=slot.base_url,
                message=prompt,
            )
            _register_success(state, now=_time.time())
            _save_state_debounced(states)
            latency_ms = int((_time.time() - call_started) * 1000)

            # ── Lag 1: score provider_routing outcome (sync) ────────
            if _choice_id:
                try:
                    from core.runtime.db_credit_assignment import score_provider_outcome as _spo
                    _spo(_choice_id, {
                        "status": "ok",
                        "latency_ms": latency_ms,
                        "cost_per_token": 0.0,  # TODO: extract from result
                        "fallback_used": attempts > 1,
                    })
                except Exception:
                    pass

            try:
                from core.eventbus.events import emit  # type: ignore
                _emit_balancer_event("cheap_balancer.call_succeeded", {
                    "slot_id": slot.slot_id,
                    "daemon": daemon_name,
                    "latency_ms": latency_ms,
                    "attempt": attempts,
                })
            except Exception:
                pass
            _append_recent_call(slot.slot_id, daemon_name, "ok", latency_ms)
            # ── WS2: log costs-række (balanceren var før usynlig for ledgeren) ──
            # record_cost egress-observer selv + beregner cost_usd fra pris-tabel
            # når provider ikke returnerer pris (DeepSeek). Aldrig-vælt daemon-kald.
            try:
                from core.costing.ledger import record_cost
                record_cost(
                    lane="cheap-balanced", provider=slot.provider, model=slot.model,
                    input_tokens=int(result.get("input_tokens") or 0),
                    output_tokens=int(result.get("output_tokens") or 0),
                    cost_usd=float(result.get("cost_usd") or 0.0),
                    cache_hit_tokens=int(result.get("cache_hit_tokens") or result.get("prompt_cache_hit_tokens") or 0),
                    cache_miss_tokens=int(result.get("cache_miss_tokens") or result.get("prompt_cache_miss_tokens") or 0),
                )
            except Exception:
                pass
            return {
                "status": "ok",
                "lane": "cheap-balanced",
                "provider": slot.provider,
                "model": slot.model,
                "attempts": attempts,
                "text": str(result.get("text") or ""),
                "output_tokens": result.get("output_tokens"),
            }
        except CheapProviderError as exc:
            last_error = exc
            _register_failure(
                state,
                exc.code,
                retry_after_s=getattr(exc, "retry_after_seconds", 0),
                now=_time.time(),
            )
            # ── Lag 1: score failed provider_routing ─────────────────
            if _choice_id:
                try:
                    from core.runtime.db_credit_assignment import score_provider_outcome as _spo
                    _spo(_choice_id, {
                        "status": "error",
                        "latency_ms": int((_time.time() - call_started) * 1000),
                        "cost_per_token": 0.0,
                        "fallback_used": False,
                    })
                except Exception:
                    pass
            # If this is a DNS / connection-level error, all slots from the
            # same provider are affected — apply provider-wide cooldown so
            # we don't burn retries on the other dead slots.
            if _is_dns_or_connection_error(exc.code, exc):
                _register_provider_wide_failure(
                    states, pool, slot.provider, _time.time(),
                    reason=exc.code,
                )
                # Add all that provider's slot_ids to tried set so next
                # iteration's eligible_pool excludes them too.
                for s in pool:
                    if s.provider == slot.provider:
                        tried_slot_ids.add(s.slot_id)
            latency_ms = int((_time.time() - call_started) * 1000)
            _append_recent_call(slot.slot_id, daemon_name, "error", latency_ms,
                                error=exc.code)
            try:
                from core.eventbus.events import emit  # type: ignore
                _emit_balancer_event("cheap_balancer.call_failed", {
                    "slot_id": slot.slot_id,
                    "daemon": daemon_name,
                    "error_kind": exc.code,
                    "retry_after": getattr(exc, "retry_after_seconds", 0),
                })
            except Exception:
                pass
        except Exception as exc:
            last_error = exc
            _register_failure(state, "unknown", retry_after_s=0, now=_time.time())
            # ── Lag 1: score failed provider_routing ─────────────────
            if _choice_id:
                try:
                    from core.runtime.db_credit_assignment import score_provider_outcome as _spo
                    _spo(_choice_id, {
                        "status": "error",
                        "latency_ms": int((_time.time() - call_started) * 1000),
                        "cost_per_token": 0.0,
                        "fallback_used": False,
                    })
                except Exception:
                    pass
            # Same DNS/connection check for non-CheapProviderError exceptions
            if _is_dns_or_connection_error("", exc):
                _register_provider_wide_failure(
                    states, pool, slot.provider, _time.time(),
                    reason=f"unknown:{type(exc).__name__}",
                )
                for s in pool:
                    if s.provider == slot.provider:
                        tried_slot_ids.add(s.slot_id)
            latency_ms = int((_time.time() - call_started) * 1000)
            _append_recent_call(slot.slot_id, daemon_name, "error", latency_ms,
                                error=type(exc).__name__)

    # Pool-exhaustion is rare + important enough to persist immediately
    # (skip debounce so breaker state survives restart of caller / runtime).
    _save_state(states)
    try:
        from core.eventbus.events import emit  # type: ignore
        _emit_balancer_event("cheap_balancer.pool_exhausted", {
            "tried_slots": list(tried_slot_ids),
            "daemon": daemon_name,
            "last_error": str(last_error) if last_error else None,
        })
    except Exception:
        pass
    # Fund 4: aldrig rejse ved udmattelse — fald til garanteret bund.
    from core.services.cheap_lane_floor import attempt_floor
    fr = attempt_floor(message=prompt, lane="cheap", reason="balancer-exhausted")
    fr.setdefault("attempts", len(tried_slot_ids))
    fr.setdefault("output_tokens", int(fr.get("output_tokens") or 0))
    return fr


def build_slot_pool() -> list[BalancerSlot]:
    """Build daemon-eligible slot pool from provider_router × CHEAP_PROVIDER_DEFAULTS.

    Excludes local ollama (visible lane), openai-codex (paid, expensive),
    codex-cli (paid, expensive). Skips models marked enabled=False or
    providers without working credentials.
    """
    slots: list[BalancerSlot] = []
    for entry in _router_enabled_models():
        if not entry.get("enabled"):
            continue
        # Filter by lane: only "cheap" or unset (legacy) — skip "local",
        # "coding", or other non-cheap lanes since those are reserved for
        # other purposes (visible/coding lanes).
        lane = str(entry.get("lane") or "").strip()
        if lane and lane != "cheap":
            continue
        provider = str(entry.get("provider") or "").strip()
        model = str(entry.get("model") or "").strip()
        auth_profile = str(entry.get("auth_profile") or "").strip()
        if not provider or not model:
            continue
        if provider in _EXCLUDED_PROVIDERS:
            continue
        # Routable + cost-filter: betalte providers (deepseek routable=False; copilot-
        # premium cost_class=paid) holdes UDE af balanceren/inderlivet — de må ALDRIG
        # brænde premium-kvote. Kun gratis. Betalt kun via central_route(allow_paid).
        from core.services.cheap_provider_runtime_adapters import (
            is_routable_provider, provider_cost_class)
        if not is_routable_provider(provider) or provider_cost_class(provider) == "paid":
            continue
        meta = _provider_metadata(provider)
        # Multiprofil (flag ON): én slot pr. klar auth-profil for provideren.
        # Flag OFF (default): uændret — kun entry'ens egen auth_profile.
        if _flag_multiprofile():
            from core.services.auth_profile_scan import ready_profiles_for
            for prof in ready_profiles_for(provider):
                if not _credentials_ready(provider, prof):
                    continue
                sid = f"{provider}::{model}::{prof or 'default'}"
                if any(s.slot_id == sid for s in slots):
                    continue
                slots.append(BalancerSlot(
                    provider=provider,
                    model=model,
                    auth_profile=prof,
                    base_url=str(meta.get("base_url") or ""),
                    rpm_limit=meta.get("rpm_limit"),
                    daily_limit=meta.get("daily_limit"),
                    is_public_proxy=provider in _PUBLIC_PROXIES,
                    egress=resolve_egress(provider, prof),
                ))
                # Task 15: observe kun NON-default profil-slots (multiprofile-effekt),
                # ikke default — hold det billigt og ikke-spammy.
                if prof and prof != "default":
                    _observe_central("cheap_pool", {"event": "profile_slot_added",
                                                    "provider": provider,
                                                    "auth_profile": prof})
            continue
        # --- OFF-sti: uændret adfærd ---
        if not _credentials_ready(provider, auth_profile):
            continue
        slot = BalancerSlot(
            provider=provider,
            model=model,
            auth_profile=auth_profile,
            base_url=str(meta.get("base_url") or ""),
            rpm_limit=meta.get("rpm_limit"),
            daily_limit=meta.get("daily_limit"),
            is_public_proxy=provider in _PUBLIC_PROXIES,
            egress=resolve_egress(provider, auth_profile),
        )
        slots.append(slot)

    # static_models-injektion (2026-07-14): providers hvis modeller KUN lever i
    # CHEAP_PROVIDER_DEFAULTS.static_models (cerebras/aihubmix/requesty/cline) fik
    # ellers aldrig en slot her — så inderlivet (daemon_llm) kørte på et smallere
    # sæt end agent-lanen. Mirror selection-stien så HELE huset har samme pool.
    from core.services.cheap_provider_runtime_adapters import (
        CHEAP_PROVIDER_DEFAULTS, is_routable_provider, provider_cost_class)
    seen = {s.slot_id for s in slots}
    prov_profiles: dict[str, str] = {}
    try:
        data = json.loads(_provider_router_path().read_text(encoding="utf-8"))
        for pe in data.get("providers", []):
            prov_profiles[str(pe.get("provider") or "")] = str(pe.get("auth_profile") or "")
    except Exception:
        pass
    for provider, cfg in CHEAP_PROVIDER_DEFAULTS.items():
        static_models = cfg.get("static_models") or []
        if (not static_models or provider in _EXCLUDED_PROVIDERS
                or not is_routable_provider(provider)
                or provider_cost_class(provider) == "paid"):  # betalt aldrig i balancer
            continue
        # Multiprofil (flag ON): iterér klare auth-profiler; OFF: kun entry-profilen.
        if _flag_multiprofile():
            from core.services.auth_profile_scan import ready_profiles_for
            static_profiles = ready_profiles_for(provider)
        else:
            static_profiles = [prov_profiles.get(provider) or "default"]
        for auth_profile in static_profiles:
            if not _credentials_ready(provider, auth_profile):
                continue
            for model in static_models:
                sid = f"{provider}::{model}::{auth_profile or 'default'}"
                if sid in seen:
                    continue
                seen.add(sid)
                slots.append(BalancerSlot(
                    provider=provider, model=str(model), auth_profile=auth_profile,
                    base_url=str(cfg.get("base_url") or ""),
                    rpm_limit=cfg.get("rpm_limit"), daily_limit=cfg.get("daily_limit"),
                    is_public_proxy=provider in _PUBLIC_PROXIES,
                    egress=resolve_egress(provider, auth_profile),
                ))
                # Task 15: observe kun NON-default profil-slots (multiprofile-effekt).
                if _flag_multiprofile() and auth_profile and auth_profile != "default":
                    _observe_central("cheap_pool", {"event": "profile_slot_added",
                                                    "provider": provider,
                                                    "auth_profile": auth_profile})
    return slots


# ---------------------------------------------------------------------------
# Manual controls (Mission Control)
# ---------------------------------------------------------------------------


def reset_slot(slot_id: str) -> dict:
    """Clear breaker, cooldown, and consecutive-failure streak for a slot."""
    states = _load_state()
    state = _ensure_state(states, slot_id)
    state.consecutive_failures = 0
    state.breaker_level = 0
    state.cooldown_until = None
    state.cooldown_reason = ""
    _save_state(states)
    return {"status": "ok", "slot_id": slot_id}


def disable_slot(slot_id: str) -> dict:
    """Force a slot's weight to 0 until enable_slot is called."""
    states = _load_state()
    state = _ensure_state(states, slot_id)
    state.manually_disabled = True
    _save_state(states)
    return {"status": "ok", "slot_id": slot_id, "manually_disabled": True}


def enable_slot(slot_id: str) -> dict:
    """Re-enable a manually-disabled slot."""
    states = _load_state()
    state = _ensure_state(states, slot_id)
    state.manually_disabled = False
    _save_state(states)
    return {"status": "ok", "slot_id": slot_id, "manually_disabled": False}


def refresh_pool() -> dict:
    """Re-build the slot pool from provider_router.json. Returns current size."""
    pool = build_slot_pool()
    return {"status": "ok", "pool_size": len(pool)}


# ---------------------------------------------------------------------------
# Snapshot for Mission Control telemetry
# ---------------------------------------------------------------------------


def _is_enabled() -> bool:
    """Check RuntimeSettings.daemon_balancer_enabled. Default True."""
    try:
        from core.runtime.settings import load_settings
        return bool(getattr(load_settings(), "daemon_balancer_enabled", True))
    except Exception:
        return True


def balancer_snapshot() -> dict:
    """Return full state surface for Mission Control telemetry."""
    states = _load_state()
    pool = build_slot_pool()
    now = _time.time()

    eligible = 0
    blocked = 0
    slot_payloads: list[dict] = []
    for slot in pool:
        state = _ensure_state(states, slot.slot_id)
        weight = _compute_weight(slot, state, now)
        if weight > 0:
            eligible += 1
        else:
            blocked += 1

        headroom_pct = 100.0
        if slot.daily_limit and state.daily_window_start == _today_iso(now):
            headroom_pct = max(0.0, 100.0 * (1.0 - state.daily_use_count / slot.daily_limit))

        rpm_used = _count_recent_calls(state.recent_call_timestamps, now, 60)
        status = _slot_status(slot, state, now)
        # success_rate: fraction of successful calls; None when no calls yet
        # (no data to report a rate). Callers treat None as "unknown", not 0/1.
        success_rate = (
            (state.total_calls - state.total_failures) / state.total_calls
            if state.total_calls > 0 else None
        )
        cooldown_until_iso = (
            datetime.fromtimestamp(state.cooldown_until, tz=timezone.utc).isoformat()
            if state.cooldown_until else None
        )
        last_success_iso = (
            datetime.fromtimestamp(state.last_success_at, tz=timezone.utc).isoformat()
            if state.last_success_at else None
        )

        slot_payloads.append({
            "slot_id": slot.slot_id,
            "provider": slot.provider,
            "model": slot.model,
            "auth_profile": slot.auth_profile or "default",
            "egress": slot.egress,
            "status": status,
            "is_public_proxy": slot.is_public_proxy,
            "rpm_limit": slot.rpm_limit,
            "daily_limit": slot.daily_limit,
            # New canonical names (Task A2) + legacy aliases kept for existing consumers.
            "rpm_used": rpm_used,
            "rpm_used_now": rpm_used,
            "daily_used": _daily_used_from_db(slot.provider, slot.auth_profile),
            "daily_used_today": state.daily_use_count,
            "daily_headroom": round(_daily_headroom_for(slot, state), 4),
            "headroom_pct": round(headroom_pct, 2),
            "weight": round(weight, 4),
            "current_weight": round(weight, 4),
            "cooldown_until": cooldown_until_iso,
            "cooldown_reason": state.cooldown_reason,
            "breaker_level": state.breaker_level,
            "consecutive_failures": state.consecutive_failures,
            "manually_disabled": state.manually_disabled,
            "total_calls": state.total_calls,
            "total_failures": state.total_failures,
            "success_rate": success_rate,
            "last_success_at": last_success_iso,
            "daily_observed": state.daily_observed,
            "stale": bool(state.stale_until_daily_reset),
        })

    slot_payloads.sort(key=lambda s: s["weight"] or 0, reverse=True)

    # --- Header aggregate (Task A2) ---
    by_profile: dict[str, int] = {}
    by_egress: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    providers: set[str] = set()
    for s in slot_payloads:
        by_profile[s["auth_profile"]] = by_profile.get(s["auth_profile"], 0) + 1
        by_egress[s["egress"]] = by_egress.get(s["egress"], 0) + 1
        status_counts[s["status"]] = status_counts.get(s["status"], 0) + 1
        providers.add(s["provider"])

    header = {
        "total_slots": len(slot_payloads),
        "healthy": status_counts.get("healthy", 0),
        "cooldown": status_counts.get("cooldown", 0),
        "disabled": status_counts.get("disabled", 0),
        "stale": status_counts.get("stale", 0),
        # "breaker" = ACTIVE circuit-breaker (blocking). An open breaker shows as
        # "cooldown" by _slot_status severity, so this is ~always 0 now and kept
        # only for schema back-compat. "recovering" = breaker tripped earlier but
        # its cooldown has expired (half-open, eligible again) — surfaced
        # separately so stale trips don't read as live outages in Mission Control.
        "breaker": status_counts.get("breaker", 0),
        "recovering": status_counts.get("recovering", 0),
        "by_profile": by_profile,
        "by_egress": by_egress,
        "providers": len(providers),
    }

    return {
        "enabled": _is_enabled(),
        "pool_size": len(pool),
        "eligible_now": eligible,
        "blocked_now": blocked,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "header": header,
        "slots": slot_payloads,
        "recent_calls": recent_calls(),
    }
