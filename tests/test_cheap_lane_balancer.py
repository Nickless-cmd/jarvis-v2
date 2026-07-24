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
    assert s.slot_id == "groq::llama-3.1-8b-instant::default"


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
    assert by_id["ollamafreeapi::gpt-oss:20b::default"].is_public_proxy is True
    assert by_id["opencode::minimax-m2.5-free::default"].is_public_proxy is True
    assert by_id["arko::jarvis-cheap-lane::default"].is_public_proxy is True
    assert by_id["groq::llama-3.1-8b-instant::default"].is_public_proxy is False


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


def _slot(provider="groq", model="m", rpm_limit=None, daily_limit=None, is_public_proxy=False):
    from core.services.cheap_lane_balancer import BalancerSlot
    return BalancerSlot(
        provider=provider, model=model, auth_profile="default",
        base_url="", rpm_limit=rpm_limit, daily_limit=daily_limit,
        is_public_proxy=is_public_proxy,
    )


def test_weight_zero_during_cooldown():
    from core.services.cheap_lane_balancer import (
        _compute_weight, SlotState,
    )
    s = _slot(rpm_limit=30, daily_limit=10000)
    state = SlotState(slot_id=s.slot_id, cooldown_until=_time.time() + 60)
    assert _compute_weight(s, state, _time.time()) == 0.0


def test_weight_zero_when_manually_disabled():
    from core.services.cheap_lane_balancer import (
        _compute_weight, SlotState,
    )
    s = _slot(rpm_limit=30, daily_limit=10000)
    state = SlotState(slot_id=s.slot_id, manually_disabled=True)
    assert _compute_weight(s, state, _time.time()) == 0.0


def test_weight_decreases_with_daily_usage(monkeypatch):
    # Fund 5: daily headroom kommer nu fra SQLite (_daily_used_from_db), ikke
    # SlotState.daily_use_count. Vægten skal stadig falde med stigende brug.
    from core.services import cheap_lane_balancer as clb
    s = _slot(rpm_limit=30, daily_limit=100)
    state = clb.SlotState(slot_id=s.slot_id)
    now = _time.time()
    monkeypatch.setattr(clb, "_daily_used_from_db", lambda provider, auth_profile="": 0)
    w_low = clb._compute_weight(s, state, now)
    monkeypatch.setattr(clb, "_daily_used_from_db", lambda provider, auth_profile="": 80)
    w_high = clb._compute_weight(s, state, now)
    assert w_low > w_high


def test_public_proxy_boost_applied():
    from core.services.cheap_lane_balancer import (
        _compute_weight, SlotState,
    )
    paid = _slot(provider="groq", rpm_limit=None, daily_limit=None, is_public_proxy=False)
    free = _slot(provider="ollamafreeapi", rpm_limit=None, daily_limit=None, is_public_proxy=True)
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
    s = _slot(rpm_limit=None, daily_limit=None, is_public_proxy=False)
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
    assert chosen.slot_id == "p7::m7::default"


def test_weighted_random_distribution_respects_weights():
    """Statistical: with 2000 picks and weights 1.5:1.0, ratio ~60/40."""
    import random
    from core.services.cheap_lane_balancer import (
        _select_slot, SlotState,
    )
    high = _slot(provider="high", model="m", rpm_limit=None, daily_limit=None, is_public_proxy=True)
    low = _slot(provider="low", model="m", rpm_limit=None, daily_limit=None, is_public_proxy=False)
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
        lambda: [_slot(provider="ollamafreeapi", model="m", is_public_proxy=True)],
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
        _slot(provider="p1", model="m", is_public_proxy=False),
        _slot(provider="p2", model="m", is_public_proxy=False),
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
    # Fund 4: udmattelse rejser ikke længere — den falder til bunden.
    monkeypatch.setattr("core.services.cheap_lane_floor.attempt_floor",
                        lambda **kw: {"status": "degraded", "provider": "floor",
                                      "lane": "cheap", "text": "", "is_floor": True})
    res = clb.call_balanced(prompt="hi", daemon_name="test", max_retries=3)
    assert res["provider"] == "floor"


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
    monkeypatch.setattr("core.services.cheap_lane_floor.attempt_floor",
                        lambda **kw: {"status": "degraded", "provider": "floor",
                                      "lane": "cheap", "text": "", "is_floor": True})
    res = clb.call_balanced(prompt="hi", daemon_name="test", max_retries=5)
    assert res["provider"] == "floor"   # falder til bund frem for at rejse
    assert call_count["n"] == 1          # men retryer stadig ikke samme slot


# --- Task 7: Manual controls ---


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


def test_reset_slot_returns_ok_for_unknown(tmp_path, monkeypatch):
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_state_path", lambda: tmp_path / "s.json")
    res = clb.reset_slot("nonexistent::slot")
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


# --- Task 8: Snapshot for Mission Control ---


def test_snapshot_returns_pool_metadata(monkeypatch, tmp_path):
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_state_path", lambda: tmp_path / "s.json")
    monkeypatch.setattr(
        clb, "build_slot_pool",
        lambda: [
            _slot(provider="groq", model="m1", rpm_limit=30, daily_limit=10000),
            _slot(provider="ollamafreeapi", model="x", is_public_proxy=True),
        ],
    )
    snap = clb.balancer_snapshot()
    assert snap["pool_size"] == 2
    assert "eligible_now" in snap
    assert "saved_at" in snap
    assert isinstance(snap["slots"], list)
    assert len(snap["slots"]) == 2
    slot_ids = {s["slot_id"] for s in snap["slots"]}
    assert "groq::m1::default" in slot_ids
    assert "ollamafreeapi::x::default" in slot_ids


def test_snapshot_marks_blocked_slots(monkeypatch, tmp_path):
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_state_path", lambda: tmp_path / "s.json")
    monkeypatch.setattr(
        clb, "build_slot_pool",
        lambda: [_slot(provider="groq", model="m")],
    )
    state = clb.SlotState(slot_id="groq::m::default", cooldown_until=_time.time() + 600)
    clb._save_state({"groq::m::default": state})
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


# --- Provider-wide DNS / connection circuit breaker ---


def test_dns_error_detection():
    from core.services.cheap_lane_balancer import _is_dns_or_connection_error
    assert _is_dns_or_connection_error("connection-error") is True
    assert _is_dns_or_connection_error("dns-failure") is True
    assert _is_dns_or_connection_error("http-error:503") is False
    assert _is_dns_or_connection_error("http-error:429") is False

    class FakeExc(Exception):
        pass

    assert _is_dns_or_connection_error("", FakeExc("getaddrinfo failed")) is True
    assert _is_dns_or_connection_error("", FakeExc("name or service not known")) is True
    assert _is_dns_or_connection_error("", FakeExc("normal error message")) is False


def test_register_provider_wide_failure_cools_all_provider_slots(tmp_path, monkeypatch):
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_state_path", lambda: tmp_path / "s.json")
    pool = [
        _slot(provider="ollamafreeapi", model="m1", is_public_proxy=True),
        _slot(provider="ollamafreeapi", model="m2", is_public_proxy=True),
        _slot(provider="ollamafreeapi", model="m3", is_public_proxy=True),
        _slot(provider="groq", model="g1", is_public_proxy=False),
    ]
    states = {}
    affected = clb._register_provider_wide_failure(
        states, pool, "ollamafreeapi", now=1000.0, reason="dns-down",
    )
    assert affected == 3
    # All 3 ollamafreeapi slots have cooldown
    for sid in ("ollamafreeapi::m1::default", "ollamafreeapi::m2::default",
                "ollamafreeapi::m3::default"):
        st = states[sid]
        assert st.cooldown_until == 1000.0 + 600  # default cooldown
        assert "provider-wide" in st.cooldown_reason
        assert "dns-down" in st.cooldown_reason
    # groq is NOT touched
    assert "groq::g1::default" not in states or states["groq::g1::default"].cooldown_until is None


def test_call_balanced_dns_failure_excludes_whole_provider(monkeypatch, tmp_path):
    """If first attempt fails with connection-error, balancer should NOT try
    other slots from the same provider — only different providers."""
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_state_path", lambda: tmp_path / "s.json")
    pool = [
        _slot(provider="ollamafreeapi", model="m1", is_public_proxy=True),
        _slot(provider="ollamafreeapi", model="m2", is_public_proxy=True),
        _slot(provider="ollamafreeapi", model="m3", is_public_proxy=True),
        _slot(provider="groq", model="alive", is_public_proxy=False),
    ]
    monkeypatch.setattr(clb, "build_slot_pool", lambda: pool)

    # Deterministic selection: pick first slot in eligible_pool list order.
    # That guarantees ollamafreeapi is tried first (it appears earlier in pool).
    def deterministic_select(states, current_pool, now):
        return current_pool[0] if current_pool else None
    monkeypatch.setattr(clb, "_select_slot", deterministic_select)

    call_log = []

    def fake_executor(*, provider, model, **kw):
        call_log.append((provider, model))
        if provider == "ollamafreeapi":
            from core.services.cheap_provider_runtime import CheapProviderError
            raise CheapProviderError(
                provider="ollamafreeapi", code="connection-error",
                message="DNS down",
            )
        return {"text": "ok from groq"}

    monkeypatch.setattr(clb, "_call_provider_chat", fake_executor)

    res = clb.call_balanced(prompt="hi", daemon_name="test", max_retries=5)
    assert res["status"] == "ok"
    assert res["provider"] == "groq"
    # Should have hit ollamafreeapi exactly ONCE (not 3 times) before
    # provider-wide cooldown excluded the rest, then groq succeeded.
    ofa_calls = [p for p, _ in call_log if p == "ollamafreeapi"]
    groq_calls = [p for p, _ in call_log if p == "groq"]
    assert len(ofa_calls) == 1, f"expected 1 ofa call, got {len(ofa_calls)}: {call_log}"
    assert len(groq_calls) == 1


# --- Fase A: floor + SQLite-kvote + Central-observe ---

def test_call_balanced_falls_to_floor_on_exhaustion(monkeypatch):
    """Task 3 / Fund 4: call_balanced må aldrig rejse ved tom pool."""
    import core.services.cheap_lane_balancer as bal
    monkeypatch.setattr(bal, "build_slot_pool", lambda: [])

    def fake_floor(*, message, lane, reason):
        return {"status": "degraded", "provider": "floor", "lane": lane,
                "text": "", "is_floor": True}

    monkeypatch.setattr("core.services.cheap_lane_floor.attempt_floor", fake_floor)
    res = bal.call_balanced(prompt="hej", daemon_name="test")
    assert res["provider"] == "floor"   # ingen RuntimeError


def test_daily_headroom_reads_sqlite_invocations(monkeypatch):
    """Task 4 / Fund 5: daily-kvote fra SQLite, ikke privat JSON."""
    import core.services.cheap_lane_balancer as bal
    monkeypatch.setattr(bal, "_daily_used_from_db", lambda provider, auth_profile="": 90)
    slot = bal.BalancerSlot(provider="groq", model="x", auth_profile="", base_url="",
                            rpm_limit=None, daily_limit=100, is_public_proxy=False)
    assert abs(bal._daily_headroom_for(slot) - 0.1) < 1e-6


def test_balancer_events_observe_to_central(monkeypatch):
    """Task 5: fejl-events skrives til Centralens provider_health i real-tid."""
    import core.services.cheap_lane_balancer as bal
    seen = []
    monkeypatch.setattr(bal, "_observe_central",
                        lambda nerve, payload: seen.append((nerve, payload)))
    bal._emit_balancer_event("cheap_balancer.call_failed",
                             {"slot_id": "groq::x", "error_kind": "rate-limited"})
    assert seen and seen[0][0] == "provider_health"
    assert seen[0][1]["error_kind"] == "rate-limited"


def test_build_slot_pool_includes_static_models_providers(monkeypatch):
    """Fund 14. jul: inderlivet (balancer) manglede static_models-only providers
    (cerebras/aihubmix/requesty/cline). De injiceres nu → hele huset samme pool."""
    import core.services.cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_router_enabled_models", lambda: [])
    monkeypatch.setattr(clb, "_credentials_ready", lambda p, ap: True)
    monkeypatch.setattr(clb, "_provider_metadata", lambda p: {})
    provs = {s.provider for s in clb.build_slot_pool()}
    assert "cerebras" in provs and "aihubmix" in provs
    assert "deepseek" not in provs          # routable=False → ude
    assert "openai-codex" not in provs      # excluded
    monkeypatch.setattr("core.services.cheap_provider_runtime_adapters.provider_cost_class", lambda p: "paid" if p=="copilot-premium" else "free")
    provs2 = {s.provider for s in clb.build_slot_pool()}
    assert "copilot-premium" not in provs2  # betalt aldrig i balancer


# --- §5.5 central_route hook (mirror af selection-siden; shadow→live) ---


def test_central_route_hook_noop_when_flags_off(monkeypatch):
    """Begge flag OFF → byte-identisk: intet central_route-kald, weighted-pick beholdes."""
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_central_route_shadow", lambda: False)
    monkeypatch.setattr(clb, "_central_route_live", lambda: False)
    called = []
    monkeypatch.setattr("core.services.central_route.route",
                        lambda **kw: called.append(kw) or {})
    weighted = _slot(provider="groq", model="a")
    pool = [weighted, _slot(provider="nebius", model="b")]
    out = clb._maybe_central_route_slot(weighted, pool, set())
    assert out is weighted
    assert called == []          # OFF → central_route slet ikke kaldt


def test_central_route_hook_live_applies_pick(monkeypatch):
    """Live ON: central_route's pick vinder, når den mapper til en egnet slot."""
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_central_route_shadow", lambda: False)
    monkeypatch.setattr(clb, "_central_route_live", lambda: True)
    monkeypatch.setattr("core.services.central_route.route",
                        lambda **kw: {"provider": "nebius", "model": "b", "is_floor": False})
    weighted = _slot(provider="groq", model="a")
    nebius = _slot(provider="nebius", model="b")
    out = clb._maybe_central_route_slot(weighted, [weighted, nebius], set())
    assert out is nebius


def test_central_route_hook_live_floor_keeps_weighted(monkeypatch):
    """Aldrig-tør: route giver floor → behold weighted-pick (route fjerner aldrig stemmen)."""
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_central_route_shadow", lambda: False)
    monkeypatch.setattr(clb, "_central_route_live", lambda: True)
    monkeypatch.setattr("core.services.central_route.route",
                        lambda **kw: {"provider": "deepseek", "model": "x", "is_floor": True})
    weighted = _slot(provider="groq", model="a")
    out = clb._maybe_central_route_slot(weighted, [weighted], set())
    assert out is weighted


def test_central_route_hook_live_unmapped_keeps_weighted(monkeypatch):
    """Route peger på noget der ikke er en egnet slot → behold weighted-pick."""
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_central_route_shadow", lambda: False)
    monkeypatch.setattr(clb, "_central_route_live", lambda: True)
    monkeypatch.setattr("core.services.central_route.route",
                        lambda **kw: {"provider": "ghost", "model": "z", "is_floor": False})
    weighted = _slot(provider="groq", model="a")
    out = clb._maybe_central_route_slot(weighted, [weighted], set())
    assert out is weighted


def test_central_route_hook_shadow_records_divergence(monkeypatch):
    """Shadow ON, live OFF: gammel sti BESLUTTER, divergens observeres til Central."""
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_central_route_shadow", lambda: True)
    monkeypatch.setattr(clb, "_central_route_live", lambda: False)
    monkeypatch.setattr("core.services.central_route.route",
                        lambda **kw: {"provider": "nebius", "model": "b", "is_floor": False})
    seen = []
    monkeypatch.setattr(clb, "_observe_central",
                        lambda nerve, payload: seen.append((nerve, payload)))
    weighted = _slot(provider="groq", model="a")
    nebius = _slot(provider="nebius", model="b")
    out = clb._maybe_central_route_slot(weighted, [weighted, nebius], set())
    assert out is weighted        # shadow-only → weighted beslutter
    assert seen and seen[0][0] == "route_shadow"
    assert seen[0][1]["new_provider"] == "nebius"


def test_call_balanced_live_hook_floor_still_works(monkeypatch, tmp_path):
    """Med central_route_live ON og en tom pool falder call_balanced stadig til floor —
    aldrig-tør-garantien er urørt af hook'en."""
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_state_path", lambda: tmp_path / "s.json")
    monkeypatch.setattr(clb, "_central_route_live", lambda: True)
    monkeypatch.setattr(clb, "_central_route_shadow", lambda: False)
    monkeypatch.setattr(clb, "build_slot_pool", lambda: [])

    def fake_floor(*, message, lane, reason):
        return {"status": "degraded", "provider": "floor", "model": "", "text": "",
                "lane": lane, "is_floor": True}
    monkeypatch.setattr("core.services.cheap_lane_floor.attempt_floor", fake_floor)
    res = clb.call_balanced(prompt="hej", daemon_name="test")
    assert res["provider"] == "floor"     # ingen RuntimeError, floor holdt


def test_call_balanced_live_hook_routes_to_central_pick(monkeypatch, tmp_path):
    """Live ON: call_balanced eksekverer central_route's valgte slot i stedet for weighted."""
    from core.services import cheap_lane_balancer as clb
    monkeypatch.setattr(clb, "_state_path", lambda: tmp_path / "s.json")
    monkeypatch.setattr(clb, "_central_route_live", lambda: True)
    monkeypatch.setattr(clb, "_central_route_shadow", lambda: False)
    pool = [_slot(provider="groq", model="a"), _slot(provider="nebius", model="b")]
    monkeypatch.setattr(clb, "build_slot_pool", lambda: pool)
    # weighted-random ville tage groq (index 0); central_route overruler til nebius
    monkeypatch.setattr(clb, "_select_slot", lambda states, p, now: p[0] if p else None)
    monkeypatch.setattr("core.services.central_route.route",
                        lambda **kw: {"provider": "nebius", "model": "b", "is_floor": False})
    monkeypatch.setattr(clb, "_call_provider_chat",
                        lambda *, provider, model, **kw: {"text": f"reply from {provider}", "output_tokens": 3})
    res = clb.call_balanced(prompt="hi", daemon_name="test")
    assert res["status"] == "ok"
    assert res["provider"] == "nebius"    # central_route's pick, ikke groq


# --- 15. jul: pålideligheds-vægtning + fejl-tælling-fix ---

def _slot(**over):
    from core.services.cheap_lane_balancer import BalancerSlot
    d = dict(provider="p", model="m", auth_profile="default", base_url="",
             rpm_limit=None, daily_limit=None, is_public_proxy=False)
    d.update(over)
    return BalancerSlot(**d)


def test_register_failure_increments_total_calls():
    """FIX: total_calls skal tælle ALLE forsøg (før: kun succes → fejl% kunne >100%)."""
    from core.services.cheap_lane_balancer import SlotState, _register_failure
    st = SlotState(slot_id="p::m")
    _register_failure(st, "500 server_error", now=1000.0)
    assert st.total_calls == 1 and st.total_failures == 1


def test_reliability_deweights_high_failure_slot():
    """Bjørn: læg de mest fejlende længere ned (fjern dem ikke). En slot der fejler
    meget (≥ min-sample) skal veje MINDRE end en pålidelig — men aldrig 0."""
    from core.services.cheap_lane_balancer import (
        SlotState, _compute_weight, _RELIABILITY_FLOOR, _MIN_RELIABILITY_SAMPLES)
    slot = _slot()
    good = SlotState(slot_id="p::m", total_calls=100, total_failures=2)
    bad = SlotState(slot_id="p::m", total_calls=100, total_failures=81)
    wg = _compute_weight(slot, good, now=1000.0)
    wb = _compute_weight(slot, bad, now=1000.0)
    assert wb < wg              # de-vægtet
    assert wb > 0.0             # men ALDRIG fjernet (gulv)
    assert wb >= wg * _RELIABILITY_FLOOR


def test_reliability_not_penalized_below_min_samples():
    """En ny/lav-volumen-slot straffes ikke på 1-2 uheldige kald."""
    from core.services.cheap_lane_balancer import (
        SlotState, _compute_weight, _MIN_RELIABILITY_SAMPLES)
    slot = _slot()
    fresh = SlotState(slot_id="p::m", total_calls=0, total_failures=0)
    noisy = SlotState(slot_id="p::m",
                      total_calls=_MIN_RELIABILITY_SAMPLES - 1, total_failures=_MIN_RELIABILITY_SAMPLES - 1)
    assert _compute_weight(slot, noisy, now=1000.0) == _compute_weight(slot, fresh, now=1000.0)


def test_slot_id_includes_auth_profile():
    from core.services.cheap_lane_balancer import BalancerSlot
    a = BalancerSlot(provider="groq", model="x", auth_profile="default",
                     base_url="", rpm_limit=None, daily_limit=None, is_public_proxy=False)
    b = BalancerSlot(provider="groq", model="x", auth_profile="account2",
                     base_url="", rpm_limit=None, daily_limit=None, is_public_proxy=False)
    assert a.slot_id != b.slot_id
    assert a.slot_id == "groq::x::default"
    assert b.slot_id == "groq::x::account2"


def test_daily_used_from_db_per_profile(isolated_runtime):
    from core.runtime.db_cheap_provider import record_cheap_provider_invocation as rec
    from core.services import cheap_lane_balancer as bal
    for _ in range(3):
        rec(provider="groq", status="ok", auth_profile="default")
    rec(provider="groq", status="ok", auth_profile="account2")
    assert bal._daily_used_from_db("groq", "default") == 3
    assert bal._daily_used_from_db("groq", "account2") == 1
    assert bal._daily_used_from_db("groq") == 4   # no profile => all (backward compat)


def test_build_slot_pool_multiprofile_when_flag_on(monkeypatch):
    from core.services import cheap_lane_balancer as bal
    monkeypatch.setattr(bal, "_router_enabled_models", lambda: [
        {"provider": "groq", "model": "llama-x", "enabled": True,
         "lane": "cheap", "auth_profile": "default"}])
    monkeypatch.setattr(
        "core.services.auth_profile_scan.ready_profiles_for",
        lambda provider: ["default", "account2"] if provider == "groq" else ["default"])
    monkeypatch.setattr(bal, "_credentials_ready", lambda p, a: True)
    monkeypatch.setattr(bal, "_flag_multiprofile", lambda: True)
    ids = {s.slot_id for s in bal.build_slot_pool()}
    assert "groq::llama-x::default" in ids
    assert "groq::llama-x::account2" in ids


def test_build_slot_pool_single_profile_when_flag_off(monkeypatch):
    from core.services import cheap_lane_balancer as bal
    monkeypatch.setattr(bal, "_router_enabled_models", lambda: [
        {"provider": "groq", "model": "llama-x", "enabled": True,
         "lane": "cheap", "auth_profile": "default"}])
    monkeypatch.setattr(bal, "_credentials_ready", lambda p, a: True)
    monkeypatch.setattr(bal, "_flag_multiprofile", lambda: False)
    ids = {s.slot_id for s in bal.build_slot_pool()}
    assert "groq::llama-x::account2" not in ids


def test_built_slots_carry_egress(monkeypatch):
    from core.services import cheap_lane_balancer as bal
    monkeypatch.setattr(bal, "_router_enabled_models", lambda: [
        {"provider": "groq", "model": "llama-x", "enabled": True,
         "lane": "cheap", "auth_profile": "default"}])
    monkeypatch.setattr(
        "core.services.auth_profile_scan.ready_profiles_for",
        lambda provider: ["default", "account2"] if provider == "groq" else ["default"])
    monkeypatch.setattr(bal, "_credentials_ready", lambda p, a: True)
    monkeypatch.setattr(bal, "_flag_multiprofile", lambda: True)
    slots = {s.slot_id: s for s in bal.build_slot_pool()}
    # default profile -> home; account2 groq -> he6 (Cloudflare-blocked VPN IP)
    assert slots["groq::llama-x::default"].egress == "home"
    assert slots["groq::llama-x::account2"].egress == "he6"


# ---------------------------------------------------------------------------
# Task 8c: account2 = equal parallel tier (egress-separated), NOT a lower-priority
# fallback. _compute_weight must NOT down-weight by auth_profile, and weighted-random
# selection must reach BOTH default and account2 slots (neither starved).
# ---------------------------------------------------------------------------


def _profile_slot(provider, model, profile, egress="home"):
    from core.services.cheap_lane_balancer import BalancerSlot
    return BalancerSlot(provider=provider, model=model, auth_profile=profile,
                        base_url="", rpm_limit=None, daily_limit=None,
                        is_public_proxy=False, egress=egress)


def test_account2_equal_weight_to_default():
    from core.services import cheap_lane_balancer as bal
    now = 1000.0
    sd = _profile_slot("groq", "x", "default", "home")
    sa = _profile_slot("groq", "x", "account2", "he6")
    st_d = bal.SlotState(slot_id=sd.slot_id)
    st_a = bal.SlotState(slot_id=sa.slot_id)
    assert bal._compute_weight(sd, st_d, now) == bal._compute_weight(sa, st_a, now) > 0


def test_both_profiles_get_selected_over_many_draws():
    # Two equal-weight slots (default + account2). Weighted-random _select_slot must
    # pick BOTH across many draws; neither is starved. _select_slot uses the module
    # `random`, so seed it for determinism.
    import random
    from core.services import cheap_lane_balancer as bal
    sd = _profile_slot("groq", "x", "default", "home")
    sa = _profile_slot("groq", "x", "account2", "he6")
    pool = [sd, sa]
    states = {
        sd.slot_id: bal.SlotState(slot_id=sd.slot_id),
        sa.slot_id: bal.SlotState(slot_id=sa.slot_id),
    }
    now = 1000.0
    random.seed(12345)
    seen = Counter()
    for _ in range(200):
        picked = bal._select_slot(states, pool, now)
        assert picked is not None
        seen[picked.slot_id] += 1
    assert seen[sd.slot_id] > 0, "default slot starved"
    assert seen[sa.slot_id] > 0, "account2 slot starved"


# ---------------------------------------------------------------------------
# Task 12: SlotState learns daily_observed, safely (adaptive quota)
# ---------------------------------------------------------------------------


def test_transient_429_does_not_learn(monkeypatch):
    from core.services import cheap_lane_balancer as bal
    monkeypatch.setattr(bal, "_flag_adaptive_quota", lambda: True)
    st = bal.SlotState(slot_id="groq::x::default")
    bal._register_failure(st, "429 rate limit", now=1000.0, retry_after_s=2)
    assert st.daily_observed is None   # rate/transient -> no learning


def test_learns_only_after_corroboration(monkeypatch):
    from core.services import cheap_lane_balancer as bal
    monkeypatch.setattr(bal, "_flag_adaptive_quota", lambda: True)
    st = bal.SlotState(slot_id="groq::x::default")
    # config_daily=70 -> floor=35, below observed_used=40, so 40 is preserved
    # (floor test below covers the noise-floor guard with config_daily=100).
    bal._register_failure(st, "quota exhausted daily", now=1000.0, observed_used=40, config_daily=70)
    assert st.daily_observed is None   # first event: not yet corroborated
    bal._register_failure(st, "quota exhausted daily", now=1001.0, observed_used=40, config_daily=70)
    assert st.daily_observed is not None and st.daily_observed <= 40


def test_config_floor_not_undercut(monkeypatch):
    from core.services import cheap_lane_balancer as bal
    monkeypatch.setattr(bal, "_flag_adaptive_quota", lambda: True)
    st = bal.SlotState(slot_id="groq::x::default")
    for _ in range(2):
        bal._register_failure(st, "quota exhausted daily", now=1000.0, observed_used=1, config_daily=100)
    assert st.daily_observed >= 50   # floored at 50% of config, not driven to ~1


def test_flag_off_no_learning(monkeypatch):
    from core.services import cheap_lane_balancer as bal
    monkeypatch.setattr(bal, "_flag_adaptive_quota", lambda: False)
    st = bal.SlotState(slot_id="groq::x::default")
    for _ in range(3):
        bal._register_failure(st, "quota exhausted daily", now=1000.0, observed_used=1, config_daily=100)
    assert st.daily_observed is None


def test_persist_roundtrip_of_learned_fields():
    from core.services import cheap_lane_balancer as bal
    st = bal.SlotState(slot_id="groq::x::default"); st.daily_observed = 55; st.quota_429_count = 2
    d = bal._state_to_dict(st); st2 = bal._state_from_dict(d)
    assert st2.daily_observed == 55 and st2.quota_429_count == 2


def test_predictive_skip_when_at_learned_ceiling(monkeypatch):
    from core.services import cheap_lane_balancer as bal
    monkeypatch.setattr(bal, "_flag_adaptive_quota", lambda: True)
    # config allows 100/day, but we've learned the real ceiling is 40, and 40 already used
    monkeypatch.setattr(bal, "_daily_used_from_db", lambda provider, auth_profile="": 40)
    slot = bal.BalancerSlot(provider="groq", model="x", auth_profile="account2",
                            base_url="", rpm_limit=None, daily_limit=100, is_public_proxy=False)
    st = bal.SlotState(slot_id=slot.slot_id); st.daily_observed = 40
    assert bal._daily_headroom_for(slot, st) == 0.0          # no headroom vs learned ceiling
    assert bal._compute_weight(slot, st, 1000.0) == 0.0      # -> skipped, no try-and-fail


def test_config_headroom_when_no_learned_ceiling(monkeypatch):
    from core.services import cheap_lane_balancer as bal
    monkeypatch.setattr(bal, "_flag_adaptive_quota", lambda: True)
    monkeypatch.setattr(bal, "_daily_used_from_db", lambda provider, auth_profile="": 40)
    slot = bal.BalancerSlot(provider="groq", model="x", auth_profile="account2",
                            base_url="", rpm_limit=None, daily_limit=100, is_public_proxy=False)
    st = bal.SlotState(slot_id=slot.slot_id)  # daily_observed is None
    # falls back to config limit 100: 40/100 used -> headroom 0.6
    assert abs(bal._daily_headroom_for(slot, st) - 0.6) < 1e-9


def test_flag_off_ignores_learned_ceiling(monkeypatch):
    from core.services import cheap_lane_balancer as bal
    monkeypatch.setattr(bal, "_flag_adaptive_quota", lambda: False)
    monkeypatch.setattr(bal, "_daily_used_from_db", lambda provider, auth_profile="": 40)
    slot = bal.BalancerSlot(provider="groq", model="x", auth_profile="account2",
                            base_url="", rpm_limit=None, daily_limit=100, is_public_proxy=False)
    st = bal.SlotState(slot_id=slot.slot_id); st.daily_observed = 40
    # flag off -> learned ceiling ignored -> config 100 -> headroom 0.6
    assert abs(bal._daily_headroom_for(slot, st) - 0.6) < 1e-9


# ---------------------------------------------------------------------------
# Task 14: anti-jag stale marking
# ---------------------------------------------------------------------------


def _q(st, bal, now):
    bal._register_failure(st, "quota exhausted daily", now=now, observed_used=10, config_daily=100)


def test_three_quota_failures_mark_stale(monkeypatch):
    from core.services import cheap_lane_balancer as bal
    monkeypatch.setattr(bal, "_flag_adaptive_quota", lambda: True)
    st = bal.SlotState(slot_id="groq::x::default")
    _q(st, bal, 1000.0); _q(st, bal, 1001.0)
    assert st.stale_until_daily_reset is False   # 2 not enough
    _q(st, bal, 1002.0)
    assert st.stale_until_daily_reset is True     # 3 -> stale


def test_stale_slot_has_zero_weight(monkeypatch):
    from core.services import cheap_lane_balancer as bal
    monkeypatch.setattr(bal, "_flag_adaptive_quota", lambda: True)
    slot = bal.BalancerSlot(provider="groq", model="x", auth_profile="default",
                            base_url="", rpm_limit=None, daily_limit=None, is_public_proxy=False)
    st = bal.SlotState(slot_id=slot.slot_id); st.stale_until_daily_reset = True
    assert bal._compute_weight(slot, st, 1000.0) == 0.0


def test_flag_off_ignores_stale(monkeypatch):
    from core.services import cheap_lane_balancer as bal
    monkeypatch.setattr(bal, "_flag_adaptive_quota", lambda: False)
    slot = bal.BalancerSlot(provider="groq", model="x", auth_profile="default",
                            base_url="", rpm_limit=None, daily_limit=None, is_public_proxy=False)
    st = bal.SlotState(slot_id=slot.slot_id); st.stale_until_daily_reset = True
    assert bal._compute_weight(slot, st, 1000.0) > 0.0   # flag off -> field ignored, slot healthy


def test_stale_persist_roundtrip():
    from core.services import cheap_lane_balancer as bal
    st = bal.SlotState(slot_id="groq::x::default"); st.stale_until_daily_reset = True
    st2 = bal._state_from_dict(bal._state_to_dict(st))
    assert st2.stale_until_daily_reset is True


# --- Task A2: enriched balancer_snapshot (egress, status, header) ---


def _slot_egress(provider="groq", model="m", egress="home", is_public_proxy=False):
    from core.services.cheap_lane_balancer import BalancerSlot
    return BalancerSlot(
        provider=provider, model=model, auth_profile="default",
        base_url="", rpm_limit=None, daily_limit=None,
        is_public_proxy=is_public_proxy, egress=egress,
    )


def test_slot_status_severity_order():
    from core.services import cheap_lane_balancer as bal
    now = 1000.0
    slot = bal.BalancerSlot(provider="groq", model="m", auth_profile="default",
                            base_url="", rpm_limit=None, daily_limit=None,
                            is_public_proxy=False)

    # healthy
    st = bal.SlotState(slot_id=slot.slot_id)
    assert bal._slot_status(slot, st, now) == "healthy"

    # breaker_level>0 uden aktiv cooldown = 'recovering' (half-open, eligible),
    # ikke 'breaker' — en aktivt blokerende breaker sætter cooldown og vises som
    # 'cooldown' (se test nedenfor).
    st = bal.SlotState(slot_id=slot.slot_id, breaker_level=2)
    assert bal._slot_status(slot, st, now) == "recovering"

    # stale outranks recovering
    st = bal.SlotState(slot_id=slot.slot_id, breaker_level=2)
    st.stale_until_daily_reset = True
    assert bal._slot_status(slot, st, now) == "stale"

    # cooldown outranks stale + breaker
    st = bal.SlotState(slot_id=slot.slot_id, breaker_level=2,
                       cooldown_until=now + 60)
    st.stale_until_daily_reset = True
    assert bal._slot_status(slot, st, now) == "cooldown"

    # a past cooldown does NOT count
    st = bal.SlotState(slot_id=slot.slot_id, cooldown_until=now - 60)
    assert bal._slot_status(slot, st, now) == "healthy"

    # disabled outranks everything
    st = bal.SlotState(slot_id=slot.slot_id, breaker_level=3,
                       cooldown_until=now + 60, manually_disabled=True)
    st.stale_until_daily_reset = True
    assert bal._slot_status(slot, st, now) == "disabled"


def test_balancer_snapshot_has_egress_status_and_header(monkeypatch, tmp_path):
    from core.services import cheap_lane_balancer as bal
    monkeypatch.setattr(bal, "_state_path", lambda: tmp_path / "s.json")
    monkeypatch.setattr(
        bal, "build_slot_pool",
        lambda: [
            _slot_egress(provider="groq", model="m1", egress="home"),
            _slot_egress(provider="cerebras", model="m2", egress="vpn"),
            _slot_egress(provider="ollamafreeapi", model="m3", egress="he6",
                         is_public_proxy=True),
        ],
    )
    snap = bal.balancer_snapshot()

    # header aggregate
    assert "header" in snap
    h = snap["header"]
    for k in ("total_slots", "healthy", "cooldown", "disabled",
              "by_egress", "by_profile", "providers"):
        assert k in h
    assert h["total_slots"] == 3
    assert h["providers"] == 3
    assert h["by_egress"] == {"home": 1, "vpn": 1, "he6": 1}
    assert h["by_profile"] == {"default": 3}

    # existing top-level keys preserved (backward compat)
    for k in ("enabled", "pool_size", "eligible_now", "blocked_now",
              "saved_at", "slots", "recent_calls"):
        assert k in snap

    # per-slot fields
    slots = snap["slots"]
    assert slots
    for s in slots:
        for k in ("slot_id", "provider", "model", "auth_profile", "egress",
                  "status", "weight", "daily_headroom", "daily_used",
                  "daily_limit", "rpm_used", "rpm_limit", "breaker_level",
                  "cooldown_until", "cooldown_reason", "last_success_at",
                  "total_calls", "total_failures", "success_rate",
                  "daily_observed", "stale"):
            assert k in s, f"missing {k}"
    egresses = {s["egress"] for s in slots}
    assert egresses == {"home", "vpn", "he6"}
    assert all(s["status"] == "healthy" for s in slots)


def test_balancer_snapshot_header_counts_status(monkeypatch, tmp_path):
    from core.services import cheap_lane_balancer as bal
    monkeypatch.setattr(bal, "_state_path", lambda: tmp_path / "s.json")
    monkeypatch.setattr(
        bal, "build_slot_pool",
        lambda: [
            _slot_egress(provider="groq", model="ok", egress="home"),
            _slot_egress(provider="groq", model="cold", egress="home"),
            _slot_egress(provider="groq", model="off", egress="home"),
        ],
    )
    bal._save_state({
        "groq::cold::default": bal.SlotState(
            slot_id="groq::cold::default", cooldown_until=_time.time() + 600),
        "groq::off::default": bal.SlotState(
            slot_id="groq::off::default", manually_disabled=True),
    })
    snap = bal.balancer_snapshot()
    h = snap["header"]
    assert h["total_slots"] == 3
    assert h["healthy"] == 1
    assert h["cooldown"] == 1
    assert h["disabled"] == 1


def test_slot_status_expired_breaker_is_recovering_not_breaker():
    """En breaker hvis cooldown er UDLØBET må vise 'recovering' (half-open,
    eligible igen), ikke 'breaker' — ellers hænger stale/døde slots som live
    outages i Mission Control (Bjørns '20 breakers' der reelt var udløbne)."""
    from core.services.cheap_lane_balancer import BalancerSlot, SlotState, _slot_status
    s = BalancerSlot(provider="p", model="m", auth_profile="default",
                     base_url="", rpm_limit=None, daily_limit=None,
                     is_public_proxy=False)
    now = 1_000_000.0
    # breaker tripped, cooldown i FORTIDEN → recovering
    st_expired = SlotState(slot_id=s.slot_id, breaker_level=2,
                           cooldown_until=now - 10)
    assert _slot_status(s, st_expired, now) == "recovering"
    # breaker tripped, cooldown i FREMTIDEN (aktivt blokerende) → cooldown
    st_active = SlotState(slot_id=s.slot_id, breaker_level=2,
                          cooldown_until=now + 300)
    assert _slot_status(s, st_active, now) == "cooldown"
    # ingen breaker → healthy
    st_ok = SlotState(slot_id=s.slot_id, breaker_level=0)
    assert _slot_status(s, st_ok, now) == "healthy"


def test_snapshot_header_separates_recovering_from_breaker():
    """balancer_snapshot's header skal have et 'recovering'-felt adskilt fra
    'breaker' (som nu ~altid er 0 fordi aktive breakers vises som cooldown)."""
    from core.services.cheap_lane_balancer import balancer_snapshot
    h = balancer_snapshot().get("header", {})
    assert "recovering" in h
    assert "breaker" in h
