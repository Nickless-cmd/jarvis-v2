"""Tests for continuity capsule mood sync from mood_oscillator."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch
from core.services.continuity import (
    sync_capsule_mood,
    read_capsule,
    write_capsule,
    CAPSULE_CURRENT,
    CAPSULE_DIR,
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

    def test_sync_preserves_other_mood_fields(self, temp_capsule):
        """Sync should not overwrite mood fields it doesn't touch."""
        # Write a capsule with existing fatigue
        capsule = dict(_EMPTY_CAPSULE)
        capsule["mood"]["fatigue"] = 0.8
        capsule["mood"]["frustration"] = 0.3
        write_capsule(capsule)

        with patch("core.services.mood_oscillator.get_current_mood", return_value="content"), \
             patch("core.services.mood_oscillator.get_mood_intensity", return_value=0.5):
            sync_capsule_mood()
            result = read_capsule()
            assert result["mood"]["fatigue"] == 0.8
            assert result["mood"]["frustration"] == 0.3
            assert result["mood"]["bearing"] == "content"

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