from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.services import in_flight_runs as ifr


@pytest.fixture(autouse=True)
def _isolated_records(monkeypatch):
    records: dict[str, dict] = {}
    monkeypatch.setattr(ifr, "_load", lambda: {k: dict(v) for k, v in records.items()})

    def save(value):
        records.clear()
        records.update({k: dict(v) for k, v in value.items()})

    monkeypatch.setattr(ifr, "_save", save)
    monkeypatch.setattr(ifr, "owner_still_alive", lambda owner: False)
    return records


def test_recoverable_settlement_survives_reload(_isolated_records):
    ifr.mark_started(run_id="r1", session_id="s1", user_message="fix it")

    rec = ifr.settle_recovering(
        "r1", reason="provider-timeout", checkpoint_ref="cp-r1"
    )

    assert rec["status"] == "recovering"
    assert ifr._load()["r1"]["checkpoint_ref"] == "cp-r1"
    assert rec["task_id"] == "r1"


def test_only_one_owner_can_claim_same_recovery(_isolated_records):
    ifr.mark_started(run_id="r1", session_id="s1", user_message="fix it")
    ifr.settle_recovering("r1", reason="shutdown")

    first = ifr.claim_due_recovery(owner="100:1")
    second = ifr.claim_due_recovery(owner="200:2")

    assert first is not None
    assert first["recovery_generation"] == 1
    assert first["recovery_attempt"] == 1
    assert second is None


def test_expired_lease_can_be_reclaimed_but_stale_generation_cannot_settle(
    _isolated_records,
):
    t0 = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)
    ifr.mark_started(run_id="r1", session_id="s1", user_message="fix it")
    ifr.settle_recovering("r1", reason="shutdown")
    first = ifr.claim_due_recovery(owner="100:1", lease_seconds=10, now=t0)
    second = ifr.claim_due_recovery(
        owner="200:2", lease_seconds=10, now=t0 + timedelta(seconds=11)
    )

    assert first is not None and first["recovery_generation"] == 1
    assert second is not None and second["recovery_generation"] == 2
    with pytest.raises(ifr.StaleRecoveryClaim):
        ifr.settle_terminal(
            "r1",
            status="completed",
            expected_generation=1,
            expected_owner="100:1",
        )


def test_release_claim_preserves_recovery_and_applies_backoff(_isolated_records):
    t0 = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)
    ifr.mark_started(run_id="r1", session_id="s1", user_message="fix it")
    ifr.settle_recovering("r1", reason="shutdown")
    claim = ifr.claim_due_recovery(owner="100:1", now=t0)
    assert claim is not None

    assert ifr.release_recovery_claim(
        "r1",
        claim["recovery_generation"],
        owner="100:1",
        reason="spawn-failed",
        retry_after_s=30,
        now=t0,
    )
    rec = ifr._load()["r1"]
    assert rec["status"] == "recovering"
    assert rec["exit_reason"] == "spawn-failed"
    assert datetime.fromisoformat(rec["next_attempt_at"]) == t0 + timedelta(seconds=30)


def test_explicit_terminal_state_is_not_claimable(_isolated_records):
    ifr.mark_started(run_id="r1", session_id="s1", user_message="fix it")
    rec = ifr.settle_terminal("r1", status="cancelled", reason="user-cancelled")

    assert rec is not None and rec["status"] == "cancelled"
    assert ifr.claim_due_recovery(owner="200:2") is None


def test_renew_rejects_wrong_owner_or_generation(_isolated_records):
    ifr.mark_started(run_id="r1", session_id="s1", user_message="fix it")
    ifr.settle_recovering("r1", reason="shutdown")
    claim = ifr.claim_due_recovery(owner="100:1")
    assert claim is not None

    assert not ifr.renew_recovery_lease("r1", 99, owner="100:1")
    assert not ifr.renew_recovery_lease(
        "r1", claim["recovery_generation"], owner="200:2"
    )
    assert ifr.renew_recovery_lease(
        "r1", claim["recovery_generation"], owner="100:1"
    )
