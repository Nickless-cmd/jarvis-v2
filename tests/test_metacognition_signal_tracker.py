"""Tests for metacognition_signal_tracker (Step E.v1).

Two signals scored on response text:
  1. contradiction_within_response — pairs sharing nouns + opposite
     polarity, or matching nouns + differing numbers.
  2. claim_density — fraction of sentences carrying a factual claim.
     Healthy band 0.3–0.7.
"""
import json
import sqlite3
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_db(monkeypatch):
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    path = Path(tmp.name)
    import core.services.metacognition_signal_tracker as mod
    monkeypatch.setattr(mod, "DB_PATH", path)
    yield path
    path.unlink(missing_ok=True)


# ── score_contradiction ──────────────────────────────────────────────────


def test_polarity_contradiction_detected():
    from core.services.metacognition_signal_tracker import score_contradiction
    text = (
        "DeepSeek flash modellen kører hurtigt på prompts. "
        "Faktisk kører DeepSeek flash modellen ikke hurtigt overhovedet."
    )
    result = score_contradiction(text)
    assert result["score"] > 0.0
    assert any(p["kind"] == "polarity" for p in result["pairs"])


def test_numeric_contradiction_detected():
    from core.services.metacognition_signal_tracker import score_contradiction
    text = (
        "Cache hit ratio er 38 procent på flash modellen. "
        "Cache hit ratio er 99 procent på flash modellen."
    )
    result = score_contradiction(text)
    assert result["score"] > 0.0
    assert any(p["kind"] == "numeric" for p in result["pairs"])


def test_no_contradiction_returns_zero():
    from core.services.metacognition_signal_tracker import score_contradiction
    text = (
        "Vejret er fint i dag. Solen skinner over byen. "
        "Jeg drikker kaffe ved skrivebordet."
    )
    result = score_contradiction(text)
    assert result["score"] == 0.0
    assert result["pairs"] == []


def test_score_capped_at_one():
    """3+ contradiction pairs should saturate at 1.0."""
    from core.services.metacognition_signal_tracker import score_contradiction
    text = (
        "Cache er 30 procent. Cache er ikke 30 procent. "
        "Modellen kører hurtigt. Modellen kører ikke hurtigt. "
        "Systemet virker. Systemet virker ikke. "
        "Testen passerer altid. Testen passerer aldrig."
    )
    result = score_contradiction(text)
    assert result["score"] == 1.0


# ── score_claim_density ──────────────────────────────────────────────────


def test_high_density_factual_text():
    from core.services.metacognition_signal_tracker import score_claim_density
    text = (
        "Cache hit er 38 procent. Modellen kører på port 8011. "
        "Database er på 1 GB. Runtime starter ved boot."
    )
    result = score_claim_density(text)
    assert result["score"] >= 0.7  # most sentences have claims


def test_low_density_chatty_text():
    from core.services.metacognition_signal_tracker import score_claim_density
    text = (
        "Hmm, det tænker jeg over. Måske, måske ikke. "
        "Jeg ved ikke helt. Det føles uklart. "
        "Vi ser hvad der sker. Tja."
    )
    result = score_claim_density(text)
    assert result["score"] < 0.5


def test_empty_text_zero_density():
    from core.services.metacognition_signal_tracker import score_claim_density
    result = score_claim_density("")
    assert result["score"] == 0.0
    assert result["n_sentences"] == 0


def test_healthy_band_flag():
    from core.services.metacognition_signal_tracker import score_claim_density
    # Construct text squarely in the healthy band
    text = (
        "DeepSeek er en model. Solen skinner i dag. "
        "Database har 1 GB data. Kaffe er godt."
    )
    result = score_claim_density(text)
    assert "in_healthy_band" in result


# ── record_signals (DB persistence) ──────────────────────────────────────


def test_record_signals_persists_both_dimensions(tmp_db):
    from core.services.metacognition_signal_tracker import record_signals
    record_signals("run-test-1", "Cache er 38 procent. Modellen virker.")
    with sqlite3.connect(str(tmp_db)) as conn:
        rows = conn.execute(
            "SELECT dimension, score FROM metacognition_signals "
            "WHERE run_id=? ORDER BY dimension",
            ("run-test-1",),
        ).fetchall()
    dims = [r[0] for r in rows]
    assert "claim_density" in dims
    assert "contradiction_within_response" in dims


def test_record_signals_stores_evidence_json(tmp_db):
    from core.services.metacognition_signal_tracker import record_signals
    record_signals("run-test-2", "Modellen virker. Modellen virker ikke.")
    with sqlite3.connect(str(tmp_db)) as conn:
        row = conn.execute(
            "SELECT evidence_json FROM metacognition_signals "
            "WHERE run_id=? AND dimension='contradiction_within_response'",
            ("run-test-2",),
        ).fetchone()
    evidence = json.loads(row[0])
    assert "pairs" in evidence
    assert evidence["score"] > 0.0


# ── latest_signals_section ───────────────────────────────────────────────


def test_quiet_when_no_data(tmp_db):
    from core.services.metacognition_signal_tracker import latest_signals_section
    # No data → no section
    assert latest_signals_section() is None


def test_quiet_when_in_healthy_band(tmp_db):
    """Healthy claim-density runs should not surface a warning."""
    from core.services.metacognition_signal_tracker import (
        record_signals, latest_signals_section,
    )
    for i in range(5):
        record_signals(
            f"run-healthy-{i}",
            "Modellen er hurtig. Vejret er fint. Solen skinner.",
        )
    # contradiction = 0, density mid → no flag
    section = latest_signals_section()
    # Either None or a section that doesn't flag contradiction
    if section is not None:
        assert "contradiction-rate" not in section


def test_surfaces_when_contradiction_high(tmp_db):
    """Multiple runs with high contradiction should surface a flag."""
    from core.services.metacognition_signal_tracker import (
        record_signals, latest_signals_section,
    )
    contradicting = (
        "Cache er 38 procent på flash. Cache er ikke 38 procent på flash. "
        "Modellen kører hurtigt. Modellen kører ikke hurtigt."
    )
    for i in range(5):
        record_signals(f"run-contra-{i}", contradicting)
    section = latest_signals_section()
    assert section is not None
    assert "contradiction-rate" in section
