"""Rigdoms-gate: cached injektion må ikke være fladere end den direkte build."""
from __future__ import annotations
from scripts.injection_richness_check import richness_ok


def test_richness_ok_equal_or_richer():
    assert richness_ok(direct="linje a\nlinje b", cached="linje a\nlinje b\nlinje c") is True
    assert richness_ok(direct="linje a\nlinje b", cached="linje a\nlinje b") is True


def test_richness_flags_flatter():
    assert richness_ok(direct="a\nb\nc\nd\ne", cached="a") is False


def test_richness_empty_direct_is_ok():
    assert richness_ok(direct="", cached="") is True
