"""WS2: cheap_lane_balancer.call_balanced skal logge en costs-række pr. kald.

Balanceren er daemon-lanens default-vej (daemon_balancer_enabled=True) og var
FØR WS2 usynlig for cost-ledgeren → dominerende reconciliation-hul.
"""
from __future__ import annotations
import pytest


@pytest.fixture
def clb(tmp_path, monkeypatch):
    from core.services import cheap_lane_balancer as _clb
    monkeypatch.setattr(_clb, "_state_path", lambda: tmp_path / "state.json")
    _clb._RECENT_CALLS.clear()
    yield _clb


def _slot(provider, model):
    from core.services.cheap_lane_balancer import BalancerSlot
    return BalancerSlot(
        provider=provider, model=model, auth_profile="default",
        base_url="", rpm_limit=None, daily_limit=None, is_public_proxy=False,
    )


def test_call_balanced_logs_costs_row(clb, monkeypatch):
    monkeypatch.setattr(clb, "build_slot_pool", lambda: [_slot("deepseek", "deepseek-v4-flash")])
    monkeypatch.setattr(clb, "_call_provider_chat", lambda **kw: {
        "text": "ok", "input_tokens": 100, "output_tokens": 50,
        "cache_hit_tokens": 30, "cache_miss_tokens": 70, "cost_usd": 0.0,
    })
    captured = {}
    import core.costing.ledger as ledger
    monkeypatch.setattr(ledger, "record_cost", lambda **kw: captured.update(kw))

    res = clb.call_balanced(prompt="q", daemon_name="t")
    assert res["status"] == "ok"
    assert captured, "call_balanced skal kalde record_cost"
    assert captured["provider"] == "deepseek"
    assert captured["model"] == "deepseek-v4-flash"
    assert captured["lane"] == "cheap-balanced"
    assert captured["input_tokens"] == 100
    assert captured["output_tokens"] == 50
    assert captured["cache_hit_tokens"] == 30
    assert captured["cache_miss_tokens"] == 70


def test_call_balanced_survives_record_cost_error(clb, monkeypatch):
    monkeypatch.setattr(clb, "build_slot_pool", lambda: [_slot("deepseek", "deepseek-v4-flash")])
    monkeypatch.setattr(clb, "_call_provider_chat", lambda **kw: {"text": "ok", "output_tokens": 5})

    def boom(**kw):
        raise RuntimeError("db down")
    import core.costing.ledger as ledger
    monkeypatch.setattr(ledger, "record_cost", boom)

    # cost-logging må ALDRIG vælte et daemon-kald
    res = clb.call_balanced(prompt="q", daemon_name="t")
    assert res["status"] == "ok"
