"""Tests for R2.5-blocking-gatens konfigurerbare tærskler (2026-06-22).

Tærsklerne (heed_rate + tier-unverified-lofter) er gjort settings-backed så de kan
justeres uden kode-deploy. Modul-konstanterne er fallback hvis settings ikke kan læses.
"""
from __future__ import annotations

from unittest.mock import patch

from core.services import r2_5_blocking_gate as gate


def test_live_thresholds_reads_settings():
    class _S:
        r2_5_unverified_threshold_deep = 2
        r2_5_unverified_threshold_reasoning = 4
        r2_5_unverified_threshold_fast = 9
        r2_5_heed_rate_threshold = 0.55
        r2_5_activity_ceiling = 6

    with patch("core.runtime.settings.load_settings", return_value=_S()):
        tiers, heed, ceiling = gate._live_thresholds()
    assert tiers == {"deep": 2, "reasoning": 4, "fast": 9}
    assert heed == 0.55
    assert ceiling == 6


def test_live_thresholds_falls_back_to_module_constants():
    with patch("core.runtime.settings.load_settings", side_effect=RuntimeError("no cfg")):
        tiers, heed, ceiling = gate._live_thresholds()
    # fallback = modul-konstanterne
    assert tiers == gate._UNVERIFIED_THRESHOLD_BY_TIER
    assert heed == gate._HEED_RATE_THRESHOLD
    assert ceiling == gate._ACTIVITY_CEILING


def test_default_thresholds_match_documented_baseline():
    # baseline pr. 2026-06-22 (Phase 1 retune): deep 3 / reasoning 5 / fast 8, heed 0.4
    tiers, heed, ceiling = gate._live_thresholds()
    assert tiers["deep"] <= tiers["reasoning"] <= tiers["fast"]
    assert 0.0 < heed < 1.0
    # Loftet må aldrig ligge under deep-tærsklen, ellers ville det løsne den
    assert ceiling >= tiers["deep"]


def test_block_path_emits_central_trace_and_returns_block():
    """Proactivity-cluster trace (2026-06-22): når R2.5 faktisk soft-blokerer, skal
    den returnere en block-dict OG emittere central observe (best-effort) uden at kaste."""
    from unittest.mock import patch
    gate._last_block_at = None  # nulstil cooldown
    fake_gate = {"failed_verify_count": 2, "unverified_effective": 99,
                 "suggestions": ["read_file X"]}
    with patch("core.services.verification_gate.evaluate_verification_gate",
               return_value=fake_gate), \
         patch.object(gate, "_heed_rate_24h", return_value=0.05):
        out = gate.should_block_for_verification(reasoning_tier="fast")
    assert out is not None and "reason" in out
    assert out["tier"] == "fast"


# ── Observabilitet: et "nej" skal også efterlade et spor (19. sep 2026) ─────
# Målt: `r2_5_gate.blocked` havde 0 forekomster over 738.510 events. Et 0-tal
# kan ikke skelnes fra "gaten kiggede og sagde nej" — så vi kunne ikke afgøre
# om gaten overhovedet blev kørt i drift. Nu publiceres HVER evaluering.

def _capture(monkeypatch) -> list:
    import core.eventbus.bus as busmod
    seen: list = []
    monkeypatch.setattr(
        busmod, "event_bus",
        type("B", (), {"publish": staticmethod(lambda kind, payload=None, **kw: seen.append((kind, payload)))})(),
    )
    return seen


def test_nej_under_taerskel_efterlader_spor(monkeypatch):
    """Tærskel ikke nået → intet block, MEN en 'evaluated' med grunden."""
    seen = _capture(monkeypatch)
    gate._last_block_at = None
    fake = {"failed_verify_count": 0, "unverified_effective": 4, "suggestions": []}
    with patch("core.services.verification_gate.evaluate_verification_gate", return_value=fake):
        assert gate.should_block_for_verification(reasoning_tier="fast") is None
    kinds = [k for k, _ in seen]
    assert "r2_5_gate.evaluated" in kinds
    ev = next(p for k, p in seen if k == "r2_5_gate.evaluated")
    assert ev["blocked"] is False
    assert ev["unverified_effective"] == 4
    tiers, _heed, ceiling = gate._live_thresholds()
    assert ev["threshold"] == min(tiers["fast"], ceiling)
    assert "under tærskel" in ev["reason"]


# ── Aktivitets-loftet (19. sep 2026) ────────────────────────────────────────
# Målt over 500 surfaces: deep-tærsklen ville fyre i 51% af tilfældene og
# reasoning i 27% — men den tærskel der faktisk blev brugt var 'fast' (9%),
# fordi klassifikatoren læser BESKEDEN og korte beskeder ("1->2->3", "tag den
# nu") giver nul point. Gaten beskyttede altså det tungeste arbejde med den
# mest eftergivende tærskel. En høj mutationsbyrde ER dybt arbejde.

def test_hoej_byrde_blokerer_ogsaa_naar_beskeden_var_kort():
    """Byrde over loftet → blokér selvom tier er 'fast' (før: nej, tærskel 8)."""
    gate._last_block_at = None
    fake = {"failed_verify_count": 0, "unverified_effective": 6, "suggestions": []}
    with patch("core.services.verification_gate.evaluate_verification_gate", return_value=fake), \
         patch.object(gate, "_heed_rate_24h", return_value=0.05):
        assert gate.should_block_for_verification(reasoning_tier="fast") is not None


def test_loftet_loesner_aldrig_deep():
    """Deep beholder sin stramme tærskel — loftet kan kun stramme."""
    gate._last_block_at = None
    fake = {"failed_verify_count": 0, "unverified_effective": 3, "suggestions": []}
    with patch("core.services.verification_gate.evaluate_verification_gate", return_value=fake), \
         patch.object(gate, "_heed_rate_24h", return_value=0.05):
        assert gate.should_block_for_verification(reasoning_tier="deep") is not None


def test_loftet_kan_saettes_ud_af_spil_via_settings():
    """Sættes loftet over fast-tærsklen, gælder den gamle adfærd igen."""
    class _S:
        r2_5_unverified_threshold_deep = 3
        r2_5_unverified_threshold_reasoning = 5
        r2_5_unverified_threshold_fast = 8
        r2_5_heed_rate_threshold = 0.4
        r2_5_activity_ceiling = 99

    gate._last_block_at = None
    fake = {"failed_verify_count": 0, "unverified_effective": 6, "suggestions": []}
    with patch("core.runtime.settings.load_settings", return_value=_S()), \
         patch("core.services.verification_gate.evaluate_verification_gate", return_value=fake), \
         patch.object(gate, "_heed_rate_24h", return_value=0.05):
        assert gate.should_block_for_verification(reasoning_tier="fast") is None


def test_blok_efterlader_baade_evaluated_og_blocked(monkeypatch):
    """Tærskel nået + lav heed → både 'evaluated' (blocked=True) og 'blocked'."""
    seen = _capture(monkeypatch)
    gate._last_block_at = None
    fake = {"failed_verify_count": 0, "unverified_effective": 99, "suggestions": []}
    with patch("core.services.verification_gate.evaluate_verification_gate", return_value=fake), \
         patch.object(gate, "_heed_rate_24h", return_value=0.05):
        b = gate.should_block_for_verification(reasoning_tier="fast")
    assert b is not None
    kinds = [k for k, _ in seen]
    assert "r2_5_gate.evaluated" in kinds and "r2_5_gate.blocked" in kinds
    ev = next(p for k, p in seen if k == "r2_5_gate.evaluated")
    assert ev["blocked"] is True


def test_hoej_heed_rate_efterlader_spor_med_grund(monkeypatch):
    """Mutations-tærskel nået, men heed-raten er fin → nej, med den grund."""
    seen = _capture(monkeypatch)
    gate._last_block_at = None
    fake = {"failed_verify_count": 0, "unverified_effective": 99, "suggestions": []}
    with patch("core.services.verification_gate.evaluate_verification_gate", return_value=fake), \
         patch.object(gate, "_heed_rate_24h", return_value=0.9):
        assert gate.should_block_for_verification(reasoning_tier="fast") is None
    ev = next(p for k, p in seen if k == "r2_5_gate.evaluated")
    assert ev["blocked"] is False
    assert "heed_rate ok" in ev["reason"]


# ── Tavse fallbacks skal efterlade et spor (31/10-2026) ──────────────────
#
# MAALT 31/10-2026: tre `except` i gaten faldt tilbage uden et ord.
# `_live_thresholds` faldt til modul-konstanterne, `_heed_rate_24h` til
# `None` (= «ikke nok data»), og `should_block_for_verification` til «bloker
# ikke». Den sidste havde et spor i event-bussen — men det forsvinder hvis
# bussen selv er nede.
#
# Vagterne beviser BEGGE ting: at fejlen logger, OG at returvaerdien er
# praecis den fallback kalderne forventer. En rettelse der kastede videre
# ville bestaa den foerste halvdel alene.


def test_live_thresholds_logger_naar_settings_fejler(caplog):
    import logging

    with caplog.at_level(logging.WARNING, logger="core.services.r2_5_blocking_gate"):
        with patch("core.runtime.settings.load_settings", side_effect=RuntimeError("no cfg")):
            tiers, heed, ceiling = gate._live_thresholds()
    # fallback uaendret
    assert tiers == gate._UNVERIFIED_THRESHOLD_BY_TIER
    assert heed == gate._HEED_RATE_THRESHOLD
    assert ceiling == gate._ACTIVITY_CEILING
    assert any(
        "kunne ikke laese taerskler fra settings" in r.getMessage()
        for r in caplog.records
    ), "en settings-fejl efterlod intet spor"


def test_heed_rate_logger_naar_telemetri_fejler(caplog):
    """`None` betyder «ikke nok data» — en fejl maa ikke se ens ud med det."""
    import logging

    with caplog.at_level(logging.WARNING, logger="core.services.r2_5_blocking_gate"):
        with patch(
            "core.services.verification_gate_telemetry.get_telemetry_summary",
            side_effect=RuntimeError("telemetry nede"),
        ):
            assert gate._heed_rate_24h() is None
    assert any(
        "kunne ikke laese heed-rate-telemetri" in r.getMessage()
        for r in caplog.records
    )


def test_gate_fejl_logger_men_blokerer_ikke(monkeypatch, caplog):
    """Fail-open er bevidst — men fejlen skal kunne ses i loggen."""
    import logging

    monkeypatch.setattr(gate, "_last_block_at", None)
    with caplog.at_level(logging.WARNING, logger="core.services.r2_5_blocking_gate"):
        with patch(
            "core.services.verification_gate.evaluate_verification_gate",
            side_effect=RuntimeError("gate nede"),
        ):
            out = gate.should_block_for_verification(reasoning_tier="deep")
    assert out is None, "fail-open skal bevares"
    assert any(
        "verification_gate kastede" in r.getMessage() for r in caplog.records
    )


def test_sund_vej_stoejer_ikke(caplog):
    """En laesbar settings-fil er normal drift — den maa ikke logge."""
    import logging

    class _S:
        r2_5_unverified_threshold_deep = 2
        r2_5_unverified_threshold_reasoning = 4
        r2_5_unverified_threshold_fast = 9
        r2_5_heed_rate_threshold = 0.55
        r2_5_activity_ceiling = 6

    with caplog.at_level(logging.WARNING, logger="core.services.r2_5_blocking_gate"):
        with patch("core.runtime.settings.load_settings", return_value=_S()):
            gate._live_thresholds()
    assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []
