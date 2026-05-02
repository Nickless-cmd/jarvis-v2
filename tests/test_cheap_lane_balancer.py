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
