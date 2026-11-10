"""Tests for continuity capsule mood sync from mood_oscillator."""
import pytest
from unittest.mock import patch
from core.services.continuity import (
    sync_capsule_mood,
    read_capsule,
    write_capsule,
    _EMPTY_CAPSULE,
)


@pytest.fixture
def temp_capsule(tmp_path, monkeypatch):
    """Use a temporary directory for capsule files."""
    monkeypatch.setattr("core.services.continuity.CAPSULE_DIR", tmp_path)
    monkeypatch.setattr("core.services.continuity.CAPSULE_CURRENT", tmp_path / "session_capsule.json")
    monkeypatch.setattr("core.services.continuity.CAPSULE_PREV", tmp_path / "session_capsule.prev.json")
    monkeypatch.setattr("core.services.continuity.CAPSULE_OLDER", tmp_path / "session_capsule.older.json")
    yield tmp_path


def _Snapshot(*, fatigue: float, frustration: float, confidence: float):
    """Stub for emotional_controls.EmotionalSnapshot — kun de tre felter."""
    from types import SimpleNamespace

    return SimpleNamespace(
        fatigue=fatigue,
        frustration=frustration,
        confidence=confidence,
        primary_mood="neutral",
        intensity=0.0,
    )


class TestSyncCapsuleMood:
    def test_sync_updates_bearing(self, temp_capsule):
        """Sync should update bearing from mood_oscillator."""
        with patch("core.services.mood_oscillator.get_current_mood", return_value="content"), \
             patch("core.services.mood_oscillator.get_mood_intensity", return_value=0.48):
            result = sync_capsule_mood()
            assert result is not None
            assert result["bearing"] == "content"

    def test_sync_updates_valence_positive(self, temp_capsule):
        """Content mood should map valence to intensity."""
        with patch("core.services.mood_oscillator.get_current_mood", return_value="content"), \
             patch("core.services.mood_oscillator.get_mood_intensity", return_value=0.7):
            result = sync_capsule_mood()
            assert result["valence"] == pytest.approx(0.7)

    def test_sync_updates_valence_negative(self, temp_capsule):
        """Melancholic mood should map valence inversely."""
        with patch("core.services.mood_oscillator.get_current_mood", return_value="melancholic"), \
             patch("core.services.mood_oscillator.get_mood_intensity", return_value=0.6):
            result = sync_capsule_mood()
            assert result["valence"] == pytest.approx(0.4)

    def test_sync_updates_valence_neutral(self, temp_capsule):
        """Neutral mood should map valence to 0.5."""
        with patch("core.services.mood_oscillator.get_current_mood", return_value="neutral"), \
             patch("core.services.mood_oscillator.get_mood_intensity", return_value=0.3):
            result = sync_capsule_mood()
            assert result["valence"] == pytest.approx(0.5)

    def test_sync_persists_to_disk(self, temp_capsule):
        """Sync should write the updated capsule to disk."""
        with patch("core.services.mood_oscillator.get_current_mood", return_value="content"), \
             patch("core.services.mood_oscillator.get_mood_intensity", return_value=0.5):
            sync_capsule_mood()
            capsule = read_capsule()
            assert capsule is not None
            assert capsule["mood"]["bearing"] == "content"

    def test_sync_overwrites_stale_fatigue_from_live_snapshot(self, temp_capsule):
        """De tre felter skal foelge den LEVENDE maaling, ikke arves.

        Maalt 10/11-2026: filen stod paa fatigue=0.8 / frustration=0.3 /
        confidence=0.5 hele eftermiddagen, mens den levende maaling sagde
        0.0 / 0.0 / 1.0. Aarsagen var at sync kun skrev bearing/valence/
        curiosity, og capture_state derfor arvede de tre felter fremad.
        Denne test fæstner den modsatte egenskab: en foraeldet vaerdi i
        filen maa IKKE overleve en sync.
        """
        capsule = dict(_EMPTY_CAPSULE)
        capsule["mood"]["fatigue"] = 0.8
        capsule["mood"]["frustration"] = 0.3
        capsule["mood"]["confidence"] = 0.5
        write_capsule(capsule)

        snap = _Snapshot(fatigue=0.05, frustration=0.12, confidence=0.93)
        with patch("core.services.mood_oscillator.get_current_mood", return_value="neutral"), \
             patch("core.services.mood_oscillator.get_mood_intensity", return_value=0.07), \
             patch("core.services.emotional_controls.read_emotional_snapshot", return_value=snap):
            sync_capsule_mood()
            result = read_capsule()
            assert result["mood"]["fatigue"] == pytest.approx(0.05)
            assert result["mood"]["frustration"] == pytest.approx(0.12)
            assert result["mood"]["confidence"] == pytest.approx(0.93)
            assert result["mood"]["bearing"] == "neutral"

    def test_sync_preserves_fields_it_does_not_own(self, temp_capsule):
        """Sync maa kun eje de felter den maaler — ikke arousal/dominance."""
        capsule = dict(_EMPTY_CAPSULE)
        capsule["mood"]["arousal"] = 0.42
        capsule["mood"]["dominance"] = 0.61
        write_capsule(capsule)

        snap = _Snapshot(fatigue=0.1, frustration=0.0, confidence=0.9)
        with patch("core.services.mood_oscillator.get_current_mood", return_value="content"), \
             patch("core.services.mood_oscillator.get_mood_intensity", return_value=0.5), \
             patch("core.services.emotional_controls.read_emotional_snapshot", return_value=snap):
            sync_capsule_mood()
            result = read_capsule()
            assert result["mood"]["arousal"] == 0.42
            assert result["mood"]["dominance"] == 0.61
            assert result["mood"]["bearing"] == "content"

    def test_sync_bevarer_felterne_naar_maalingen_fejler(self, temp_capsule):
        """Kan den levende maaling ikke laves, bevares vaerdien — ikke et gaet."""
        capsule = dict(_EMPTY_CAPSULE)
        capsule["mood"]["fatigue"] = 0.37
        write_capsule(capsule)

        with patch("core.services.mood_oscillator.get_current_mood", return_value="neutral"), \
             patch("core.services.mood_oscillator.get_mood_intensity", return_value=0.2), \
             patch("core.services.emotional_controls.read_emotional_snapshot",
                   side_effect=RuntimeError("boom")):
            sync_capsule_mood()
            result = read_capsule()
            assert result["mood"]["fatigue"] == 0.37
            assert result["mood"]["bearing"] == "neutral"

    def test_sync_returns_none_on_failure(self, temp_capsule):
        """Sync should return None if mood_oscillator fails."""
        with patch("core.services.mood_oscillator.get_current_mood", side_effect=Exception("boom")):
            result = sync_capsule_mood()
            assert result is None

    def test_sync_creates_capsule_if_missing(self, temp_capsule):
        """Sync should create a capsule if none exists."""
        from core.services import continuity as cont
        assert not cont.CAPSULE_CURRENT.exists()
        with patch("core.services.mood_oscillator.get_current_mood", return_value="euphoric"), \
             patch("core.services.mood_oscillator.get_mood_intensity", return_value=0.9):
            sync_capsule_mood()
            assert cont.CAPSULE_CURRENT.exists()
            capsule = read_capsule()
            assert capsule["mood"]["bearing"] == "euphoric"