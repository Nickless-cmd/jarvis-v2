"""Tests for core/services/central_noise_filter.py — støjfangeren."""
from __future__ import annotations

import pytest

from core.services import central_noise_filter as nf


@pytest.fixture(autouse=True)
def _clean():
    nf._reset_for_tests()
    yield
    nf._reset_for_tests()


def test_single_blip_is_not_a_signal():
    # ét enkelt udslag = støj, slippes ikke igennem (kræver persistens)
    assert nf.is_real_signal("k", True, min_persistence=2, now_monotonic=100.0) is False


def test_persistent_breach_becomes_signal():
    assert nf.is_real_signal("k", True, min_persistence=2, now_monotonic=100.0) is False
    assert nf.is_real_signal("k", True, min_persistence=2, now_monotonic=101.0) is True


def test_non_breach_resets_persistence():
    nf.is_real_signal("k", True, min_persistence=2, now_monotonic=100.0)   # 1
    nf.is_real_signal("k", False, min_persistence=2, now_monotonic=101.0)  # reset
    # tælleren er nulstillet → næste breach er igen kun 1/2
    assert nf.is_real_signal("k", True, min_persistence=2, now_monotonic=102.0) is False


def test_cooldown_dedup_suppresses_repeats():
    nf.is_real_signal("k", True, min_persistence=1, cooldown_s=1000.0, now_monotonic=0.0)  # flag
    # vedvarende tilstand inden for cooldown → ingen gentaget signal
    assert nf.is_real_signal("k", True, min_persistence=1, cooldown_s=1000.0, now_monotonic=500.0) is False
    # efter cooldown → nyt signal
    assert nf.is_real_signal("k", True, min_persistence=1, cooldown_s=1000.0, now_monotonic=1001.0) is True


def test_independent_keys():
    assert nf.is_real_signal("a", True, min_persistence=1, now_monotonic=0.0) is True
    # anden nøgle har egen tilstand
    assert nf.is_real_signal("b", True, min_persistence=2, now_monotonic=0.0) is False


def test_peek_and_never_raises():
    nf.is_real_signal("k", True, min_persistence=1, now_monotonic=0.0)
    p = nf.peek("k")
    assert p["key"] == "k"
    assert p["flagged"] is True
    # dårlig input må ikke kaste
    assert nf.is_real_signal("k", None) in (True, False)  # type: ignore[arg-type]
