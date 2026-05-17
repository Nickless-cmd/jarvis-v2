"""TDD: Red → Green → Refactor for accumulate_bias.

Phase: RED — testen skal fejle først.
"""

import pytest

from core.services.dream_bias_engine import accumulate_bias

# Faktiske keys fra ATTENTION_VOCAB og THRESHOLD_VOCAB
ATTN = "unfinished_business"
THR = "friction_tolerance"


def test_empty_prior_with_new_value():
    """Baseline: tom prior + en valid key = kun den key i output."""
    result = accumulate_bias({}, {ATTN: 0.5}, intensity=1.0)
    assert ATTN in result
    assert result[ATTN] == 0.5


def test_clamping_at_positive_one():
    """Clamping: værdi over 1.0 skal låses til 1.0."""
    result = accumulate_bias({}, {ATTN: 2.0}, intensity=1.0)
    assert result[ATTN] == 1.0


def test_clamping_at_negative_one():
    """Clamping: værdi under -1.0 skal låses til -1.0."""
    result = accumulate_bias({}, {ATTN: -2.0}, intensity=1.0)
    assert result[ATTN] == -1.0


def test_intensity_scales_contribution():
    """Intensity: 0.5 * 0.8 = 0.4 contribution."""
    result = accumulate_bias({}, {ATTN: 0.8}, intensity=0.5)
    assert result[ATTN] == pytest.approx(0.4)


def test_accumulation_onto_prior():
    """Prior + ny bidrag = summeret."""
    result = accumulate_bias({ATTN: 0.3}, {ATTN: 0.2}, intensity=1.0)
    assert result[ATTN] == 0.5


def test_unknown_keys_are_dropped():
    """Keys uden for vocab skal ignoreres."""
    result = accumulate_bias({}, {"nonexistent_key": 1.0}, intensity=1.0)
    assert "nonexistent_key" not in result


def test_valid_keys_survive_prior_filtering():
    """Prior keys uden for vocab skal filtreres fra."""
    result = accumulate_bias(
        {ATTN: 0.5, "stale_old_key": 0.9},
        {THR: 0.3},
        intensity=1.0,
    )
    assert ATTN in result
    assert THR in result
    assert "stale_old_key" not in result


def test_accumulation_with_clamping():
    """Prior 0.8 + contribution 0.4 = 1.2 → clampet til 1.0."""
    result = accumulate_bias({ATTN: 0.8}, {ATTN: 0.4}, intensity=1.0)
    assert result[ATTN] == 1.0
