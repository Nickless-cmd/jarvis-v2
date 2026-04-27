"""Unit tests for provider_circuit_breaker."""
from __future__ import annotations

import time
from unittest.mock import patch

import core.services.provider_circuit_breaker as cb


def setup_function(_fn):
    cb.reset_all()


def test_no_failures_does_not_skip():
    assert cb.should_skip("p", "m") is False


def test_under_threshold_does_not_open():
    cb.record_failure("p", "m")
    cb.record_failure("p", "m")
    assert cb.should_skip("p", "m") is False


def test_threshold_opens_breaker():
    for _ in range(3):
        cb.record_failure("p", "m")
    assert cb.should_skip("p", "m") is True


def test_success_clears_breaker():
    for _ in range(3):
        cb.record_failure("p", "m")
    assert cb.should_skip("p", "m") is True
    cb.record_success("p", "m")
    assert cb.should_skip("p", "m") is False


def test_breaker_isolated_per_provider_model():
    for _ in range(3):
        cb.record_failure("p1", "m1")
    assert cb.should_skip("p1", "m1") is True
    assert cb.should_skip("p2", "m2") is False
    assert cb.should_skip("p1", "m2") is False


def test_empty_provider_or_model_no_op():
    cb.record_failure("", "m")
    cb.record_failure("p", "")
    assert cb.should_skip("", "m") is False
    assert cb.should_skip("p", "") is False


def test_breaker_state_observability():
    cb.record_failure("p", "m")
    cb.record_failure("p", "m")
    state = cb.breaker_state()
    assert state["recent_failures"]
    assert state["recent_failures"][0]["failure_count"] == 2
    assert state["open_breakers"] == []


def test_open_state_in_observability():
    for _ in range(3):
        cb.record_failure("p", "m")
    state = cb.breaker_state()
    assert len(state["open_breakers"]) == 1
    assert state["open_breakers"][0]["provider"] == "p"
    assert state["open_breakers"][0]["retry_in_seconds"] > 0


def test_cooldown_expires_after_open_duration():
    for _ in range(3):
        cb.record_failure("p", "m")
    assert cb.should_skip("p", "m") is True
    # Fake time passing past the cooldown
    with patch.object(cb, "_OPEN_DURATION_SECONDS", 0.01):
        time.sleep(0.02)
        assert cb.should_skip("p", "m") is False
