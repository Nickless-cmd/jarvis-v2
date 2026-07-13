"""Tests for dispatch_guards — de fire dispatch-backstops (C3).

Idempotens · dead-man-timeout · circuit-breaker · budget-loft. Alle deterministiske
(tid gives ind som now/now_ts). Bruger isolated_runtime så runtime_state_kv + den
dedikerede idempotens-tabel lever i en tmp-DB.
"""
from __future__ import annotations

from core.services import dispatch_guards as dg
from core.services.dispatch_status import DispatchStatus


# --------------------------------------------------------------------------
# Guard 1 — Idempotens
# --------------------------------------------------------------------------
def test_try_consume_first_true_then_false(isolated_runtime):
    assert dg.try_consume("k") is True
    assert dg.try_consume("k") is False


def test_try_consume_different_key_true(isolated_runtime):
    assert dg.try_consume("k") is True
    assert dg.try_consume("other") is True


def test_try_consume_reconsumable_after_ttl(isolated_runtime):
    assert dg.try_consume("k", now=1000.0, ttl_s=100.0) is True
    # inden for TTL → stadig forbrugt
    assert dg.try_consume("k", now=1050.0, ttl_s=100.0) is False
    # efter TTL → må forbruges igen
    assert dg.try_consume("k", now=2000.0, ttl_s=100.0) is True


def test_try_consume_empty_key_false(isolated_runtime):
    assert dg.try_consume("") is False


# --------------------------------------------------------------------------
# Guard 2 — Dead-man-timeout
# --------------------------------------------------------------------------
def test_synthesize_timeout_envelope_shape():
    env = dg.synthesize_timeout_envelope("agent-7", 30000)
    assert env["status"] == DispatchStatus.TIMEOUT
    assert env["duration_ms"] == 30000
    # fast 7-nøgle-envelope
    assert set(env.keys()) == {
        "status", "tokens_in", "tokens_out", "cost_usd",
        "duration_ms", "tool_calls", "result",
    }
    assert "no completion by deadline" in str(env["result"])


def test_register_and_overdue_finds_only_expired(isolated_runtime):
    dg.register_deadline("d-expired", deadline_ts=1000.0)
    dg.register_deadline("d-fresh", deadline_ts=5000.0)
    od = dg.overdue(now_ts=2000.0)
    assert "d-expired" in od
    assert "d-fresh" not in od


def test_clear_deadline_removes(isolated_runtime):
    dg.register_deadline("d1", deadline_ts=1000.0)
    dg.clear_deadline("d1")
    assert dg.overdue(now_ts=9999.0) == []


# --------------------------------------------------------------------------
# Guard 3 — Circuit-breaker
# --------------------------------------------------------------------------
def test_breaker_trips_after_five_consecutive_failures(isolated_runtime):
    lane = "autonomous"
    for i in range(4):
        dg.record_outcome(lane, ok=False, now=100.0 + i)
        assert dg.is_tripped(lane, now=100.0 + i) is False
    dg.record_outcome(lane, ok=False, now=105.0)  # 5th
    assert dg.is_tripped(lane, now=105.0) is True


def test_breaker_success_resets_consecutive(isolated_runtime):
    lane = "lane-x"
    for i in range(4):
        dg.record_outcome(lane, ok=False, now=100.0 + i)
    dg.record_outcome(lane, ok=True, now=104.0)  # reset
    dg.record_outcome(lane, ok=False, now=105.0)  # count now 1, not 5
    assert dg.is_tripped(lane, now=105.0) is False


def test_breaker_auto_resets_after_cooldown(isolated_runtime):
    lane = "lane-cool"
    for i in range(5):
        dg.record_outcome(lane, ok=False, now=100.0 + i)
    assert dg.is_tripped(lane, now=105.0) is True
    # default cooldown 900s → stadig tripped lige inden
    assert dg.is_tripped(lane, now=104.0 + 899.0) is True
    # efter cooldown → auto-reset
    assert dg.is_tripped(lane, now=104.0 + 900.0) is False


# --------------------------------------------------------------------------
# Guard 4 — Budget-loft
# --------------------------------------------------------------------------
def test_budget_allows_until_count_exceeded(isolated_runtime, monkeypatch):
    from core.runtime.db_core import set_runtime_state_value
    set_runtime_state_value("dispatch_budget_max_count", 3)
    lane = "b-count"
    for i in range(3):
        assert dg.budget_allows(lane, 0.0, now=1000.0 + i) is True
        dg.record_spend(lane, 0.0, now=1000.0 + i)
    # 4th would exceed count=3
    assert dg.budget_allows(lane, 0.0, now=1003.0) is False


def test_budget_allows_until_cost_exceeded(isolated_runtime):
    from core.runtime.db_core import set_runtime_state_value
    set_runtime_state_value("dispatch_budget_max_cost_usd", 1.0)
    lane = "b-cost"
    assert dg.budget_allows(lane, 0.6, now=1000.0) is True
    dg.record_spend(lane, 0.6, now=1000.0)
    # spent 0.6, another 0.6 → 1.2 > 1.0 → blocked
    assert dg.budget_allows(lane, 0.6, now=1001.0) is False
    # a cheaper one still fits (0.6 + 0.3 = 0.9)
    assert dg.budget_allows(lane, 0.3, now=1001.0) is True


def test_budget_window_rolls_after_24h(isolated_runtime):
    from core.runtime.db_core import set_runtime_state_value
    set_runtime_state_value("dispatch_budget_max_count", 1)
    lane = "b-window"
    dg.record_spend(lane, 0.0, now=1000.0)
    assert dg.budget_allows(lane, 0.0, now=1001.0) is False  # window full
    # >24h later the old event ages out → allowed again
    assert dg.budget_allows(lane, 0.0, now=1000.0 + 86401.0) is True


def test_budget_empty_lane_false(isolated_runtime):
    assert dg.budget_allows("", 0.0) is False
