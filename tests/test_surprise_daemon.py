from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittest.mock import patch
import apps.api.jarvis_api.services.surprise_daemon as sd


def _reset():
    sd._mode_history.clear()
    sd._energy_history.clear()
    sd._cached_surprise = ""
    sd._cached_surprise_at = None
    sd._heartbeats_since_surprise = 0


def test_no_surprise_on_short_history():
    _reset()
    result = sd.tick_surprise_daemon("searching", "medium")
    assert result["generated"] is False


def test_no_surprise_during_cooldown():
    _reset()
    sd._mode_history[:] = ["work-steady"] * 9
    sd._energy_history[:] = ["medium"] * 9
    sd._heartbeats_since_surprise = 3
    with patch.object(sd, "_compute_divergence", return_value=["mode:work-steady→searching"]):
        result = sd.tick_surprise_daemon("searching", "medium")
    assert result["generated"] is False


def test_surprise_on_mode_divergence():
    _reset()
    sd._mode_history[:] = ["work-steady"] * 9
    sd._energy_history[:] = ["medium"] * 9
    sd._heartbeats_since_surprise = 10
    with patch.object(sd, "_generate_surprise", return_value="Det overraskede mig at skifte mode."):
        with patch.object(sd, "_store_surprise"):
            result = sd.tick_surprise_daemon("searching", "medium")
    assert result["generated"] is True


def test_cache_returned_when_no_divergence():
    _reset()
    sd._cached_surprise = "En gammel overraskelse."
    sd._mode_history[:] = ["work-steady"] * 9
    sd._energy_history[:] = ["medium"] * 9
    sd._heartbeats_since_surprise = 10
    with patch.object(sd, "_compute_divergence", return_value=[]):
        result = sd.tick_surprise_daemon("work-steady", "medium")
    assert result["generated"] is False
    assert result["surprise"] == "En gammel overraskelse."


def test_compute_divergence_detects_mode_change():
    _reset()
    sd._mode_history[:] = ["work-steady"] * 6
    divergence = sd._compute_divergence("searching", "medium")
    assert any("mode" in d for d in divergence)


def test_compute_divergence_detects_energy_jump():
    _reset()
    sd._energy_history[:] = ["høj", "høj", "høj", "høj", "lav"]
    divergence = sd._compute_divergence("work-steady", "udmattet")
    assert any("energy" in d for d in divergence)


def test_private_brain_record_written_on_store():
    _reset()
    with patch("apps.api.jarvis_api.services.surprise_daemon.insert_private_brain_record") as mock_insert:
        sd._store_surprise("Jeg blev overrasket.", ["mode:work-steady→searching"])
    mock_insert.assert_called_once()
    kwargs = mock_insert.call_args[1]
    assert kwargs["record_type"] == "self-surprise"
    assert kwargs["summary"] == "Jeg blev overrasket."
