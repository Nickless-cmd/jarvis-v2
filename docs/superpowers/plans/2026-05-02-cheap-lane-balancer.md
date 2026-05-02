# Cheap Lane Balancer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Spread Jarvis' daemon-LLM-traffic across all available cheap-lane provider+model combinations using weighted-random selection, so daemons never get stuck because one provider's quota is drained while others sit idle.

**Architecture:** New `cheap_lane_balancer.py` module that wraps existing `_execute_provider_chat()`. Builds a flat pool of (provider, model) slots from `CHEAP_PROVIDER_DEFAULTS` × `provider_router.json` (excluding local ollama / openai-codex / codex-cli). Per-slot quota tracking and progressive circuit breaker. `daemon_llm.py` routes through balancer when `RuntimeSettings.daemon_balancer_enabled=True`.

**Tech Stack:** Python 3.11+, existing cheap_provider_runtime executor, SQLite-free (state in JSON file), numpy not required (pure stdlib `random`).

**Brainstorm decisions:**
- Scope: daemons only (visible/heartbeat untouched)
- Granularity: flat (provider, model) slots — NOT provider-only
- Selection: weighted random by `headroom × health × proxy_boost(1.5×)`
- Failure: auto-retry on pool (max 3) + progressive circuit breaker (5min/15min/1h)
- Quota: local RPM tracking + reactive 429 for daily/TPD
- Default: `daemon_balancer_enabled=True` (auto-rollout, manual flip-off if regression)
- Mission Control: own tab with slot-grid + 75-call recent-history + manual controls

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `core/services/cheap_lane_balancer.py` | All balancer logic: pool, state, selection, retry, controls |
| Create | `tests/test_cheap_lane_balancer.py` | Unit tests (pool, weights, breaker, retry, persistence) |
| Modify | `core/services/daemon_llm.py:152-163` | 1-block change: route through balancer when enabled |
| Modify | `core/runtime/settings.py` | Add `daemon_balancer_enabled` field + load_settings + to_dict round-trip |
| Modify | `~/.jarvis-v2/config/provider_router.json` | Add 2 new Groq models (runtime config, not source) |
| Create | `apps/api/jarvis_api/routes/cheap_balancer.py` | MC endpoints (GET state + manual controls) |
| Modify | `apps/api/jarvis_api/app.py` | Register cheap_balancer router |
| Create | `apps/ui/src/missioncontrol/CheapBalancerTab.tsx` | MC tab UI |
| Modify | `apps/ui/src/missioncontrol/<router>.tsx` | Add tab to MC navigation |
| Create | `tests/test_cheap_balancer_routes.py` | API endpoint tests |

---

## Conventions

- **Conda env:** All `pytest` calls assume `conda activate ai` is active (per CLAUDE.md memory).
- **State file location:** `~/.jarvis-v2/state/cheap_balancer_state.json` — same root as `jarvis_brain_index.sqlite`. Use `Path.home() / ".jarvis-v2" / "state"` with env override `JARVIS_STATE_ROOT` for tests.
- **Atomic writes:** tmp + rename (same pattern as jarvis_brain).
- **Visibility-niveau N/A:** This balancer is for daemons only; all calls are public-safe-eligible since they go to free or paid third-party providers.
- **Eventbus emits:** Use `from core.eventbus.events import emit` (best-effort, wrapped in try/except — never block on emit failure).

---

## Task 1: Module skeleton + `BalancerSlot` + `SlotState` dataclasses

**Files:**
- Create: `core/services/cheap_lane_balancer.py`
- Create: `tests/test_cheap_lane_balancer.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_cheap_lane_balancer.py
from __future__ import annotations
from collections import deque
import pytest


def test_balancer_slot_has_slot_id():
    from core.services.cheap_lane_balancer import BalancerSlot
    s = BalancerSlot(
        provider="groq", model="llama-3.1-8b-instant",
        auth_profile="default", base_url="https://api.groq.com/openai/v1",
        rpm_limit=30, daily_limit=10000, is_public_proxy=False,
    )
    assert s.slot_id == "groq::llama-3.1-8b-instant"


def test_balancer_slot_is_frozen():
    from core.services.cheap_lane_balancer import BalancerSlot
    s = BalancerSlot(
        provider="groq", model="m", auth_profile="d",
        base_url="", rpm_limit=None, daily_limit=None,
        is_public_proxy=False,
    )
    with pytest.raises((AttributeError, Exception)):
        s.provider = "other"


def test_slot_state_defaults():
    from core.services.cheap_lane_balancer import SlotState
    st = SlotState(slot_id="x::y")
    assert st.consecutive_failures == 0
    assert st.breaker_level == 0
    assert st.cooldown_until is None
    assert st.daily_use_count == 0
    assert st.total_calls == 0
    assert st.total_failures == 0
    assert isinstance(st.recent_call_timestamps, deque)
    assert st.manually_disabled is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda activate ai && pytest tests/test_cheap_lane_balancer.py -v`
Expected: ImportError / module not found.

- [ ] **Step 3: Implement minimal module**

```python
# core/services/cheap_lane_balancer.py
"""Cheap Lane Balancer — weighted-random load balancing for daemon LLM calls.

Spreads daemon traffic across all available (provider, model) slots
(excluding local ollama, openai-codex, codex-cli) so that no single
quota gets drained while others sit idle.

Brainstorm: docs/superpowers/plans/2026-05-02-cheap-lane-balancer.md
"""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda activate ai && pytest tests/test_cheap_lane_balancer.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/cheap_lane_balancer.py tests/test_cheap_lane_balancer.py
git commit -m "feat(balancer): scaffold module with BalancerSlot and SlotState dataclasses

Task 1 of cheap-lane-balancer plan. Adds:
- BalancerSlot (frozen) — identity of a (provider, model) lane
- SlotState (mutable) — runtime state with RPM deque, daily count,
  cooldown, breaker level, manual disable flag, telemetry counters

3 tests covering slot_id, frozen-immutability, and state defaults.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Slot pool construction (`build_slot_pool`)

**Files:**
- Modify: `core/services/cheap_lane_balancer.py`
- Modify: `tests/test_cheap_lane_balancer.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cheap_lane_balancer.py — append
def test_pool_excludes_local_ollama_and_codex(monkeypatch):
    from core.services import cheap_lane_balancer as clb

    def fake_router_models():
        return [
            {"provider": "ollama", "model": "qwen3.5:9b", "enabled": True},
            {"provider": "openai-codex", "model": "gpt-5.4", "enabled": True},
            {"provider": "codex-cli", "model": "x", "enabled": True},
            {"provider": "groq", "model": "llama-3.1-8b-instant", "enabled": True},
        ]
    monkeypatch.setattr(clb, "_router_enabled_models", fake_router_models)
    monkeypatch.setattr(clb, "_credentials_ready", lambda p, a: True)

    pool = clb.build_slot_pool()
    providers = {s.provider for s in pool}
    assert "ollama" not in providers
    assert "openai-codex" not in providers
    assert "codex-cli" not in providers
    assert "groq" in providers


def test_pool_skips_providers_without_credentials(monkeypatch):
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_router_enabled_models", lambda: [
        {"provider": "groq", "model": "llama-3.1-8b-instant", "enabled": True},
        {"provider": "mistral", "model": "mistral-small-latest", "enabled": True},
    ])
    monkeypatch.setattr(
        clb, "_credentials_ready",
        lambda p, a: p == "groq",  # mistral has no creds
    )

    pool = clb.build_slot_pool()
    providers = {s.provider for s in pool}
    assert "groq" in providers
    assert "mistral" not in providers


def test_pool_marks_public_proxies_correctly(monkeypatch):
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_router_enabled_models", lambda: [
        {"provider": "groq", "model": "llama-3.1-8b-instant", "enabled": True},
        {"provider": "ollamafreeapi", "model": "gpt-oss:20b", "enabled": True},
        {"provider": "opencode", "model": "minimax-m2.5-free", "enabled": True},
        {"provider": "arko", "model": "jarvis-cheap-lane", "enabled": True},
    ])
    monkeypatch.setattr(clb, "_credentials_ready", lambda p, a: True)

    pool = clb.build_slot_pool()
    by_id = {s.slot_id: s for s in pool}
    assert by_id["ollamafreeapi::gpt-oss:20b"].is_public_proxy is True
    assert by_id["opencode::minimax-m2.5-free"].is_public_proxy is True
    assert by_id["arko::jarvis-cheap-lane"].is_public_proxy is True
    assert by_id["groq::llama-3.1-8b-instant"].is_public_proxy is False


def test_pool_skips_disabled_models(monkeypatch):
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_router_enabled_models", lambda: [
        {"provider": "groq", "model": "old-model", "enabled": False},
        {"provider": "groq", "model": "new-model", "enabled": True},
    ])
    monkeypatch.setattr(clb, "_credentials_ready", lambda p, a: True)
    pool = clb.build_slot_pool()
    models = {s.model for s in pool}
    assert "old-model" not in models
    assert "new-model" in models
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda activate ai && pytest tests/test_cheap_lane_balancer.py -v`
Expected: ImportError on `build_slot_pool`, `_router_enabled_models`, `_credentials_ready`.

- [ ] **Step 3: Implement pool construction**

```python
# core/services/cheap_lane_balancer.py — append
import json
import os
from pathlib import Path

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda activate ai && pytest tests/test_cheap_lane_balancer.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/cheap_lane_balancer.py tests/test_cheap_lane_balancer.py
git commit -m "feat(balancer): build_slot_pool from provider_router × CHEAP_PROVIDER_DEFAULTS

Task 2. Constructs flat (provider, model) slot pool excluding local
ollama (visible lane), openai-codex, codex-cli. Skips disabled models
and providers without credentials. Marks ollamafreeapi/arko/opencode
as public proxies.

4 new tests covering exclusions, credentials gate, public-proxy marking,
disabled-model filter.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: State persistence (load/save with debounce)

**Files:**
- Modify: `core/services/cheap_lane_balancer.py`
- Modify: `tests/test_cheap_lane_balancer.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cheap_lane_balancer.py — append
def test_state_round_trip(tmp_path, monkeypatch):
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_state_path", lambda: tmp_path / "state.json")

    states = {
        "groq::m1": clb.SlotState(
            slot_id="groq::m1",
            consecutive_failures=2,
            breaker_level=1,
            cooldown_until=1714680000.0,
            cooldown_reason="429",
            daily_use_count=42,
            daily_window_start="2026-05-02",
            total_calls=100,
            total_failures=5,
            last_success_at=1714680123.45,
        ),
    }
    clb._save_state(states)

    loaded = clb._load_state()
    assert "groq::m1" in loaded
    assert loaded["groq::m1"].consecutive_failures == 2
    assert loaded["groq::m1"].breaker_level == 1
    assert loaded["groq::m1"].daily_use_count == 42


def test_load_state_returns_empty_when_file_missing(tmp_path, monkeypatch):
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_state_path", lambda: tmp_path / "missing.json")
    states = clb._load_state()
    assert states == {}


def test_load_state_returns_empty_on_corrupt_json(tmp_path, monkeypatch):
    from core.services import cheap_lane_balancer as clb
    p = tmp_path / "corrupt.json"
    p.write_text("not valid json {{{", encoding="utf-8")
    monkeypatch.setattr(clb, "_state_path", lambda: p)
    states = clb._load_state()
    assert states == {}


def test_save_state_atomic_write(tmp_path, monkeypatch):
    from core.services import cheap_lane_balancer as clb
    p = tmp_path / "out.json"
    monkeypatch.setattr(clb, "_state_path", lambda: p)
    clb._save_state({"x::y": clb.SlotState(slot_id="x::y", total_calls=7)})
    assert p.exists()
    assert not (tmp_path / "out.json.tmp").exists()
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["slots"]["x::y"]["total_calls"] == 7


def test_get_or_create_state_for_unknown_slot():
    from core.services.cheap_lane_balancer import _ensure_state
    states = {}
    s = _ensure_state(states, "new::slot")
    assert s.slot_id == "new::slot"
    assert s.consecutive_failures == 0
    # Idempotent — second call returns same instance
    s2 = _ensure_state(states, "new::slot")
    assert s is s2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda activate ai && pytest tests/test_cheap_lane_balancer.py -v`
Expected: ImportError on `_load_state`, `_save_state`, `_ensure_state`.

- [ ] **Step 3: Implement state persistence**

Add `import json` at top if not already there.

```python
# core/services/cheap_lane_balancer.py — append
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda activate ai && pytest tests/test_cheap_lane_balancer.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/cheap_lane_balancer.py tests/test_cheap_lane_balancer.py
git commit -m "feat(balancer): state persistence with atomic writes and debounce

Task 3. Adds:
- _state_path() — ~/.jarvis-v2/state/cheap_balancer_state.json
- _load_state / _save_state — atomic write via tmp+rename, json format
- _save_state_debounced — max 1 save per 5s
- _ensure_state — get-or-create per slot_id
- Corrupt/missing file → empty dict (fail-soft)

5 new tests covering round-trip, missing file, corrupt JSON, atomic
write, and ensure_state idempotency.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Selection algorithm (`_compute_weight`, `_select_slot`)

**Files:**
- Modify: `core/services/cheap_lane_balancer.py`
- Modify: `tests/test_cheap_lane_balancer.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cheap_lane_balancer.py — append
import time as _time
from collections import Counter


def _slot(provider="groq", model="m", rpm=None, daily=None, proxy=False):
    from core.services.cheap_lane_balancer import BalancerSlot
    return BalancerSlot(
        provider=provider, model=model, auth_profile="default",
        base_url="", rpm_limit=rpm, daily_limit=daily,
        is_public_proxy=proxy,
    )


def test_weight_zero_during_cooldown():
    from core.services.cheap_lane_balancer import (
        _compute_weight, SlotState,
    )
    s = _slot(rpm=30, daily=10000)
    state = SlotState(slot_id=s.slot_id, cooldown_until=_time.time() + 60)
    assert _compute_weight(s, state, _time.time()) == 0.0


def test_weight_zero_when_manually_disabled():
    from core.services.cheap_lane_balancer import (
        _compute_weight, SlotState,
    )
    s = _slot(rpm=30, daily=10000)
    state = SlotState(slot_id=s.slot_id, manually_disabled=True)
    assert _compute_weight(s, state, _time.time()) == 0.0


def test_weight_decreases_with_daily_usage():
    from core.services.cheap_lane_balancer import (
        _compute_weight, SlotState,
    )
    s = _slot(rpm=30, daily=100)
    today = "2026-05-02"
    state_low = SlotState(slot_id=s.slot_id, daily_use_count=0,
                           daily_window_start=today)
    state_high = SlotState(slot_id=s.slot_id, daily_use_count=80,
                            daily_window_start=today)
    now = _time.time()
    # Mock today
    import core.services.cheap_lane_balancer as clb
    import datetime as _dt

    class _FakeNow:
        @staticmethod
        def now(tz=None):
            return _dt.datetime(2026, 5, 2, tzinfo=_dt.timezone.utc)

    clb._datetime_for_today = _FakeNow
    w_low = _compute_weight(s, state_low, now)
    w_high = _compute_weight(s, state_high, now)
    assert w_low > w_high


def test_public_proxy_boost_applied():
    from core.services.cheap_lane_balancer import (
        _compute_weight, SlotState,
    )
    paid = _slot(provider="groq", rpm=30, daily=10000, proxy=False)
    free = _slot(provider="ollamafreeapi", rpm=None, daily=None, proxy=True)
    state_paid = SlotState(slot_id=paid.slot_id)
    state_free = SlotState(slot_id=free.slot_id)
    now = _time.time()
    w_paid = _compute_weight(paid, state_paid, now)
    w_free = _compute_weight(free, state_free, now)
    # free has unlimited (base=1.0) × proxy_boost(1.5) = 1.5
    # paid has 0 used (base≈1.0) × no_boost(1.0) = 1.0
    assert w_free > w_paid
    assert abs(w_free - 1.5) < 0.05
    assert abs(w_paid - 1.0) < 0.05


def test_breaker_level_reduces_weight():
    from core.services.cheap_lane_balancer import (
        _compute_weight, SlotState,
    )
    s = _slot(rpm=None, daily=None, proxy=False)
    state_healthy = SlotState(slot_id=s.slot_id, breaker_level=0)
    state_breaker = SlotState(slot_id=s.slot_id, breaker_level=2)
    now = _time.time()
    w_healthy = _compute_weight(s, state_healthy, now)
    w_breaker = _compute_weight(s, state_breaker, now)
    assert w_healthy > w_breaker


def test_select_slot_returns_none_when_all_blocked():
    from core.services.cheap_lane_balancer import (
        _select_slot, SlotState,
    )
    pool = [_slot()]
    states = {pool[0].slot_id: SlotState(
        slot_id=pool[0].slot_id, cooldown_until=_time.time() + 60,
    )}
    result = _select_slot(states, pool, _time.time())
    assert result is None


def test_select_slot_picks_only_eligible(monkeypatch):
    """When 9 slots blocked and 1 healthy, the healthy one must be picked."""
    from core.services.cheap_lane_balancer import (
        _select_slot, SlotState,
    )
    pool = [_slot(provider=f"p{i}", model=f"m{i}") for i in range(10)]
    states = {}
    for i, sl in enumerate(pool):
        states[sl.slot_id] = SlotState(
            slot_id=sl.slot_id,
            cooldown_until=(_time.time() + 60) if i != 7 else None,
        )
    chosen = _select_slot(states, pool, _time.time())
    assert chosen is not None
    assert chosen.slot_id == "p7::m7"


def test_weighted_random_distribution_respects_weights(monkeypatch):
    """Statistical: with 1000 picks and weights 3:1, ratio should be roughly 3:1."""
    import random
    from core.services.cheap_lane_balancer import (
        _select_slot, SlotState,
    )
    high = _slot(provider="high", model="m", rpm=None, daily=None, proxy=True)
    low = _slot(provider="low", model="m", rpm=None, daily=None, proxy=False)
    pool = [high, low]
    states = {sl.slot_id: SlotState(slot_id=sl.slot_id) for sl in pool}
    # high weight = 1.5 (unlimited × proxy_boost)
    # low weight  = 1.0 (unlimited × no_boost)
    # Ratio expected: 1.5 / 1.0 = 60% high, 40% low

    random.seed(42)
    picks = Counter()
    for _ in range(2000):
        s = _select_slot(states, pool, _time.time())
        picks[s.provider] += 1

    high_pct = picks["high"] / 2000
    assert 0.55 < high_pct < 0.65  # 60% ± 5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda activate ai && pytest tests/test_cheap_lane_balancer.py -v`
Expected: ImportError on `_compute_weight`, `_select_slot`.

- [ ] **Step 3: Implement selection**

```python
# core/services/cheap_lane_balancer.py — append
import random
from datetime import datetime as _dt_mod, timezone as _tz_mod


_PROXY_BOOST = 1.5
_BREAKER_HEALTH = {0: 1.0, 1: 0.5, 2: 0.2, 3: 0.05}


def _today_iso(now: float | None = None) -> str:
    """Returns UTC date string. Override in tests via _datetime_for_today."""
    dt_mod = globals().get("_datetime_for_today", _dt_mod)
    return dt_mod.now(_tz_mod.utc).strftime("%Y-%m-%d")


def _count_recent_calls(timestamps, now: float, window_seconds: int) -> int:
    """Count timestamps falling within [now - window, now]."""
    threshold = now - window_seconds
    return sum(1 for t in timestamps if t >= threshold)


def _compute_weight(slot: BalancerSlot, state: SlotState, now: float) -> float:
    """Returns non-negative weight; 0 means slot is ineligible right now.

    weight = headroom_factor × health_multiplier × proxy_boost
    """
    # Manual disable
    if state.manually_disabled:
        return 0.0
    # Cooldown gate
    if state.cooldown_until and now < state.cooldown_until:
        return 0.0

    # Headroom factor — start at 1.0 for unlimited slots
    base = 1.0
    if slot.rpm_limit:
        rpm_used = _count_recent_calls(state.recent_call_timestamps, now, 60)
        rpm_headroom = max(0.0, 1.0 - rpm_used / slot.rpm_limit)
        base *= rpm_headroom
    if slot.daily_limit:
        # Reset daily counter if date changed
        today = _today_iso(now)
        if state.daily_window_start != today:
            state.daily_use_count = 0
            state.daily_window_start = today
        daily_headroom = max(0.0, 1.0 - state.daily_use_count / slot.daily_limit)
        base *= daily_headroom

    # Health multiplier (breaker decay)
    health = _BREAKER_HEALTH.get(state.breaker_level, 0.05)

    # Public-proxy boost
    preference = _PROXY_BOOST if slot.is_public_proxy else 1.0

    return max(0.0, base * health * preference)


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
    return eligible[-1][0]  # fallback for floating-point edge case
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda activate ai && pytest tests/test_cheap_lane_balancer.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/cheap_lane_balancer.py tests/test_cheap_lane_balancer.py
git commit -m "feat(balancer): weighted-random selection algorithm

Task 4. Adds:
- _compute_weight(slot, state, now) — formula:
  headroom × health × proxy_boost(1.5×)
  Manual disable + active cooldown → weight 0
  Breaker levels 0-3 map to health multipliers 1.0/0.5/0.2/0.05
- _select_slot(states, pool, now) — weighted-random pick across
  eligible slots; returns None when all blocked
- _today_iso() helper with override hook for tests

8 new tests including statistical distribution check (2000 picks,
expects 60/40 split for proxy/non-proxy unlimited slots within ±5%).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Failure + success registration (circuit breaker)

**Files:**
- Modify: `core/services/cheap_lane_balancer.py`
- Modify: `tests/test_cheap_lane_balancer.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cheap_lane_balancer.py — append
def test_429_with_retry_after_uses_header_value():
    from core.services.cheap_lane_balancer import (
        _register_failure, SlotState,
    )
    state = SlotState(slot_id="x::y")
    now = 1000.0
    _register_failure(state, "http-error:429:rate", retry_after_s=300, now=now)
    assert state.cooldown_until == now + 300
    assert "429" in state.cooldown_reason
    # 429 should NOT escalate breaker level (provider was honest)
    assert state.breaker_level == 0


def test_429_without_retry_after_defaults_to_1h():
    from core.services.cheap_lane_balancer import (
        _register_failure, SlotState,
    )
    state = SlotState(slot_id="x::y")
    now = 1000.0
    _register_failure(state, "http-error:429:rate", retry_after_s=0, now=now)
    assert state.cooldown_until == now + 3600


def test_breaker_escalates_after_3_consecutive_5xx():
    from core.services.cheap_lane_balancer import (
        _register_failure, SlotState,
    )
    state = SlotState(slot_id="x::y")
    for _ in range(3):
        _register_failure(state, "http-error:503", retry_after_s=0, now=1000.0)
    assert state.breaker_level == 1
    assert state.cooldown_until == 1000.0 + 300  # 5min for level 1


def test_breaker_caps_at_level_3():
    from core.services.cheap_lane_balancer import (
        _register_failure, SlotState,
    )
    state = SlotState(slot_id="x::y", breaker_level=3, consecutive_failures=15)
    _register_failure(state, "http-error:503", retry_after_s=0, now=1000.0)
    assert state.breaker_level == 3  # capped


def test_register_success_resets_streak_and_decays_breaker():
    from core.services.cheap_lane_balancer import (
        _register_success, SlotState,
    )
    state = SlotState(
        slot_id="x::y",
        consecutive_failures=2,
        breaker_level=2,
        cooldown_until=9999.0,
    )
    _register_success(state, now=1000.0)
    assert state.consecutive_failures == 0
    assert state.cooldown_until is None
    assert state.last_success_at == 1000.0
    assert state.breaker_level == 1  # decay one level


def test_register_success_increments_total_calls():
    from core.services.cheap_lane_balancer import (
        _register_success, SlotState,
    )
    state = SlotState(slot_id="x::y", total_calls=5)
    _register_success(state, now=1000.0)
    assert state.total_calls == 6


def test_register_success_appends_to_rpm_deque():
    from core.services.cheap_lane_balancer import (
        _register_success, SlotState,
    )
    state = SlotState(slot_id="x::y")
    _register_success(state, now=1000.0)
    _register_success(state, now=1010.0)
    assert len(state.recent_call_timestamps) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda activate ai && pytest tests/test_cheap_lane_balancer.py -v`
Expected: ImportError on `_register_failure`, `_register_success`.

- [ ] **Step 3: Implement failure handling**

```python
# core/services/cheap_lane_balancer.py — append
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
    Other errors → escalate breaker after 3 consecutive failures, apply
                    breaker-level cooldown.
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
        # 429 doesn't escalate breaker
        return

    # 5xx / timeout / unknown — escalate breaker after threshold
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
    # Decay breaker one level toward 0 on success
    if state.breaker_level > 0:
        state.breaker_level = max(0, state.breaker_level - 1)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda activate ai && pytest tests/test_cheap_lane_balancer.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/cheap_lane_balancer.py tests/test_cheap_lane_balancer.py
git commit -m "feat(balancer): failure registration + circuit breaker

Task 5. Adds:
- _register_failure(state, error_kind, retry_after_s, now):
  - 429 with retry-after → use header verbatim
  - 429 without → 1h default
  - 5xx/timeout → escalate breaker after 3 consecutive failures
  - Breaker levels 1-3 cool down 5min/15min/1h
- _register_success(state, now):
  - reset consecutive_failures, clear cooldown
  - decay breaker level by 1 toward healthy
  - append timestamp to RPM deque
  - increment total_calls / last_success_at

7 new tests covering 429 paths, breaker escalation/cap, success
recovery, RPM deque growth.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: `call_balanced` retry-flow

**Files:**
- Modify: `core/services/cheap_lane_balancer.py`
- Modify: `tests/test_cheap_lane_balancer.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cheap_lane_balancer.py — append
def test_call_balanced_succeeds_on_first_slot(monkeypatch, tmp_path):
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_state_path", lambda: tmp_path / "s.json")
    monkeypatch.setattr(
        clb, "build_slot_pool",
        lambda: [_slot(provider="ollamafreeapi", model="m", proxy=True)],
    )

    def fake_executor(*, provider, model, auth_profile, base_url, message):
        return {"text": f"reply from {provider}", "output_tokens": 10}

    monkeypatch.setattr(clb, "_call_provider_chat", fake_executor)

    res = clb.call_balanced(prompt="hi", daemon_name="test")
    assert res["status"] == "ok"
    assert res["text"] == "reply from ollamafreeapi"
    assert res["provider"] == "ollamafreeapi"
    assert res["attempts"] == 1


def test_call_balanced_retries_on_failure_until_success(monkeypatch, tmp_path):
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_state_path", lambda: tmp_path / "s.json")
    pool = [
        _slot(provider="p1", model="m", proxy=False),
        _slot(provider="p2", model="m", proxy=False),
    ]
    monkeypatch.setattr(clb, "build_slot_pool", lambda: pool)

    call_log = []

    def fake_executor(*, provider, model, **kw):
        call_log.append(provider)
        if provider == "p1":
            from core.services.cheap_provider_runtime import CheapProviderError
            raise CheapProviderError(
                provider=provider, code="http-error:503",
                message="bad gateway",
            )
        return {"text": "ok"}

    monkeypatch.setattr(clb, "_call_provider_chat", fake_executor)

    res = clb.call_balanced(prompt="hi", daemon_name="test")
    assert res["status"] == "ok"
    assert res["provider"] == "p2"
    assert res["attempts"] == 2
    assert len(call_log) == 2


def test_call_balanced_raises_when_all_slots_exhausted(monkeypatch, tmp_path):
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_state_path", lambda: tmp_path / "s.json")
    monkeypatch.setattr(
        clb, "build_slot_pool",
        lambda: [_slot(provider=f"p{i}", model="m") for i in range(3)],
    )

    def always_fail(*, provider, **kw):
        from core.services.cheap_provider_runtime import CheapProviderError
        raise CheapProviderError(
            provider=provider, code="http-error:503",
            message="dead",
        )

    monkeypatch.setattr(clb, "_call_provider_chat", always_fail)

    with pytest.raises(RuntimeError, match="exhausted"):
        clb.call_balanced(prompt="hi", daemon_name="test", max_retries=3)


def test_call_balanced_does_not_retry_same_slot_twice(monkeypatch, tmp_path):
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_state_path", lambda: tmp_path / "s.json")
    pool = [_slot(provider="only", model="m")]  # one slot only
    monkeypatch.setattr(clb, "build_slot_pool", lambda: pool)

    call_count = {"n": 0}

    def fake_executor(*, provider, **kw):
        call_count["n"] += 1
        from core.services.cheap_provider_runtime import CheapProviderError
        raise CheapProviderError(
            provider=provider, code="http-error:503", message="x",
        )

    monkeypatch.setattr(clb, "_call_provider_chat", fake_executor)

    with pytest.raises(RuntimeError):
        clb.call_balanced(prompt="hi", daemon_name="test", max_retries=5)
    # Should call exactly once (the one slot), then exhaust
    assert call_count["n"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda activate ai && pytest tests/test_cheap_lane_balancer.py -v`
Expected: ImportError on `call_balanced`, `_call_provider_chat`.

- [ ] **Step 3: Implement call_balanced**

```python
# core/services/cheap_lane_balancer.py — append
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
            break  # all remaining slots blocked

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
                from core.eventbus.events import emit
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
                from core.eventbus.events import emit
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
        from core.eventbus.events import emit
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


# Recent calls ring buffer (in-memory, 75 max)
_RECENT_CALLS: list[dict] = []
_RECENT_CALLS_MAX = 75


def _append_recent_call(
    slot_id: str, daemon: str, status: str, latency_ms: int,
    *, error: str = "",
) -> None:
    from datetime import datetime, timezone
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda activate ai && pytest tests/test_cheap_lane_balancer.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/cheap_lane_balancer.py tests/test_cheap_lane_balancer.py
git commit -m "feat(balancer): call_balanced retry-flow with eventbus emits

Task 6. Adds:
- call_balanced(prompt, daemon_name, max_retries=3) — picks slot via
  weighted random, executes via _call_provider_chat (wraps
  cheap_provider_runtime._execute_provider_chat), retries next slot
  on CheapProviderError. Each slot tried at most once per call.
- Eventbus emits: call_succeeded / call_failed / pool_exhausted
- Recent calls ring buffer (75 most recent, in-memory)
- _append_recent_call / recent_calls() helpers

4 new tests covering happy path, retry, exhaustion, no-double-tap.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Manual controls (reset / disable / enable / refresh)

**Files:**
- Modify: `core/services/cheap_lane_balancer.py`
- Modify: `tests/test_cheap_lane_balancer.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cheap_lane_balancer.py — append
def test_reset_slot_clears_breaker_and_cooldown(tmp_path, monkeypatch):
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_state_path", lambda: tmp_path / "s.json")

    states = {"groq::m": clb.SlotState(
        slot_id="groq::m",
        consecutive_failures=5,
        breaker_level=2,
        cooldown_until=9999.0,
    )}
    clb._save_state(states)

    res = clb.reset_slot("groq::m")
    assert res["status"] == "ok"

    loaded = clb._load_state()
    assert loaded["groq::m"].consecutive_failures == 0
    assert loaded["groq::m"].breaker_level == 0
    assert loaded["groq::m"].cooldown_until is None


def test_reset_slot_returns_error_for_unknown(tmp_path, monkeypatch):
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_state_path", lambda: tmp_path / "s.json")
    res = clb.reset_slot("nonexistent::slot")
    # Reset is idempotent — creates empty state and clears it; allow ok
    # (No specific failure mode for unknown slot — graceful)
    assert res["status"] == "ok"


def test_disable_slot_forces_weight_zero(tmp_path, monkeypatch):
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_state_path", lambda: tmp_path / "s.json")
    s = _slot(provider="groq", model="m")
    state = clb.SlotState(slot_id=s.slot_id)
    clb._save_state({s.slot_id: state})

    res = clb.disable_slot(s.slot_id)
    assert res["status"] == "ok"

    loaded = clb._load_state()
    assert loaded[s.slot_id].manually_disabled is True
    # Weight should be 0
    weight = clb._compute_weight(s, loaded[s.slot_id], _time.time())
    assert weight == 0.0


def test_enable_slot_restores_eligibility(tmp_path, monkeypatch):
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_state_path", lambda: tmp_path / "s.json")
    state = clb.SlotState(slot_id="groq::m", manually_disabled=True)
    clb._save_state({"groq::m": state})

    res = clb.enable_slot("groq::m")
    assert res["status"] == "ok"

    loaded = clb._load_state()
    assert loaded["groq::m"].manually_disabled is False


def test_refresh_pool_returns_current_slot_count(monkeypatch):
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(
        clb, "build_slot_pool",
        lambda: [_slot(provider=f"p{i}", model="m") for i in range(7)],
    )
    res = clb.refresh_pool()
    assert res["status"] == "ok"
    assert res["pool_size"] == 7
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda activate ai && pytest tests/test_cheap_lane_balancer.py -v`
Expected: ImportError on `reset_slot`, `disable_slot`, `enable_slot`, `refresh_pool`.

- [ ] **Step 3: Implement controls**

```python
# core/services/cheap_lane_balancer.py — append

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda activate ai && pytest tests/test_cheap_lane_balancer.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/cheap_lane_balancer.py tests/test_cheap_lane_balancer.py
git commit -m "feat(balancer): manual controls (reset, disable, enable, refresh)

Task 7. Adds 4 control functions for Mission Control:
- reset_slot(slot_id) — clears breaker, cooldown, consecutive_failures
- disable_slot(slot_id) — sets manually_disabled=True (weight forced to 0)
- enable_slot(slot_id) — clears manually_disabled
- refresh_pool() — rebuilds slot pool from provider_router.json
  (use after adding new models without restarting runtime)

5 new tests covering happy paths and idempotency on unknown slot.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Public snapshot for Mission Control telemetry

**Files:**
- Modify: `core/services/cheap_lane_balancer.py`
- Modify: `tests/test_cheap_lane_balancer.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cheap_lane_balancer.py — append
def test_snapshot_returns_pool_metadata(monkeypatch, tmp_path):
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_state_path", lambda: tmp_path / "s.json")
    monkeypatch.setattr(
        clb, "build_slot_pool",
        lambda: [
            _slot(provider="groq", model="m1", rpm=30, daily=10000),
            _slot(provider="ollamafreeapi", model="x", proxy=True),
        ],
    )
    snap = clb.balancer_snapshot()
    assert snap["pool_size"] == 2
    assert "eligible_now" in snap
    assert "saved_at" in snap
    assert isinstance(snap["slots"], list)
    assert len(snap["slots"]) == 2
    slot_ids = {s["slot_id"] for s in snap["slots"]}
    assert "groq::m1" in slot_ids
    assert "ollamafreeapi::x" in slot_ids


def test_snapshot_marks_blocked_slots(monkeypatch, tmp_path):
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_state_path", lambda: tmp_path / "s.json")
    monkeypatch.setattr(
        clb, "build_slot_pool",
        lambda: [_slot(provider="groq", model="m")],
    )
    state = clb.SlotState(slot_id="groq::m", cooldown_until=_time.time() + 600)
    clb._save_state({"groq::m": state})
    snap = clb.balancer_snapshot()
    assert snap["blocked_now"] == 1
    assert snap["eligible_now"] == 0


def test_snapshot_includes_recent_calls(monkeypatch, tmp_path):
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_state_path", lambda: tmp_path / "s.json")
    monkeypatch.setattr(clb, "build_slot_pool", lambda: [])
    clb._RECENT_CALLS.clear()
    clb._append_recent_call("groq::m", "curiosity", "ok", 412)
    clb._append_recent_call("groq::m", "thought_stream", "ok", 156)
    snap = clb.balancer_snapshot()
    assert len(snap["recent_calls"]) == 2
    # Newest first
    assert snap["recent_calls"][0]["daemon"] == "thought_stream"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda activate ai && pytest tests/test_cheap_lane_balancer.py -v`
Expected: ImportError on `balancer_snapshot`.

- [ ] **Step 3: Implement snapshot**

```python
# core/services/cheap_lane_balancer.py — append

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

        # Compute headroom percent
        headroom_pct = 100.0
        if slot.daily_limit and state.daily_window_start == _today_iso(now):
            headroom_pct = max(0.0, 100.0 * (1.0 - state.daily_use_count / slot.daily_limit))

        from datetime import datetime, timezone

        slot_payloads.append({
            "slot_id": slot.slot_id,
            "provider": slot.provider,
            "model": slot.model,
            "is_public_proxy": slot.is_public_proxy,
            "rpm_limit": slot.rpm_limit,
            "daily_limit": slot.daily_limit,
            "rpm_used_now": _count_recent_calls(state.recent_call_timestamps, now, 60),
            "daily_used_today": state.daily_use_count,
            "headroom_pct": round(headroom_pct, 2),
            "current_weight": round(weight, 4),
            "cooldown_until": (
                datetime.fromtimestamp(state.cooldown_until, tz=timezone.utc).isoformat()
                if state.cooldown_until else None
            ),
            "cooldown_reason": state.cooldown_reason,
            "breaker_level": state.breaker_level,
            "consecutive_failures": state.consecutive_failures,
            "manually_disabled": state.manually_disabled,
            "total_calls": state.total_calls,
            "total_failures": state.total_failures,
            "success_rate": (
                (state.total_calls - state.total_failures) / state.total_calls
                if state.total_calls > 0 else None
            ),
            "last_success_at": (
                datetime.fromtimestamp(state.last_success_at, tz=timezone.utc).isoformat()
                if state.last_success_at else None
            ),
        })

    # Sort by weight desc (UI shows healthiest first)
    slot_payloads.sort(key=lambda s: s["current_weight"] or 0, reverse=True)

    return {
        "enabled": _is_enabled(),
        "pool_size": len(pool),
        "eligible_now": eligible,
        "blocked_now": blocked,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "slots": slot_payloads,
        "recent_calls": recent_calls(),
    }


def _is_enabled() -> bool:
    """Check RuntimeSettings.daemon_balancer_enabled. Default True (after Task 9)."""
    try:
        from core.runtime.settings import load_settings
        return bool(getattr(load_settings(), "daemon_balancer_enabled", True))
    except Exception:
        return True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda activate ai && pytest tests/test_cheap_lane_balancer.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/cheap_lane_balancer.py tests/test_cheap_lane_balancer.py
git commit -m "feat(balancer): balancer_snapshot() for Mission Control telemetry

Task 8. Surfaces full state:
- Pool size, eligible_now / blocked_now counts
- Per-slot: provider, model, limits, current usage, headroom_pct,
  current_weight, breaker level, cooldown details, success rate,
  last_success_at, manually_disabled flag
- recent_calls (last 75, newest first)
- Sorted by weight desc (UI shows healthiest first)

3 new tests covering pool metadata, blocked-slot accounting, recent
calls ordering.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: RuntimeSettings field

**Files:**
- Modify: `core/runtime/settings.py`

- [ ] **Step 1: Add field to RuntimeSettings dataclass**

Find the field definitions block (around line 80-110, just before `extra: dict[str, Any] = field(default_factory=dict)`). Add:

```python
# Cheap-lane balancer for daemon LLM traffic. When True (default),
# daemon_llm.py routes through cheap_lane_balancer with weighted-random
# selection across all eligible (provider, model) slots and circuit
# breakers. When False, falls back to task_kind="background" routing.
daemon_balancer_enabled: bool = True
```

- [ ] **Step 2: Add to to_dict typed block**

In `to_dict()` (around line 85-115), add the new key:

```python
"daemon_balancer_enabled": self.daemon_balancer_enabled,
```

- [ ] **Step 3: Add to load_settings construction**

In `load_settings()` (around line 119+), add another field-mapping line before `extra=...`:

```python
daemon_balancer_enabled=bool(data.get("daemon_balancer_enabled", defaults.daemon_balancer_enabled)),
```

- [ ] **Step 4: Verify round-trip**

Run:
```bash
conda activate ai && python -c "
from core.runtime.settings import RuntimeSettings, load_settings
s = RuntimeSettings()
print('default:', s.daemon_balancer_enabled)
print('to_dict has key:', 'daemon_balancer_enabled' in s.to_dict())
print('load_settings:', load_settings().daemon_balancer_enabled)
"
```

Expected: `default: True`, `to_dict has key: True`, `load_settings: True`

- [ ] **Step 5: Commit**

```bash
git add core/runtime/settings.py
git commit -m "feat(balancer): add daemon_balancer_enabled RuntimeSettings field

Task 9. New field:
- daemon_balancer_enabled: bool = True (default on)

Wired through to_dict + load_settings for full round-trip persistence.
Default True so balancer is active immediately after deploy; flip to
False if regression observed (rollback path).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: Wire balancer into `daemon_llm.py`

**Files:**
- Modify: `core/services/daemon_llm.py:142-167`

- [ ] **Step 1: Read current `_daemon_llm_call_impl` block**

```bash
sed -n '142,170p' core/services/daemon_llm.py
```

- [ ] **Step 2: Replace the `# 1. Try primary execution path` block**

Find this block (around line 145-167):

```python
    # 1. Try primary execution path
    try:
        if public_safe:
            from core.services.cheap_provider_runtime import (
                execute_public_safe_cheap_lane,
            )

            result = execute_public_safe_cheap_lane(message=prompt)
        else:
            from core.services.non_visible_lane_execution import (
                execute_cheap_lane,
            )

            # Daemons are inner-layer noise — relevance scoring, mood
            # introspection, dream distillation, etc. They run on every
            # heartbeat tick. Send them through the public-proxy tier so
            # they don't drain Groq/NVIDIA/Gemini quotas that the visible
            # lane and council deliberation actually need.
            result = execute_cheap_lane(message=prompt, task_kind="background")
        text = str(result.get("text") or "").strip()
        provider = str(
            result.get("provider") or ("public-safe" if public_safe else "cheap")
        )
    except Exception:
        pass
```

Replace with:

```python
    # 1. Try primary execution path
    try:
        if public_safe:
            from core.services.cheap_provider_runtime import (
                execute_public_safe_cheap_lane,
            )

            result = execute_public_safe_cheap_lane(message=prompt)
        else:
            # Cheap-lane balancer: spread daemon traffic across all
            # eligible (provider, model) slots via weighted random.
            # Falls back to task_kind="background" if disabled.
            from core.runtime.settings import load_settings as _ls

            if getattr(_ls(), "daemon_balancer_enabled", True):
                from core.services.cheap_lane_balancer import call_balanced

                result = call_balanced(prompt=prompt, daemon_name=daemon_name)
            else:
                from core.services.non_visible_lane_execution import (
                    execute_cheap_lane,
                )

                result = execute_cheap_lane(
                    message=prompt, task_kind="background",
                )
        text = str(result.get("text") or "").strip()
        provider = str(
            result.get("provider") or ("public-safe" if public_safe else "cheap")
        )
    except Exception:
        pass
```

- [ ] **Step 3: Run daemon_llm tests if any exist**

```bash
conda activate ai && pytest tests/ -k "daemon_llm" -v 2>&1 | tail -10
```

Expected: tests pass (or no tests found — that's also acceptable since this file doesn't have a dedicated test).

- [ ] **Step 4: Smoke test the wiring**

```bash
conda activate ai && python -c "
from core.services.daemon_llm import daemon_llm_call
out = daemon_llm_call('Say only: hello', daemon_name='test_smoke', max_len=50)
print('result:', repr(out))
"
```

Expected: prints some non-empty string (the LLM response). If balancer is healthy, response comes via balanced lane.

- [ ] **Step 5: Commit**

```bash
git add core/services/daemon_llm.py
git commit -m "feat(balancer): route daemon LLM calls through cheap_lane_balancer

Task 10. _daemon_llm_call_impl now checks
RuntimeSettings.daemon_balancer_enabled:
- True (default) → call_balanced (weighted random across eligible slots)
- False → existing execute_cheap_lane(task_kind=background) fallback

Heartbeat-model fallback (step 2 in the function) is unchanged. If
balancer raises (all slots exhausted), the existing except path catches
and the call falls through to heartbeat. Same end-user contract.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 11: Add Groq models to provider_router.json

**Files:**
- Modify: `~/.jarvis-v2/config/provider_router.json` (runtime config — **NOT** in repo)

- [ ] **Step 1: Backup current config**

```bash
cp ~/.jarvis-v2/config/provider_router.json ~/.jarvis-v2/config/provider_router.json.bak
```

- [ ] **Step 2: Add new Groq models via Python**

```bash
conda activate ai && python -c "
import json
from pathlib import Path
from datetime import datetime, timezone

p = Path.home() / '.jarvis-v2' / 'config' / 'provider_router.json'
data = json.loads(p.read_text())

now = datetime.now(timezone.utc).isoformat()
new_entries = [
    {'enabled': True, 'lane': 'cheap', 'model': 'llama-3.3-70b-versatile',
     'provider': 'groq', 'auth_profile': 'default', 'updated_at': now},
    {'enabled': True, 'lane': 'cheap', 'model': 'gemma2-9b-it',
     'provider': 'groq', 'auth_profile': 'default', 'updated_at': now},
]

# Skip if already present
existing = {(m['provider'], m['model']) for m in data['models']}
added = []
for entry in new_entries:
    key = (entry['provider'], entry['model'])
    if key not in existing:
        data['models'].append(entry)
        added.append(entry['model'])

p.write_text(json.dumps(data, indent=2))
print('Added:', added if added else '(already present)')
"
```

Expected: `Added: ['llama-3.3-70b-versatile', 'gemma2-9b-it']`

- [ ] **Step 3: Verify pool sees them**

```bash
conda activate ai && python -c "
from core.services.cheap_lane_balancer import build_slot_pool
pool = build_slot_pool()
groq_slots = [s for s in pool if s.provider == 'groq']
for s in groq_slots:
    print(s.slot_id)
print(f'total pool: {len(pool)} slots')
"
```

Expected: 3 groq slots listed (`groq::llama-3.1-8b-instant`, `groq::llama-3.3-70b-versatile`, `groq::gemma2-9b-it`), and total pool size around 22-26.

- [ ] **Step 4: No commit needed**

This is a runtime config change, not a source-code change. Note in shell history that it happened. (If we want to track, we could add a script in `scripts/` for re-running on other deployments — defer to v2.)

---

## Task 12: Mission Control backend route

**Files:**
- Create: `apps/api/jarvis_api/routes/cheap_balancer.py`
- Modify: `apps/api/jarvis_api/app.py`
- Create: `tests/test_cheap_balancer_routes.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cheap_balancer_routes.py
from __future__ import annotations
from fastapi.testclient import TestClient
import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_state_path", lambda: tmp_path / "s.json")
    monkeypatch.setattr(clb, "build_slot_pool", lambda: [])

    # Import after monkeypatch so fresh state
    from apps.api.jarvis_api.app import create_app
    return TestClient(create_app())


def test_get_state_returns_pool_summary(client):
    r = client.get("/mc/cheap-balancer-state")
    assert r.status_code == 200
    data = r.json()
    assert "pool_size" in data
    assert "slots" in data
    assert "recent_calls" in data


def test_post_reset_slot(client, monkeypatch):
    from core.services import cheap_lane_balancer as clb
    state = clb.SlotState(slot_id="groq::m", breaker_level=2, consecutive_failures=5)
    clb._save_state({"groq::m": state})

    r = client.post("/mc/cheap-balancer/slot/groq::m/reset")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    loaded = clb._load_state()
    assert loaded["groq::m"].breaker_level == 0


def test_post_disable_slot(client):
    r = client.post("/mc/cheap-balancer/slot/groq::m/disable")
    assert r.status_code == 200
    assert r.json()["manually_disabled"] is True


def test_post_enable_slot(client):
    from core.services import cheap_lane_balancer as clb
    clb._save_state({"groq::m": clb.SlotState(slot_id="groq::m", manually_disabled=True)})

    r = client.post("/mc/cheap-balancer/slot/groq::m/enable")
    assert r.status_code == 200
    loaded = clb._load_state()
    assert loaded["groq::m"].manually_disabled is False


def test_post_refresh_pool(client):
    r = client.post("/mc/cheap-balancer/refresh-pool")
    assert r.status_code == 200
    data = r.json()
    assert "pool_size" in data
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda activate ai && pytest tests/test_cheap_balancer_routes.py -v`
Expected: 404 errors (routes don't exist yet).

- [ ] **Step 3: Create router file**

```python
# apps/api/jarvis_api/routes/cheap_balancer.py
"""Mission Control endpoints for cheap_lane_balancer telemetry + controls."""
from __future__ import annotations
from fastapi import APIRouter

router = APIRouter(prefix="/mc", tags=["mc-cheap-balancer"])


@router.get("/cheap-balancer-state")
def get_state() -> dict:
    """Return full snapshot: pool, slot states, recent calls."""
    from core.services.cheap_lane_balancer import balancer_snapshot
    return balancer_snapshot()


@router.post("/cheap-balancer/slot/{slot_id}/reset")
def reset(slot_id: str) -> dict:
    """Clear breaker, cooldown, and consecutive_failures for a slot."""
    from core.services.cheap_lane_balancer import reset_slot
    return reset_slot(slot_id)


@router.post("/cheap-balancer/slot/{slot_id}/disable")
def disable(slot_id: str) -> dict:
    """Force a slot's weight to 0 (excluded from selection until enabled)."""
    from core.services.cheap_lane_balancer import disable_slot
    return disable_slot(slot_id)


@router.post("/cheap-balancer/slot/{slot_id}/enable")
def enable(slot_id: str) -> dict:
    """Restore a manually-disabled slot to selection eligibility."""
    from core.services.cheap_lane_balancer import enable_slot
    return enable_slot(slot_id)


@router.post("/cheap-balancer/refresh-pool")
def refresh() -> dict:
    """Rebuild slot pool from provider_router.json."""
    from core.services.cheap_lane_balancer import refresh_pool
    return refresh_pool()
```

- [ ] **Step 4: Register router in app.py**

Find the router-registration block in `apps/api/jarvis_api/app.py` (search for `include_router`). Add:

```python
from apps.api.jarvis_api.routes.cheap_balancer import router as cheap_balancer_router
app.include_router(cheap_balancer_router)
```

(Place near other `include_router` calls, alphabetical order if existing pattern follows it.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `conda activate ai && pytest tests/test_cheap_balancer_routes.py -v`
Expected: all 5 passed.

- [ ] **Step 6: Commit**

```bash
git add apps/api/jarvis_api/routes/cheap_balancer.py apps/api/jarvis_api/app.py tests/test_cheap_balancer_routes.py
git commit -m "feat(balancer): MC API endpoints for state + manual controls

Task 12. New routes (apps/api/jarvis_api/routes/cheap_balancer.py):
- GET  /mc/cheap-balancer-state
- POST /mc/cheap-balancer/slot/{slot_id}/reset
- POST /mc/cheap-balancer/slot/{slot_id}/disable
- POST /mc/cheap-balancer/slot/{slot_id}/enable
- POST /mc/cheap-balancer/refresh-pool

Registered in app.py. 5 endpoint tests passing.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 13: Mission Control frontend tab

**Files:**
- Create: `apps/ui/src/missioncontrol/CheapBalancerTab.tsx`
- Modify: `apps/ui/src/missioncontrol/<existing tab nav>` (find via grep)

- [ ] **Step 1: Find existing MC tab pattern**

```bash
ls apps/ui/src/missioncontrol/ 2>&1 | head -20
grep -rln "TradingView\|TradingTab\|TradingDashboard" apps/ui/src/ 2>/dev/null | head -5
```

Use the existing trading tab as the pattern for layout, polling, and styling. The plan assumes React + TypeScript + Tailwind (existing JarvisX/MC stack).

- [ ] **Step 2: Create CheapBalancerTab.tsx**

```tsx
// apps/ui/src/missioncontrol/CheapBalancerTab.tsx
import { useState, useEffect, useCallback } from 'react';

interface SlotPayload {
  slot_id: string;
  provider: string;
  model: string;
  is_public_proxy: boolean;
  rpm_limit: number | null;
  daily_limit: number | null;
  rpm_used_now: number;
  daily_used_today: number;
  headroom_pct: number;
  current_weight: number;
  cooldown_until: string | null;
  cooldown_reason: string;
  breaker_level: number;
  consecutive_failures: number;
  manually_disabled: boolean;
  total_calls: number;
  total_failures: number;
  success_rate: number | null;
  last_success_at: string | null;
}

interface RecentCall {
  at: string;
  slot_id: string;
  daemon: string;
  status: string;
  latency_ms: number;
  error?: string;
}

interface BalancerState {
  enabled: boolean;
  pool_size: number;
  eligible_now: number;
  blocked_now: number;
  saved_at: string;
  slots: SlotPayload[];
  recent_calls: RecentCall[];
}

const API_BASE = ''; // same-origin

export function CheapBalancerTab() {
  const [state, setState] = useState<BalancerState | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchState = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/mc/cheap-balancer-state`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      setState(data);
      setError(null);
    } catch (e) {
      setError(String(e));
    }
  }, []);

  useEffect(() => {
    fetchState();
    const id = setInterval(fetchState, 4000);
    return () => clearInterval(id);
  }, [fetchState]);

  const action = useCallback(
    async (path: string) => {
      await fetch(`${API_BASE}${path}`, { method: 'POST' });
      fetchState();
    },
    [fetchState],
  );

  if (error) return <div className="text-red-500 p-4">Error: {error}</div>;
  if (!state) return <div className="p-4 text-gray-400">Loading…</div>;

  return (
    <div className="p-4 space-y-4 text-sm font-mono">
      <header className="flex items-center justify-between">
        <h2 className="text-lg font-bold">
          Cheap Lane Balancer{' '}
          <span className={state.enabled ? 'text-green-500' : 'text-gray-500'}>
            [{state.enabled ? 'enabled ✓' : 'disabled'}]
          </span>
        </h2>
        <button
          onClick={() => action('/mc/cheap-balancer/refresh-pool')}
          className="px-3 py-1 bg-blue-700 hover:bg-blue-600 rounded text-white"
        >
          🔄 Refresh pool
        </button>
      </header>

      <div className="bg-gray-900 p-3 rounded">
        Pool: {state.pool_size} slots · {state.eligible_now} eligible ·{' '}
        {state.blocked_now} blocked · saved {state.saved_at.slice(11, 19)}
      </div>

      <section>
        <h3 className="font-bold mb-2">Slot grid (sorted by weight)</h3>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-2">
          {state.slots.map((s) => (
            <SlotCard key={s.slot_id} slot={s} action={action} />
          ))}
        </div>
      </section>

      <section>
        <h3 className="font-bold mb-2">Recent calls (last 75, newest first)</h3>
        <div className="bg-gray-900 p-2 rounded max-h-80 overflow-y-auto space-y-1">
          {state.recent_calls.map((c, i) => (
            <div key={i} className="flex gap-2 text-xs">
              <span className="text-gray-400">{c.at.slice(11, 19)}</span>
              <span className={c.status === 'ok' ? 'text-green-400' : 'text-red-400'}>
                {c.status === 'ok' ? '✓' : '✗'}
              </span>
              <span className="text-blue-300 w-32 truncate">{c.daemon || '(unnamed)'}</span>
              <span className="text-yellow-300 truncate">{c.slot_id}</span>
              <span className="text-gray-400">{c.latency_ms}ms</span>
              {c.error && <span className="text-red-400 truncate">{c.error}</span>}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function SlotCard({ slot, action }: { slot: SlotPayload; action: (p: string) => void }) {
  const status =
    slot.manually_disabled
      ? '⚫'
      : slot.current_weight > 0.3
      ? '🟢'
      : slot.current_weight > 0.05
      ? '🟡'
      : '🔴';

  return (
    <div className="bg-gray-900 p-3 rounded border border-gray-800">
      <div className="flex items-center justify-between mb-1">
        <div>
          {status} <span className="font-bold">{slot.slot_id}</span>
        </div>
        <div className="text-gray-400">weight {slot.current_weight.toFixed(2)}</div>
      </div>
      <div className="text-xs text-gray-400">
        {slot.is_public_proxy ? 'public-proxy' : 'paid'}
        {slot.rpm_limit && ` · ${slot.rpm_used_now}/${slot.rpm_limit} RPM`}
        {slot.daily_limit && ` · ${slot.daily_used_today}/${slot.daily_limit}/day`}
        {slot.total_calls > 0 &&
          ` · ${(slot.success_rate ? slot.success_rate * 100 : 0).toFixed(1)}% ok`}
      </div>
      {slot.cooldown_until && (
        <div className="text-red-400 text-xs mt-1">
          Cooldown until {slot.cooldown_until.slice(11, 19)} · {slot.cooldown_reason}
        </div>
      )}
      <div className="mt-2 flex gap-2">
        {slot.breaker_level > 0 && (
          <button
            onClick={() => action(`/mc/cheap-balancer/slot/${encodeURIComponent(slot.slot_id)}/reset`)}
            className="px-2 py-0.5 bg-yellow-700 hover:bg-yellow-600 rounded text-white text-xs"
          >
            🔄 Reset breaker (L{slot.breaker_level})
          </button>
        )}
        {slot.manually_disabled ? (
          <button
            onClick={() => action(`/mc/cheap-balancer/slot/${encodeURIComponent(slot.slot_id)}/enable`)}
            className="px-2 py-0.5 bg-green-700 hover:bg-green-600 rounded text-white text-xs"
          >
            ✅ Enable
          </button>
        ) : (
          <button
            onClick={() => action(`/mc/cheap-balancer/slot/${encodeURIComponent(slot.slot_id)}/disable`)}
            className="px-2 py-0.5 bg-red-700 hover:bg-red-600 rounded text-white text-xs"
          >
            🚫 Disable
          </button>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Add tab to MC navigation**

Find the Mission Control tab navigation (typically a TabsList or similar in `apps/ui/src/missioncontrol/`). Locate by:

```bash
grep -rln "TradingView\|TradingTab" apps/ui/src/missioncontrol/ 2>/dev/null | head
```

Open the navigation file and add:

```tsx
import { CheapBalancerTab } from './CheapBalancerTab';

// In the tab list:
{ id: 'cheap-balancer', label: 'Cheap Balancer', component: CheapBalancerTab },
```

Exact integration depends on the existing tab pattern — adapt to match.

- [ ] **Step 4: Build UI**

```bash
cd apps/ui && npm run build 2>&1 | tail -10
```

Expected: build succeeds. (If TypeScript errors on imports, adjust paths to match existing patterns.)

- [ ] **Step 5: Manual smoke test**

Restart jarvis-api (or wait until next deploy), navigate to MC → Cheap Balancer tab. Verify:
- Pool count shows
- Slot grid renders (will be empty until daemon makes first call after restart)
- Refresh-pool button works
- After daemons run a few cycles, slots populate with weights

- [ ] **Step 6: Commit**

```bash
git add apps/ui/src/missioncontrol/CheapBalancerTab.tsx apps/ui/src/missioncontrol/
git commit -m "feat(balancer): Mission Control tab with slot grid and controls

Task 13. New CheapBalancerTab.tsx renders:
- Header: enabled status + refresh pool button
- Pool summary line (size, eligible, blocked, saved_at)
- Slot grid (2 cols on lg+, 1 col mobile), sorted by weight desc
- Per-slot cards: status emoji, weight, limits/usage, cooldown info,
  reset breaker / disable / enable buttons
- Recent calls list (75 entries, newest first), color-coded by status

Polls /mc/cheap-balancer-state every 4s. Action buttons hit POST
endpoints and immediately refetch.

Registered in MC tab navigation.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 14: End-to-end smoke test

**Files:**
- Create: `tests/test_cheap_lane_balancer_e2e.py`

- [ ] **Step 1: Write E2E test**

```python
# tests/test_cheap_lane_balancer_e2e.py
"""End-to-end smoke for cheap_lane_balancer.

Stubbed executor; real selection/persistence/retry/state.
"""
from __future__ import annotations
from collections import Counter
import pytest


@pytest.fixture
def e2e(tmp_path, monkeypatch):
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_state_path", lambda: tmp_path / "state.json")
    clb._RECENT_CALLS.clear()
    yield clb


def _slot(provider, model, proxy=False):
    from core.services.cheap_lane_balancer import BalancerSlot
    return BalancerSlot(
        provider=provider, model=model, auth_profile="default",
        base_url="", rpm_limit=None, daily_limit=None,
        is_public_proxy=proxy,
    )


def test_e2e_50_calls_distribute_across_slots(e2e, monkeypatch):
    """50 calls should hit multiple slots, not concentrate on one."""
    pool = [
        _slot("ollamafreeapi", "gpt-oss:20b", proxy=True),
        _slot("opencode", "minimax-m2.5-free", proxy=True),
        _slot("groq", "llama-3.1-8b-instant", proxy=False),
        _slot("groq", "llama-3.3-70b-versatile", proxy=False),
        _slot("nvidia-nim", "llama", proxy=False),
    ]
    monkeypatch.setattr(e2e, "build_slot_pool", lambda: pool)
    monkeypatch.setattr(
        e2e, "_call_provider_chat",
        lambda **kw: {"text": f"ok from {kw['provider']}", "output_tokens": 5},
    )

    providers_used = Counter()
    for i in range(50):
        res = e2e.call_balanced(prompt=f"q{i}", daemon_name="e2e_test")
        providers_used[res["provider"]] += 1

    # Should hit at least 3 different providers (proves spread)
    assert len(providers_used) >= 3
    # No single provider should get everything (proves balancing)
    most_hits = max(providers_used.values())
    assert most_hits < 50


def test_e2e_failover_when_first_slot_429s(e2e, monkeypatch):
    """If first slot 429s, retry hits a different slot and succeeds."""
    pool = [
        _slot("dead", "m1"),
        _slot("alive", "m2"),
    ]
    monkeypatch.setattr(e2e, "build_slot_pool", lambda: pool)

    def fake_executor(*, provider, **kw):
        if provider == "dead":
            from core.services.cheap_provider_runtime import CheapProviderError
            raise CheapProviderError(
                provider="dead", code="http-error:429:tpd",
                message="rate limit", retry_after_seconds=3600,
            )
        return {"text": "ok"}

    monkeypatch.setattr(e2e, "_call_provider_chat", fake_executor)

    # Force "dead" first by manipulating randomness — actually the
    # weighted random handles it; we just need to verify both paths.
    # Run 10 times; at least some should hit dead first then succeed on alive.
    results = [
        e2e.call_balanced(prompt="q", daemon_name="t") for _ in range(10)
    ]
    assert all(r["status"] == "ok" for r in results)
    # All successes come from "alive"
    assert all(r["provider"] == "alive" for r in results)


def test_e2e_state_survives_restart(e2e, monkeypatch):
    """After save+reload, breaker_level and totals persist."""
    pool = [_slot("groq", "m1")]
    monkeypatch.setattr(e2e, "build_slot_pool", lambda: pool)

    def always_fails(**kw):
        from core.services.cheap_provider_runtime import CheapProviderError
        raise CheapProviderError(
            provider="groq", code="http-error:503", message="bad",
        )

    monkeypatch.setattr(e2e, "_call_provider_chat", always_fails)

    # Burn 4 failures (escalates breaker)
    for _ in range(4):
        try:
            e2e.call_balanced(prompt="q", daemon_name="t", max_retries=1)
        except RuntimeError:
            pass

    # Force save
    e2e._save_state(e2e._load_state())

    loaded = e2e._load_state()
    assert "groq::m1" in loaded
    assert loaded["groq::m1"].consecutive_failures >= 3
    assert loaded["groq::m1"].breaker_level >= 1


def test_e2e_recent_calls_capped_at_75(e2e, monkeypatch):
    pool = [_slot("p", "m")]
    monkeypatch.setattr(e2e, "build_slot_pool", lambda: pool)
    monkeypatch.setattr(
        e2e, "_call_provider_chat",
        lambda **kw: {"text": "ok"},
    )

    for i in range(100):
        e2e.call_balanced(prompt=f"q{i}", daemon_name="t")

    snap = e2e.balancer_snapshot()
    assert len(snap["recent_calls"]) <= 75
```

- [ ] **Step 2: Run E2E test**

```bash
conda activate ai && pytest tests/test_cheap_lane_balancer_e2e.py -v
```

Expected: 4 passed.

- [ ] **Step 3: Run full suite**

```bash
conda activate ai && pytest tests/test_cheap_lane_balancer.py tests/test_cheap_lane_balancer_e2e.py tests/test_cheap_balancer_routes.py -v 2>&1 | tail -10
```

Expected: all green.

- [ ] **Step 4: Commit**

```bash
git add tests/test_cheap_lane_balancer_e2e.py
git commit -m "test(balancer): end-to-end integration smoke test

Task 14 (final). Four E2E scenarios:

- 50 calls distribute across multiple providers (proves balancing)
- 429 on first slot triggers retry to alive slot (proves failover)
- State (breaker level, failure count) survives save+reload
- Recent calls ring buffer capped at 75

This completes the cheap-lane-balancer plan (14/14 tasks). After
jarvis-runtime restart (user consent required), daemon LLM traffic
will route through the balancer with weighted-random selection
across all eligible (provider, model) slots.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Final review

After all 14 tasks are committed:

```bash
conda activate ai && pytest tests/ -k "balancer" -v 2>&1 | tail -10
python -m compileall core apps/api scripts
git log --oneline -16
```

If all green:
- jarvis-runtime restart needed for `daemon_balancer_enabled=True` to take effect (user consent per CLAUDE.md memory)
- Watch `/mc/cheap-balancer-state` after restart to confirm slots populating
- Check journalctl for log noise reduction (Groq 429s should largely disappear because traffic spreads)

---

## Self-review notes

**Spec coverage:**
- Sektion 1 (architecture): ✓ Tasks 1-10 (module + integration)
- Sektion 2 (datamodel — slot, state, persistence): ✓ Tasks 1, 3
- Sektion 3 (komponenter): ✓ Tasks 1-13 cover all listed files
- Sektion 4 (selection algorithm): ✓ Task 4 implements full formula + statistical test
- Sektion 5 (MC tab + telemetry): ✓ Tasks 8, 12, 13 (snapshot + endpoints + UI)
- Sektion 6 (controls + error handling + testing + migration): ✓ Tasks 7, 9 (settings flag for rollback)

**No placeholders:** All steps have concrete code or exact commands.

**Type consistency:** `BalancerSlot` (frozen), `SlotState` (mutable), `_compute_weight`, `_select_slot`, `call_balanced`, `_register_failure`, `_register_success`, `reset_slot`, `disable_slot`, `enable_slot`, `refresh_pool`, `balancer_snapshot`, `recent_calls` — all consistent across tasks.

**Known known-unknowns** (validated in early tasks):
- Provider router file location (Task 2 reads from `~/.jarvis-v2/config/provider_router.json`)
- `_execute_provider_chat` signature (Task 6 uses verified signature `provider, model, auth_profile, base_url, message`)
- `provider_auth_ready` exists (Task 2 step 3 calls it; if signature differs adjust)
- MC tab navigation pattern (Task 13 step 3 finds via grep — adapt)
- RuntimeSettings location (Task 9 — confirmed in `core/runtime/settings.py` from earlier session)
