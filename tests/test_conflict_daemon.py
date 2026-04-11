from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittest.mock import patch
from datetime import UTC, datetime, timedelta
import apps.api.jarvis_api.services.conflict_daemon as cd


def _reset():
    cd._cached_conflict = ""
    cd._cached_conflict_at = None
    cd._conflict_type = ""
    cd._last_snapshot = {}


def test_no_conflict_without_tension():
    """When no conflict rules trigger, no generation occurs."""
    _reset()
    snapshot = {
        "energy_level": "medium",
        "inner_voice_mode": "work-steady",
        "pending_proposals_count": 0,
        "latest_fragment": "",
        "last_surprise": "",
        "last_surprise_at": "",
        "fragment_count": 0,
    }
    result = cd.tick_conflict_daemon(snapshot)
    assert result["generated"] is False
    assert cd._cached_conflict == ""


def test_energy_impulse_conflict_detected():
    """Low energy + pending proposals triggers energy_impulse conflict."""
    _reset()
    snapshot = {
        "energy_level": "lav",
        "inner_voice_mode": "work-steady",
        "pending_proposals_count": 2,
        "latest_fragment": "Vil gerne undersøge noget.",
        "last_surprise": "",
        "last_surprise_at": "",
        "fragment_count": 3,
    }
    with patch.object(cd, "_generate_conflict_phrase", return_value="En del af mig vil handle, men kroppen er udmattet."):
        with patch.object(cd, "_store_conflict"):
            result = cd.tick_conflict_daemon(snapshot)
    assert result["generated"] is True
    assert result["conflict_type"] == "energy_impulse"


def test_mode_thought_conflict_detected():
    """Rest mode + non-empty thought fragment triggers mode_thought conflict."""
    _reset()
    snapshot = {
        "energy_level": "medium",
        "inner_voice_mode": "rest",
        "pending_proposals_count": 0,
        "latest_fragment": "Tankerne flyder stadig.",
        "last_surprise": "",
        "last_surprise_at": "",
        "fragment_count": 5,
    }
    with patch.object(cd, "_generate_conflict_phrase", return_value="Noget i mig ønsker ro, men tankerne vil ikke stilne."):
        with patch.object(cd, "_store_conflict"):
            result = cd.tick_conflict_daemon(snapshot)
    assert result["generated"] is True
    assert result["conflict_type"] == "mode_thought"


def test_surprise_unprocessed_conflict_detected():
    """Recent surprise + no thought fragments triggers surprise_unprocessed conflict."""
    _reset()
    recent = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    snapshot = {
        "energy_level": "medium",
        "inner_voice_mode": "work-steady",
        "pending_proposals_count": 0,
        "latest_fragment": "",
        "last_surprise": "Noget overraskede mig.",
        "last_surprise_at": recent,
        "fragment_count": 0,
    }
    with patch.object(cd, "_generate_conflict_phrase", return_value="Noget overraskede mig, men jeg har endnu ikke behandlet det."):
        with patch.object(cd, "_store_conflict"):
            result = cd.tick_conflict_daemon(snapshot)
    assert result["generated"] is True
    assert result["conflict_type"] == "surprise_unprocessed"


def test_cooldown_prevents_repeat():
    """Conflict not regenerated within 10 minutes of last generation."""
    _reset()
    cd._cached_conflict_at = datetime.now(UTC) - timedelta(minutes=5)
    snapshot = {
        "energy_level": "lav",
        "inner_voice_mode": "work-steady",
        "pending_proposals_count": 3,
        "latest_fragment": "Vil gerne handle.",
        "last_surprise": "",
        "last_surprise_at": "",
        "fragment_count": 2,
    }
    result = cd.tick_conflict_daemon(snapshot)
    assert result["generated"] is False


def test_store_called_on_conflict():
    """_store_conflict is called when conflict is detected."""
    _reset()
    snapshot = {
        "energy_level": "lav",
        "inner_voice_mode": "work-steady",
        "pending_proposals_count": 1,
        "latest_fragment": "",
        "last_surprise": "",
        "last_surprise_at": "",
        "fragment_count": 0,
    }
    with patch.object(cd, "_generate_conflict_phrase", return_value="Konflikt."):
        with patch.object(cd, "_store_conflict") as mock_store:
            cd.tick_conflict_daemon(snapshot)
    mock_store.assert_called_once()


def test_build_surface_structure():
    """build_conflict_surface returns expected keys."""
    _reset()
    surface = cd.build_conflict_surface()
    assert "last_conflict" in surface
    assert "conflict_type" in surface
    assert "generated_at" in surface
