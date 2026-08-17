"""Agentic-round watchdog — må ikke henrette et run fordi VI selv var blokeret.

Rod (Bjørn 17. aug 2026): desk pollede 515 req/min → API-loopet hakkede
(loop_lag_peak 347ms) → det detached runs frames blev ikke læst i 180s → den rene
stopur-watchdog kaldte det "provider-silence" → runet blev kasseret midt-flugt
(vis_len=0), 13 gange. Tavshed under selv-forskyldt sult er IKKE bevis på en død
provider. Se reference_cutoff_rootcause_pollstorm.
"""
from __future__ import annotations

from core.services.visible_runs_watchdog import (
    STARVATION_LAG_MS,
    agentic_watchdog_timeout_reason,
    effective_silence_budget_s,
)


def _reason(*, silent_s: float, total_s: float = 10.0, lag_ms: float = 0.0,
            max_silence_s: float = 180.0, max_total_s: float = 300.0):
    now = 1000.0
    return agentic_watchdog_timeout_reason(
        started_at=now - total_s,
        last_progress_at=now - silent_s,
        now=now,
        max_total_s=max_total_s,
        max_silence_s=max_silence_s,
        loop_lag_peak_ms=lag_ms,
    )


class TestNormalDrift:
    def test_ingen_timeout_indenfor_budget(self):
        assert _reason(silent_s=10.0) is None

    def test_silence_timeout_naar_loopet_er_sundt(self):
        # Sundt loop (lag ~0) + 181s tavshed → ægte provider-stall
        assert _reason(silent_s=181.0) == "provider-silence-timeout"

    def test_total_timeout_er_haard_loft(self):
        assert _reason(silent_s=1.0, total_s=301.0) == "provider-round-timeout"


class TestStarvationGrace:
    def test_hoej_loop_lag_giver_naade_i_stedet_for_henrettelse(self):
        """Samme tavshed, men VORES loop var blokeret → ingen timeout."""
        assert _reason(silent_s=181.0, lag_ms=347.7) is None

    def test_naaden_er_begraenset_ikke_uendelig(self):
        """Selv med sult opgives runden til sidst (dobbelt budget)."""
        assert _reason(silent_s=400.0, lag_ms=347.7, max_total_s=100_000) == (
            "provider-silence-timeout"
        )

    def test_lavt_lag_giver_ingen_naade(self):
        """Under tærsklen er loopet sundt → tavshed tæller fuldt."""
        assert _reason(silent_s=181.0, lag_ms=STARVATION_LAG_MS - 1) == (
            "provider-silence-timeout"
        )

    def test_total_loft_gaelder_stadig_under_sult(self):
        """Sult må ALDRIG omgå det totale rundeloft (ingen evige runder)."""
        assert _reason(silent_s=181.0, total_s=301.0, lag_ms=999.0) == (
            "provider-round-timeout"
        )


class TestBudgetHelper:
    def test_budget_uaendret_ved_sundt_loop(self):
        assert effective_silence_budget_s(180.0, 0.0) == 180.0

    def test_budget_udvides_ved_sult(self):
        assert effective_silence_budget_s(180.0, 500.0) > 180.0

    def test_deaktiveret_budget_forbliver_deaktiveret(self):
        """max_silence_s <= 0 = slået fra; sult må ikke genoplive den."""
        assert effective_silence_budget_s(0.0, 999.0) == 0.0
        assert _reason(silent_s=9999.0, lag_ms=999.0, max_silence_s=0.0,
                       max_total_s=100_000) is None
