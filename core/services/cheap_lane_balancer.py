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
