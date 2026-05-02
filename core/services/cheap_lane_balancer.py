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
