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

    @property
    def slot_id(self) -> str:
        return f"{self.provider}::{self.model}"


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
    """Return list of dicts {provider, model, enabled, ...} from provider_router.json.

    Returns empty list if file missing or malformed (best-effort).
    """
    p = _provider_router_path()
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    return list(data.get("models") or [])


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


def _compute_weight(slot: BalancerSlot, state: SlotState, now: float) -> float:
    """Returns non-negative weight; 0 means slot is ineligible right now.

    weight = headroom_factor × health_multiplier × proxy_boost
    """
    if state.manually_disabled:
        return 0.0
    if state.cooldown_until and now < state.cooldown_until:
        return 0.0

    base = 1.0
    if slot.rpm_limit:
        rpm_used = _count_recent_calls(state.recent_call_timestamps, now, 60)
        rpm_headroom = max(0.0, 1.0 - rpm_used / slot.rpm_limit)
        base *= rpm_headroom
    if slot.daily_limit:
        today = _today_iso(now)
        if state.daily_window_start != today:
            state.daily_use_count = 0
            state.daily_window_start = today
        daily_headroom = max(0.0, 1.0 - state.daily_use_count / slot.daily_limit)
        base *= daily_headroom

    health = _BREAKER_HEALTH.get(state.breaker_level, 0.05)
    preference = _PROXY_BOOST if slot.is_public_proxy else 1.0

    return max(0.0, base * health * preference)


# ---------------------------------------------------------------------------
# Failure / success handling — circuit breaker
# ---------------------------------------------------------------------------


_BREAKER_COOLDOWN_SECONDS = {0: 0, 1: 300, 2: 900, 3: 3600}  # 5min/15min/1h
_CONSECUTIVE_FAILURE_THRESHOLD = 3
_DEFAULT_429_COOLDOWN_SECONDS = 3600


def _register_failure(
    state: SlotState,
    error_kind: str,
    *,
    retry_after_s: int = 0,
    now: float,
) -> None:
    """Update state after a failed call.

    429 with retry-after → use header verbatim, don't escalate breaker.
    429 without retry-after → 1h default cooldown.
    Other errors → escalate breaker after 3 consecutive failures.
    """
    state.consecutive_failures += 1
    state.last_failure_at = now
    state.total_failures += 1
    state.cooldown_reason = error_kind

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
    """
    from core.services.cheap_provider_runtime import CheapProviderError

    states = _load_state()
    pool = build_slot_pool()
    if not pool:
        raise RuntimeError("cheap_lane_balancer: empty pool (no eligible slots)")

    tried_slot_ids: set[str] = set()
    last_error: Exception | None = None
    attempts = 0

    while attempts < max_retries:
        eligible_pool = [s for s in pool if s.slot_id not in tried_slot_ids]
        if not eligible_pool:
            break

        now = _time.time()
        slot = _select_slot(states, eligible_pool, now)
        if slot is None:
            break

        tried_slot_ids.add(slot.slot_id)
        attempts += 1
        state = _ensure_state(states, slot.slot_id)
        call_started = _time.time()

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
            try:
                from core.eventbus.events import emit  # type: ignore
                emit("cheap_balancer.call_succeeded", {
                    "slot_id": slot.slot_id,
                    "daemon": daemon_name,
                    "latency_ms": latency_ms,
                    "attempt": attempts,
                })
            except Exception:
                pass
            _append_recent_call(slot.slot_id, daemon_name, "ok", latency_ms)
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
            latency_ms = int((_time.time() - call_started) * 1000)
            _append_recent_call(slot.slot_id, daemon_name, "error", latency_ms,
                                error=exc.code)
            try:
                from core.eventbus.events import emit  # type: ignore
                emit("cheap_balancer.call_failed", {
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
            latency_ms = int((_time.time() - call_started) * 1000)
            _append_recent_call(slot.slot_id, daemon_name, "error", latency_ms,
                                error=type(exc).__name__)

    _save_state_debounced(states)
    try:
        from core.eventbus.events import emit  # type: ignore
        emit("cheap_balancer.pool_exhausted", {
            "tried_slots": list(tried_slot_ids),
            "daemon": daemon_name,
            "last_error": str(last_error) if last_error else None,
        })
    except Exception:
        pass
    raise RuntimeError(
        f"cheap_lane_balancer exhausted {len(tried_slot_ids)} slots; "
        f"last error: {last_error}"
    )


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
        provider = str(entry.get("provider") or "").strip()
        model = str(entry.get("model") or "").strip()
        auth_profile = str(entry.get("auth_profile") or "default").strip()
        if not provider or not model:
            continue
        if provider in _EXCLUDED_PROVIDERS:
            continue
        if not _credentials_ready(provider, auth_profile):
            continue
        meta = _provider_metadata(provider)
        slot = BalancerSlot(
            provider=provider,
            model=model,
            auth_profile=auth_profile,
            base_url=str(meta.get("base_url") or ""),
            rpm_limit=meta.get("rpm_limit"),
            daily_limit=meta.get("daily_limit"),
            is_public_proxy=provider in _PUBLIC_PROXIES,
        )
        slots.append(slot)
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
