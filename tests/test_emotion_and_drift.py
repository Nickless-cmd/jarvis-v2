"""Unit tests for emotion_tagging + personality_drift."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from core.services.emotion_tagging import current_emotion_tag, format_emotion_tag
from core.services.personality_drift import (
    take_snapshot,
    compute_baseline,
    detect_drift,
    personality_drift_section,
)


def test_emotion_tag_with_no_mood_returns_empty_mood():
    with patch("core.services.mood_oscillator.get_current_mood", return_value=""), \
         patch("core.services.mood_oscillator.get_mood_intensity", return_value=0.0):
        tag = current_emotion_tag()
    assert tag["mood"] == {}
    assert tag["dominant_affect"] == ""


def test_emotion_tag_picks_dominant_affect():
    with patch("core.services.mood_oscillator.get_current_mood", return_value="curiosity"), \
         patch("core.services.mood_oscillator.get_mood_intensity", return_value=0.8):
        tag = current_emotion_tag()
    assert tag["dominant_affect"] == "curiosity"


def test_emotion_tag_no_dominant_when_below_threshold():
    with patch("core.services.mood_oscillator.get_current_mood", return_value="curiosity"), \
         patch("core.services.mood_oscillator.get_mood_intensity", return_value=0.3):
        tag = current_emotion_tag()
    assert tag["dominant_affect"] == ""


def test_format_emotion_tag_compact():
    tag = {
        "mood": {"curiosity": 0.7, "fatigue": 0.2, "confidence": 0.5},
        "dominant_affect": "curiosity",
        "temperature_field": "restless",
    }
    out = format_emotion_tag(tag)
    assert "curiosity" in out
    assert "restless" in out


def test_format_emotion_tag_empty_returns_empty():
    assert format_emotion_tag({}) == ""
    assert format_emotion_tag({"mood": {}}) == ""


def _fake_snapshot(mood, days_ago=0):
    ts = (datetime.now(UTC) - timedelta(days=days_ago)).isoformat()
    return {"ts": ts, "mood": mood}


def test_compute_baseline_returns_empty_with_no_data():
    with patch("core.services.personality_drift._load_snapshots", return_value=[]):
        assert compute_baseline() == {}


def test_compute_baseline_calculates_mean_stddev():
    snapshots = [_fake_snapshot({"curiosity": v}) for v in [0.5, 0.6, 0.7, 0.8, 0.9]]
    with patch("core.services.personality_drift._load_snapshots", return_value=snapshots):
        baseline = compute_baseline()
    assert "curiosity" in baseline
    assert abs(baseline["curiosity"]["mean"] - 0.7) < 0.01
    assert baseline["curiosity"]["n"] == 5


def test_drift_returns_no_drift_with_few_samples():
    snapshots = [_fake_snapshot({"curiosity": 0.5}) for _ in range(5)]
    with patch("core.services.personality_drift._load_snapshots", return_value=snapshots):
        result = detect_drift()
    assert result["drift_detected"] is False


def test_drift_detected_when_recent_shifts():
    # 30 baseline snapshots at curiosity=0.3 (very stable)
    baseline = [_fake_snapshot({"curiosity": 0.30 + i*0.01}) for i in range(30)]  # mean ~0.45, std ~0.087
    # Recent 10 snapshots all at curiosity=0.9 (way above)
    recent = [_fake_snapshot({"curiosity": 0.9}) for _ in range(10)]
    snapshots = baseline + recent
    with patch("core.services.personality_drift._load_snapshots", return_value=snapshots):
        result = detect_drift()
    assert result["drift_detected"] is True
    assert any(d["direction"] == "up" for d in result["drifts"])


def test_section_returns_none_when_no_drift():
    with patch("core.services.personality_drift.detect_drift",
               return_value={"drift_detected": False, "drifts": []}):
        assert personality_drift_section() is None


def test_section_lists_drifts_when_present():
    with patch("core.services.personality_drift.detect_drift", return_value={
        "drift_detected": True,
        "drifts": [
            {"dimension": "curiosity", "recent_mean": 0.9, "baseline_mean": 0.4,
             "baseline_stdev": 0.1, "z_score": 5.0, "direction": "up"},
        ],
    }):
        section = personality_drift_section()
    assert section is not None
    assert "curiosity" in section
    assert "↑" in section
