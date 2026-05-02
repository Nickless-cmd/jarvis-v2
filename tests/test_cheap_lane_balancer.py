"""Tests for core/services/cheap_lane_balancer.py — daemon LLM load balancer."""
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


# --- Task 2: build_slot_pool ---


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


# --- Task 3: State persistence ---


import json as _json


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
    data = _json.loads(p.read_text(encoding="utf-8"))
    assert data["slots"]["x::y"]["total_calls"] == 7


def test_get_or_create_state_for_unknown_slot():
    from core.services.cheap_lane_balancer import _ensure_state
    states = {}
    s = _ensure_state(states, "new::slot")
    assert s.slot_id == "new::slot"
    assert s.consecutive_failures == 0
    s2 = _ensure_state(states, "new::slot")
    assert s is s2


# --- Task 4: Selection algorithm ---


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
        _compute_weight, SlotState, _today_iso,
    )
    s = _slot(rpm=30, daily=100)
    today = _today_iso(_time.time())
    state_low = SlotState(slot_id=s.slot_id, daily_use_count=0,
                           daily_window_start=today)
    state_high = SlotState(slot_id=s.slot_id, daily_use_count=80,
                            daily_window_start=today)
    now = _time.time()
    w_low = _compute_weight(s, state_low, now)
    w_high = _compute_weight(s, state_high, now)
    assert w_low > w_high


def test_public_proxy_boost_applied():
    from core.services.cheap_lane_balancer import (
        _compute_weight, SlotState,
    )
    paid = _slot(provider="groq", rpm=None, daily=None, proxy=False)
    free = _slot(provider="ollamafreeapi", rpm=None, daily=None, proxy=True)
    state_paid = SlotState(slot_id=paid.slot_id)
    state_free = SlotState(slot_id=free.slot_id)
    now = _time.time()
    w_paid = _compute_weight(paid, state_paid, now)
    w_free = _compute_weight(free, state_free, now)
    # free has unlimited (base=1.0) × proxy_boost(1.5) = 1.5
    # paid has unlimited (base=1.0) × no_boost(1.0) = 1.0
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


def test_select_slot_picks_only_eligible():
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


def test_weighted_random_distribution_respects_weights():
    """Statistical: with 2000 picks and weights 1.5:1.0, ratio ~60/40."""
    import random
    from core.services.cheap_lane_balancer import (
        _select_slot, SlotState,
    )
    high = _slot(provider="high", model="m", rpm=None, daily=None, proxy=True)
    low = _slot(provider="low", model="m", rpm=None, daily=None, proxy=False)
    pool = [high, low]
    states = {sl.slot_id: SlotState(slot_id=sl.slot_id) for sl in pool}

    random.seed(42)
    picks = Counter()
    for _ in range(2000):
        s = _select_slot(states, pool, _time.time())
        picks[s.provider] += 1

    high_pct = picks["high"] / 2000
    assert 0.55 < high_pct < 0.65  # 60% ± 5


# --- Task 5: Failure/success handling ---


def test_429_with_retry_after_uses_header_value():
    from core.services.cheap_lane_balancer import (
        _register_failure, SlotState,
    )
    state = SlotState(slot_id="x::y")
    now = 1000.0
    _register_failure(state, "http-error:429:rate", retry_after_s=300, now=now)
    assert state.cooldown_until == now + 300
    assert "429" in state.cooldown_reason
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
    assert state.cooldown_until == 1000.0 + 300


def test_breaker_caps_at_level_3():
    from core.services.cheap_lane_balancer import (
        _register_failure, SlotState,
    )
    state = SlotState(slot_id="x::y", breaker_level=3, consecutive_failures=15)
    _register_failure(state, "http-error:503", retry_after_s=0, now=1000.0)
    assert state.breaker_level == 3


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
    assert state.breaker_level == 1


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


# --- Task 6: call_balanced retry-flow ---


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

    # Force p1 first by replacing _select_slot with pool-order picker
    def deterministic_select(states, current_pool, now):
        return current_pool[0] if current_pool else None
    monkeypatch.setattr(clb, "_select_slot", deterministic_select)

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
    assert call_log == ["p1", "p2"]


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
    pool = [_slot(provider="only", model="m")]
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
    assert call_count["n"] == 1
