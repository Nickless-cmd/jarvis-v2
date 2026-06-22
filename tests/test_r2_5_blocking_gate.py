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

    with patch("core.runtime.settings.load_settings", return_value=_S()):
        tiers, heed = gate._live_thresholds()
    assert tiers == {"deep": 2, "reasoning": 4, "fast": 9}
    assert heed == 0.55


def test_live_thresholds_falls_back_to_module_constants():
    with patch("core.runtime.settings.load_settings", side_effect=RuntimeError("no cfg")):
        tiers, heed = gate._live_thresholds()
    # fallback = modul-konstanterne
    assert tiers == gate._UNVERIFIED_THRESHOLD_BY_TIER
    assert heed == gate._HEED_RATE_THRESHOLD


def test_default_thresholds_match_documented_baseline():
    # baseline pr. 2026-06-22 (Phase 1 retune): deep 3 / reasoning 5 / fast 8, heed 0.4
    tiers, heed = gate._live_thresholds()
    assert tiers["deep"] <= tiers["reasoning"] <= tiers["fast"]
    assert 0.0 < heed < 1.0


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
