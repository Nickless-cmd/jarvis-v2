"""Tests for scripts/interlanguage_drift_classifier — pre-registered method."""

import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


def test_imports():
    import interlanguage_drift_classifier as m
    assert m.CHUNK_SIZE == 15
    assert m.DRIFT_HALF == 5
    assert len(m.OPS) == 5
    assert len(m.VOCAB) == 14
    assert m.RANDOM_SEED == 42


def test_snapshot_featurize_dims():
    """Featurize_snapshot must produce 19-dim vector (5 ops + 14 vocab)."""
    import interlanguage_drift_classifier as m
    sample = ["fokus → ro | agens ↔ signal | drøm ⊂ lys"] * 3
    vec = m.featurize_snapshot(sample)
    assert vec.shape == (19,)
    # Frequencies should sum (ops alone or vocab alone) — at least one positive
    assert vec[:5].sum() > 0  # operator section
    assert vec[5:].sum() > 0  # vocab section


def test_chunk_featurize_returns_two_19dim():
    import interlanguage_drift_classifier as m
    chunk = [
        "fokus → ro | agens ↔ signal | drøm ⊂ lys",
    ] * m.CHUNK_SIZE
    snap, drift = m.featurize_chunk(chunk)
    assert snap.shape == (19,)
    assert drift.shape == (19,)
    # Drift on identical chunk should be ~0
    assert np.allclose(drift, 0, atol=1e-9)


def test_drift_nonzero_when_chunk_changes():
    """Drift should reflect early-vs-late difference."""
    import interlanguage_drift_classifier as m
    # Early half: only → operator. Late half: only ↔.
    early = ["fokus → ro"] * m.DRIFT_HALF
    middle = ["fokus → ro"] * (m.CHUNK_SIZE - 2 * m.DRIFT_HALF)
    late = ["fokus ↔ ro"] * m.DRIFT_HALF
    chunk = early + middle + late
    snap, drift = m.featurize_chunk(chunk)
    # Drift on → should be negative (less in late), ↔ should be positive
    assert drift[0] < 0  # → freq decreased
    assert drift[1] > 0  # ↔ freq increased


def test_phase_end_date_locked():
    """Critical: phase-end gate must point to 2026-05-28 22:16 UTC (locked)."""
    from datetime import datetime, UTC
    import interlanguage_drift_classifier as m
    assert m.PHASE_END_UTC == datetime(2026, 5, 28, 22, 16, tzinfo=UTC)
