"""Output-conservation-invariant: produced == emitted, ellers nerve-gap."""
from __future__ import annotations

from core.services import central_output_conservation as C


def test_no_gap_when_equal():
    assert C.observe_conservation(layer="test", produced_chars=100, emitted_chars=100) == 0


def test_gap_when_produced_exceeds_emitted():
    # 100 produceret, 80 udsendt → 20 tabt
    gap = C.observe_conservation(layer="test", produced_chars=100, emitted_chars=80)
    assert gap == 20


def test_tolerance_suppresses_small_gap():
    # gap 5 <= tolerance 10 → intet gap rapporteret (returnerer faktisk gap men fyrer ikke)
    gap = C.observe_conservation(layer="test", produced_chars=105, emitted_chars=100, tolerance=10)
    assert gap == 5


def test_self_safe_on_garbage():
    assert C.observe_conservation(layer="x", produced_chars=0, emitted_chars=0) == 0
