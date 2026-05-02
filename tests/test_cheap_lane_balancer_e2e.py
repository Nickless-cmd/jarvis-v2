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
    # No single provider should get everything
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

    # Run 10 times; all should succeed (eventually hitting "alive")
    results = [
        e2e.call_balanced(prompt="q", daemon_name="t") for _ in range(10)
    ]
    assert all(r["status"] == "ok" for r in results)
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
