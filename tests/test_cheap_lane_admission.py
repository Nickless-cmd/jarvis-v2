from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest


def test_provider_drain_blocks_new_lease_but_keeps_active_one(isolated_runtime):
    from core.services.cheap_lane_admission import (
        AdmissionRejected,
        acquire_admission,
        admission_snapshot,
        release_admission,
        set_admission_mode,
    )

    first = acquire_admission(
        correlation_id="run-1", provider="groq", slot_id="groq::llama::default"
    )
    drained = set_admission_mode(scope="provider", target="groq", mode="draining")
    assert drained["active_calls"] == 1
    with pytest.raises(AdmissionRejected):
        acquire_admission(
            correlation_id="run-2", provider="groq", slot_id="groq::llama::default"
        )
    assert admission_snapshot(scope="provider", target="groq")["active_calls"] == 1
    release_admission(first.lease_id)
    assert admission_snapshot(scope="provider", target="groq")["active_calls"] == 0


def test_expired_lease_does_not_hold_drain_open(isolated_runtime):
    from core.runtime.db_core import connect
    from core.services.cheap_lane_admission import (
        acquire_admission,
        admission_snapshot,
        set_admission_mode,
    )

    lease = acquire_admission(
        correlation_id="run-old", provider="groq", slot_id="groq::llama::default",
        lease_seconds=1,
    )
    with connect() as conn:
        conn.execute(
            "UPDATE cheap_lane_admission_leases SET expires_at=? WHERE lease_id=?",
            ((datetime.now(UTC) - timedelta(seconds=1)).isoformat(), lease.lease_id),
        )
        conn.commit()
    state = set_admission_mode(scope="provider", target="groq", mode="draining")
    assert state["active_calls"] == 0
    assert admission_snapshot(scope="provider", target="groq")["active_calls"] == 0


def test_lane_pause_rejects_all_providers(isolated_runtime):
    from core.services.cheap_lane_admission import (
        AdmissionRejected,
        acquire_admission,
        set_admission_mode,
    )

    set_admission_mode(scope="lane", target="cheap", mode="paused")
    with pytest.raises(AdmissionRejected):
        acquire_admission(correlation_id="run", provider="mistral", slot_id="slot")
