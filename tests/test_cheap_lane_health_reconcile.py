"""Shared invocation success must heal only the matching balancer slot."""

from __future__ import annotations

import time


def test_reconcile_respects_model_profile_and_manual_disable(isolated_runtime):
    from core.runtime.db_cheap_provider import record_cheap_provider_invocation
    from core.services.cheap_lane_balancer import SlotState
    from core.services.cheap_lane_health_reconcile import reconcile_successes

    now = time.time()
    states = {
        f"p::{model}::{profile}": SlotState(
            slot_id=f"p::{model}::{profile}",
            last_failure_at=now - 60,
            cooldown_until=now + 3600,
            cooldown_reason="model-not-found",
            breaker_level=3,
            consecutive_failures=5,
            manually_disabled=disabled,
        )
        for model, profile, disabled in (
            ("m1", "default", False),
            ("m1", "account2", False),
            ("m2", "default", False),
            ("m3", "default", True),
        )
    }
    for model in ("m1", "m3"):
        record_cheap_provider_invocation(
            provider="p", model=model, auth_profile="default",
            status="completed",
        )

    assert reconcile_successes(states, now)
    assert states["p::m1::default"].cooldown_until is None
    assert states["p::m1::default"].consecutive_failures == 0
    assert states["p::m1::account2"].consecutive_failures == 5
    assert states["p::m2::default"].consecutive_failures == 5
    assert states["p::m3::default"].manually_disabled
    assert states["p::m3::default"].consecutive_failures == 5
    assert not reconcile_successes(states, now)
