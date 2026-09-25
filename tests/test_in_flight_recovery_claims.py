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


def test_failed_last_attempt_is_terminal_not_endless_recovering(_isolated_records):
    ifr.mark_started(run_id="r-last", session_id="s1", user_message="fix it",
                     recovery_limit=1)
    ifr.settle_recovering("r-last", reason="shutdown", recovery_limit=1)
    claim = ifr.claim_due_recovery(owner="100:1")
    assert claim is not None
    assert ifr.release_recovery_claim(
        "r-last", claim["recovery_generation"], owner="100:1",
        reason="budget-opbrugt", retry_after_s=30,
    )
    rec = ifr.get_record("r-last")
    assert rec is not None and rec["status"] == "failed_terminal"
    assert ifr.claim_due_recovery(owner="200:2") is None


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


def test_udskydelse_efterlader_ingen_ny_generation(_isolated_records):
    """En udskydelse er et OPSLAG, ikke et forsøg — den må ikke ændre identiteten.

    Målt 25/9-2026 i journalen: `visible-d9ab73c5` stod med
    ``recovery_generation=10``, ``recovery_attempt=1`` og 9 udskydelser — altså
    10 = 1 forsøg + 9 opslag. Generationen talte hvert opslag med, mens
    ``release_recovery_claim(attempted=False)`` kun rullede forsøgstælleren
    tilbage. Her måles invarianten direkte: efter et rent opslag står begge
    tal hvor de stod.
    """
    t0 = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)
    ifr.mark_started(run_id="r1", session_id="s1", user_message="fix it")
    ifr.settle_recovering("r1", reason="shutdown")

    claim = ifr.claim_due_recovery(owner="100:1", now=t0)
    assert claim is not None and claim["recovery_generation"] == 1
    assert ifr.release_recovery_claim(
        "r1",
        claim["recovery_generation"],
        owner="100:1",
        reason="samtalen har et levende run",
        retry_after_s=30,
        attempted=False,
        now=t0,
    )

    rec = ifr._load()["r1"]
    assert rec["recovery_generation"] == 0, "et opslag må ikke efterlade en generation"
    assert rec["recovery_attempt"] == 0, "et opslag må ikke efterlade et forsøg"
    assert rec["recovery_deferrals"] == 1, "udskydelsen skal stadig bogføres"
    assert rec["status"] == "recovering"
    assert datetime.fromisoformat(rec["next_attempt_at"]) == t0 + timedelta(seconds=30)


def test_koersel_startet_foer_en_udskydelse_kan_stadig_afregne(_isolated_records):
    """Selve loopet: en startet genoptagelse må ikke gøres uafregnelig af et opslag.

    Rækkefølgen er den målte: kørslen starter med generation G, dens lejemål
    udløber mens den stadig lever (den fornyer det ikke), dispatcheren tager et
    NYT krav for at kunne se samtalen og opdager at den er optaget. Uden
    tilbagerulningen stod generationen nu på G+1 og ejerskabet var ryddet — så
    `settle_terminal` kastede StaleRecoveryClaim, `_afregn_genoptaget_run`
    slugte den, og opgaven blev aldrig lukket.
    """
    t0 = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)
    ifr.mark_started(run_id="r1", session_id="s1", user_message="fix it")
    ifr.settle_recovering("r1", reason="shutdown")

    # Første krav bliver til en ÆGTE start: kørslen bærer generation 1 og ejer 100:1.
    start = ifr.claim_due_recovery(owner="100:1", lease_seconds=10, now=t0)
    assert start is not None and start["recovery_generation"] == 1

    # Lejemålet udløber mens kørslen lever. Nyt krav — men samtalen er optaget.
    opslag = ifr.claim_due_recovery(
        owner="100:1", lease_seconds=10, now=t0 + timedelta(seconds=11)
    )
    assert opslag is not None and opslag["recovery_generation"] == 2
    assert ifr.release_recovery_claim(
        "r1",
        opslag["recovery_generation"],
        owner="100:1",
        reason="samtalen har et levende run",
        retry_after_s=30,
        attempted=False,
        now=t0 + timedelta(seconds=11),
    )

    # Den kørende tur afregner med den generation OG den ejer den blev startet med.
    rec = ifr.settle_terminal(
        "r1",
        status="completed",
        reason="recovery-run-terminal",
        expected_generation=1,
        expected_owner="100:1",
    )
    assert rec is not None, "opgaven kunne ikke lukkes — loopet er tilbage"
    assert rec["status"] == "completed"
